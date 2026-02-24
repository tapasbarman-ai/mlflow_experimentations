import pandas as pd
import os
import sys

def validate_data(file_path):
    print(f"Starting Data Validation for: {file_path}")
    
    if not os.path.exists(file_path):
        print(f"Error: Data file {file_path} not found!")
        sys.exit(1)
        
    df = pd.read_csv(file_path)
    
    # 1. Check for expected columns
    expected_cols = ['season', 'mnth', 'hr', 'holiday', 'weekday', 'workingday', 'weathersit', 'temp', 'atemp', 'hum', 'windspeed', 'cnt']
    for col in expected_cols:
        if col not in df.columns:
            print(f"Error: Missing expected column '{col}'")
            sys.exit(1)
            
    # 2. Check for null values
    null_counts = df.isnull().sum().sum()
    if null_counts > 0:
        print(f"Warning: Data contains {null_counts} null values. Handling basic cleaning...")
        df = df.dropna()
        
    # 3. Value Range Checks
    if not df['temp'].between(0, 1).all():
        print("Warning: Temperature values outside expected [0,1] range (likely UCI normalized).")

    # 4. Schema check
    if len(df) < 100:
        print(f"Error: Dataset too small for training ({len(df)} rows).")
        sys.exit(1)

    print("Data Validation PASSED!")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    data_path = os.path.join(root_dir, "data", "bike_hour.csv")
    validate_data(data_path)
