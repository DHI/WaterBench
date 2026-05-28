#!/usr/bin/env python3
"""Review a WaterBench case repository against STRUCTURE.md.

Cross-platform: pure Python standard library, with an OPTIONAL `mikeio`
dependency used only to validate `.dfs0` content (EUM item type + unit). Runs
identically on Windows, macOS, and Linux — no POSIX shell tools required.

Usage:

    python3 review_case.py --repo /path/to/WaterBench-MIKE21HD-SomeCase

Emits a markdown findings report to stdout. This script is the deterministic
application of the spec in STRUCTURE.md; it is read-only and changes nothing.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Reuse the model-setup path extractor that ships alongside this skill.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_model_paths import (  # noqa: E402
    HEADER_RE,
    PATH_RE,
    classify,
    is_absolute,
    resolve,
)

# mikeio is OPTIONAL. When present we validate .dfs0 content; when absent we
# fall back to extension checks and emit a NOTE so the reviewer knows content
# was not verified.
try:
    import mikeio  # type: ignore

    HAVE_MIKEIO = True
except Exception:  # pragma: no cover - environment dependent
    HAVE_MIKEIO = False


MODEL_FAMILIES = {"MIKE21HD", "MIKE3HD", "MIKE21SW", "MIKESHE", "MIKEplus"}
DATA_FAMILIES = {"TimeSeries", "WD"}

# §4.1 forbidden top-level directory synonyms -> canonical name.
FORBIDDEN_DIRS = {
    "measurements": "observations/",
    "obs": "observations/",
    "gauges": "observations/",
    "sensors": "observations/",
    "notebooks": "code/",
    "scripts": "code/",
    "src": "code/",
    "analysis": "code/",
    "plots": "figures/",
    "images": "figures/",
    "img": "figures/",
    "sample_output": "output_sample/",
    "outputs": "output_sample/",
    "results": "output_sample/",
    "data_sample": "output_sample/",
    "inputs": "input/",
    "forcing": "input/",
    "bc": "input/",
    "setup": "model/",
    "simulation": "model/",
    "dataset": "data/",
    "derived": "processed/",
    "prepared": "processed/",
    "intermediate": "processed/",
}

FORBIDDEN_LICENSE = ("license.txt", "License", "LICENSE.md", "COPYING")

# §5 canonical README sections (order matters only for NOTE-level checks).
README_SECTIONS = [
    "Disclaimer",
    "Intended Use",
    "Folder Structure",
    "Case Description",
    "Model Setup",
    "Validation",
    "Data Sources",
]

SUBDIR_READMES = [
    "code",
    "input",
    "model",
    "observations",
    "output_sample",
    "figures",
    ".preprocessing",
    ".publish",
]


@dataclass
class Report:
    findings: list[tuple[str, str]] = field(default_factory=list)

    def must(self, msg: str) -> None:
        self.findings.append(("MUST", msg))

    def should(self, msg: str) -> None:
        self.findings.append(("SHOULD", msg))

    def note(self, msg: str) -> None:
        self.findings.append(("NOTE", msg))

    def of(self, sev: str) -> list[str]:
        return [m for s, m in self.findings if s == sev]


def detect_family(repo: Path) -> tuple[str, bool]:
    """Return (family, is_model_based). Falls back to content detection."""
    m = re.match(r"WaterBench-([^-]+)-", repo.name)
    fam = m.group(1) if m else None
    if fam in MODEL_FAMILIES:
        return fam, True
    if fam in DATA_FAMILIES:
        return fam, False
    # Content-based fallback when the directory is not named WaterBench-*.
    model_based = (repo / "model").is_dir() or any(
        next(repo.rglob(pat), None)
        for pat in ("*.m21fm", "*.m3fm", "*.sw", "*.she", "*.mupp")
    )
    return fam or "Other", bool(model_based)


def check_universal_core(repo: Path, rep: Report) -> None:
    """§2 — README.md, LICENSE, code/, and no top-level data sprawl."""
    if not (repo / "README.md").exists():
        rep.must("Missing required file: README.md (§2)")
    if not (repo / "LICENSE").is_file():
        found = next((n for n in FORBIDDEN_LICENSE if (repo / n).exists()), None)
        if found:
            rep.must(
                f"License filename is '{found}' — canonical name is 'LICENSE' (uppercase, no extension) (§4.2)"
            )
        else:
            rep.must("Missing required file: LICENSE (§2)")
    if not (repo / "code").is_dir():
        rep.must("Missing required directory: code/ (§2)")

    for f in repo.iterdir():
        if not f.is_file():
            continue
        suffix = f.suffix.lower()
        if suffix in (".csv", ".parquet", ".zip") or ".dfs" in suffix:
            rep.must(
                f"Top-level data sprawl: {f.name} belongs inside a domain directory (§2/§9)"
            )


def check_addendum(repo: Path, family: str, model_based: bool, rep: Report) -> None:
    """§3 — required directories by family."""
    if model_based:
        required = [
            "model",
            "input",
            "output_sample",
            "observations",
            "figures",
            ".preprocessing",
            ".publish",
        ]
        she_split = (
            family == "MIKESHE"
            and not (repo / "model").is_dir()
            and (repo / "input").is_dir()
            and any((repo / "input").rglob("*.she"))
        )
        for d in required:
            if d == "model" and she_split:
                continue  # MIKESHE may keep the model under input/
            if not (repo / d).is_dir():
                rep.must(f"Missing required directory: {d}/ (§3.1)")
    else:
        if not (repo / "observations").is_dir() and not (repo / "data").is_dir():
            rep.must("Data-only case must contain observations/ or data/ (§3.2)")
        for d in ("processed", "figures", ".publish"):
            if not (repo / d).is_dir():
                rep.should(f"Data-only case should contain {d}/ (§3.2)")


def check_vocabulary(repo: Path, rep: Report) -> None:
    """§4.1 — forbidden top-level directory synonyms."""
    for d in repo.iterdir():
        if not d.is_dir():
            continue
        canonical = FORBIDDEN_DIRS.get(d.name)
        if canonical:
            rep.must(
                f"Forbidden synonym at top level: {d.name}/ (canonical: {canonical}) (§4.1)"
            )


def check_observations(repo: Path, rep: Report) -> None:
    """§8 — observation contract (model-based cases)."""
    obs = repo / "observations"
    if not obs.is_dir():
        return  # absence is handled by the §3 addendum check

    # §8.1 / §8.3 — format and manifest naming.
    for csv_file in obs.glob("*.csv"):
        name = csv_file.name
        if name == "stations.csv":
            continue
        if "stations" in name:
            rep.must(
                f"Variable-encoded station manifest: observations/{name} "
                "(use one variable-agnostic stations.csv; variable lives in the .dfs0 items) (§8.3)"
            )
        else:
            rep.must(
                f"Observation data in non-.dfs0 format: observations/{name} "
                "(observation time series MUST be .dfs0; only stations.csv may be .csv) (§8.1)"
            )

    manifest = obs / "stations.csv"
    station_ids: list[str] = []
    if manifest.exists():
        header, rows = _read_csv(manifest)
        norm = [h.strip().lower() for h in header]
        if "crs" not in norm:
            rep.must(
                "stations.csv declares no 'crs' column (CRS MUST be explicit — no implicit WGS84) (§8.3)"
            )
        id_col = next(
            (i for i, h in enumerate(norm) if h in ("station_id", "station")), None
        )
        if id_col is None:
            rep.must(
                "stations.csv has no station-id column ('station_id' or 'station') (§8.3)"
            )
        else:
            station_ids = [
                r[id_col].strip() for r in rows if len(r) > id_col and r[id_col].strip()
            ]
        if "vertical_datum" not in norm:
            rep.should(
                "stations.csv has no 'vertical_datum' column (required for water-level stations) (§8.3)"
            )
    else:
        rep.must("observations/ has no stations.csv manifest (§8.3)")

    # §8.5 — bidirectional referential integrity (manifest row <-> .dfs0 file).
    dfs0_stems = {
        p.stem for p in obs.glob("*.dfs0") if not p.name.startswith("Altimetry_")
    }
    for sid in station_ids:
        if not (obs / f"{sid}.dfs0").exists():
            rep.must(
                f"Orphan station: '{sid}' in stations.csv has no observations/{sid}.dfs0 (§8.5)"
            )
    if manifest.exists():
        id_set = set(station_ids)
        for stem in sorted(dfs0_stems):
            if stem not in id_set:
                rep.must(
                    f"Orphan data file: observations/{stem}.dfs0 has no row in stations.csv (§8.5)"
                )

    # §8.1 / §8.4 — content: each .dfs0 carries EUM item type + unit. Needs mikeio.
    _check_dfs0_content(obs, rep)


def _check_dfs0_content(obs: Path, rep: Report) -> None:
    dfs0_files = sorted(obs.glob("*.dfs0"))
    if not dfs0_files:
        return
    if not HAVE_MIKEIO:
        rep.note(
            f"mikeio not installed: {len(dfs0_files)} observation .dfs0 file(s) "
            "checked by name only; EUM item type/unit content not verified (§8.1/§8.4)"
        )
        return
    for f in dfs0_files:
        try:
            ds = mikeio.read(str(f))
        except Exception as exc:  # noqa: BLE001
            rep.must(f"observations/{f.name} is not a readable .dfs0: {exc} (§8.1)")
            continue
        for item in ds.items:
            type_name = getattr(item.type, "name", str(item.type))
            if "Undefined" in type_name:
                rep.should(
                    f"observations/{f.name}: item '{item.name}' has Undefined EUM type "
                    "(observation variables should carry a real EUM item type) (§8.4)"
                )


def check_readme(repo: Path, rep: Report) -> None:
    """§5 — top-level README sections and sub-directory READMEs."""
    readme = repo / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="ignore")
        headings = re.findall(r"^#+\s+(.+?)\s*$", text, re.MULTILINE)
        joined = "\n".join(headings).lower()
        for section in README_SECTIONS:
            if section.lower() not in joined:
                rep.should(f"README.md missing recommended section: {section} (§5)")
    for sub in SUBDIR_READMES:
        d = repo / sub
        if d.is_dir() and not (d / "README.md").exists():
            rep.should(f"Sub-directory has no README.md: {sub}/ (§5.1)")


def check_runnability(repo: Path, family: str, rep: Report) -> None:
    """§7 — model setup references inputs by resolvable relative paths."""
    search_root = repo if family == "MIKESHE" else (repo / "model")
    if not search_root.exists():
        return
    setups: list[Path] = []
    for ext in ("*.m21fm", "*.m3fm", "*.sw", "*.she", "*.mupp"):
        setups.extend(search_root.rglob(ext))
    for setup in sorted(set(setups)):
        try:
            text = setup.read_text(encoding="utf-8", errors="strict")
        except UnicodeDecodeError:
            rep.note(
                f"Setup file not UTF-8 text ({setup.name}); runnability not verified (§7)"
            )
            continue
        section: str | None = None
        seen: set[tuple[str, str]] = set()
        for line in text.splitlines():
            hm = HEADER_RE.match(line)
            if hm:
                section = hm.group(1)
                continue
            for pm in PATH_RE.finditer(line):
                raw = pm.group(1).strip()
                if not raw or (raw, section or "") in seen:
                    continue
                seen.add((raw, section or ""))
                if is_absolute(raw):
                    rep.must(
                        f"Absolute path in {setup.name}: {raw}; setup is not portable (§7)"
                    )
                    continue
                resolves_to, exists = resolve(raw, setup, repo)
                if exists is False:
                    if classify(section) == "output":
                        rep.note(
                            f"{setup.name}: output destination {raw} does not exist "
                            "(created at run time; verify path) (§7)"
                        )
                    else:
                        rep.must(
                            f"{setup.name} references missing input: {raw} "
                            f"(expected at {resolves_to}) (§7)"
                        )


def check_publishing(repo: Path, rep: Report) -> None:
    """§6 — publishing workflow artifacts (SHOULD)."""
    pub = repo / ".publish"
    if pub.is_dir():
        if not (pub / "zip_repo.py").exists():
            rep.should(".publish/zip_repo.py is missing (§6)")
        if not (pub / "zenodo_text.md").exists():
            rep.should(".publish/zenodo_text.md is missing (§6)")
    wf = repo / ".github" / "workflows"
    if not (wf.is_dir() and any(wf.glob("*.y*ml"))):
        rep.should(
            "No GitHub Actions workflow under .github/workflows/ (README->PDF render) (§6)"
        )


def check_anti_patterns(repo: Path, rep: Report) -> None:
    """§9 — archives at the root, large top-level output/."""
    for f in repo.glob("*.zip"):
        rep.must(f"Archive at repo root: {f.name} — belongs in .publish/ (§9)")
    out = repo / "output"
    if out.is_dir() and any(p.is_file() for p in out.rglob("*")):
        rep.note(
            "Top-level output/ contains files — published cases must ship only output_sample/ (§9)"
        )


def _read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8", errors="ignore") as fh:
        reader = list(csv.reader(fh))
    if not reader:
        return [], []
    return reader[0], reader[1:]


def render(repo: Path, family: str, model_based: bool, rep: Report) -> str:
    must, should, note = rep.of("MUST"), rep.of("SHOULD"), rep.of("NOTE")
    kind = "model-based" if model_based else "data-only"
    lines = [
        f"# WaterBench Review: {repo.name}",
        "",
        f"**Case family detected:** {family} ({kind})",
        f"**EUM content check:** {'mikeio available' if HAVE_MIKEIO else 'mikeio NOT installed — .dfs0 content unverified'}",
        f"**Total findings:** {len(must)} MUST, {len(should)} SHOULD, {len(note)} NOTE",
        "",
        f"## MUST ({len(must)})",
        *([f"- {m}" for m in must] or ["- none"]),
        "",
        f"## SHOULD ({len(should)})",
        *([f"- {m}" for m in should] or ["- none"]),
        "",
        f"## NOTE ({len(note)})",
        *([f"- {m}" for m in note] or ["- none"]),
        "",
        "## Summary",
    ]
    if must:
        lines.append(f"{len(must)} blocking issue(s) must be fixed before publishing.")
    elif should:
        lines.append(
            "No blocking issues; some conventions to tidy on the next release."
        )
    else:
        lines.append(
            "Conforms to STRUCTURE.md as checked. (Value-correctness still needs a domain reviewer.)"
        )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Review a WaterBench case against STRUCTURE.md."
    )
    ap.add_argument(
        "--repo", default=".", help="Path to a cloned WaterBench case repository"
    )
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"error: not a directory: {repo}", file=sys.stderr)
        return 2

    family, model_based = detect_family(repo)
    rep = Report()

    check_universal_core(repo, rep)
    check_addendum(repo, family, model_based, rep)
    check_vocabulary(repo, rep)
    if model_based:
        check_observations(repo, rep)
        check_runnability(repo, family, rep)
    check_readme(repo, rep)
    check_publishing(repo, rep)
    check_anti_patterns(repo, rep)

    print(render(repo, family, model_based, rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
