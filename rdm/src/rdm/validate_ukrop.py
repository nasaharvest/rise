"""
Checks a standardized ground-truth file against ukrop's actual ingestion
contract (ingest_processed_data.py / models.py), as documented in CLAUDE.md.

This is deliberately narrow: it only checks things ukrop's ingestion code
itself cares about (required fields, enum values, the single-date-per-
operation rule). It does not check general data quality (geometry validity,
land cover, overlaps, etc.) - that's qa_checks.ipynb's job.
"""

CROP_SEASON_ALLOWED = {"Winter", "Spring", "Summer", "Fall"}

CHEMICAL_OPERATION_TYPE_ALLOWED = {
    "Fertilizer", "Pesticide", "Herbicide", "Fungicide", "Insecticide",
    "CP product (Herbicide)", "CP product (Fungicide)", "CP product (Insecticide)",
    "Other",
}

# Columns ukrop's models don't have at all - present here just means the data
# in them never reaches the database, not that anything is wrong.
UKROP_UNMODELED_FIELDS = ["Src_File", "Variety", "Yield_Clean", "Urea_Date"]

# Not required by ukrop (won't cause a row to be dropped), but their absence
# means the corresponding DB field is null for every row.
EXPECTED_NOT_ENFORCED = ["Geom_id", "Src_id", "Est_Sow_Year"]

DATE_OPERATIONS = ["Sow", "Harvest", "Tillage"]

# Column names known to carry a chemical operation type in data produced by
# the raw-provider notebooks seen so far (Protect_Type/Input_Type in CSVs,
# operation_type on the ukrop side). Extend this list if a new provider uses
# a different raw column name for the same concept.
CHEMICAL_TYPE_CANDIDATE_COLUMNS = ["operation_type", "Operation_Type", "Protect_Type", "Input_Type"]


def check_season_id(gdf):
    """Season_id is required by ukrop - rows missing it are silently dropped on ingest."""
    issues = []
    if "Season_id" not in gdf.columns:
        issues.append("'Season_id' column is missing entirely - ALL rows would be dropped by ukrop.")
        return issues
    n_missing = int(gdf["Season_id"].isna().sum())
    if n_missing:
        issues.append(
            f"{n_missing} / {len(gdf)} rows have a null 'Season_id' - "
            f"these rows would be silently dropped by ukrop."
        )
    return issues


def check_expected_fields(gdf):
    """Geom_id/Src_id/Est_Sow_Year aren't required, but their absence means null DB fields."""
    notes = []
    for col in EXPECTED_NOT_ENFORCED:
        if col not in gdf.columns:
            notes.append(
                f"'{col}' is missing - not required by ukrop, but the corresponding "
                f"DB field will be null for every row."
            )
        else:
            n_missing = int(gdf[col].isna().sum())
            if n_missing:
                notes.append(f"'{col}' is null for {n_missing} / {len(gdf)} rows.")
    return notes


def check_single_date_columns(gdf):
    """Flag any _Start_Date/_End_Date columns still present - a sign collapsing hasn't happened."""
    issues = []
    for op in DATE_OPERATIONS:
        plain = f"{op}_Date"
        for suffix in ("Start_Date", "End_Date"):
            raw_col = f"{op}_{suffix}"
            if raw_col in gdf.columns:
                issues.append(
                    f"'{raw_col}' is still present alongside the plain '{plain}' column - "
                    f"ukrop only ever reads '{plain}'. Collapse start/end dates before "
                    f"delivery (see Section 4a of preprocess_data.ipynb)."
                )
    return issues


def check_crop_season_enum(gdf):
    issues = []
    if "Crop_Season" in gdf.columns:
        bad = set(gdf["Crop_Season"].dropna().unique()) - CROP_SEASON_ALLOWED
        if bad:
            issues.append(
                f"'Crop_Season' has values outside {sorted(CROP_SEASON_ALLOWED)}: "
                f"{sorted(bad)} - these will be silently NULLed by ukrop."
            )
    return issues


def check_chemical_operation_type_enum(gdf):
    issues = []
    for candidate in CHEMICAL_TYPE_CANDIDATE_COLUMNS:
        if candidate in gdf.columns:
            bad = set(gdf[candidate].dropna().unique()) - CHEMICAL_OPERATION_TYPE_ALLOWED
            if bad:
                issues.append(
                    f"'{candidate}' has values outside ukrop's allowed list: "
                    f"{sorted(bad)} - these will be silently NULLed by ukrop."
                )
    return issues


def check_src_id_casing(gdf):
    issues = []
    if "Src_Id" in gdf.columns:
        issues.append("Column 'Src_Id' found (wrong casing) - use lowercase 'Src_id' consistently.")
    return issues


def check_unmodeled_fields(gdf):
    notes = []
    present = [c for c in UKROP_UNMODELED_FIELDS if c in gdf.columns]
    if present:
        notes.append(
            f"These columns are present but not read by ukrop at all: {present}. "
            f"Not an error - the data in them just won't reach the database."
        )
    return notes


def validate_ukrop_format(gdf):
    """
    Runs all ukrop-format checks on a standardized (geo)dataframe.

    Returns:
        dict with:
        - "errors": issues that would cause data loss or silent NULLing on
          ukrop ingestion - fix these before delivery.
        - "notes": informational only, not enforced by ukrop.
    """
    errors = []
    errors += check_season_id(gdf)
    errors += check_single_date_columns(gdf)
    errors += check_crop_season_enum(gdf)
    errors += check_chemical_operation_type_enum(gdf)
    errors += check_src_id_casing(gdf)

    notes = []
    notes += check_expected_fields(gdf)
    notes += check_unmodeled_fields(gdf)

    return {"errors": errors, "notes": notes}


def print_validation_report(result):
    if not result["errors"]:
        print("PASS - no ukrop-format issues found.")
    else:
        print(
            f"FAIL - {len(result['errors'])} issue(s) found that would cause "
            f"data loss or silent NULLing on ukrop ingestion:\n"
        )
        for i, issue in enumerate(result["errors"], 1):
            print(f"  {i}. {issue}")

    if result["notes"]:
        print(f"\n{len(result['notes'])} informational note(s):\n")
        for i, note in enumerate(result["notes"], 1):
            print(f"  {i}. {note}")
