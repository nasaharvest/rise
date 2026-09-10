import geopandas as gpd
import pandas as pd
from pathlib import Path
from typing import Union, List, Optional, Tuple


def read_ground_data(
    file_paths: Union[str, List[str]],
    join_key: Union[str, Tuple[str, str], None] = None,
    lat_lon_cols: Optional[tuple] = None
) -> gpd.GeoDataFrame:

    # ... [File Loading Logic remains exactly the same] ...
    # (Assuming we have now loaded 'gdf' and 'df')

    # 1. Normalize Input to a list of Path objects
    if isinstance(file_paths, str):
        files = [Path(file_paths)]
    else:
        files = [Path(f) for f in file_paths]

    geo_exts = {'.shp', '.geojson', '.gpkg', '.parquet', '.fgb'}
    table_exts = {'.csv', '.xlsx', '.xls', '.txt'}

    geo_file, attr_file = None, None

    for f in files:
        if not f.exists(): raise FileNotFoundError(f"File not found: {f}")
        if f.suffix.lower() in geo_exts: geo_file = f
        elif f.suffix.lower() in table_exts: attr_file = f

    if len(files) == 1 and not geo_file and not attr_file: geo_file = files[0]

    gdf, df = None, None

    # Load Geometry
    if geo_file:
        try:
            gdf = gpd.read_parquet(geo_file) if geo_file.suffix == '.parquet' else gpd.read_file(geo_file)
        except Exception as e: raise ValueError(f"Error reading geometry: {e}")

    # Load Attributes
    if attr_file:
        try:
            print(f"\n--- DEBUGGING EXCEL LOAD: {attr_file.name} ---")

            if attr_file.suffix in ['.xlsx', '.xls']:
                # 1. Read the file (defaults to first sheet)
                df = pd.read_excel(attr_file)

                # DIAGNOSTIC: Print what we found
                print(f"Columns detected: {list(df.columns)}")
                print(f"Row count: {len(df)}")
                print(f"First 2 rows:\n{df.head(2)}")

                # CHECK: Does it look like a valid table?
                # If the headers look like "Unnamed: 1", the header row is wrong.
                if "Unnamed: 0" in df.columns or "Unnamed: 1" in df.columns:
                    print("WARNING: 'Unnamed' columns detected. Your header might be on a lower row.")
                    # Optional: Try to auto-fix by grabbing the next valid row (Advanced)

            elif attr_file.suffix == '.csv':
                df = pd.read_csv(attr_file)
            elif attr_file.suffix == '.txt':
                df = pd.read_csv(attr_file, sep='\t')

        except Exception as e:
            raise ValueError(f"Error reading attributes: {e}")

    # ==========================================
    # MERGE LOGIC WITH TYPE FIX
    # ==========================================
    if gdf is not None and df is not None:

        # 1. Determine the Left (Geo) and Right (Attr) keys
        left_key, right_key = None, None

        if isinstance(join_key, (tuple, list)) and len(join_key) == 2:
            left_key, right_key = join_key
        elif isinstance(join_key, str):
            left_key, right_key = join_key, join_key
        else:
            # Auto-detect
            common_cols = set(gdf.columns) & set(df.columns)
            common_cols.discard('geometry')
            if len(common_cols) == 1:
                k = list(common_cols)[0]
                left_key, right_key = k, k
            else:
                raise ValueError("Could not auto-detect join keys. Please specify.")

        # 2. VALIDATION
        if left_key not in gdf.columns: raise ValueError(f"Key '{left_key}' missing in Geometry file.")
        if right_key not in df.columns: raise ValueError(f"Key '{right_key}' missing in Attribute file.")

        # 3. TYPE HARMONIZATION (ROBUST FIX)
        print(f"Sanitizing keys: Casting '{left_key}' and '{right_key}'...")
        #Had to change it to this aggressive typcasting to get close to a standard method for getting equal keys for merging
        def clean_key_column(series):
            """
            Aggressively normalizes keys by trying to convert to integer first.
            Pipeline: Raw Value -> Float -> Int -> String
            Example: "123.0" -> 123.0 -> 123 -> "123"
            """
            try:
                # 1. Force to numeric (coerces errors to NaN)
                #    This handles '123', '123.0', '123.00', ' 123 '
                s_numeric = pd.to_numeric(series, errors='coerce')

                # 2. Check if we have valid numbers
                #    (If the whole column is "District A", this logic is skipped)
                if s_numeric.notna().sum() > 0:
                    # Fill NaNs with a dummy to allow Int casting, then cast to Int
                    # This chops off the decimal: 123.0 -> 123
                    s_int = s_numeric.fillna(-9999).astype(int).astype(str)

                    # Restore NaNs
                    return s_int.replace('-9999', 'nan')
                else:
                    # Fallback for purely text columns
                    return series.astype(str).str.strip()
            except:
                # Ultimate fallback
                return series.astype(str).str.strip()

        # Apply the cleaner
        gdf[left_key] = clean_key_column(gdf[left_key])
        df[right_key] = clean_key_column(df[right_key])

        print(f"Merging on {left_key} == {right_key}")
        #Changing  the merge strategy from left to outer to keep more information
        gdf = gdf.merge(df, left_on=left_key, right_on=right_key, how='outer')
        #df = gpd.GeoDataFrame(df,crs='EPSG:4326')
        return gdf
    # [Rest of logic for single files...]
    if df is not None and gdf is None:
         if lat_lon_cols:
            return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lat_lon_cols[1]], df[lat_lon_cols[0]]), crs="EPSG:4326")
    if gdf is not None:
        return gdf
