## Overview

This is the ground-truth reference-data (RDM) preprocessing part of the `rise`
pipeline. It standardizes raw ground-truth data (field geometries + attributes)
into a harmonized format, then runs a set of QA checks on the result. A
separate, in-progress piece of code (not in this repo yet) pushes the
standardized output into the `ukrop` database/dashboard on Azure.

Two notebooks, run in order:

1. **`notebooks/preprocess_data.ipynb`** — merges a raw geometry file (+
   optional attribute file) into one standardized table (crop type, sow date,
   `Season_id`, `Geom_id`, etc.) and exports it (e.g. `data/check_file.geojson`).
2. **`notebooks/qa_checks.ipynb`** — takes that standardized output and runs
   geometry, land-cover, road-proximity, and overlap QA checks on it before you
   trust the data enough to hand it off.

## Environment Setup

```bash
conda env create -f environment.yml
conda activate fresh_test
```

(The environment is named `fresh_test` in `environment.yml` — despite the name,
it's the one both notebooks in this repo use.)

## Repo structure

- `notebooks/`
  - `preprocess_data.ipynb` — the standardization pipeline.
  - `qa_checks.ipynb` — QA checks.
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
