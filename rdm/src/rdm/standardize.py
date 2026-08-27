import pandas as pd
from rdm import utils
from rdm import crop_type
import ipywidgets as widgets
from IPython.display import display, clear_output
import pprint

class display_final_cols:
    def __init__(self, df, schema_dict):
        self.df = df
        self.schema = schema_dict
        self.mapping_widgets = {}
        self.final_mapping = {}
        self.output_area = widgets.Output()
        
        # Build the UI immediately upon creation
        self.ui = self._build_ui()

    def _build_ui(self):
        """Internal method to construct the widget interface."""
    
        user_cols = ['(None)'] + sorted(list(self.df.columns))
        
        accordion = widgets.Accordion(children=[])
        titles = []
        children = []
        
        # 1. Create Tabs for each Category
        for category, fields in self.schema.items():
            titles.append(category)
            rows = []
            
            for field_name, field_info in fields.items():
                # Auto-match logic
                default_val = '(None)'
                for col in self.df.columns:
                    if col.lower() == field_name.lower():
                        default_val = col
                        break
                dd = widgets.Dropdown(options=user_cols, value=default_val, layout=widgets.Layout(width='300px'))
                
                # UI Elements
                required = field_info.get("required", False)
                label_text = f"{field_name} *" if required else field_name

                lbl = widgets.Label(
                    value=f"{label_text}:",
                    layout=widgets.Layout(width='200px')
                )
                
    
                self.mapping_widgets[field_name] = dd
                
                required = field_info.get("required", False)
                label_text = f"{field_name} *" if required else field_name
                
                field_label = widgets.HTML(
                    f"<b>{label_text}</b> "
                    f"<span style='color:#666; font-size:0.85em;'>"
                    f"{field_info['description']}"
                    f"</span>"
                )
                
                row = widgets.HBox(
                    [field_label, dd],
                    layout=widgets.Layout(
                        justify_content='space-between',
                        align_items='center',
                        margin='6px 0'
                    )
                )
                
                rows.append(row)
            
            children.append(widgets.VBox(rows, layout=widgets.Layout(padding='10px')))

        accordion.children = tuple(children)
        for i, title in enumerate(titles):
            accordion.set_title(i, title)
            
        # 2. Create the Button
        btn = widgets.Button(
            description="Confirm Mapping", 
            button_style='success', # Make it green
            layout=widgets.Layout(width='300px', margin='10px 0px')
        )
        btn.on_click(self._on_click)
        
        # 3. Return the full layout
        container = widgets.VBox(
            [accordion, btn, self.output_area],
            layout=widgets.Layout(
                width='800px',
                margin='0 auto',
                padding='20px'
            )
            )
        return container

    def _on_click(self, b):
        """Internal callback when button is clicked."""
        with self.output_area:
            clear_output()
            self._apply_mapping()

    def confirm(self):
        """Apply the current dropdown mapping without requiring a UI click.

        Use this in headless contexts (scripts, nbconvert, tests) where there is
        no live widget frontend to click "Confirm Mapping" in. Uses whatever
        values are currently set on the dropdowns (auto-matched defaults unless
        changed).
        """
        self._apply_mapping()

    def _apply_mapping(self):
        self.final_mapping = {}
        assigned_cols = set()

        # Harvest values from dropdowns
        for field, widget in self.mapping_widgets.items():
            if widget.value != '(None)':
                self.final_mapping[field] = widget.value
                assigned_cols.add(widget.value)

        # Check for unmapped columns
        all_cols = set(self.df.columns)
        unmapped = list(all_cols - assigned_cols)
        unmapped.sort()

        print(f"Successfully Mapped: {len(self.final_mapping)} columns.")

        if unmapped:
            print("\n" + "="*40)
            print(f"UNMAPPED COLUMNS ({len(unmapped)})")
            print("The following columns from your file were NOT assigned:")
            print("="*40)

            # Use pprint here for clean output
            pp = pprint.PrettyPrinter(indent=4, width=80, compact=True)
            pp.pprint(unmapped)
        else:
            print("\nAll columns in the file have been mapped.")

        for field, widget in self.mapping_widgets.items():
            selected_col = widget.value
            if selected_col != '(None)':
                expected_dtype = self._get_field_dtype(field)
                actual_dtype = self.df[selected_col].dtype

                if not self._check_dtype(actual_dtype, expected_dtype):
                    print(f"⚠ Warning: '{selected_col}' does not match expected type '{expected_dtype}'")
    
    def _get_field_dtype(self, field_name):
        for category in self.schema.values():
            if field_name in category:
                return category[field_name].get("dtype")
        return None
                        
    def _check_dtype(self, actual, expected):
        if expected == "string":
            return pd.api.types.is_string_dtype(actual)
        elif expected == "float":
            return pd.api.types.is_float_dtype(actual)
        elif expected == "int":
            return pd.api.types.is_integer_dtype(actual)
        elif expected == "datetime":
            return pd.api.types.is_datetime64_any_dtype(actual)
        else:
            return True

    def show(self):
        """Display the UI in the notebook."""
        display(self.ui)
        
    def get_mapping(self):
        """Returns the dictionary needed for pandas .rename()"""
        # Flip the dict: {User_Col : Standard_Name}
        return {v: k for k, v in self.final_mapping.items()}
    
#creating the group list
crop_to_group = {}
for group_name, group_info in utils.group_codes.items():
    for crop in group_info["crops"].keys():
        crop_to_group[crop] = group_name    
    
def crop_type_preprocess(dataset:pd.DataFrame,crop_column:str):
    data_ct = dataset.rename(columns={f"{crop_column}":"Crop_unprocessed"})
    ct_column = "Crop_unprocessed"
    #data_ct = crop_type.remove_null_ct(ct_column_name = ct_column, dataset = data_ct)  
    #getting the crops list to create group, variation and season columns
    crops_list = data_ct[ct_column].apply(crop_type.map_variations,
                                                 dict_variations = utils.crop_variations).str.split(",")  
    data_crops = crops_list.apply(
        crop_type.assign_crop_columns, 
        season_codes_dict=utils.season_codes,
        variation_codes_dict=utils.variation_codes,
        crop_to_group_dict=crop_to_group
        )
    
    print("The crop types in this dataset: ",data_crops['Crop'].value_counts())
    print("The number of variations in this dataset: ",data_crops['Crop_Variation'].value_counts())
    print("The number of group in this dataset: ",data_crops['Crop_Group'].value_counts())
    return data_crops
    
    
def assign_sow_info(dataset:pd.DataFrame):
    """
    Assigns necessary sow information to get Season_ids in the next step
    
    Parameters:
    1. Input dataframe
    
    Returns:
    Dataframe with Sow_Year column and Sow_Month, Sow_Day (if Sow_Date is available)
    
    """
    if "Sow_Date" in dataset.columns:
        dataset["Sow_Year"] = dataset["Sow_Date"].dt.year.astype("Int64")
        dataset["Sow_Month"] = dataset["Sow_Date"].dt.month.astype("Int64")
        dataset["Sow_Day"] = dataset["Sow_Date"].dt.day.astype("Int64")
        print("Columns 'Sow_Year', 'Sow_Month' and 'Sow_Date' assigned from 'Sow_Date'")
        
    else:
        if "Sow_Year" not in dataset.columns:
            dataset["Sow_Year"] = pd.NA
            print("No Sow_Date or Sow_Year found. Created Sow_Year with NA")
        else:
            print("Sow_Year already exists. Leaving as is.")
    
    return dataset    

def assign_est_sow_year(country:str,dataset:pd.DataFrame,season_year:int):
    """
    Assigns Est_Sow_Year where Sow_Year is not available (important to assign Season_id)
    
    Parameters: 
    1. Country name; currently only Ukraine has separate logic
    2. Input dataframe
    3. The crop season 
     
    Returns:
    Dataset with Est_Sow_Year column 
    
    """
    
    if "Sow_Year" not in dataset.columns:
        raise ValueError("Required column 'Sow_Year' is missing from dataset.")
    
    if country == "Ukraine" and "Crop_Season" not in dataset.columns:
        raise ValueError(
            "Column 'Crop_Season' is required for Ukraine to assign estimated sowing year."
        )
    
    dataset = dataset.copy()
    dataset["Est_Sow_Year"] = pd.Series(
    pd.NA, index=dataset.index, dtype="Int64"
    )
    mask_null = dataset["Sow_Year"].isnull()
    
    if (country == "Ukraine"):
        dataset.loc[
            mask_null & (dataset["Crop_Season"] == "Winter"),
            "Est_Sow_Year"
        ] = season_year - 1
        
        dataset.loc[
            mask_null & (dataset["Crop_Season"] != "Winter"),
            "Est_Sow_Year"
        ] = season_year
    else:
        dataset.loc[mask_null, "Est_Sow_Year"] = season_year
    print("Column 'Est_Sow_Year' successfully assigned")    
    return dataset