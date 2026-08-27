## Overview

This is the `rdm/` (ground-truth reference-data management) component of the
`rise` pipeline — one self-contained piece of a larger monorepo, with its own
environment, notebooks, and code. It's unrelated to (and doesn't share
dependencies with) other `rise` components like training or inference, which
live in their own top-level folders.

`rdm/` standardizes raw ground-truth data (field geometries + attributes) into
the shape `ukrop` (a separate repo — Django + PostGIS, ingesting from Azure
Blob Storage) requires. A separate, in-progress piece of code (not in this
repo yet) actually pushes the standardized output there.

**`notebooks/preprocess_data.ipynb` is the only notebook you need to get to
ukrop-ready data.** It merges a raw geometry file (+ optional attribute file)
into one standardized table (crop type, sow date, `Season_id`, `Geom_id`,
etc.) and exports it (e.g. `data/check_file.geojson`).

Two more notebooks exist as **optional, orthogonal follow-up checks** — run
either, both, or neither depending on what you want to verify:

- **`notebooks/qa_checks.ipynb`** — general geometric/data-quality QA
  (geometry validity, land-cover sanity, road proximity, overlapping
  boundaries). This is about whether the *data itself* looks right — it has
  nothing to do with whether the file matches ukrop's schema.
- **`notebooks/validate_ukrop_format.ipynb`** — checks the standardized
  output against ukrop's actual ingestion contract specifically (required
  fields, enum values, the single-date-per-operation rule, etc. — see the
  schema reference below). This is the one to run if the question is
  "will ukrop accept this file."

All paths in this document are relative to this `rdm/` folder.

## Environment Setup

From inside `rdm/`:

```bash
conda env create -f environment.yml
conda activate fresh_test
```

(The environment is named `fresh_test` in `environment.yml` — despite the name,
it's the one both notebooks in this folder use.)

## Repo structure

- `notebooks/`
  - `preprocess_data.ipynb` — the standardization pipeline (the only
    required step).
  - `qa_checks.ipynb` — optional general data-quality QA.
  - `validate_ukrop_format.ipynb` — optional ukrop-schema-compliance check.
- `src/rdm/` — shared logic imported by the notebooks (add `src/` to
  `sys.path` before importing, as the notebooks already do):
  - `read_data.py` — reads/merges a raw geometry file with an optional
    separate attribute file (`read_ground_data`).
  - `standardize.py` — crop-type preprocessing, sow-info/`Est_Sow_Year`
    assignment, and the interactive column-mapping UI (`display_final_cols`)
    used to produce the final standardized schema.
  - `crop_type.py` — crop name parsing/coding.
  - `geom_processing.py` — geometry validity/repair/duplicate checks.
  - `observation_processing.py` — datetime/yield standardization,
    start/end-date collapsing, `Season_id` assignment.
  - `validate_ukrop.py` — the checks behind `validate_ukrop_format.ipynb`.
  - `utils.py` — shared lookup tables (crop groups, season codes, target
    schema).
- `data/` — sample/working inputs and outputs (not meant to be exhaustive —
  point the notebooks at your own raw files via the `USER INPUT SECTION`
  cell). Gitignored except `data/sample_data/`, which holds synthetic
  practice datasets safe to share (see the notebook's default
  `USER INPUT SECTION` for how to switch between them).

## `notebooks/preprocess_data.ipynb`

**Expected inputs:** a geometry file (`.shp`, `.geojson`, or `.parquet`) and,
optionally, a separate attribute file (`.xlsx`/`.csv`) joined on a shared key —
set these in the `USER INPUT SECTION` cell (`INPUT_GEOMETRY`, `INPUT_ATTRIBUTES`,
`PROVIDER_NAME`, `SEASON_YEAR`, `JOIN_KEY`).

**Column mapping is interactive.** Section 8 ("Standardization of column names")
displays a widget UI — you map each raw column to the target schema
(`Geom_id`, `Season_id`, `Src_id`, `Crop`, `Sow_Date`, etc.) and click
**Confirm Mapping**. This requires a live Jupyter session. For headless/scripted
runs (CI, batch processing), call `final_cols.confirm()` instead of clicking the
button — it applies whatever mapping is currently on the dropdowns (auto-matched
by column name equality). Note this means anything that isn't an exact name match
— e.g. a raw `Field` column that should map to `Src_id` — won't get mapped
automatically, so a headless run can silently drop columns a human would have
mapped by hand. Check the "Successfully Mapped" / "UNMAPPED COLUMNS" printout
either way.

**Output:** a standardized geometry file with one row per field per season,
ready for the QA notebook or for ingestion into the database pipeline.

## `notebooks/qa_checks.ipynb`

Runs a suite of checks on the standardized output before it's considered ready
to ship:

1. **Load Data**
2. **Geometry & CRS Checks** — null/invalid geometry detection, CRS check,
   `make_valid` repair, size and aspect-ratio anomaly detection, disconnected
   multipolygon flagging.
3. **Land Cover / Crop Mask Checks** — flags the fraction of each field that
   falls on non-cropland (forest, built-up, water) using ESA WorldCover via the
   Microsoft Planetary Computer STAC API.
4. **Road Proximity Checks** — fetches the OSM road network (via `osmnx`) and
   flags fields sitting exactly on a road, or split by one.
5. **Overlap Detection** — finds pairs of fields whose boundaries overlap and
   reports the overlap ratio.

This notebook doesn't write an output file — it's a diagnostic pass. Review
flagged rows manually before dropping any or editing geometries.

**Requires internet access** (Planetary Computer + OpenStreetMap). The overlap
and road-proximity sections use `Src_id`, so it must have been mapped when
`check_file.geojson` was produced (see the mapping note above).

### Known limitations

- **Scale:** road/land-cover checks fetch data live per run. A 15-field,
  ~30km-wide test cluster took ~70s just for the OSM road-graph fetch;
  country-scale runs (thousands of scattered fields) can be very slow or
  memory-heavy. Batch by region/tile rather than running the full extent at
  once for large datasets.
- **Overpass reliability:** `fetch_osm_roads` goes through `osmnx`'s Overpass
  client rather than a raw request — the public Overpass API (`overpass-api.de`)
  has been known to reject plain `requests` calls (406 errors) while still
  serving `osmnx`'s client fine on the same host.
- **The WorldCover mosaic cell calls `plt.show()`**, which pops up a GUI image
  window. That's expected and fine in a normal interactive Jupyter session —
  just close the window to let the notebook continue — but it will block
  indefinitely if this notebook is ever run headless/non-interactively (e.g.
  via `nbconvert --execute` or a script), since there's no window to close.

## `notebooks/validate_ukrop_format.ipynb`

Checks a standardized output file against ukrop's actual ingestion contract
(not general data quality — that's `qa_checks.ipynb`). Answers "will ukrop
accept this file," not "is this good data."

- **Required:** `Season_id` present and non-null on every row (ukrop silently
  drops any row missing it).
- **Expected but not enforced:** `Geom_id`, `Src_id`, `Est_Sow_Year` — ukrop
  won't reject a file missing these, but the corresponding DB fields will
  just be null.
- **Single-date rule:** flags any `_Start_Date`/`_End_Date`-suffixed column
  still present alongside its plain-named counterpart (`Sow_Date`,
  `Harvest_Date`, `Tillage_Date`) — a sign the start/end collapsing step
  (Section 4a of `preprocess_data.ipynb`) hasn't been run yet.
- **Enum checks:** `Crop_Season` values outside `Winter`/`Spring`/`Summer`/
  `Fall`, and (if present) chemical `operation_type` values outside ukrop's
  fixed list, both get silently NULLed by ukrop rather than rejected — this
  notebook flags them instead of letting them through quietly.
- **Casing:** flags `Src_Id` (wrong casing) if present instead of `Src_id`.
- **Informational only:** notes `Src_File`, `Variety`, `Yield_Clean`, and
  `Urea_Date` if present, since ukrop doesn't read any of them (not an error
  — just a heads-up that data there is going nowhere).
- **Does not validate:** provider-folder naming/placement, since that's a
  property of where the file gets delivered, not of the file itself — see
  the schema reference below for the provider-name rule.

## ukrop schema quick reference

The full contract (with exact source citations) lives in `CLAUDE.md` — this
is the short version, current as of when this pipeline was last checked
against ukrop's actual code (`ingest_processed_data.py`, `models.py`).

| | |
|---|---|
| Provider folder name | Becomes `Provider.name` verbatim. Known providers: `FRENDT, IMC, KERNEL, KUSSUL, NIBULON, ZELENA_DOLYNA`. |
| Required per row | `Season_id` (rows without it are dropped) |
| Per-operation date columns | Exactly one plain-named column per operation: `Sow_Date`, `Harvest_Date`, `Tillage_Date`. No end-date field exists in ukrop's schema at all — pick one value (convention here: the end date) before delivery. |
| `Crop_Season` allowed values | `Winter`, `Spring`, `Summer`, `Fall` (else silently `NULL`) |
| Chemical `operation_type` allowed values | `Fertilizer`, `Pesticide`, `Herbicide`, `Fungicide`, `Insecticide`, `"CP product (Herbicide)"`, `"CP product (Fungicide)"`, `"CP product (Insecticide)"`, `Other` (else silently `NULL`) |
| Fields ukrop does not model | `Src_File`, `Variety` (only `Crop_Variation` exists), `Yield_Clean`, `Urea_Date` |
| CSV filename → operation type | Substring match: `_sow`, `_harv`, `_till`, `_spread`/`_input`/`_protect`, `_crops` |
| Year | Derived from the immediate parent folder name via `str.isdigit()` — non-numeric folders silently get `year=None` |
