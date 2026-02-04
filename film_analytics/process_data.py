import pandas as pd
from utils.data_processing import process_movie_data

def main():
    print("Starting data processing...")
    
    # Load and process - use the correct path
    df = pd.read_csv('../data/movie_dataset.csv')  # Go up one level
    df_clean = process_movie_data(df)
    
    # Save processed data in the same data folder
    df_clean.to_pickle('../data/processed_movies.pkl')
    
    print(f"Saved {len(df_clean)} records to processed_movies.pkl")

if __name__ == '__main__':
    main()