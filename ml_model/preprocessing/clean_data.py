import pandas as pd
import numpy as np

def clean_diabetes_data(input_file, output_file):
   
    # Load data
    df = pd.read_csv(input_file)
    
    print(f"Original dataset shape: {df.shape}")
    print(f"\nMissing values:\n{df.isnull().sum()}")
    
    # Replace zeros with NaN for columns where 0 is not valid
    zero_not_valid = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']
    for col in zero_not_valid:
        if col in df.columns:
            df[col] = df[col].replace(0, np.nan)
    
    # Fill missing values with median
    for col in zero_not_valid:
        if col in df.columns:
            df[col].fillna(df[col].median(), inplace=True)
    
    # Remove outliers using IQR method
    for col in df.select_dtypes(include=[np.number]).columns:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        df = df[(df[col] >= lower_bound) & (df[col] <= upper_bound)]
    
    print(f"\nCleaned dataset shape: {df.shape}")
    
    # Save cleaned data
    df.to_csv(output_file, index=False)
    print(f"\nCleaned data saved to {output_file}")
    
    return df

if __name__ == '__main__':
    clean_diabetes_data(
        'ml_model/dataset/diabetes.csv',
        'ml_model/dataset/diabetes_cleaned.csv'
    )
