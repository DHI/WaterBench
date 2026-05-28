# WaterBench Repository Structure

This document defines the canonical structure for a [WaterBench](https://dhi.github.io/WaterBench/) case repository. It is the rubric used by the [`review-waterbench-case`](.github/skills/review-waterbench-case/SKILL.md) agent skill, and the reference for anyone creating or maintaining a WaterBench case.

The spec is **tiered**:

- A **Universal Core** that every WaterBench case must follow.
- An **Addendum** that depends on the case family (model-based, data-only, urban-water, etc.).
- A **Controlled Vocabulary** (MUST) that prevents synonym drift across cases.
- **Conventions** (SHOULD) that describe shared practice but allow case-specific deviation.

Existing cases may not yet conform to the latest version of this spec — when the spec evolves, old cases are not retro-fitted unless a new release is published. The spec is a target for new cases and a checklist for reviews, not a CI gate.

Conformance keywords follow [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119): **MUST**, **SHOULD**, **MAY**.

---

## 1. Case families

Detect the case family from the repository name and contents. The family determines which addendum applies.

| Family            | Repo name pattern                           | Hallmark                                                          |
| ----------------- | ------------------------------------------- | ----------------------------------------------------------------- |
| MIKE21HD          | `WaterBench-MIKE21HD-<Location>`            | 2D hydrodynamic MIKE setup (`.m21fm`, `.mesh`, `.dfs*`)           |
| MIKE3HD           | `WaterBench-MIKE3HD-<Location>`             | 3D hydrodynamic MIKE setup                                        |
| MIKE21SW          | `WaterBench-MIKE21SW-<Location>`            | Spectral wave MIKE setup (`.sw`)                                  |
| MIKESHE           | `WaterBench-MIKESHE-<Location>`             | Integrated hydrology MIKE SHE setup                               |
| MIKEplus          | `WaterBench-MIKEplus-<Location>`            | Urban water MIKE+ setup (`.mupp`, `.sqlite`)                      |
| TimeSeries        | `WaterBench-TimeSeries-<Topic>`             | Pure time-series data case, no physical model                     |
| WD (Water Distr.) | `WaterBench-WD-<Topic>`                     | Water-distribution sensor data, no physical model                 |
| Other             | `WaterBench-<Type>-<Location>`              | New family — must extend this spec before being accepted          |

Families that include a physical model (`MIKE*`, and any future model family) are collectively **model-based**. Families without a physical model (`TimeSeries`, `WD`) are **data-only**.

---

## 2. Universal Core (every case)

Every WaterBench case **MUST** contain, at the repository root:

| Path           | Kind | Notes                                                                                   |
| -------------- | ---- | --------------------------------------------------------------------------------------- |
| `README.md`    | File | Top-level description. See [§5 README conventions](#5-readme-conventions).              |
| `LICENSE`      | File | Plain text. Filename **MUST** be exactly `LICENSE` (uppercase, no extension). See §4.   |
| `code/`        | Dir  | Notebooks and scripts for data exploration and validation.                              |

A case **SHOULD** also contain at the repository root:

| Path             | Kind | Notes                                                                                |
| ---------------- | ---- | ------------------------------------------------------------------------------------ |
| `pyproject.toml` | File | Python project metadata. Preferred over a free-standing `requirements.txt`.          |

A case **MUST NOT** contain at the repository root:

- Top-level data files (e.g. `*.csv`, `*.parquet`, `*.dfs*`) — these belong inside a domain directory.
- Top-level zip/archive artifacts (e.g. `zenodo_upload.zip`) — these belong in `.publish/`.

---

## 3. Addendum by family

### 3.1 Model-based cases (MIKE21HD / MIKE3HD / MIKE21SW / MIKESHE / MIKEplus / future model families)

A model-based case **MUST** additionally contain:

| Path              | Kind | Notes                                                                                              |
| ----------------- | ---- | -------------------------------------------------------------------------------------------------- |
| `model/`          | Dir  | Model setup files and simulation logs. MIKE SHE cases **MAY** omit this if the model is in `input/`. |
| `input/`          | Dir  | Boundary conditions, forcing, mesh, parameters.                                                    |
| `output_sample/`  | Dir  | Reduced model outputs for testing. See §4 — name is fixed.                                         |
| `observations/`   | Dir  | Observation data used for validation. See §4 — name is fixed.                                      |
| `figures/`        | Dir  | Plots generated by the notebooks in `code/`.                                                       |
| `.preprocessing/` | Dir  | Notebooks that produced the data under `input/` and `observations/` from raw sources.              |
| `.publish/`       | Dir  | Scripts and metadata for the Zenodo publication workflow.                                          |

`.preprocessing/` is hidden (leading dot) because it is part of the *source* used to *produce* the published data, not part of the published artifact itself. `.publish/` is hidden for the same reason. Both **SHOULD** be excluded from the Zenodo upload.

### 3.2 Data-only cases (TimeSeries / WD / future data-only families)

A data-only case **MUST** additionally contain one of:

| Path             | Kind | Notes                                                                                |
| ---------------- | ---- | ------------------------------------------------------------------------------------ |
| `observations/`  | Dir  | When the case is observation-centric. Same name as the model-based equivalent.       |
| `data/`          | Dir  | When the case is generic data (e.g. sensor logs not tied to a specific phenomenon).  |

A data-only case **SHOULD** additionally contain:

| Path             | Kind | Notes                                                                                |
| ---------------- | ---- | ------------------------------------------------------------------------------------ |
| `processed/`     | Dir  | Cleaned / derived data products built from raw inputs.                               |
| `figures/`       | Dir  | Plots generated by the notebooks in `code/`.                                         |
| `.publish/`      | Dir  | Scripts and metadata for the Zenodo publication workflow.                            |

---

## 4. Controlled vocabulary (MUST)

To prevent synonym drift between cases authored by different people, the following names are **canonical**. They **MUST** be used when the concept applies; the listed synonyms **MUST NOT** be used at the top level of a WaterBench repository.

### 4.1 Top-level directories

| Canonical name     | Forbidden synonyms                                       |
| ------------------ | -------------------------------------------------------- |
| `code/`            | `notebooks/`, `scripts/`, `src/`, `analysis/`            |
| `observations/`    | `measurements/`, `obs/`, `gauges/`, `sensors/`           |
| `data/`            | `dataset/`, `inputs/` (when the case is data-only)       |
| `model/`           | `setup/`, `simulation/`                                  |
| `input/`           | `inputs/`, `forcing/`, `bc/`                             |
| `output_sample/`   | `sample_output/`, `outputs/`, `results/`, `data_sample/` |
| `processed/`       | `derived/`, `prepared/`, `intermediate/`                 |
| `figures/`         | `plots/`, `images/`, `img/`                              |
| `.preprocessing/`  | `preprocess/`, `raw/`, `prep/`                           |
| `.publish/`        | `publish/`, `zenodo/`, `release/`                        |

### 4.2 Required filenames

| Canonical name        | Forbidden variants                                |
| --------------------- | ------------------------------------------------- |
| `README.md`           | `Readme.md`, `readme.md`, `README.MD`             |
| `LICENSE`             | `license.txt`, `License`, `LICENSE.md`, `COPYING` |

`LICENSE` is the historical drift point — several cases use `license.txt`. New cases **MUST** use `LICENSE`; existing cases **SHOULD** be migrated when next published.

### 4.3 Glossary (advisory, applies anywhere)

When the following concepts are referenced in READMEs, notebook filenames, column names, or subdirectory names, the canonical term **SHOULD** be used. The skill flags deviations as advisories rather than errors.

| Concept                              | Canonical                  | Synonyms to avoid                       |
| ------------------------------------ | -------------------------- | --------------------------------------- |
| Observed data used for validation    | observation(s)             | measurement(s), gauge data              |
| Comparison of model to observations  | validation                 | verification                            |
| Adjusting parameters to fit data     | calibration                | tuning, fitting                         |
| The unstructured grid                | mesh                       | grid (when MIKE-flexible-mesh is meant) |
| Atmospheric/oceanic input            | forcing                    | drivers, inputs (in this context only)  |
| Lateral driving condition            | boundary condition         | open boundary, BC (in prose)            |
| Reduced sample of model output       | output sample              | sample output, sample data              |
| Notebook for exploring observations  | `explore_observation_data` | `explore_obs`, `analyze_measurements`   |
| Notebook for exploring model results | `explore_model_result_data`| `explore_model`, `analyze_results`      |
| Notebook for validation              | `model_validation_<variable>`| `validate_<variable>`, `compare_*`    |

---

## 5. README conventions (SHOULD)

The repository `README.md` **SHOULD** contain, in order, the following top-level sections. Section names **SHOULD** match exactly (case-sensitive).

1. **Title** — `# WaterBench Case: <Human readable name>`
2. **Disclaimer** — short paragraph stating that the data is for educational/research use, not operational.
3. **Intended Use** — bullet list of supported use cases.
4. **Folder Structure** — an indented list mirroring §2 + §3 for the relevant family.
5. **Model description** — one of: `MIKE 21 Flow Model FM`, `MIKE 21 Spectral Wave Model`, `MIKE SHE Integrated Hydrological Model`, `MIKE+`, or a custom heading for non-model cases (`Data Description`, `Workflow`).
6. **Case Description** — geographic location, system type, extent, hydrodynamic or hydrological characteristics.
7. **Model Setup** (or **Workflow** for non-model cases) — domain, mesh/grid, forcing, parameters, outputs.
8. **Validation** — observation coverage, validation approach, skill metrics. Reference validation notebooks under `code/model_validation_*.ipynb`.
9. **Data Sources** — table of source, citation, license per data set used.

The [`WaterBench-template`](https://github.com/DHI/WaterBench-template) repository provides a fillable scaffold for this README.

### 5.1 Sub-directory READMEs (SHOULD)

Each of `code/`, `input/`, `model/`, `observations/`, `output_sample/`, `figures/`, `.preprocessing/`, `.publish/` **SHOULD** contain a one-paragraph `README.md` describing what is inside. The template repo demonstrates this pattern.

---

## 6. Publishing workflow (SHOULD)

A model-based case **SHOULD** include in `.publish/`:

- `zip_repo.py` — bundles the repository (minus large output) for Zenodo.
- `zip_output.py` — bundles full output data for Zenodo (when output data exceeds what fits in `output_sample/`).
- `zenodo_text.md` — text used in the Zenodo deposit description.
- `README.pdf` — rendered version of the top-level README, produced by the GitHub Actions workflow in `.github/workflows/`.

The repository **SHOULD** carry a GitHub Actions workflow that renders `README.md` to `README.pdf` and commits it to `.publish/`. See the template for the reference workflow.

---

## 7. Model setup runnability (MUST, model-based cases)

A WaterBench case is meant to be **runnable without modifications** after cloning. The model setup file (`.m21fm`, `.sw`, `.she`, `.mupp`, etc.) **MUST** reference all input data using **relative paths** that resolve from the model file's directory.

### 7.1 Path requirements

In the model setup file(s):

- Every referenced file (mesh, boundary conditions, forcing, parameter files) **MUST** exist in the repository at the referenced path, resolved relative to the model file's location.
- Absolute paths (e.g. `C:\Projects\Hamburg\input\mesh.mesh`, `/mnt/d/...`, `\\server\share\...`) **MUST NOT** appear. Such paths are residue from the author's local environment and break reproducibility for everyone else.
- Path separators **SHOULD** use `\` *or* `/` consistently per file family — MIKE setup files traditionally use `\`. The skill does not flag separator choice; only existence.
- Forward references **MUST** resolve to a file under one of `input/`, `model/`, or the model directory itself. References that escape the repository root (e.g. `..\..\external\data`) are not allowed.

### 7.2 What the skill checks

The skill extracts path-like tokens (any token containing a file extension known to MIKE: `.mesh`, `.dfs0`, `.dfs1`, `.dfs2`, `.dfsu`, `.bnd`, `.dat`, etc.) from the model setup file. For each token:

- If the token is an absolute path → **MUST** finding.
- If the token does not resolve to a file in the repository → **MUST** finding.
- If the token resolves but contains backslashes on a Unix-only repo, or vice versa → **SHOULD** finding (cosmetic).

For binary or opaque setup files (e.g. `.mupp` SQLite-backed), the skill **MAY** skip path extraction and report the limitation as a **NOTE**.

### 7.3 Author guidance

When saving a MIKE setup from a working directory tree like:

```
case/
  model/Case.m21fm
  input/mesh.mesh
```

ensure the setup is saved with the working directory at `case/` so that `Case.m21fm` references `..\input\mesh.mesh` (relative), not `C:\Users\name\case\input\mesh.mesh` (absolute). The MIKE editor offers a "store paths relative to setup" option — use it.

---

## 8. Observation filename conventions (SHOULD)

Inside `observations/` of a model-based case:

- A `stations.csv` file **SHOULD** list station metadata (id, name, lon, lat, source, units).
- Per-station time series **SHOULD** be named `<Station>_<variable>.csv`, with `<variable>` from a controlled set:
  - `wl` — water level
  - `u_v` — current velocity components
  - `swh` — significant wave height
  - `mwd` — mean wave direction
  - `pwp` — peak wave period
- Altimetry data **SHOULD** be named `Altimetry_<variable>_<mission>.csv` (e.g. `Altimetry_wl_3a.csv`).

---

## 9. Anti-patterns (MUST NOT)

- **Synonym directories at the top level**: see §4.1.
- **Mixed-case license filename**: see §4.2.
- **Top-level data sprawl**: data files at the repo root that should live under a domain directory.
- **`output/` at the top of a published case** that duplicates `output_sample/`: keep full outputs on Zenodo, only sample data in the repo. The template carries an empty `output/` for clarity, but published cases **MUST NOT** ship large output files in the repository.
- **Hidden zenodo zip in the repo root**: archives belong in `.publish/`, never in the root.

---

## 10. How conformance is checked

The skill at [`.github/skills/review-waterbench-case/`](.github/skills/review-waterbench-case/SKILL.md) reads this spec and produces a markdown findings report against a target WaterBench repository. It is invoked from the agent CLI (Claude Code, GitHub Copilot CLI, or any compatible agent that supports `.github/skills/` or `.claude/skills/`) with:

```
/review-waterbench-case <path-to-cloned-case>
```

The skill is **read-only**: it produces a report. It does not open issues, push branches, or rename files. Findings are graded:

- **MUST** — a violation of the controlled vocabulary or a missing core/addendum item.
- **SHOULD** — a deviation from convention. Worth fixing on the next release; not blocking.
- **NOTE** — an observation worth flagging to a human reviewer.

---

## 11. Evolving this spec

The spec evolves. When it does:

1. Update this document.
2. Update the skill body if new MUST checks have been added.
3. Note in the changelog (below) which existing cases now fall behind.
4. Existing cases are **not** retro-fitted automatically. They catch up the next time they are published.

### Changelog

- **2026-05-28** — initial version. Derived from a survey of `WaterBench-template`, `MIKE21HD-Oresund`, `MIKE3HD-Oresund`, `MIKE21HD-HamburgElbeEstuary`, `MIKE21HD-ConceptionBay`, `MIKE21HD-SouthernNorthSea`, `MIKE21SW-SouthernNorthSea`, `MIKESHE-Skjern`, `MIKEplus-Bellinge`, `TimeSeries-WWTPINflow`, and `WD-SensorData`.
