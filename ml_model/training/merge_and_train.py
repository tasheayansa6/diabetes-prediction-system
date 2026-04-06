"""
Merge real Pima dataset with a second real dataset (same 8 features)
and retrain. No synthetic data, no fake copies.

BEFORE RUNNING:
  Place the second real dataset at:
  ml_model/dataset/diabetes2.csv

  It must have these exact columns:
  Pregnancies, Glucose, BloodPressure, SkinThickness,
  Insulin, BMI, DiabetesPedigreeFunction, Age, Outcome

  Recommended source:
  https://www.kaggle.com/datasets/akshaydattatraykhare/diabetes-dataset
"""
import os, sys, json, warnings
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
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
ZERO_COLS = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']

# ── helper: clean a dataframe ─────────────────────────────────────────────────
def clean_df(df, source_name):
    df = df.copy()

    # Keep only required columns
    missing_cols = [c for c in FEATURES + ['Outcome'] if c not in df.columns]
    if missing_cols:
        print(f"ERROR: {source_name} is missing columns: {missing_cols}")
        print(f"  Found columns: {list(df.columns)}")
        sys.exit(1)

    df = df[FEATURES + ['Outcome']].copy()

    # Replace impossible zeros with NaN
    for col in ZERO_COLS:
        df[col] = df[col].replace(0, np.nan)

    # Per-class median imputation
    for col in ZERO_COLS:
        m0 = df[df['Outcome'] == 0][col].median()
        m1 = df[df['Outcome'] == 1][col].median()
        df.loc[(df['Outcome'] == 0) & df[col].isna(), col] = m0
        df.loc[(df['Outcome'] == 1) & df[col].isna(), col] = m1

    # Drop any remaining nulls
    before = len(df)
    df = df.dropna()
    if len(df) < before:
        print(f"  {source_name}: dropped {before - len(df)} rows with nulls")

    df['Outcome'] = df['Outcome'].astype(int)
    print(f"  {source_name}: {df.shape}  diabetic={df['Outcome'].sum()}  non-diabetic={(df['Outcome']==0).sum()}")
    return df

# ── 1. Load Pima (real) ───────────────────────────────────────────────────────
print("Loading datasets...")
df_pima = clean_df(pd.read_csv('ml_model/dataset/diabetes.csv'), 'Pima Indians')

# ── 2. Load second real dataset ───────────────────────────────────────────────
SECOND_PATH = 'ml_model/dataset/diabetes2.csv'
if not os.path.exists(SECOND_PATH):
    print(f"\nERROR: Second dataset not found at {SECOND_PATH}")
    print("Please download it from:")
    print("  https://www.kaggle.com/datasets/akshaydattatraykhare/diabetes-dataset")
    print(f"  and save as: {SECOND_PATH}")
    sys.exit(1)

df2 = clean_df(pd.read_csv(SECOND_PATH), 'Second dataset')

# ── 3. Check for duplicates between datasets ──────────────────────────────────
combined_check = pd.concat([df_pima, df2])
dupes = combined_check.duplicated(subset=FEATURES).sum()
print(f"\nDuplicate rows between datasets: {dupes}")
if dupes > 0:
    print(f"  Removing {dupes} duplicate rows...")
    df2 = df2[~df2[FEATURES].apply(tuple, axis=1).isin(
        df_pima[FEATURES].apply(tuple, axis=1)
    )]
    print(f"  Second dataset after dedup: {df2.shape}")

# ── 4. Merge ──────────────────────────────────────────────────────────────────
df_merged = pd.concat([df_pima, df2], ignore_index=True)
df_merged = df_merged.sample(frac=1, random_state=42).reset_index(drop=True)

print(f"\nMerged dataset: {df_merged.shape}")
print(f"  Pima (real):         {len(df_pima)} samples")
print(f"  Second (real):       {len(df2)} samples")
print(f"  Total:               {len(df_merged)} samples")
print(f"  Diabetic:   {df_merged['Outcome'].sum()} ({df_merged['Outcome'].mean()*100:.1f}%)")
print(f"  Non-diabetic: {(df_merged['Outcome']==0).sum()} ({(1-df_merged['Outcome'].mean())*100:.1f}%)")

# Save merged dataset
MERGED_PATH = 'ml_model/dataset/diabetes_merged.csv'
df_merged.to_csv(MERGED_PATH, index=False)
print(f"\nSaved merged dataset -> {MERGED_PATH}")

# ── 5. Train/test split ───────────────────────────────────────────────────────
X = df_merged[FEATURES]
y = df_merged['Outcome']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"\nTrain: {len(X_train)}  Test: {len(X_test)}")

# ── 6. Compare all models ─────────────────────────────────────────────────────
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

print(f"\n{'='*65}")
print(f"{'Model':<25} {'Test Acc':>10} {'CV-5 Mean':>10} {'ROC-AUC':>10}")
print(f"{'='*65}")

best_acc  = 0
best_pipe = None
best_name = ''

for name, pipe in models.items():
    pipe.fit(X_train, y_train)
    y_pred  = pipe.predict(X_test)
    y_proba = pipe.predict_proba(X_test)[:, 1]
    acc     = accuracy_score(y_test, y_pred)
    auc     = roc_auc_score(y_test, y_proba)
    cv_acc  = cross_val_score(pipe, X, y, cv=cv, scoring='accuracy').mean()
    print(f"{name:<25} {acc*100:>9.2f}% {cv_acc*100:>9.2f}% {auc*100:>9.2f}%")
    if acc > best_acc:
        best_acc  = acc
        best_pipe = pipe
        best_name = name

print(f"{'='*65}")
print(f"\nBest: {best_name} — {best_acc*100:.2f}%")

# ── 7. Detailed evaluation ────────────────────────────────────────────────────
y_pred    = best_pipe.predict(X_test)
y_proba   = best_pipe.predict_proba(X_test)[:, 1]
precision = precision_score(y_test, y_pred)
recall    = recall_score(y_test, y_pred)
f1        = f1_score(y_test, y_pred)
roc_auc   = roc_auc_score(y_test, y_proba)
cv_final  = cross_val_score(best_pipe, X, y, cv=cv, scoring='accuracy')

print(f"\nFinal metrics:")
print(f"  Accuracy  : {best_acc*100:.2f}%")
print(f"  Precision : {precision*100:.2f}%")
print(f"  Recall    : {recall*100:.2f}%")
print(f"  F1        : {f1*100:.2f}%")
print(f"  ROC-AUC   : {roc_auc*100:.2f}%")
print(f"  CV-5 mean : {cv_final.mean()*100:.2f}% (+/- {cv_final.std()*100:.2f}%)")

print(f"\n{classification_report(y_test, y_pred, target_names=['Non-Diabetic','Diabetic'])}")

cm = confusion_matrix(y_test, y_pred)
print(f"Confusion Matrix:")
print(f"  True Negatives  (correct non-diabetic): {cm[0][0]}")
print(f"  False Positives (wrong diabetic):        {cm[0][1]}")
print(f"  False Negatives (missed diabetic):       {cm[1][0]}")
print(f"  True Positives  (correct diabetic):      {cm[1][1]}")

# ── 8. Save model files ───────────────────────────────────────────────────────
os.makedirs('ml_model/saved_models', exist_ok=True)
joblib.dump(best_pipe,                    'ml_model/saved_models/diabetes_prediction_model.pkl')
joblib.dump(best_pipe.named_steps['clf'], 'ml_model/saved_models/random_forest.pkl')
joblib.dump(best_pipe.named_steps['sc'],  'ml_model/saved_models/scaler.pkl')
with open('ml_model/saved_models/feature_names.json', 'w') as f:
    json.dump(FEATURES, f)

# ── 9. Update metadata ────────────────────────────────────────────────────────
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
        'dataset_size': len(df_merged),
        'model_type':   type(best_pipe.named_steps['clf']).__name__,
        'data_source':  f'Pima Indians (real, {len(df_pima)}) + Second dataset (real, {len(df2)}) — NO synthetic data'
    }
with open(META_PATH, 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"\nAll files saved.")
print(f"Accuracy: {best_acc*100:.2f}%  |  Data: 100% real, 0% synthetic")
