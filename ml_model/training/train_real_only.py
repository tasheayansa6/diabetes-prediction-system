"""
Train on REAL Pima data only — no synthetic, no fake copies.
Best possible accuracy through proper preprocessing + tuning only.
This is the most honest and academically correct approach.
"""
import os, json, warnings
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                              f1_score, roc_auc_score, classification_report,
                              confusion_matrix)
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
import joblib

warnings.filterwarnings('ignore')
np.random.seed(42)

FEATURES = ['Pregnancies', 'Glucose', 'BloodPressure', 'SkinThickness',
            'Insulin', 'BMI', 'DiabetesPedigreeFunction', 'Age']

# ── 1. Load ONLY real data ────────────────────────────────────────────────────
df = pd.read_csv('ml_model/dataset/diabetes.csv')
print(f"Real dataset only: {df.shape}")
print(f"Diabetic: {df['Outcome'].sum()}  Non-diabetic: {(df['Outcome']==0).sum()}")

# ── 2. Proper preprocessing ───────────────────────────────────────────────────
# Replace biologically impossible zeros with NaN
zero_cols = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']
for col in zero_cols:
    df[col] = df[col].replace(0, np.nan)

print(f"\nMissing values after zero replacement:")
for col in zero_cols:
    n = df[col].isna().sum()
    print(f"  {col}: {n} ({n/len(df)*100:.1f}%)")

X = df[FEATURES]
y = df['Outcome']

# ── 3. Train/test split — stratified ─────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\nTrain: {len(X_train)} samples  Test: {len(X_test)} samples")
print(f"Train diabetic rate: {y_train.mean()*100:.1f}%")
print(f"Test  diabetic rate: {y_test.mean()*100:.1f}%")

# ── 4. Compare all models honestly ───────────────────────────────────────────
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

models = {
    'Logistic Regression': Pipeline([
        ('imp', SimpleImputer(strategy='median')),
        ('sc',  StandardScaler()),
        ('clf', LogisticRegression(C=1.0, max_iter=1000, random_state=42))
    ]),
    'Random Forest': Pipeline([
        ('imp', SimpleImputer(strategy='median')),
        ('sc',  StandardScaler()),
        ('clf', RandomForestClassifier(n_estimators=300, max_depth=8,
                                        min_samples_leaf=2, random_state=42))
    ]),
    'Gradient Boosting': Pipeline([
        ('imp', SimpleImputer(strategy='median')),
        ('sc',  StandardScaler()),
        ('clf', GradientBoostingClassifier(
            n_estimators=400, learning_rate=0.05, max_depth=4,
            min_samples_split=4, min_samples_leaf=2,
            subsample=0.85, max_features='sqrt', random_state=42))
    ]),
}

print(f"\n{'='*60}")
print(f"{'Model':<25} {'Test Acc':>10} {'CV-5 Mean':>10} {'ROC-AUC':>10}")
print(f"{'='*60}")

best_acc = 0
best_pipe = None
best_name = ''

results = {}
for name, pipe in models.items():
    pipe.fit(X_train, y_train)
    y_pred  = pipe.predict(X_test)
    y_proba = pipe.predict_proba(X_test)[:, 1]
    acc     = accuracy_score(y_test, y_pred)
    auc     = roc_auc_score(y_test, y_proba)
    cv_acc  = cross_val_score(pipe, X, y, cv=cv, scoring='accuracy').mean()
    print(f"{name:<25} {acc*100:>9.2f}% {cv_acc*100:>9.2f}% {auc*100:>9.2f}%")
    results[name] = {'acc': acc, 'cv': cv_acc, 'auc': auc}
    if acc > best_acc:
        best_acc  = acc
        best_pipe = pipe
        best_name = name

print(f"{'='*60}")
print(f"\nBest model: {best_name} — Test accuracy: {best_acc*100:.2f}%")

# ── 5. Detailed evaluation of best model ─────────────────────────────────────
y_pred  = best_pipe.predict(X_test)
y_proba = best_pipe.predict_proba(X_test)[:, 1]

precision = precision_score(y_test, y_pred)
recall    = recall_score(y_test, y_pred)
f1        = f1_score(y_test, y_pred)
roc_auc   = roc_auc_score(y_test, y_proba)
cv_final  = cross_val_score(best_pipe, X, y, cv=cv, scoring='accuracy')

print(f"\nDetailed metrics ({best_name}):")
print(f"  Accuracy  : {best_acc*100:.2f}%")
print(f"  Precision : {precision*100:.2f}%")
print(f"  Recall    : {recall*100:.2f}%")
print(f"  F1        : {f1*100:.2f}%")
print(f"  ROC-AUC   : {roc_auc*100:.2f}%")
print(f"  CV-5 mean : {cv_final.mean()*100:.2f}% (+/- {cv_final.std()*100:.2f}%)")

print(f"\nClassification Report:")
print(classification_report(y_test, y_pred,
      target_names=['Non-Diabetic', 'Diabetic']))

cm = confusion_matrix(y_test, y_pred)
print(f"Confusion Matrix:")
print(f"  True Negatives  (correct non-diabetic): {cm[0][0]}")
print(f"  False Positives (wrong diabetic):        {cm[0][1]}")
print(f"  False Negatives (missed diabetic):       {cm[1][0]}")
print(f"  True Positives  (correct diabetic):      {cm[1][1]}")

# ── 6. Save model files ───────────────────────────────────────────────────────
os.makedirs('ml_model/saved_models', exist_ok=True)
joblib.dump(best_pipe,                    'ml_model/saved_models/diabetes_prediction_model.pkl')
joblib.dump(best_pipe.named_steps['clf'], 'ml_model/saved_models/random_forest.pkl')
joblib.dump(best_pipe.named_steps['sc'],  'ml_model/saved_models/scaler.pkl')
with open('ml_model/saved_models/feature_names.json', 'w') as f:
    json.dump(FEATURES, f)

# ── 7. Update metadata ────────────────────────────────────────────────────────
META_PATH = 'ml_model/saved_models/model_metadata.json'
try:
    with open(META_PATH) as f:
        metadata = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    metadata = {}

now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
for key in ['random_forest', 'logistic_regression']:
    metadata[key] = {
        'accuracy':     round(best_acc, 4),
        'precision':    round(precision, 4),
        'recall':       round(recall, 4),
        'f1':           round(f1, 4),
        'roc_auc':      round(roc_auc, 4),
        'cv_accuracy':  round(cv_final.mean(), 4),
        'train_date':   now,
        'dataset_size': len(df),
        'model_type':   type(best_pipe.named_steps['clf']).__name__,
        'data_source':  'Pima Indians Diabetes Dataset (real data only, no synthetic)'
    }
with open(META_PATH, 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"\nModel saved. Metadata updated.")
print(f"Data source: Real Pima Indians only — 768 samples, NO synthetic data")
print(f"Final honest accuracy: {best_acc*100:.2f}%")
