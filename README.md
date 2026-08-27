## Overview

This repo standardizes raw ground-truth data (field geometries + attributes) into a
harmonized format, then runs a set of QA checks on the result. It's the first stage
of a larger satellite-processing pipeline — a separate repo handles pushing the
standardized output into the Azure database/dashboard.

Two notebooks, run in order:

1. **`preprocessing_notebook.ipynb`** — merges a raw geometry file (+ optional
   attribute file) into one standardized table (crop type, sow date, `Season_id`,
   `Geom_id`, etc.) and exports it (e.g. `data/check_file.geojson`).
2. **`geometric_checks.ipynb`** — takes that standardized output and runs geometry,
   land-cover, road-proximity, and overlap QA checks on it before you trust the data
   enough to hand it off.

`geometric_checks_halo.ipynb` is a variant of the same QA notebook pointed at a
different input (HALO's Ukraine minefield survey polygons instead of
`check_file.geojson`) — same checks, different source data.

## Environment Setup

```bash
conda env create -f environment.yml
conda activate fresh_test
```

(The environment is named `fresh_test` in `environment.yml` — despite the name,
it's the one both notebooks in this repo use.)

## Repo structure

- `preprocessing_notebook.ipynb` / `preprocessing_notebook_zel.ipynb` — the
  standardization pipeline (the `_zel` variant is an earlier run against the
  Zelena Dolyna dataset).
- `geometric_checks.ipynb` / `geometric_checks_halo.ipynb` — QA checks.
- `scripts/` — shared logic imported by the notebooks:
  - `automation.py` — reads/merges raw files, assigns sow info & `Est_Sow_Year`,
    and the interactive column-mapping UI (`display_final_cols`) used to produce
    the final standardized schema.
  - `crop_type.py` — crop name parsing/coding.
  - `geom_processing.py` — geometry validity/repair/duplicate checks.
  - `observation_processing.py` — datetime/yield standardization, `Season_id`
    assignment.
- `utils.py` — shared lookup tables (crop groups, season codes, target schema).
- `data/` — sample/working inputs and outputs (not meant to be exhaustive —
  point the notebooks at your own raw files via the `USER INPUT SECTION` cell).

## `preprocessing_notebook.ipynb`

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

## `geometric_checks.ipynb`

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
