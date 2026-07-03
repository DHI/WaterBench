#!/usr/bin/env python3
"""Extract file-path references from a MIKE model setup file and check resolution.

Used by the `review-waterbench-case` skill. Reads a MIKE setup file (`.m21fm`,
`.sw`, `.she`, etc. — anything text-based using the MIKE pipe-delimited
`file_name = |path|` convention) and emits one JSON object per reference to
stdout.

Each emitted object has:

    path          The raw path as it appears in the setup file (back-slashes preserved).
    kind          'input' if the reference appears in an input/forcing/mesh/initial section,
                  'output' if it appears in an output section, 'unknown' otherwise.
    absolute      True if the path is absolute (drive letter, UNC, or leading /).
    resolves_to   The path normalized relative to the repo root (POSIX separators),
                  or null if it could not be resolved (e.g. escapes the repo root).
    exists        Whether resolves_to exists in the repo. Null when resolves_to is null.

For unsupported (non-text / binary) setup files the script writes a single object:

    {"unsupported": true, "reason": "<message>"}

and exits 0.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PATH_RE = re.compile(r"= \|([^|]+)\|")

# Header lines we walk past to track the current "section" context. Mike setup
# files use bracketed section headers like [INITIAL_CONDITIONS] or
# [OUTPUT_1]. We track the last header seen and use it to label each path as
# input vs output.
HEADER_RE = re.compile(r"^\s*\[([A-Z0-9_]+)\]\s*$")

OUTPUT_HINTS = ("OUTPUT", "RESULT")


def classify(section: str | None) -> str:
    """Classify a MIKE setup section as 'input' or 'output'.

    MIKE setup files have hundreds of distinct section names (CODE_2,
    SMAGORINSKY_FORMULATION, MANNING_NUMBER, OUTPUT_1, ...). Only the output
    sections are reliably named — everything else is some form of input. So we
    treat anything containing OUTPUT_HINTS as output and default the rest to
    input. Sections with no header context (e.g. top-of-file lines) fall back
    to 'input' too, which biases the report toward flagging missing files as
    blocking (MUST) rather than informational (NOTE).
    """
    if section is None:
        return "input"
    if any(h in section for h in OUTPUT_HINTS):
        return "output"
    return "input"


def is_absolute(raw: str) -> bool:
    """Return True for Windows drive paths, UNC paths, and Unix absolute paths."""
    if len(raw) >= 2 and raw[1] == ":":
        return True
    if raw.startswith("\\\\") or raw.startswith("//"):
        return True
    if raw.startswith("/"):
        return True
    return False


def resolve(raw: str, setup_path: Path, repo: Path) -> tuple[str | None, bool | None]:
    """Resolve a setup-file path relative to the setup file's directory.

    Returns (resolves_to, exists). `resolves_to` is a POSIX relative path from
    the repo root, or None if the path escapes the repo root.
    """
    norm = raw.replace("\\", "/")
    candidate = (setup_path.parent / norm).resolve()
    try:
        rel = candidate.relative_to(repo.resolve())
    except ValueError:
        return None, None
    return rel.as_posix(), candidate.exists()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", required=True, help="Path to the WaterBench repository root")
    ap.add_argument(
        "--setup",
        required=True,
        help="Path to the model setup file (.m21fm/.sw/.she/etc.)",
    )
    args = ap.parse_args()

    repo = Path(args.repo)
    setup = Path(args.setup)

    if not setup.exists():
        print(json.dumps({"unsupported": True, "reason": f"Setup file not found: {setup}"}))
        return 0

    try:
        text = setup.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        print(
            json.dumps(
                {
                    "unsupported": True,
                    "reason": f"Setup file is not UTF-8 text: {setup.name} — runnability not verified",
                }
            )
        )
        return 0

    section: str | None = None
    seen: set[tuple[str, str]] = set()

    for line in text.splitlines():
        m = HEADER_RE.match(line)
        if m:
            section = m.group(1)
            continue
        for pmatch in PATH_RE.finditer(line):
            raw = pmatch.group(1).strip()
            if not raw:
                continue
            # de-duplicate identical (path, section) pairs — MIKE setups can
            # repeat the same file under multiple boundary/forcing groups
            key = (raw, section or "")
            if key in seen:
                continue
            seen.add(key)

            kind = classify(section)
            absolute = is_absolute(raw)
            if absolute:
                resolves_to, exists = None, None
            else:
                resolves_to, exists = resolve(raw, setup, repo)

            print(
                json.dumps(
                    {
                        "path": raw,
                        "section": section,
                        "kind": kind,
                        "absolute": absolute,
                        "resolves_to": resolves_to,
                        "exists": exists,
                    }
                )
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
