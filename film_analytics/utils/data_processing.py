import pandas as pd
import numpy as np
import logging
import json
import re
import ast


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('movie_data_processing.log'),
        logging.StreamHandler()
    ]
)

def examine_data(df):
    """
    Examine the quality of a dataset and print summary statistics
    
    This function performs a comprehensive check of data quality, helping us
    identify potential issues before they affect our visualizations.
    """
    print("\nBasic Information:")
    print(df.info())    # Shows data types and identifies missing values
    
    print("\nMissing Values:")
    print(df.isnull().sum())    # Counts missing values in each column
    
    print("\nDuplicate Rows:", df.duplicated().sum())    # Identifies duplicate entries

    print("\nSummary Statistics:")
    print(df.describe())    # Provides statistical overview of numeric columns
    
    return df

def remove_unnecessary_columns(
    df, 
    drop_cols = ["homepage", "overview", "tagline", "crew"]
    ):
    """
    Remove columns unneeded columns
    """
    for col in drop_cols:
        df = df.drop(col, axis = 1)

    # Confirm Columns have been removed 
    for col in drop_cols:
        if col in df.columns:
            print(f"{col} still exists!")
        else:
            print(f"{col} has been removed")
    
    return df

def remove_duplicates(df):
    """
    Remove duplicate rows and keys 
    """
    
    # Step 2: Remove Duplicates (eventhough there aren't any :) but for assurance)
    print("Dupliccates Before:", df.duplicated().sum())
    # 2.1: Remove exact duplicates (identical in all columns)
    df = df.drop_duplicates()
    # 2.2: Remove any remaining identical IDs (entries that are identical in ID column)
    df = df.drop_duplicates(subset=['id'])
    print("Dupliccates After:", df.duplicated().sum())
    
    return df
    
def standardize_missing_values(df):
    """ 
    Converts missing values to NaN 
    """
    # List of common values that represent missing data
    missing_values = ["", "nan", "null", "none", "missing", "unknown", "na", "n/a"]

    # Replace all these values with np.nan
    for col in df.columns:
        if df[col].dtype == 'object':  # Only for string columns
            df[col] = df[col].replace(missing_values, np.nan)

    # For numeric columns, replace zeros or negative values with NaN where appropriate
    # Budget and revenue shouldn't be zero or negative
    if 'budget' in df.columns:
        df.loc[df['budget'] <= 0, 'budget'] = np.nan
       
    # Revenue should be positive 
    if 'revenue' in df.columns:
        df.loc[df['revenue'] <= 0, 'revenue'] = np.nan

    # Runtime should be positive
    if 'runtime' in df.columns:
        df.loc[df['runtime'] <= 0, 'runtime'] = np.nan

    # Print missing values count after standardization
    print("Missing values after standardization:")
    print(df.isna().sum())
    
    return df


def convert_numeric_columns(
    df, 
    numeric_int_columns = ['budget', 'revenue', 'vote_count'],
    numeric_float_columns = ['popularity', 'runtime', 'vote_average']
):
    """
    Convert columns into numeric data types with error handling
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame to process
    numeric_int_columns : list
        Columns to convert to numeric (but kept as float64 to preserve NaN)
    numeric_float_columns : list
        Columns to convert to float64
        
    Returns:
    --------
    pd.DataFrame
        DataFrame with converted numeric columns
    """
    # Input validation
    if not isinstance(df, pd.DataFrame):
        logging.error("Input is not a pandas DataFrame")
        raise TypeError("Input must be a pandas DataFrame")
    
    try:
        # For integer columns - keep as float to preserve NaN to not impact calculations
        for col in numeric_int_columns:
            try:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    logging.info(f"Converted {col} to numeric (with NaN values)")
                else:
                    logging.warning(f"Column {col} not found in DataFrame")
            except Exception as e:
                logging.error(f"Error converting column {col} to numeric: {e}")
                # Continue with other columns instead of failing entirely
                continue

        # For float columns - same as before, keeping NaN
        for col in numeric_float_columns:
            try:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    logging.info(f"Converted {col} to float64 (with NaN values)")
                else:
                    logging.warning(f"Column {col} not found in DataFrame")
            except Exception as e:
                logging.error(f"Error converting column {col} to float64: {e}")
                continue
                
    except Exception as e:
        logging.error(f"Unexpected error in numeric conversion: {e}")
        # Re-raise with context
        raise RuntimeError(f"Failed to convert numeric columns: {e}")
    
    return df


def convert_date_columns(df):
    """
    Convert date columns from release_date to datetime
    """
    try:
        # release_date to datetime
        if 'release_date' in df.columns:
            df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce')
            logging.info("Converted release_date to datetime")
    except Exception as e:
        logging.error(f"Error converting release_date: {e}")
        # Continue with original column unchanged
    
    return df


def clean_string_columns(
    df,
    string_columns = ['original_title', 'title', 'original_language', 'status', 'director']
):
    """
    String Conversion with proper error handling
    """
    import numpy as np
    
    for col in string_columns:
        if col in df.columns and df[col].dtype == 'object':
            # Create a copy of the original column in case operations fail
            original_values = df[col].copy()
            
            try:
                # Fill NaN values with empty string
                df[col] = df[col].fillna('')
                
                # Apply string operations with element-wise error handling
                def clean_string(x):
                    try:
                        # Skip empty strings
                        if x == '':
                            return x
                        
                        # Apply cleaning operations
                        x = x.strip()
                        x = re.sub(r'\s+', ' ', x)
                        
                        # Apply case conversions if needed
                        if col in ['director', 'original_title', 'title']:
                            x = x.title()
                        elif col == 'original_language':
                            x = x.upper()
                            
                        return x
                    except Exception:
                        # If any operation fails, return NaN
                        return np.nan
                
                # Apply the cleaning function to each value
                df[col] = df[col].apply(clean_string)
                
                logging.info(f"Cleaned {col} - filled NaN and stripped whitespace")
                
            except Exception as e:
                # If the entire operation fails, restore original values
                df[col] = original_values
                logging.error(f"Error cleaning string column {col}: {e}")
    
    return df


def process_text_to_list_columns(df, text_columns=['genres', 'keywords', 'cast']):
    """
    Process text columns into list format, setting invalid values to NaN
    
    Args:
        df (pd.DataFrame): DataFrame containing text columns to process
        text_columns (list, optional): Columns to convert to lists
        
    Returns:
        pd.DataFrame: DataFrame with processed columns
    """
    import numpy as np
    
    for col in text_columns:
        if col in df.columns:
            try:
                # Get a sample to check format
                sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
                print(f"\nProcessing text column {col}. Sample: {str(sample)[:50]}...")
                
                # Skip if already in list format
                if isinstance(sample, list):
                    print(f"{col} is already in list format, no conversion needed")
                    continue
                
                # Convert to list by splitting - handle errors by wrapping in try/except in a function
                df[col] = df[col].apply(
                    lambda x: 
                        try_convert(x, lambda val: val.split() if isinstance(val, str) and val.strip() != '' 
                                   else [] if pd.isna(val) else val)
                )
                
                # Standardize text
                df[col] = df[col].apply(
                    lambda items: 
                        try_convert(items, lambda val: [item.capitalize() for item in val] 
                                   if isinstance(val, list) else val)
                )
                
                print(f"Successfully converted {col} to list format")
                
            except Exception as e:
                print(f"Error processing column {col}: {e}")
                print(f"Keeping {col} in original format")
    
    return df

# Helper function to use with lambda
def try_convert(value, conversion_func):
    """
    Try to apply a conversion function, return np.nan if it fails
    
    Args:
        value: The value to convert
        conversion_func: The function to apply
        
    Returns:
        Converted value or np.nan if conversion fails
    """
    try:
        return conversion_func(value)
    except Exception:
        return np.nan
    
    
    
def process_json_columns(
    df,
    json_columns = ['production_companies', 'production_countries', 'spoken_languages']
):
    """
    Process JSON columns with improved error handling
    """
    import numpy as np
    
    for col in json_columns:
        if col in df.columns:
            # First check the format
            sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
            print(f"\nProcessing potential JSON column {col}. Sample: {str(sample)[:100]}...")
            
            # Skip if already in Python object format
            if isinstance(sample, (list, dict)):
                print(f"{col} is already in Python object format, no conversion needed")
                continue
                
            # Only try JSON parsing if it looks like JSON
            if isinstance(sample, str) and (sample.startswith('[') or sample.startswith('{')):
                # Define a safe JSON parsing function for each value
                def safe_parse_json(x):
                    try:
                        if isinstance(x, str) and x != '' and (x.startswith('[') or x.startswith('{')):
                            return json.loads(x)
                        elif pd.isna(x):
                            return []
                        else:
                            return x
                    except Exception:
                        # Return NaN for values that fail to parse
                        return np.nan
                
                try:
                    # Apply the safe parsing function
                    df[col] = df[col].apply(safe_parse_json)
                    print(f"Successfully converted {col} using json.loads() with NaN for failed values")
                    
                    # Report how many values failed to parse
                    nan_count = df[col].isna().sum()
                    if nan_count > 0:
                        print(f"  Note: {nan_count} values failed to parse and were set to NaN")
                        
                except Exception as e:
                    print(f"Error processing {col}: {e}")
                    
                    # Try ast.literal_eval as fallback
                    try:
                        def safe_parse_literal(x):
                            try:
                                if isinstance(x, str) and x != '' and (x.startswith('[') or x.startswith('{')):
                                    return ast.literal_eval(x)
                                elif pd.isna(x):
                                    return []
                                else:
                                    return x
                            except Exception:
                                # Return NaN for values that fail to parse
                                return np.nan
                        
                        df[col] = df[col].apply(safe_parse_literal)
                        print(f"Successfully converted {col} using ast.literal_eval() with NaN for failed values")
                        
                        # Report how many values failed to parse
                        nan_count = df[col].isna().sum()
                        if nan_count > 0:
                            print(f"  Note: {nan_count} values failed to parse and were set to NaN")
                            
                    except Exception as e2:
                        print(f"Both JSON parsing methods failed: {e2}")
                        print(f"Keeping {col} as string format")
            else:
                print(f"{col} doesn't appear to be in JSON format, keeping as is")
    
    return df




def extract_features(df):
    """ Remove columns 
    """
    
    # Extract useful information from JSON columns if they were successfully converted
    # For production companies
    if 'production_companies' in df.columns:
        # Check if conversion was successful by examining a sample
        product_sample = df['production_companies'].dropna().iloc[0] if not df['production_companies'].dropna().empty else None

        if isinstance(product_sample, list):
            # Extract first production company
            df['primary_production_company'] = df['production_companies'].apply(
                lambda x: x[0]['name'] if isinstance(x, list) and len(x) > 0 and isinstance(x[0], dict) and 'name' in x[0] 
                else None
            )
            # Count production companies
            df['production_company_count'] = df['production_companies'].apply(
                lambda x: len(x) if isinstance(x, list) else 0
            )

    # For cast
    if 'cast' in df.columns:
        # Check if conversion was successful
        cast_sample = df['cast'].dropna().iloc[0] if not df['cast'].dropna().empty else None

        if isinstance(cast_sample, list):
            # Extract lead actor/actress
            df['lead_actor'] = df['cast'].apply(
                lambda x: x[0]['name'] if isinstance(x, list) and len(x) > 0 and isinstance(x[0], dict) and 'name' in x[0]
                else None
            )
            # Count cast members
            df['cast_count'] = df['cast'].apply(
                lambda x: len(x) if isinstance(x, list) else 0
            )

    # For production countries
    if 'production_countries' in df.columns:
        # Check if conversion was successful
        countries_sample = df['production_countries'].dropna().iloc[0] if not df['production_countries'].dropna().empty else None

        if isinstance(countries_sample, list):
            # Extract primary country
            df['primary_country'] = df['production_countries'].apply(
                lambda x: x[0]['name'] if isinstance(x, list) and len(x) > 0 and isinstance(x[0], dict) and 'name' in x[0]
                else None
            )


    # Add derived columns
    # Add year column from release_date
    if 'release_date' in df.columns:
        df['release_year'] = df['release_date'].dt.year
    print("Added release_year column")

    # Add profit column
    if 'revenue' in df.columns and 'budget' in df.columns:
        df['profit'] = df['revenue'] - df['budget']
        df['roi'] = df.apply(
            lambda x: (x['profit'] / x['budget']) * 100 if x['budget'] > 0 else None, 
            axis=1
        )
    print("Added profit and ROI columns")

    # Add decade column
    if 'release_year' in df.columns:
        df['decade'] = df['release_year'].apply(
            lambda x: (x // 10) * 10 if not pd.isna(x) else None
        )
    print("Added decade column")
    
    
    return df


# Validation checks
def validate_data_quality(df_clean, df_original):
    """Validate the quality of processed data"""
    logging.info("Performing data quality validation...")
    
    # Check for data loss
    if len(df_clean) != len(df_original):
        logging.warning(f"Row count changed! Original: {len(df_original)}, Cleaned: {len(df_clean)}")
    
    # Check numeric columns have expected ranges
    if 'budget' in df_clean.columns:
        budget_max = df_clean['budget'].max()
        if budget_max > 1000000000:  # Over 1 billion
            logging.warning(f"Unusually high budget detected: ${budget_max}")
    
    if 'runtime' in df_clean.columns:
        runtime_max = df_clean['runtime'].max()
        if runtime_max > 300:  # Over 5 hours
            logging.warning(f"Unusually long runtime detected: {runtime_max} minutes")
    
    # Check derived columns exist and have expected values
    if 'profit' in df_clean.columns:
        if df_clean['profit'].isnull().sum() > len(df_clean) * 0.5:
            logging.warning("Over 50% of profit values are null")
    
    # Ensure all expected columns are present
    expected_columns = ['id', 'title', 'release_year', 'budget', 'revenue', 'profit']
    missing_columns = [col for col in expected_columns if col not in df_clean.columns]
    if missing_columns:
        logging.warning(f"Missing expected columns: {missing_columns}")
    
    logging.info("Data validation complete")

def verify_column_types(df):
    """
    Verify column data types are as expected
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame to verify
    """
    expected_types = {
        'index': 'int64',
        'budget': 'float64',
        'genres': 'object',
        'id': 'int64',
        'keywords': 'object',
        'original_language': 'object',
        'original_title': 'object',
        'popularity': 'float64',
        'production_companies': 'object',
        'production_countries': 'object',
        'release_date': 'datetime64[ns]',
        'revenue': 'float64',
        'runtime': 'float64',
        'spoken_languages': 'object',
        'status': 'object',
        'title': 'object',
        'vote_average': 'float64',
        'vote_count': 'int64',
        'cast': 'object',
        'director': 'object',
        'primary_production_company': 'object',
        'production_company_count': 'int64',
        'lead_actor': 'object',
        'cast_count': 'int64',
        'primary_country': 'object',
        'release_year': 'float64',
        'profit': 'float64',
        'roi': 'float64',
        'decade': 'float64'
    }
    
    # Check for missing columns
    missing_columns = [col for col in expected_types.keys() if col not in df.columns]
    if missing_columns:
        logging.info(f"Columns not found in DataFrame: {missing_columns}")
    
    # Check column types
    for column, expected_type in expected_types.items():
        if column in df.columns:
            actual_type = str(df[column].dtype)
            if actual_type != expected_type:
                logging.warning(f"Column {column} has type {actual_type}, expected {expected_type}")
    
    # Check for unexpected columns
    unexpected_columns = [col for col in df.columns if col not in expected_types]
    if unexpected_columns:
        logging.info(f"Additional columns found in DataFrame: {unexpected_columns}")
    
    # Summary
    total_columns = len(df.columns)
    verified_columns = len([col for col in df.columns if col in expected_types])
    logging.info(f"Verified {verified_columns} of {total_columns} columns")
    

# Pipeline structure with functions
def process_movie_data(df):
    """Main function to process movie dataset"""
    print("Starting data processing pipeline...")
    
    # Keep original for comparison
    df_clean = df.copy()
    
    # Apply each processing step
    df_clean = remove_unnecessary_columns(df_clean)
    df_clean = remove_duplicates(df_clean)
    df_clean = standardize_missing_values(df_clean)
    df_clean = convert_numeric_columns(df_clean)
    df_clean = convert_date_columns(df_clean)
    df_clean = clean_string_columns(df_clean)
    df_clean = process_text_to_list_columns(df_clean)
    df_clean = process_json_columns(df_clean)
    df_clean = extract_features(df_clean)
    
    # Data quality check
    validate_data_quality(df_clean, df)
    
    print("Data processing complete!")
    return df_clean