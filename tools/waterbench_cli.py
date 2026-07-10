#!/usr/bin/env python3
"""Draft WaterBench CLI for internal DHI usage.

Implements a small command set inspired by issue #15:
- list: enumerate known WaterBench cases
- info <case>: print case metadata and description
- download <case> [target]: download mirrored files from Azure Blob Storage
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

AZURE_CONTAINER_URL = "https://dhiwaterbench.blob.core.windows.net/waterbench"
RAW_INDEX_URL = "https://raw.githubusercontent.com/DHI/WaterBench/main/index.qmd"


@dataclass(frozen=True)
class CaseInfo:
    name: str
    case_type: str
    description: str
    zenodo_url: str
    github_url: str


def _read_index_text(index_file: str | None) -> str:
    if index_file:
        path = Path(index_file)
        if not path.exists():
            raise FileNotFoundError(f"Index file not found: {path}")
        return path.read_text(encoding="utf-8")

    local = Path(__file__).resolve().parents[1] / "index.qmd"
    if local.exists():
        return local.read_text(encoding="utf-8")

    with urllib.request.urlopen(RAW_INDEX_URL) as response:
        return response.read().decode("utf-8")


def _extract_links(cell_text: str) -> tuple[str, str]:
    doi_match = re.search(r"https?://doi\.org/[^)\]\s]+", cell_text)
    zenodo_match = re.search(r"https?://zenodo\.org/[^)\]\s]+", cell_text)
    github_match = re.search(r"https?://github\.com/[^)\]\s]+", cell_text)

    zenodo = doi_match.group(0) if doi_match else (zenodo_match.group(0) if zenodo_match else "")
    github = github_match.group(0) if github_match else ""
    return zenodo, github


def _parse_overview_cases(index_text: str) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    in_table = False
    for line in index_text.splitlines():
        striped = line.strip()
        if striped.startswith("| Case | Type | Links |"):
            in_table = True
            continue
        if not in_table:
            continue
        if striped.startswith(":::"):
            break
        if not striped.startswith("|"):
            continue
        if striped.startswith("|------"):
            continue

        match = re.match(
            r"^\|\s*\[([^\]]+)\]\([^)]*\)\s*\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|\s*$",
            striped,
        )
        if not match:
            continue

        name = match.group(1).strip()
        case_type = match.group(2).strip()
        links_cell = match.group(3).strip()
        zenodo, github = _extract_links(links_cell)
        rows.append((name, case_type, zenodo, github))

    return rows


def _parse_case_descriptions(index_text: str) -> dict[str, str]:
    heading_re = re.compile(r"^###\s+([^\n{]+?)\s+\{#[^}]+\}\s*$", re.MULTILINE)
    matches = list(heading_re.finditer(index_text))
    descriptions: dict[str, str] = {}

    for i, match in enumerate(matches):
        case_name = match.group(1).strip()
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(index_text)
        block = index_text[body_start:body_end]
        description = ""
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("[![]("):
                continue
            if line.startswith("![]("):
                continue
            if line.startswith(">"):
                continue
            if line.startswith("---"):
                continue
            description = line
            break
        if description:
            descriptions[case_name] = description

    return descriptions


def load_cases(index_file: str | None = None) -> list[CaseInfo]:
    text = _read_index_text(index_file)
    table_rows = _parse_overview_cases(text)
    descriptions = _parse_case_descriptions(text)
    cases: list[CaseInfo] = []
    for name, case_type, zenodo, github in table_rows:
        cases.append(
            CaseInfo(
                name=name,
                case_type=case_type,
                description=descriptions.get(name, ""),
                zenodo_url=zenodo,
                github_url=github,
            )
        )
    return cases


def _find_case(cases: list[CaseInfo], case_name: str) -> CaseInfo:
    for case in cases:
        if case.name.lower() == case_name.lower():
            return case
    raise KeyError(f"Unknown case: {case_name}")


def _iter_blobs(prefix: str) -> Iterable[str]:
    marker = ""
    while True:
        query = {
            "restype": "container",
            "comp": "list",
            "prefix": prefix,
        }
        if marker:
            query["marker"] = marker
        url = f"{AZURE_CONTAINER_URL}?{urllib.parse.urlencode(query)}"
        with urllib.request.urlopen(url) as response:
            xml_payload = response.read()

        root = ET.fromstring(xml_payload)
        for blob in root.findall("./Blobs/Blob/Name"):
            if blob.text:
                yield blob.text

        next_marker = root.findtext("./NextMarker", default="")
        if not next_marker:
            return
        marker = next_marker


def _case_prefix_candidates(case: CaseInfo) -> list[str]:
    candidates = [case.name]
    if case.github_url:
        repo_name = case.github_url.rstrip("/").split("/")[-1]
        if repo_name.startswith("WaterBench-"):
            candidates.append(repo_name.removeprefix("WaterBench-"))
    # Some mirrors may keep the repository name as the top-level folder.
    if case.github_url:
        candidates.append(case.github_url.rstrip("/").split("/")[-1])

    unique: list[str] = []
    for c in candidates:
        if c and c not in unique:
            unique.append(c)
    return unique


def _safe_relative_blob_path(blob_name: str, prefix_name: str) -> Path:
    parts = PurePosixPath(blob_name).parts
    if not parts:
        raise ValueError(f"Unexpected blob name: {blob_name}")
    if parts[0].lower() != prefix_name.lower():
        raise ValueError(
            f"Blob '{blob_name}' does not belong to requested prefix '{prefix_name}'"
        )

    rel_parts = [p for p in parts[1:] if p not in ("", ".")]
    if any(p == ".." for p in rel_parts):
        raise ValueError(f"Unsafe blob path: {blob_name}")
    return Path(*rel_parts)


def _download_blob(blob_name: str, prefix_name: str, target_root: Path, overwrite: bool) -> Path:
    rel_path = _safe_relative_blob_path(blob_name, prefix_name)
    output_path = target_root / rel_path
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not overwrite:
        return output_path

    blob_url = f"{AZURE_CONTAINER_URL}/{urllib.parse.quote(blob_name, safe='/')}"
    with urllib.request.urlopen(blob_url) as response, output_path.open("wb") as file_obj:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            file_obj.write(chunk)

    return output_path


def cmd_list(args: argparse.Namespace) -> int:
    cases = load_cases(args.index_file)
    for case in cases:
        print(case.name)
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    cases = load_cases(args.index_file)
    try:
        case = _find_case(cases, args.case)
    except KeyError as err:
        print(str(err), file=sys.stderr)
        return 2

    print(f"Case: {case.name}")
    print(f"Type: {case.case_type}")
    if case.description:
        print("")
        print(case.description)
    if case.zenodo_url:
        print("")
        print(f"Zenodo: {case.zenodo_url}")
    if case.github_url:
        print(f"GitHub: {case.github_url}")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    cases = load_cases(args.index_file)
    try:
        case = _find_case(cases, args.case)
    except KeyError as err:
        print(str(err), file=sys.stderr)
        return 2

    resolved_prefix = ""
    blobs: list[str] = []
    for candidate in _case_prefix_candidates(case):
        prefix = f"{candidate}/"
        blobs = list(_iter_blobs(prefix))
        if blobs:
            resolved_prefix = candidate
            break

    if not blobs:
        candidates = ", ".join(_case_prefix_candidates(case))
        print(
            f"No blobs found for '{case.name}'. Tried Azure prefixes: {candidates}",
            file=sys.stderr,
        )
        return 3

    target = Path(args.target).expanduser().resolve() / case.name
    print(f"Found {len(blobs)} files for {case.name}")
    print(f"Azure prefix: {resolved_prefix}")
    print(f"Target: {target}")

    downloaded = 0
    skipped = 0
    for blob_name in blobs:
        rel_path = _safe_relative_blob_path(blob_name, resolved_prefix)
        output_path = target / rel_path
        if output_path.exists() and not args.overwrite:
            skipped += 1
            print(f"skip {rel_path}")
            continue

        if args.dry_run:
            downloaded += 1
            print(f"plan {rel_path}")
            continue

        try:
            _download_blob(blob_name, resolved_prefix, target, args.overwrite)
            downloaded += 1
            print(f"ok   {rel_path}")
        except urllib.error.URLError as err:
            print(f"fail {rel_path}: {err}", file=sys.stderr)
            return 4

    if args.dry_run:
        print(f"Planned: {downloaded}, skipped existing: {skipped}")
    else:
        print(f"Downloaded: {downloaded}, skipped existing: {skipped}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="Waterbench",
        description="Draft WaterBench case downloader CLI.",
    )
    parser.add_argument(
        "--index-file",
        default=None,
        help="Optional path to index.qmd. Defaults to local repo index.qmd, then GitHub main.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List known WaterBench cases")
    list_parser.set_defaults(func=cmd_list)

    info_parser = subparsers.add_parser("info", help="Show metadata about a case")
    info_parser.add_argument("case", help="Case name, for example MIKE21HD-HamburgElbeEstuary")
    info_parser.set_defaults(func=cmd_info)

    download_parser = subparsers.add_parser(
        "download", help="Download a case from the Azure mirror"
    )
    download_parser.add_argument(
        "case", help="Case name, for example MIKE21HD-HamburgElbeEstuary"
    )
    download_parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Target directory where a case folder will be created (default: current directory)",
    )
    download_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be downloaded without writing anything",
    )
    download_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite files that already exist",
    )
    download_parser.set_defaults(func=cmd_download)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        return args.func(args)
    except urllib.error.URLError as err:
        print(f"Network error: {err}", file=sys.stderr)
        return 10
    except ET.ParseError as err:
        print(f"Azure listing parse error: {err}", file=sys.stderr)
        return 11
    except FileNotFoundError as err:
        print(str(err), file=sys.stderr)
        return 12


if __name__ == "__main__":
    raise SystemExit(main())
