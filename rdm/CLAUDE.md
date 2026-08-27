# Purpose

This is the `rdm/` (ground-truth reference-data management) component of the
`rise` pipeline (`nasaharvest/rise`), self-contained under this folder with
its own environment, notebooks, and code — unrelated to sibling `rise`
components (e.g. training, inference) that live in their own top-level
folders with their own conventions. Everything in this file is scoped to
`rdm/` only. All paths below are relative to this folder.

`rdm/` turns raw per-provider ground-truth field data (geometries +
crop/sow/harvest/tillage/protection attributes) into the standardized shape
required for ingestion into **`ukrop`** (a separate repo: Django + PostGIS,
ingestion reads from Azure Blob Storage — see `ukrop/ukrop/models.py` and
`ukrop/.../ingest_processed_data.py`). **`ukrop` is the real target system.**
A different local `.gpkg`/SQLite database used in the `GROUND DATA PREPROCESS`
repo (this component's predecessor, kept around for historical reference — new
work happens here in `rise`) is a separate, legacy setup — don't confuse the
two, and don't assume anything written for one applies to the other.

Pipeline today: `notebooks/preprocess_data.ipynb` (raw → standardized
geojson/parquet) → `notebooks/qa_checks.ipynb` (QA on that output). **Nothing
in `rdm/` yet writes into ukrop's expected folder/file layout or talks to it
directly** — that step is separate, in-progress work, not part of this
codebase yet. Don't assume a "standardized" file from this pipeline is
ukrop-ready without checking it against the contract below first.

# The ukrop ingestion contract

This is what `ukrop`'s ingestion code (`ingest_processed_data.py`) actually
requires — treat this section and `ukrop/docs/DATA_SCHEMA.md` as authoritative;
`ukrop`'s own top-level README has drifted from its code and should not be
trusted (documents a local `--base-path` CLI arg and a stale CSV naming
example; the real ingestion command reads Azure Blob Storage via
`--storage-account`/`--container`/`--prefix`).

**Folder layout:** `<prefix>/<PROVIDER_NAME>/...` (recursive). The top-level
subfolder name becomes `Provider.name` **verbatim** — casing and naming
matters. Providers already known to ukrop: `FRENDT, IMC, KERNEL, KUSSUL,
NIBULON, ZELENA_DOLYNA`. **`KERNEL_EBRD` is not among them** — if you're
handed Kernel_EBRD (or any provider not in this list), ask the user whether it
gets its own new provider folder or should fold into an existing one, before
picking a name.

**GeoJSON files** (any `*.geojson`, found recursively — no filename
convention required): each feature's `properties` must include `Season_id`
(**hard requirement — rows without it are silently dropped**), `Geom_id`,
`Src_id`, `Est_Sow_Year`. If a provider delivery has **zero CSV files**, the
geojson properties must also carry `Crop`/`Crop_Group`/`Crop_Season`/
`Crop_Variation`, `Sow_Date`/`Sow_Year`, `Harvest_Date`/`Harvest_Year`,
`Tillage_Type` directly.

**Don't leave anomaly-flagged files in a delivery folder.** Files like
`imc_2024_anomalies.geojson` get swept up by the same recursive `.geojson`
glob with no exclusion filter — they'd get ingested as if they were real field
data.

**CSV filename → operation type** is a case-sensitive **substring match on
the filename itself** (not the extension), against real conventions like
`frendt_2019_sow.csv`: `_sow`→Sowing, `_harv`→Harvest, `_till`→Tillage,
`_spread`/`_input`/`_protect`→Chemical, `_crops`→Crop.

**Required CSV columns per type:**
- sow: `Season_id`, `Geom_id`, `Sow_Date`, `Sow_Year/Month/Day`, `Sow_Rate`/`_Unit`, `Sow_Amount`/`_Unit`, `Sow_Row_Spacing`, `Sow_Depth`, `Sow_Speed`
- harv: `Season_id`, `Geom_id`, `Harvest_Date`, `Harvest_Year/Month/Day`, `Yield`, `Production`
- till: `Season_id`, `Geom_id`, `Tillage_Date`, `Tillage_Year/Month/Day`, `Tillage_Type`
- input/protect (→ ChemicalOperation): `Input_*`/`Protect_*`-prefixed `Date`, `Year/Month/Day`, `Type`, `Variety`, `Rate`/`_Unit`, `Amount`/`_Unit`, plus `Field`, `Machine_Tasks`, `Implements`, `Row_Spacing`, `Depth`, `Speed`
- crops: `Season_id`, `Geom_id`, `Crop`, `Crop_Group`, `Crop_Season`, `Crop_Variation`

**Confirmed from ukrop's code:** it only ever reads one plainly-named date
column per operation (`Sow_Date`, `Harvest_Date`, `Tillage_Date`) — its
database schema has no end-date field at all. If a raw file still has both a
plain-named column and a separate `_End_Date` column unresolved side by side
(as real FRENDT files do — `Sow_Date` holds the start value there, with
`Sow_End_Date` as the extra column), ukrop will read whatever the plain-named
column happens to hold, which may not be the value you intended. **Every
delivery needs its date columns collapsed to one plain-named column before
it's ukrop-ready** — this part is not optional.

**Not confirmed — a convention, not an ukrop requirement:** which of the two
dates (start or end) should end up in that plain column. The convention used
so far (`frendt_2024`, `kernel_ebrd`, and the Kernel_EBRD 2025 notebook) is to
keep the **end** date, drop the start-date fields, and rename the end-date
fields to the plain name (`Sow_End_Date` → `Sow_Date`, etc.).

**Year comes from the file's immediate parent folder name**, via a plain
`str.isdigit()` check. A folder like `FRENDT/dnipro 2022` (non-numeric) gets
`year=None` silently, with no warning. If a provider's raw folder structure
doesn't cleanly encode year, ask the user how they want it organized rather
than guessing.

**Enum-like fields validated by ukrop — anything else becomes `NULL`, silently:**
- `crop_season` must be exactly one of `Winter`, `Spring`, `Summer`, `Fall`.
- Chemical `operation_type` must be exactly one of `Fertilizer`, `Pesticide`,
  `Herbicide`, `Fungicide`, `Insecticide`, `"CP product (Herbicide)"`,
  `"CP product (Fungicide)"`, `"CP product (Insecticide)"`, `Other`.

**Fields this pipeline may produce that ukrop does not model:**
- `Src_File` — not read; ukrop tracks source file path separately via `DataSource.file_path`. Don't worry about mapping it.
- `Variety` — ukrop only has `Crop_Variation`. If a provider's cultivar/variety info is meant to be preserved, ask the user where it should go — it currently has nowhere to land.
- `Yield_Clean` — never read; only `Yield` and `Production` exist on `HarvestOperation`.
- `Urea_Date` — not modeled as its own field; nitrogen/urea applications go through `ChemicalOperation` with `operation_type="Fertilizer"` instead.

**Dedup/idempotency:** exact-duplicate CSV rows are dropped via
`drop_duplicates()`. DB-level idempotency is via `get_or_create()` on specific
field tuples per operation type (e.g. Sow on `(season, operation_date,
sow_rate, sow_amount)`, Crop on `(season, name, crop_group,
crop_variation)`) — don't assume re-running ingestion on the same file is
always a no-op if any of those tuple fields differ between runs.

# This pipeline's own conventions (`src/rdm/utils.py`, `notebooks/preprocess_data.ipynb`)

- `Season_id` = `{Geom_id}-{date or "_EST"}` — unique per field per season.
  `Geom_id` (an s2cell-derived geometry hash) repeats across seasons for the
  same physical field; that's expected.
- `Est_Sow_Year` and `Sow_Date` are complementary — never both populated for
  the same row. `Est_Sow_Year` covers seasons with no real sowing event
  logged (e.g. Abandoned/Fallow) but a known year.
- Always use lowercase `Src_id`. Casing has drifted in places (`Src_Id` shows
  up in some read-side query code and in `utils.py`'s schema dict in the
  sibling `GROUND DATA PREPROCESS` repo) — if you see `Src_Id` anywhere,
  treat it as the same field, and don't introduce more of that casing.
- The interactive `display_final_cols` widget (`src/rdm/standardize.py`) needs
  either a live-Jupyter click on "Confirm Mapping", or `.confirm()` for
  headless runs. `.confirm()` only auto-matches **exact** (case-insensitive)
  column-name equality — it will silently leave a column unmapped if the raw
  name doesn't match the target name (e.g. a raw `Field` column meant to
  become `Src_id`). Always check the printed "Successfully Mapped" /
  "UNMAPPED COLUMNS" output rather than assuming a headless run mapped
  everything a human would have.
- `src/rdm/utils.py`'s `target_schema_grouped_temp` — the schema actually driving the
  mapping widget — currently only defines `Essential`, `Crop`, `Sowing`
  (`Sow_Date`/`Sow_Day`/`Sow_Month`), and `Harvest` (`Harvest_Date`/`Yield`)
  categories. **There is no Tillage, Protection/Chemical, Inputs, or
  Soil/Env category yet.** This means the widget cannot map any tillage,
  fertilizer/protection, or soil-sensor column today. Don't tell a user a
  delivery is "fully standardized" through this pipeline if it includes those
  operation types — flag the gap instead.
- Raw data comes in more than one shape for the same concept: most providers
  give one file per operation type (`*_sow.csv`, `*_harv.csv`, `*_till.csv`,
  ...), but at least one (2025 Kernel EBRD) gives a single combined
  operation-log table with a `"sub-type of operation"` + date column that must
  be split by type first. If a new delivery's shape isn't obvious from its
  column names, ask rather than assume it matches the file-per-type pattern.
- Crop/Sow data is normally 1:1 with `Season_id` (safe to merge into one row
  per season). Tillage/Protection/Spread data is normally **not** — multiple
  applications per season are common and expected. Verify this per new
  provider rather than assuming either way.

# Tillage data — what's already been figured out

`GROUND DATA PREPROCESS`'s `notebooks/add_to_database/ukr_kernel_EBRD.ipynb` and
`ukr_kernel_EBRD_2025_claude.ipynb` (parsing English free text and Ukrainian free
text respectively, from two different raw formats) independently converged on the
same practical approach. Worth reusing this instead of re-deriving it once Tillage
support gets added to this pipeline's schema:

**Canonical `Tillage_Type` values in use** (not yet formalized in `src/rdm/utils.py` —
there is no Tillage category in `target_schema_grouped_temp` at all yet):
`Disking`, `Deep_Loosening`, `Deep_Ripping`, `Cultivation`, `Inter-Row_Cultivation`,
`Harrowing`, `Plowing`, `Rolling`, `Soil_Amelioration`, `Other` (fallback for
anything that doesn't match a known pattern). Parsed via keyword/regex matching on
the raw free-text operation name (English: `rip|deep\s*rip`, `cultivat`, `harrow`,
`disk|disc`, `plow|plough`, `roll`, `loosen`, `inter[\s-]*row`; Ukrainian:
substring match on terms like `Дискування`→Disking, `Глибоке рихлення`→Deep_Loosening,
`Боронування`→Harrowing, `Культивація`→Cultivation, `міжрядний обробіток`→
Inter-Row_Cultivation, `Внесення меліорантів`→Soil_Amelioration — order matters,
test more specific phrases before general ones).

**Grain: one row per work order/operation, never collapsed to one row per
season.** A field-season normally has many separate tillage operations. This
matches `kernel_ebrd_till.csv` and every other provider's tillage file, and
matches ukrop's `TillageOperation` model (one-to-many per `FieldSeason`). If
you're ever asked to "standardize" tillage into one row per season, that's
wrong — flag it and ask instead.

**`Tillage_End_Date` is frequently synthetic, not measured.** Older Kernel
files derive it as `start + 1 day` at a `06:59:59` boundary purely as a
placeholder — it was never a real end timestamp. The 2025 data leaves it
`null` rather than fabricating that. Since ukrop only ever reads the plain
`Tillage_Date` anyway (see contract above), don't invest effort synthesizing
`Tillage_End_Date`, and never treat it as meaningful duration/measurement data.

**Depth parsing:** `Tillage_Depth_Min`/`Tillage_Depth_Max` (+ unit) are pulled
from free text via a numeric-range regex (e.g. `"5-7 см"`, `"10-15"` →
min=10, max=15; a single number populates both min and max).

**`Tillage_Purpose` is a richer, newer field** (2025 vintage only —
`pre_sowing`, `stubble_skimming`, `moisture_conservation`, `levelling`,
parsed from parenthetical text in the raw operation name) that encodes
*when in the season* a pass happened, which `Tillage_Type` alone can't
express. **ukrop does not model this field at all.** If a new delivery has
this info available, ask the user whether it's worth preserving anyway (e.g.
for the separate `EBRD_TILLAGE` ML project) even though it has nowhere to go
in ukrop today, rather than silently dropping it.

**Watch for raw categorical-mapping typos silently dropping rows.** The 2025
notebook found that a misspelled raw category (`"Fertilzation"` instead of
`"Tillage + Fertilization"`) caused 90 legitimate inter-row-cultivation rows
to be excluded entirely from the tillage output, because they didn't match
any expected `operation_group` value. General lesson: always check
`value_counts()` of a raw categorical column against whatever mapping dict
you're using, and look for values that fall through to "unmapped" before
trusting a count as complete.

**Deriving tillage "events" (passes) from individual work-order rows** is a
recurring downstream need, not something this pipeline does today. The
pattern used consistently across notebooks: group by
`(Geom_id, Season_id/Crop, Tillage_Type)`, sort by date, and start a new
event whenever the gap since the previous same-type operation exceeds a
threshold — `5`–`10` days has been used, and in the data checked so far the
exact threshold barely matters (no gaps observed between 14 days and the
next event). Useful derived fields: `event_start`/`event_end`,
`operation_count`, `distinct_operation_days`, `event_duration_days`, and
`days_before_sow` (gap between an event and that season's sowing date). **A
more complete, purpose-built implementation of this already exists** in the
separate `EBRD_TILLAGE` project (`scripts/build_tillage_event_validation.py`,
`scripts/build_ml_dataset_EBRD_tiilage.py`) — point there rather than
reimplementing event-grouping in this repo.

# When to ask the user instead of guessing

- A provider name that doesn't already exist in ukrop's known list, or that
  could plausibly fold into an existing one (e.g. is `Kernel_EBRD` its own
  provider, or part of `KERNEL`?).
- A raw crop name/synonym not already present in `src/rdm/utils.py`'s
  `crop_variations` dict.
- A raw column that doesn't cleanly auto-match a target schema field by name
  during mapping.
- Non-numeric or otherwise irregular year folder naming in raw data.
- A raw file shape you haven't seen before (operation-log vs. one-file-per-type).
- Whether a QA flag from `notebooks/qa_checks.ipynb` (size/aspect-ratio anomaly,
  land-cover flag, boundary overlap) is a real data problem or an expected
  edge case for that specific provider/field.
- Whether a delivery missing tillage/protection/input data (because this
  pipeline can't map those columns yet) should still go out as a partial
  delivery, or wait.
- Which system a task is actually about, if not stated — this repo's local
  `.gpkg` sibling (`GROUND DATA PREPROCESS`) and `ukrop` are different targets
  with different schemas.
- A raw categorical/operation-type column has values that don't match any
  entry in whatever mapping you're using for it — don't let those rows
  silently fall through as unmapped/excluded (see the tillage
  `"Fertilzation"` typo example above); surface the unmapped values instead.
- Tillage data includes enrichment fields ukrop doesn't model
  (`Tillage_Purpose`, `Tillage_Depth_*`, `Tillage_With_Fertilizer`) — ask
  whether to preserve them anyway (e.g. for the separate `EBRD_TILLAGE`
  project) rather than dropping them for not fitting ukrop's schema.

# Known gaps in this pipeline vs. what ukrop needs (not yet built)

- **Partially addressed:** `src/rdm/validate_ukrop.py`, run as Section 9 of
  `preprocess_data.ipynb` (also importable standalone), now checks a
  standardized file against the contract above (`Season_id` presence, the
  single-date rule, `Crop_Season`
  and chemical `operation_type` enum values, `Src_id` casing). It's a
  compliance check on one file, not a folder-layout/delivery check, and its
  enum checks only recognize specific column names seen so far
  (`operation_type`/`Protect_Type`/`Input_Type`) — a new provider using a
  different raw column name for the same concept would silently skip that
  check rather than error.
- No step that writes a standardized output into ukrop's expected Azure Blob
  folder/file layout, or otherwise talks to ukrop directly.
- No Tillage / Protection (Chemical) / Inputs / Soil-Env categories in the
  column-mapping schema.
- No handling for "operation log" raw formats (single table, operation-type
  column) as an alternative to per-operation-type files.
- No cross-season/cross-year consistency checks (e.g. a field flip-flopping
  between `Abandoned` and a real crop across years, or the same `Geom_id`
  showing inconsistent attributes over time) — `notebooks/qa_checks.ipynb` only
  checks a single snapshot, never a field's history across years.
- No guard against non-numeric year folders silently producing `year=None`.
- No exclusion filter for anomaly-flagged files (`*_anomalies.geojson`)
  before a folder is treated as ready to deliver.
