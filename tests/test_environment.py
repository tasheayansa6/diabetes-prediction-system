# test_environment.py
import sys
import numpy as np
import pandas as pd
import sklearn
import joblib

print("="*50)
print("Environment Test")
print("="*50)

print(f"\n🐍 Python version: {sys.version}")
print(f"📦 NumPy version: {np.__version__}")
print(f"   NumPy location: {np.__file__}")
print(f"📦 Pandas version: {pd.__version__}")
print(f"📦 Scikit-learn version: {sklearn.__version__}")
print(f"📦 Joblib version: {joblib.__version__}")

# Test NumPy functionality
print("\n🔧 Testing NumPy...")
try:
    test_array = np.array([1, 2, 3])
    print(f"   ✅ NumPy working: {test_array}")
except Exception as e:
    print(f"   ❌ NumPy error: {e}")

# Test loading a model
print("\n🔧 Testing model loading...")
try:
    from backend.services.ml_service import MLService
    ml = MLService()
    if ml.is_ready():
        print("   ✅ Model loaded successfully")
    else:
        print("   ❌ Model not ready")
except Exception as e:
    print(f"   ❌ Error: {e}")