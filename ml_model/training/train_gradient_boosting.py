"""
Train Gradient Boosting model for diabetes prediction.
Produces: ml_model/saved_models/gradient_boosting.pkl
          ml_model/saved_models/scaler.pkl  (shared)
          ml_model/saved_models/feature_names.json
          ml_model/saved_models/model_metadata.json
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                              f1_score, roc_auc_score, classification_report)
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH   = os.path.join(BASE_DIR, 'dataset', 'diabetes.csv')
MODELS_DIR  = os.path.join(BASE_DIR, 'saved_models')
os.makedirs(MODELS_DIR, exist_ok=True)

# ── Load data ─────────────────────────────────────────────────────────────────
print("=" * 60)
print("GRADIENT BOOSTING TRAINING")
print("=" * 60)

df = pd.read_csv(DATA_PATH)
print(f"Dataset shape: {df.shape}")

# ── Per-class median imputation for zero-value columns ────────────────────────
zero_cols = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']
for col in zero_cols:
    for cls in [0, 1]:
        median = df.loc[(df['Outcome'] == cls) & (df[col] != 0), col].median()
        df.loc[(df['Outcome'] == cls) & (df[col] == 0), col] = median

X = df.drop('Outcome', axis=1)
y = df['Outcome']
feature_names = list(X.columns)
print(f"Features: {feature_names}")

# ── Train / test split ────────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Train: {len(X_train)}  |  Test: {len(X_test)}")

# ── Scale ─────────────────────────────────────────────────────────────────────
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

# ── Train Gradient Boosting ───────────────────────────────────────────────────
model = GradientBoostingClassifier(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=4,
    min_samples_split=10,
    min_samples_leaf=4,
    subsample=0.8,
    random_state=42
)
model.fit(X_train_s, y_train)

# ── Evaluate ──────────────────────────────────────────────────────────────────
y_pred  = model.predict(X_test_s)
y_proba = model.predict_proba(X_test_s)[:, 1]

accuracy  = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall    = recall_score(y_test, y_pred)
f1        = f1_score(y_test, y_pred)
auc       = roc_auc_score(y_test, y_proba)

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(model, X_train_s, y_train, cv=cv, scoring='accuracy')

print(f"\nGradient Boosting Results:")
print(f"  Accuracy  : {accuracy*100:.2f}%")
print(f"  Precision : {precision*100:.2f}%")
print(f"  Recall    : {recall*100:.2f}%")
print(f"  F1 Score  : {f1*100:.2f}%")
print(f"  ROC-AUC   : {auc*100:.2f}%")
print(f"  CV-5 Acc  : {cv_scores.mean()*100:.2f}% (+/- {cv_scores.std()*200:.2f}%)")
print(f"\n{classification_report(y_test, y_pred, target_names=['Non-Diabetic','Diabetic'])}")

# ── Save model ────────────────────────────────────────────────────────────────
model_path   = os.path.join(MODELS_DIR, 'gradient_boosting.pkl')
scaler_path  = os.path.join(MODELS_DIR, 'scaler.pkl')
feat_path    = os.path.join(MODELS_DIR, 'feature_names.json')
meta_path    = os.path.join(MODELS_DIR, 'model_metadata.json')

joblib.dump(model,  model_path)
joblib.dump(scaler, scaler_path)

with open(feat_path, 'w') as f:
    json.dump(feature_names, f)

metadata = {
    'algorithm':        'Gradient Boosting',
    'version':          'v2.0.0',
    'trained_at':       datetime.utcnow().isoformat(),
    'accuracy':         round(accuracy * 100, 2),
    'precision':        round(precision * 100, 2),
    'recall':           round(recall * 100, 2),
    'f1_score':         round(f1 * 100, 2),
    'roc_auc':          round(auc * 100, 2),
    'cv_accuracy':      round(cv_scores.mean() * 100, 2),
    'training_samples': len(X_train),
    'test_samples':     len(X_test),
    'features':         feature_names,
    'n_features':       len(feature_names),
    'hyperparameters': {
        'n_estimators':    200,
        'learning_rate':   0.05,
        'max_depth':       4,
        'subsample':       0.8,
    }
}
with open(meta_path, 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"\nSaved:")
print(f"  Model  -> {model_path}")
print(f"  Scaler -> {scaler_path}")
print(f"  Done!")
