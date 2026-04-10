"""
Emergency fix: train a Logistic Regression model (no dtype issues)
and set it as active. Works with any sklearn version.
Run: venv\Scripts\python.exe emergency_fix_model.py
"""
import joblib, json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from pathlib import Path

BASE   = Path(__file__).parent
DATA   = BASE / 'ml_model/dataset/diabetes.csv'
MODELS = BASE / 'ml_model/saved_models'

print("Loading data...")
df = pd.read_csv(DATA)
print(f"  Shape: {df.shape}")

# Impute zeros with per-class median
for col in ['Glucose','BloodPressure','SkinThickness','Insulin','BMI']:
    for cls in [0,1]:
        med = df.loc[(df['Outcome']==cls)&(df[col]!=0), col].median()
        df.loc[(df['Outcome']==cls)&(df[col]==0), col] = med

X = df.drop('Outcome', axis=1)
y = df['Outcome']
features = list(X.columns)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)

scaler = StandardScaler()
Xs = scaler.fit_transform(X_train)
Xt = scaler.transform(X_test)

print("Training Logistic Regression (sklearn-version-safe)...")
model = LogisticRegression(C=0.1, max_iter=1000, solver='lbfgs',
                           class_weight='balanced', random_state=42)
model.fit(Xs, y_train)

acc = (model.predict(Xt) == y_test).mean()
print(f"  Accuracy: {acc*100:.2f}%")

# Save as gradient_boosting.pkl so the registry still works
joblib.dump(model,  MODELS / 'gradient_boosting.pkl')
joblib.dump(scaler, MODELS / 'scaler.pkl')
with open(MODELS / 'feature_names.json', 'w') as f:
    json.dump(features, f)

print("Saved gradient_boosting.pkl (LR model, version-safe)")
print()
print("NOW: Stop the server (Ctrl+C) and restart:")
print("  venv\\Scripts\\python.exe run.py")
