"""
Retrain Random Forest with current sklearn/numpy versions.
Run from project root: venv\Scripts\python.exe retrain_rf.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import joblib
from datetime import datetime

DATASET = 'ml_model/dataset/diabetes.csv'
SAVE_DIR = 'ml_model/saved_models'

print("=" * 55)
print("  Retraining models with current sklearn/numpy")
print("=" * 55)

import sklearn, numpy
print(f"  sklearn : {sklearn.__version__}")
print(f"  numpy   : {numpy.__version__}")
print()

# ── Load data ──────────────────────────────────────────────
df = pd.read_csv(DATASET)
print(f"Dataset: {df.shape[0]} rows x {df.shape[1]} cols")

X = df.drop('Outcome', axis=1)
y = df['Outcome']
feature_names = list(X.columns)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── Scaler (shared) ────────────────────────────────────────
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

def evaluate(model, X_tr, X_te, y_tr, y_te, name):
    model.fit(X_tr, y_tr)
    y_pred  = model.predict(X_te)
    y_proba = model.predict_proba(X_te)[:, 1]
    acc  = accuracy_score(y_te, y_pred)
    prec = precision_score(y_te, y_pred, zero_division=0)
    rec  = recall_score(y_te, y_pred, zero_division=0)
    f1   = f1_score(y_te, y_pred, zero_division=0)
    auc  = roc_auc_score(y_te, y_proba)
    print(f"\n{name}")
    print(f"  Accuracy : {acc*100:.2f}%")
    print(f"  Precision: {prec*100:.2f}%")
    print(f"  Recall   : {rec*100:.2f}%")
    print(f"  F1-Score : {f1*100:.2f}%")
    print(f"  ROC-AUC  : {auc:.4f}")
    return {'accuracy': acc, 'precision': prec, 'recall': rec, 'f1': f1,
            'roc_auc': auc, 'train_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# ── Train Logistic Regression ──────────────────────────────
lr = LogisticRegression(max_iter=1000, random_state=42)
lr_metrics = evaluate(lr, X_train_s, X_test_s, y_train, y_test, "Logistic Regression")

# ── Train Random Forest ────────────────────────────────────
rf = RandomForestClassifier(
    n_estimators=100, max_depth=10,
    min_samples_split=5, min_samples_leaf=2,
    random_state=42, n_jobs=-1
)
rf_metrics = evaluate(rf, X_train_s, X_test_s, y_train, y_test, "Random Forest")

# ── Save all files ─────────────────────────────────────────
os.makedirs(SAVE_DIR, exist_ok=True)

joblib.dump(lr,     f'{SAVE_DIR}/logistic_regression.pkl')
joblib.dump(rf,     f'{SAVE_DIR}/random_forest.pkl')
joblib.dump(scaler, f'{SAVE_DIR}/scaler.pkl')

with open(f'{SAVE_DIR}/feature_names.json', 'w') as f:
    json.dump(feature_names, f)

metadata = {
    'logistic_regression': lr_metrics,
    'random_forest':       rf_metrics,
    'features': feature_names,
    'risk_thresholds': {
        'low_risk': '<30%', 'moderate_risk': '30-59%',
        'high_risk': '60-79%', 'very_high_risk': '>=80%'
    }
}
with open(f'{SAVE_DIR}/model_metadata.json', 'w') as f:
    json.dump(metadata, f, indent=4)

print("\n" + "=" * 55)
print("  All models saved successfully!")
print(f"  logistic_regression.pkl")
print(f"  random_forest.pkl")
print(f"  scaler.pkl")
print(f"  feature_names.json")
print(f"  model_metadata.json")
print("=" * 55)
