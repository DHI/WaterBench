# WaterBench


Website for overview of WaterBench cases. Uses [Quarto](https://quarto.org) for rendering a static website.

## Repository structure spec

[`STRUCTURE.md`](STRUCTURE.md) defines the canonical structure that every WaterBench case repository follows — required directories and filenames, controlled vocabulary to prevent synonym drift across cases, README conventions, and the runnability requirements for model setups.

The [`review-waterbench-case`](.github/skills/review-waterbench-case/SKILL.md) agent skill applies that spec to a cloned case repository and produces a markdown findings report. It works with any agent CLI that supports `.github/skills/` or `.claude/skills/` (Claude Code, GitHub Copilot CLI, etc.).

## Instructions to add a new dataset

In `index.qmd` do the following edits:

### 1. Add a row to the overview table

Find the overview table near the top of the file and insert a new row:

```markdown
| [WaterbenchType-WaterbenchLocation](#waterbenchtype-waterbenchlocation) | Hydrodynamics | [![](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg){height=20}](https://doi.org/10.5281/zenodo.XXXXXXX) [![](https://img.shields.io/badge/GitHub-181717?logo=github&logoColor=white){height=20}](https://github.com/DHI/WaterBench-WaterbenchType-WaterbenchLocation) |
```

### 2. Add a section below the last dataset entry

Paste the following block before the `## Related datasets and benchmarks` heading:

```markdown
### WaterbenchType-WaterbenchLocation {#waterbenchtype-waterbenchlocation}


[![](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX) [![](https://img.shields.io/badge/GitHub-181717?logo=github&logoColor=white)](https://github.com/DHI/WaterBench-WaterbenchType-WaterbenchLocation)

Brief description of the model, domain, time period, and validation data.

![](https://raw.githubusercontent.com/DHI/WaterBench-WaterbenchType-WaterbenchLocation/main/figures/geometry.png)

> DHI. (2025). Your citation here [Data set]. Zenodo. https://doi.org/10.5281/zenodo.XXXXXXX
```

### Notes

- Replace `WaterbenchType-WaterbenchLocation` with your actual case name (e.g. `MIKESHE-Skjern`).
- Replace `XXXXXXX` with your Zenodo DOI number.
- The anchor `{#waterbenchtype-waterbenchlocation}` must match the link in the table row exactly (lowercase, hyphens only).
- The figure is loaded directly from GitHub — make sure `figures/geometry.png` or a similar figure exists in your repo.
