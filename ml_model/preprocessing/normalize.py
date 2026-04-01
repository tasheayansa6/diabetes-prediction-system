import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
import joblib
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_data(input_file, output_file, scaler_path=None, method='standard', save_scaler=True):
    
    # Load data
    logger.info(f"Loading data from {input_file}")
    df = pd.read_csv(input_file)
    logger.info(f"Original shape: {df.shape}")
    
    # Separate features and target
    if 'Outcome' in df.columns:
        X = df.drop('Outcome', axis=1)
        y = df['Outcome']
        logger.info(f"Features: {list(X.columns)}")
    else:
        X = df
        y = None
        logger.info(f"No target column found. Normalizing all columns.")
    
    # Choose scaler
    if method == 'standard':
        scaler = StandardScaler()
        logger.info("Using StandardScaler (mean=0, std=1)")
    elif method == 'minmax':
        scaler = MinMaxScaler()
        logger.info("Using MinMaxScaler (range [0,1])")
    elif method == 'robust':
        scaler = RobustScaler()
        logger.info("Using RobustScaler (robust to outliers)")
    else:
        raise ValueError(f"Unknown method: {method}. Use 'standard', 'minmax', or 'robust'")
    
    # Fit and transform
    logger.info("Fitting scaler and transforming data...")
    X_normalized = scaler.fit_transform(X)
    
    # Create normalized DataFrame
    df_normalized = pd.DataFrame(X_normalized, columns=X.columns)
    
    # Add target back if it exists
    if y is not None:
        df_normalized['Outcome'] = y.values
    
    # Save normalized data
    df_normalized.to_csv(output_file, index=False)
    logger.info(f"Normalized data saved to {output_file}")
    logger.info(f"Normalized shape: {df_normalized.shape}")
    
    # Save scaler if requested
    if save_scaler and scaler_path:
        os.makedirs(os.path.dirname(scaler_path), exist_ok=True)
        joblib.dump(scaler, scaler_path)
        logger.info(f"Scaler saved to {scaler_path}")
    
    # Display statistics
    logger.info("\nNormalization Statistics:")
    for col in X.columns[:3]:  # Show first 3 columns as example
        logger.info(f"  {col}: mean={X_normalized[:, X.columns.get_loc(col)].mean():.3f}, "
                   f"std={X_normalized[:, X.columns.get_loc(col)].std():.3f}")
    
    return df_normalized, scaler

def load_scaler(scaler_path):
    """
    Load a saved scaler for later use
    
    Args:
        scaler_path: Path to saved scaler file
    
    Returns:
        Scaler object
    """
    return joblib.load(scaler_path)

def inverse_transform(scaler, normalized_data, original_columns):
   
    original = scaler.inverse_transform(normalized_data)
    return pd.DataFrame(original, columns=original_columns)

if __name__ == '__main__':
    # Define file paths
    input_path = 'ml_model/data/diabetes_cleaned.csv'
    output_path = 'ml_model/data/diabetes_normalized.csv'
    scaler_path = 'ml_model/models/scaler.pkl'
    
    # Check if cleaned data exists, otherwise use original
    if not os.path.exists(input_path):
        logger.warning(f"Cleaned data not found at {input_path}")
        input_path = 'ml_model/data/diabetes.csv'
        logger.info(f"Using original data: {input_path}")
    
    # Normalize with different methods
    print("\n" + "="*60)
    print("🔧 DATA NORMALIZATION")
    print("="*60)
    
    # Try different normalization methods
    methods = ['standard', 'minmax', 'robust']
    
    for method in methods:
        print(f"\nTesting {method.upper()} normalization...")
        try:
            df_norm, scaler = normalize_data(
                input_file=input_path,
                output_file=f'ml_model/data/diabetes_{method}.csv',
                scaler_path=f'ml_model/models/scaler_{method}.pkl',
                method=method,
                save_scaler=True
            )
            print(f"{method} normalization successful")
        except Exception as e:
            print(f"{method} failed: {e}")
    
    print("\n" + "="*60)
    print("Normalization complete!")
    print("="*60)