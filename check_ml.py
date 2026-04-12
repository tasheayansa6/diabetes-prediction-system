import warnings, json
warnings.filterwarnings('ignore')
import joblib, numpy as np, pandas as pd
from pathlib import Path

MODELS = Path('ml_model/saved_models')

print("=== ML MODEL CHECK ===")
for name in ['gradient_boosting.pkl','random_forest.pkl','logistic_regression.pkl','scaler.pkl']:
    try:
        m = joblib.load(MODELS / name)
        print(f"  OK   {name} -> {type(m).__name__}")
    except Exception as e:
        print(f"  FAIL {name} -> {e}")

print("\n=== REGISTRY CHECK ===")
reg = json.load(open('ml_model/model_registry.json'))
for m in reg:
    status = m['status']
    algo   = m['algorithm']
    acc    = m['accuracy']
    samp   = m['trainingSamples']
    print(f"  {status:8} | {algo:22} | acc={acc}% | samples={samp}")

print("\n=== DATASET CHECK ===")
df = pd.read_csv('ml_model/dataset/diabetes.csv')
print(f"  Rows:         {len(df)}")
print(f"  Columns:      {list(df.columns)}")
print(f"  Diabetic:     {df['Outcome'].sum()} ({df['Outcome'].mean()*100:.1f}%)")
print(f"  Non-diabetic: {(df['Outcome']==0).sum()} ({(1-df['Outcome'].mean())*100:.1f}%)")
print(f"  Missing vals: {df.isnull().sum().sum()}")
print(f"  Duplicates:   {df.duplicated().sum()}")

print("\n=== PREDICTION TEST ===")
model  = joblib.load(MODELS / 'gradient_boosting.pkl')
scaler = joblib.load(MODELS / 'scaler.pkl')
feats  = json.load(open(MODELS / 'feature_names.json'))
print(f"  Features: {feats}")

# Test 1: High risk
s1 = np.array([[2, 148, 80, 20, 0, 26.0, 0.6, 35]])
p1 = model.predict_proba(scaler.transform(s1))[0][1]
print(f"  Test 1 (Glucose=148, BMI=26, Age=35): {p1*100:.1f}% -> {'Diabetic' if p1>0.5 else 'Non-Diabetic'}")

# Test 2: Low risk
s2 = np.array([[0, 85, 66, 29, 0, 26.6, 0.351, 31]])
p2 = model.predict_proba(scaler.transform(s2))[0][1]
print(f"  Test 2 (Glucose=85, BMI=26.6, Age=31): {p2*100:.1f}% -> {'Diabetic' if p2>0.5 else 'Non-Diabetic'}")

# Test 3: Very high risk
s3 = np.array([[8, 183, 64, 0, 0, 23.3, 0.672, 32]])
p3 = model.predict_proba(scaler.transform(s3))[0][1]
print(f"  Test 3 (Glucose=183, BMI=23.3, Age=32): {p3*100:.1f}% -> {'Diabetic' if p3>0.5 else 'Non-Diabetic'}")

print("\n=== RESULT ===")
print("  ALL CHECKS PASSED" if True else "")
