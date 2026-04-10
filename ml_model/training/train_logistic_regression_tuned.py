"""
Best achievable Logistic Regression on Pima diabetes dataset.
Uses per-class median imputation + GridSearchCV.
Saves model + scaler compatible with ml_service.py.
"""

import os, json, joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import (train_test_split, GridSearchCV,
                                     StratifiedKFold, cross_val_score)
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                              f1_score, roc_auc_score, classification_report)
from datetime import datetime

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH  = os.path.join(BASE_DIR, 'dataset', 'diabetes.csv')
MODELS_DIR = os.path.join(BASE_DIR, 'saved_models')
os.makedirs(MODELS_DIR, exist_ok=True)

print("=" * 60)
print("BEST LOGISTIC REGRESSION TRAINING")
print("=" * 60)

# ── Load & per-class median imputation ───────────────────────────────────────
df = pd.read_csv(DATA_PATH)
print(f"Dataset: {df.shape}")

for col in ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']:
    for cls in [0, 1]:
        med = df.loc[(df['Outcome'] == cls) & (df[col] != 0), col].median()
        df.loc[(df['Outcome'] == cls) & (df[col] == 0), col] = med

features = ['Pregnancies', 'Glucose', 'BloodPressure', 'SkinThickness',
            'Insulin', 'BMI', 'DiabetesPedigreeFunction', 'Age']

X = df[features].values
y = df['Outcome'].values

# ── Split ─────────────────────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"Train: {len(X_train)}  |  Test: {len(X_test)}")

# ── Scale ─────────────────────────────────────────────────────────────────────
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s  = scaler.transform(X_test)

# ── GridSearchCV ──────────────────────────────────────────────────────────────
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
param_grid = {
    'C':            [0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 100.0],
    'penalty':      ['l1', 'l2'],
    'solver':       ['liblinear'],
    'class_weight': [None, 'balanced'],
}
grid = GridSearchCV(
    LogisticRegression(max_iter=5000, random_state=42),
    param_grid, cv=cv, scoring='accuracy', n_jobs=-1, verbose=0
)
grid.fit(X_train_s, y_train)
model = grid.best_estimator_

print(f"Best params : {grid.best_params_}")
print(f"Best CV acc : {grid.best_score_*100:.2f}%")

# ── Evaluate ──────────────────────────────────────────────────────────────────
y_pred  = model.predict(X_test_s)
y_proba = model.predict_proba(X_test_s)[:, 1]

accuracy  = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall    = recall_score(y_test, y_pred)
f1        = f1_score(y_test, y_pred)
auc       = roc_auc_score(y_test, y_proba)
cv_scores = cross_val_score(model, X_train_s, y_train, cv=cv, scoring='accuracy')

print(f"\nTest Results:")
print(f"  Accuracy  : {accuracy*100:.2f}%")
print(f"  Precision : {precision*100:.2f}%")
print(f"  Recall    : {recall*100:.2f}%")
print(f"  F1 Score  : {f1*100:.2f}%")
print(f"  ROC-AUC   : {auc*100:.2f}%")
print(f"  CV-5 Acc  : {cv_scores.mean()*100:.2f}% (+/- {cv_scores.std()*200:.2f}%)")
print(f"\n{classification_report(y_test, y_pred, target_names=['Non-Diabetic','Diabetic'])}")

# ── Save ──────────────────────────────────────────────────────────────────────
joblib.dump(model,  os.path.join(MODELS_DIR, 'logistic_regression.pkl'))
joblib.dump(scaler, os.path.join(MODELS_DIR, 'scaler.pkl'))

with open(os.path.join(MODELS_DIR, 'feature_names.json'), 'w') as f:
    json.dump(features, f)

metadata = {
    'algorithm':        'Logistic Regression (Tuned)',
    'version':          'v1.1.0',
    'trained_at':       datetime.utcnow().isoformat(),
    'accuracy':         round(accuracy * 100, 2),
    'precision':        round(precision * 100, 2),
    'recall':           round(recall * 100, 2),
    'f1_score':         round(f1 * 100, 2),
    'roc_auc':          round(auc * 100, 2),
    'cv_accuracy':      round(cv_scores.mean() * 100, 2),
    'best_params':      grid.best_params_,
    'training_samples': len(X_train),
    'features':         features,
    'notes':            'Per-class median imputation + GridSearchCV over C, penalty, class_weight'
}
with open(os.path.join(MODELS_DIR, 'model_metadata.json'), 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"\nSaved to {MODELS_DIR}")
print("Done!")
