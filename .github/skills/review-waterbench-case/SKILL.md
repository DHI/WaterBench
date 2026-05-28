---
name: review-waterbench-case
description: Review a WaterBench case repository against the canonical structure spec at STRUCTURE.md. Produces a markdown findings report covering directory layout, controlled vocabulary, README conventions, the observation contract (for model-based cases) — `.dfs0` observation data, a variable-agnostic `stations.csv` manifest with explicit CRS, and manifest↔data referential integrity — and model-setup runnability, i.e. whether the model file references inputs at paths that actually exist in the repo. Read-only — does not modify, push, or open issues.
license: MIT
allowed-tools: shell
---

# review-waterbench-case

Review a WaterBench case repository against the canonical [WaterBench Structure spec](../../../STRUCTURE.md). This skill is **read-only**: it inspects, it does not change, push, or open issues.

The checks are implemented in Python ([`review_case.py`](review_case.py)) so the skill runs identically on **Windows, macOS, and Linux** — no POSIX shell tools (`sed`/`awk`/`grep`) are required. The only hard dependency is Python 3 (standard library). `mikeio` is **optional**: when importable, the checker additionally opens each observation `.dfs0` and validates its EUM item type + unit; when absent, it falls back to name-based checks and says so in the report.

## Inputs

A single argument: the path to a cloned WaterBench case repository. If no path is given, the checker defaults to the current working directory.

```
/review-waterbench-case /path/to/WaterBench-MIKE21HD-SomeCase
```

## Output

A markdown findings report, written to stdout, with **Summary**, **MUST**, **SHOULD**, and **NOTE** sections. Findings are graded:

- **MUST** — must be fixed for the next release.
- **SHOULD** — should be fixed when convenient.
- **NOTE** — informational; needs human judgment.

## Procedure

The checks are deterministic and live in [`review_case.py`](review_case.py), which applies the rules in [STRUCTURE.md](../../../STRUCTURE.md). Run the script and present its output — do not re-implement the checks by hand.

### Step 1 — Run the checker

From the skill directory:

```
python3 review_case.py --repo /path/to/WaterBench-MIKE21HD-SomeCase
```

On Windows, use `python` instead of `python3`. With no `--repo`, the checker reviews the current directory. Its stdout is the complete findings report.

### Step 2 — (Optional) enable `.dfs0` content checks

`mikeio` is optional but recommended — with it, the checker confirms each observation `.dfs0` is a readable dfs0 carrying a real EUM item type (§8.1/§8.4), not just that the filename ends in `.dfs0`. To enable:

```
python3 -m pip install mikeio
```

Anyone consuming a WaterBench case already needs `mikeio` to read the model output, so this is not a new dependency for a real reviewer.

### Step 3 — Present the report

The script's stdout **is** the report — relay it. Do **not** add findings beyond what the checker produced. The report header states whether `mikeio` was available, so the reader knows whether `.dfs0` content was verified or only the filenames.

## What the checker verifies

| Spec  | Check |
| ----- | ----- |
| §2    | `README.md`, `LICENSE` (canonical name, not `license.txt` etc.), `code/`; no top-level data sprawl. |
| §3    | Required directories by family; MIKE SHE `model/`-in-`input/` exception. |
| §4.1  | Forbidden top-level directory synonyms (`measurements/`, `notebooks/`, …). |
| §8.1  | Observation time series is `.dfs0`; only `stations.csv` may be `.csv`. |
| §8.3  | A single **variable-agnostic** `stations.csv` with an explicit `crs` column and a station-id column; `vertical_datum` for water level; no per-variable manifests (`current_stations.csv`, `stations_<var>.csv`). |
| §8.4  | With `mikeio`: each observation `.dfs0` opens and carries a real EUM item type. |
| §8.5  | Bidirectional referential integrity — every manifest row has a `.dfs0`, every `.dfs0` has a manifest row. |
| §5    | README sections and sub-directory READMEs. |
| §7    | Model-setup runnability — input paths are relative and resolve to files that exist (via `extract_model_paths`). |
| §6    | Publishing artifacts under `.publish/` and a README→PDF workflow. |
| §9    | Archives at the repo root; large top-level `output/`. |

To change a rule, edit `review_case.py` **and** STRUCTURE.md (the source of truth) — not this document. The bundled [`extract_model_paths.py`](extract_model_paths.py) remains the model-setup path extractor and is imported by the checker.

## What this skill does NOT do

- It does not modify files, rename directories, or commit anything.
- It does not open GitHub issues or PRs.
- It does not run the MIKE model — runnability is checked statically by path resolution, not by simulation.
- It does not validate the *correctness of values*. It checks that observation data is `.dfs0`, that `stations.csv` declares the required columns (`crs`, station id), and that the manifest and `.dfs0` files reference each other (§8) — but it does **not** verify that a declared unit, coordinate, CRS, or datum is actually *right*, that EUM item types are sensible, or that time coverage is adequate. Those need a domain reviewer.
