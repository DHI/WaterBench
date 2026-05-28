---
name: review-waterbench-case
description: Review a WaterBench case repository against the canonical structure spec at STRUCTURE.md. Produces a markdown findings report covering directory layout, controlled vocabulary, README conventions, the observation contract (for model-based cases) — `.dfs0` observation data, a variable-agnostic `stations.csv` manifest with explicit CRS, and manifest↔data referential integrity — and model-setup runnability, i.e. whether the model file references inputs at paths that actually exist in the repo. Read-only — does not modify, push, or open issues.
license: MIT
allowed-tools: shell
---

# review-waterbench-case

Review a WaterBench case repository against the canonical [WaterBench Structure spec](../../../STRUCTURE.md). This skill is **read-only**: it inspects, it does not change, push, or open issues.

It works in any agent CLI that supports `.github/skills/` or `.claude/skills/` (Claude Code, GitHub Copilot CLI, etc.). It uses only shell and the bundled `extract_model_paths.py` helper — no project-specific tooling.

## Inputs

A single argument: the path to a cloned WaterBench case repository. If no path is given, default to the current working directory.

```
/review-waterbench-case /path/to/WaterBench-MIKE21HD-SomeCase
```

## Output

A markdown findings report, written to stdout. Sections:

1. **Summary** — case family detected, finding counts by severity.
2. **MUST findings** — strict violations of the controlled vocabulary, missing core files, broken model paths.
3. **SHOULD findings** — convention deviations.
4. **NOTE findings** — limitations or things to verify manually.

Findings are graded:

- **MUST** — must be fixed for the next release.
- **SHOULD** — should be fixed when convenient.
- **NOTE** — informational; needs human judgment.

## Procedure

Work through the steps below in order. Read [STRUCTURE.md](../../../STRUCTURE.md) for the source of truth — this skill is the application of that spec, not a duplicate of it.

### Step 1 — Detect the case family

From the repository directory name and contents:

```bash
NAME=$(basename "$REPO")
# extract the family token from the repo name (between "WaterBench-" and the next "-")
FAMILY=$(echo "$NAME" | sed -nE 's/^WaterBench-([^-]+)-.*/\1/p')
```

Map `$FAMILY` to one of: `MIKE21HD`, `MIKE3HD`, `MIKE21SW`, `MIKESHE`, `MIKEplus`, `TimeSeries`, `WD`, or `Other`. Model families (anything starting with `MIKE`) are **model-based**; `TimeSeries` and `WD` are **data-only**.

If the repository directory is not named `WaterBench-*`, fall back to content-based detection: presence of `model/` and `*.m21fm` / `*.sw` / `*.she` / `*.mupp` files indicates model-based.

### Step 2 — Universal core checks (§2 of STRUCTURE.md)

For each of `README.md`, `LICENSE`, `code/`:

```bash
test -e "$REPO/README.md" || finding MUST "Missing required file: README.md"
test -f "$REPO/LICENSE" || finding MUST "Missing required file: LICENSE (canonical name, uppercase, no extension)"
test -d "$REPO/code"   || finding MUST "Missing required directory: code/"
```

Also check for forbidden license variants — if `LICENSE` is missing but `license.txt`, `License`, `LICENSE.md`, or `COPYING` is present, raise a single MUST finding citing the actual name found and the canonical name.

Check absence of top-level data sprawl (any `*.csv`, `*.parquet`, `*.dfs*`, `*.zip` at the repo root) → MUST finding each.

### Step 3 — Family addendum checks (§3)

#### Model-based families

Required directories: `model/`, `input/`, `output_sample/`, `observations/`, `figures/`, `.preprocessing/`, `.publish/`. For each missing, raise a MUST finding.

**Exception:** MIKESHE cases **MAY** omit `model/` if the model is split across `input/` subdirectories. Detect this by checking for absence of `model/` AND presence of `*.she` files anywhere under `input/`.

**Observation contract (§8)** — model-based cases. Run these checks against `observations/`:

```bash
OBS="$REPO/observations"

# §8.1 — observation time series MUST be .dfs0; the only permitted .csv is the manifest.
for f in "$OBS"/*.csv; do
  [ -e "$f" ] || continue
  base=$(basename "$f")
  [ "$base" = "stations.csv" ] && continue            # the manifest — allowed
  case "$base" in
    *stations*.csv) finding MUST "Variable-encoded station manifest: observations/$base (use one variable-agnostic stations.csv; variable lives in the .dfs0 items — §8.3)" ;;
    *)              finding MUST "Observation data in non-.dfs0 format: observations/$base (observation time series MUST be .dfs0; only stations.csv may be .csv — §8.1)" ;;
  esac
done

# §8.3 — the manifest must exist and declare an explicit CRS and a station id (no implicit WGS84).
if [ -f "$OBS/stations.csv" ]; then
  hdr=$(head -1 "$OBS/stations.csv" | tr 'A-Z' 'a-z' | tr -d ' ')
  echo "$hdr" | grep -qE '(^|,)crs(,|$)'                || finding MUST "stations.csv declares no 'crs' column (CRS MUST be explicit — no implicit WGS84 — §8.3)"
  echo "$hdr" | grep -qE '(^|,)(station_id|station)(,|$)' || finding MUST "stations.csv has no station-id column (§8.3)"
  echo "$hdr" | grep -qE '(^|,)vertical_datum(,|$)'     || finding SHOULD "stations.csv has no 'vertical_datum' column (required for water-level stations — §8.3)"
elif [ -d "$OBS" ]; then
  finding MUST "observations/ has no stations.csv manifest (§8.3)"
fi

# §8.5 — referential integrity, both directions: stations.csv rows <-> .dfs0 files.
if [ -f "$OBS/stations.csv" ]; then
  ids=$(awk -F, 'NR==1{for(i=1;i<=NF;i++){h=tolower($i);gsub(/ /,"",h);if(h=="station_id"||h=="station")c=i}} NR>1&&c{gsub(/[[:space:]]/,"",$c);if($c!="")print $c}' "$OBS/stations.csv")
  for id in $ids; do
    [ -e "$OBS/$id.dfs0" ] || finding MUST "Orphan station: '$id' in stations.csv has no observations/$id.dfs0 (§8.5)"
  done
  for f in "$OBS"/*.dfs0; do
    [ -e "$f" ] || continue
    stem=$(basename "$f" .dfs0)
    case "$stem" in Altimetry_*) continue ;; esac      # altimetry tracks are not stations
    printf '%s\n' "$ids" | grep -qx "$stem" || finding MUST "Orphan data file: observations/$stem.dfs0 has no row in stations.csv (§8.5)"
  done
fi
```

#### Data-only families

At least one of `observations/` or `data/` MUST exist. `processed/`, `figures/`, `.publish/` SHOULD exist. An observation-centric data-only case **SHOULD** also follow the §8.1/§8.3 observation contract (`.dfs0` data + a variable-agnostic `stations.csv`).

### Step 4 — Controlled vocabulary checks (§4)

For each top-level directory in the case repo:

```bash
for d in "$REPO"/*/; do
  name=$(basename "$d")
  case "$name" in
    measurements|obs|gauges|sensors)  finding MUST "Forbidden synonym at top level: $name/ (canonical: observations/)" ;;
    notebooks|scripts|src|analysis)   finding MUST "Forbidden synonym at top level: $name/ (canonical: code/)" ;;
    plots|images|img)                 finding MUST "Forbidden synonym at top level: $name/ (canonical: figures/)" ;;
    sample_output|outputs|results|data_sample) finding MUST "Forbidden synonym at top level: $name/ (canonical: output_sample/)" ;;
    inputs|forcing|bc)                finding MUST "Forbidden synonym at top level: $name/ (canonical: input/)" ;;
    setup|simulation)                 finding MUST "Forbidden synonym at top level: $name/ (canonical: model/)" ;;
    dataset)                          finding MUST "Forbidden synonym at top level: $name/ (canonical: data/)" ;;
    derived|prepared|intermediate)    finding MUST "Forbidden synonym at top level: $name/ (canonical: processed/)" ;;
  esac
done
```

For the glossary (§4.3), grep the README and notebook filenames for the forbidden synonyms (`measurements`, `gauges`, `verification`, `tuning`, `fitting`, …) and raise SHOULD findings — these are advisory because prose flexibility is allowed.

### Step 5 — README conventions (§5)

Read the top-level `README.md` and extract its `^#+\s+` headings. Compare against the canonical section list in §5. For each missing section, raise a SHOULD finding. For sections that appear out of order, raise a NOTE.

For sub-directory READMEs: each of `code/`, `input/`, `model/`, `observations/`, `output_sample/`, `figures/`, `.preprocessing/`, `.publish/` SHOULD contain a `README.md`. Raise SHOULD for any missing.

### Step 6 — Model setup runnability (§7) — model-based cases only

For each model setup file under `model/` (or anywhere if MIKESHE), run the bundled helper:

```bash
python3 "$SKILL_DIR/extract_model_paths.py" --repo "$REPO" --setup "$SETUP_FILE"
```

The helper outputs JSON lines like:

```json
{"path": "..\\model\\hamburg.mesh", "kind": "input", "absolute": false, "resolves_to": "model/hamburg.mesh", "exists": false}
```

For each line:

- `absolute: true` → MUST finding ("Absolute path in model setup: …; setup is not portable").
- `exists: false` and `kind: input` → MUST finding ("Model setup references missing input: …; expected at <resolves_to>").
- `exists: false` and `kind: output` → NOTE finding ("Model output destination does not exist: …; will be created at run time, verify intended path").
- `exists: true` → no finding.

For non-text setup files (e.g. `.mupp` SQLite) the helper exits with a NOTE: "Setup file format not supported by path extractor; runnability not verified."

### Step 7 — Publishing workflow (§6)

For model-based cases:

- `.publish/zip_repo.py` SHOULD exist.
- `.publish/zenodo_text.md` SHOULD exist.
- A GitHub Actions workflow under `.github/workflows/` SHOULD exist that renders `README.md` to `README.pdf`.

Raise SHOULD findings for missing items.

### Step 8 — Anti-patterns (§9)

- `output/` containing large data files at the top level → MUST.
- Any `zenodo_upload.zip` or similar archive at the repo root → MUST.
- Any data file matching the previous controlled-vocabulary checks that escaped → MUST.

### Step 9 — Produce the report

Write the report to stdout in this shape:

```markdown
# WaterBench Review: <repo-name>

**Case family detected:** <family>
**Spec version:** STRUCTURE.md @ <commit or "HEAD">
**Total findings:** N MUST, M SHOULD, K NOTE

## MUST (N)
- …

## SHOULD (M)
- …

## NOTE (K)
- …

## Summary
<one paragraph: is this case ready to publish / what blocks it>
```

Do not invent findings beyond what the checks above produce. If a check is skipped (e.g. opaque setup file), report it under NOTE so the human reviewer can follow up.

## What this skill does NOT do

- It does not modify files, rename directories, or commit anything.
- It does not open GitHub issues or PRs.
- It does not run the MIKE model — runnability is checked statically by path resolution, not by simulation.
- It does not validate the *correctness of values*. It checks that observation data is `.dfs0`, that `stations.csv` declares the required columns (`crs`, station id), and that the manifest and `.dfs0` files reference each other (§8) — but it does **not** verify that a declared unit, coordinate, CRS, or datum is actually *right*, that EUM item types are sensible, or that time coverage is adequate. Those need a domain reviewer.
