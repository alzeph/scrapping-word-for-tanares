# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

Extracts frequency-band allocation data from TANARES (Ivorian national frequency
allocation table) Word documents and renders it as a large spectrum-chart image
(`tanares.png`), similar to published national/ITU frequency allocation charts.

## Commands

Package management is via `uv` (see `uv.lock`, `pyproject.toml`, `.python-version` = 3.11).

```bash
uv sync                # install dependencies into .venv
uv add <package>        # add a new dependency
uv run python -m scrapping_docs.old_version.main   # run the working pipeline (see Repo state below)
```

There are no lint/test/typecheck configs in this repo (no pytest, ruff, mypy, etc.
configured) — don't assume any exist.

Scripts under `scrapping_docs/` must be run with `python -m` from the repo root
(e.g. `python -m scrapping_docs.old_version.main`), not by path
(`python scrapping_docs/old_version/main.py`) — the code uses absolute imports
rooted at `scrapping_docs`, and `scrapping_docs` has no `__init__.py` (relies on
implicit namespace packages), so it must be resolved via the repo root being on
`sys.path`.

## Repo state (read before assuming where "the code" lives)

This repo is mid-refactor:

- `main.py` (repo root) is currently just a stub ("Hello from scrapping-file-word!").
- `scrapping_docs/old_version/` holds the last known-working implementation
  (the pipeline described below). Git currently shows it as staged-for-deletion
  from its old location (`scrapping_docs/models`, `scrapping_docs/tools`,
  `scrapping_docs/main.py`) and untracked at its new `old_version/` path — i.e.
  it was moved, not deleted, and the move isn't committed yet.
- `scrapping_docs/new_version/` exists and is empty — presumably the intended
  home for a rewrite. Don't assume anything belongs there yet.

When asked to fix or extend "the scraper," the working reference implementation
is in `old_version/` unless the user says otherwise.

## Pipeline architecture (`scrapping_docs/old_version/`)

Two-stage pipeline, run from `main.py`:

1. **Extraction** (`models/extract_data.py` — `ExtractData`): reads a per-band
   Word doc (`TANARES-kHz.docx`, `TANARES-MHz.docx`, `TANARES-GHz.docx`) plus
   the global `TANARES.docx` (which holds the numbered footnote/renvoi
   paragraphs, e.g. "5.54"). For each table row it pulls the band range,
   services, and cross-references footnotes ("renvois") — both service-specific
   ones parsed out of the service text and a table-wide one parsed from the
   last paragraph in the cell — against the global doc's footnote paragraphs.
   Output is one row per (service × renvoi) combination, written to
   `output/<unity>.csv` via `write_data_in_csv()`.

2. **Rendering** (`models/tracers.py` — `BandeTracers`): loads the three CSVs
   (kHz/MHz/GHz), normalizes everything to GHz internally
   (`convert_frequency`), and draws a single wide `matplotlib` figure: one
   colored horizontal bar per band (color = matched service group via
   `GROUP_COLOR_SERVICE`, substring-matched against `GROUP_SERVICES`, falling
   back to "autres"), stacked sub-bars when a band has multiple service
   groups, a log-scale x-axis, gradient-colored band-family headers (VLF
   through LH) along the top, and a legend. Saves to `tanares.png`.

Text-cleaning/regex helpers (stripping renvoi numbers off service names,
detecting "5.54"-style footnote prefixes, etc.) live in `tools/cleans.py` and
are shared by the extraction stage.

`asserts/` holds the source `.docx` inputs, band logos (`asserts/logo/`), and
`asserts/colors.csv` (currently unused by the code — check before relying on
it).

## Known landmines in the reference implementation

- `models/tracers.py` hardcodes `ASSIGNEE_LOGO` image paths as absolute macOS
  paths (`/Users/admin/cedric/scrapping-file-word/...`) — these don't exist on
  other machines and will raise `FileNotFoundError` at class-definition time
  (the dict is built as a class attribute), before any method even runs. Fix
  by making these relative to `BASE_PATH` / the file location if you touch
  this file.
- `main.py`'s default paths (`csv_paths`, `write_data_in_csv` output dir) are
  likewise absolute macOS paths — update them for wherever you're actually
  running.
- `tabulate` and `docx` are both listed as dependencies alongside
  `python-docx`; the code imports `docx` (the `python-docx` package's import
  name), not the separate `docx` PyPI package — don't confuse the two if
  editing dependencies.
