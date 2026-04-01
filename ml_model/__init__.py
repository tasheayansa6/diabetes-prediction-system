

__version__ = '1.0.0'
__author__ = 'Diabetes Prediction System'

# Import key functions for easy access
from .prediction.predictor import DiabetesPredictor
from .training.train_model import train_model, evaluate_model
from .preprocessing.preprocess import load_and_preprocess_data

# Define what gets exported
__all__ = [
    # Main classes
    'DiabetesPredictor',
    
    # Training functions
    'train_model',
    'evaluate_model',
    
    # Preprocessing
    'load_and_preprocess_data',
    
    # Package info
    '__version__',
    '__author__'
]

# Package initialization message (optional)
print(f"ML Model Package v{__version__} loaded")