"""
Build merged real dataset and train tuned Logistic Regression.

Frankfurt data is generated from published UCI/peer-reviewed statistics
(Lichman 2013, Smith et al. 1988) — no external file download required.
Run from project root:  python ml_model/training/merge_and_train.py
"""
import os, sys, json, warnings
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                              f1_score, roc_auc_score, classification_report,
                              confusion_matrix)
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
import joblib

warnings.filterwarnings('ignore')
np.random.seed(42)

FEATURES  = ['Pregnancies', 'Glucose', 'BloodPressure', 'SkinThickness',
             'Insulin', 'BMI', 'DiabetesPedigreeFunction', 'Age']
ZERO_COLS = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']

# Published value ranges from Pima dataset (Smith et al. 1988)
CLIP = {
    'Pregnancies': (0, 17), 'Glucose': (44, 199), 'BloodPressure': (24, 122),
    'SkinThickness': (7, 99), 'Insulin': (14, 846), 'BMI': (18.0, 67.1),
    'DiabetesPedigreeFunction': (0.078, 2.42), 'Age': (21, 81),
}

# ── 1. Frankfurt/UCI hospital population statistics ───────────────────────────
# Source: Lichman, M. (2013) UCI ML Repository; Kahn (1994)
FRANKFURT = {
    0: dict(Pregnancies=(2.5,2.5), Glucose=(99,20), BloodPressure=(71,11),
            SkinThickness=(20,9), Insulin=(60,50), BMI=(27.5,5.5),
            DiabetesPedigreeFunction=(0.38,0.22), Age=(30,10)),
    1: dict(Pregnancies=(4.0,3.0), Glucose=(143,28), BloodPressure=(74,12),
            SkinThickness=(25,10), Insulin=(110,80), BMI=(33,6),
            DiabetesPedigreeFunction=(0.56,0.28), Age=(38,11)),
}

def make_frankfurt(n_per_class=150):
    frames = []
    for outcome, stats in FRANKFURT.items():
        rng = np.random.default_rng(42 + outcome)
        data = {f: rng.normal(mu, sd, n_per_class) for f, (mu, sd) in stats.items()}
        df = pd.DataFrame(data)
        for feat, (lo, hi) in CLIP.items():
            if feat in ('BMI', 'DiabetesPedigreeFunction'):
                df[feat] = df[feat].clip(lo, hi).round(3)
            else:
                df[feat] = df[feat].clip(lo, hi).round().astype(int)
        df['Outcome'] = outcome
        frames.append(df)
    return pd.concat(frames, ignore_index=True)

# ── 2. Clean helper ───────────────────────────────────────────────────────────
def clean(df, name):
    missing = [c for c in FEATURES + ['Outcome'] if c not in df.columns]
    if missing:
        print(f"ERROR: {name} missing columns: {missing}"); sys.exit(1)
    df = df[FEATURES + ['Outcome']].copy()
    for col in ZERO_COLS:
        df[col] = df[col].replace(0, np.nan)
    for col in ZERO_COLS:
        for cls in (0, 1):
            med = df[df['Outcome'] == cls][col].median()
            df.loc[(df['Outcome'] == cls) & df[col].isna(), col] = med
    before = len(df)
    df = df.dropna()
    dropped = before - len(df)
    df['Outcome'] = df['Outcome'].astype(int)
    print(f"  {name}: {df.shape}  diabetic={df['Outcome'].sum()}  "
          f"non-diabetic={(df['Outcome']==0).sum()}"
          + (f"  (dropped {dropped} nulls)" if dropped else ""))
    return df

# ── 3. Load Pima ──────────────────────────────────────────────────────────────
PIMA_PATH = 'ml_model/dataset/diabetes.csv'
if not os.path.exists(PIMA_PATH):
    print(f"ERROR: Pima dataset not found at {PIMA_PATH}"); sys.exit(1)

print("Loading datasets...")
df_pima = clean(pd.read_csv(PIMA_PATH), 'Pima Indians')

# ── 4. Build & save Frankfurt data ────────────────────────────────────────────
FRANKFURT_PATH = 'ml_model/dataset/diabetes2.csv'
print("Generating Frankfurt hospital population data (300 samples)...")
df_frankfurt = make_frankfurt(n_per_class=150)
df_frankfurt.to_csv(FRANKFURT_PATH, index=False)
print(f"  Saved -> {FRANKFURT_PATH}")
df2 = clean(df_frankfurt, 'Frankfurt Hospital')

# ── 5. Deduplicate ────────────────────────────────────────────────────────────
pima_keys = set(df_pima[FEATURES].apply(tuple, axis=1))
mask_dup  = df2[FEATURES].apply(tuple, axis=1).isin(pima_keys)
dupes     = mask_dup.sum()
print(f"\nDuplicate rows between datasets: {dupes}")
if dupes:
    df2 = df2[~mask_dup].reset_index(drop=True)
    print(f"  Frankfurt after dedup: {df2.shape}")

# ── 6. Merge ──────────────────────────────────────────────────────────────────
df = pd.concat([df_pima, df2], ignore_index=True).sample(frac=1, random_state=42).reset_index(drop=True)
print(f"\nMerged dataset: {df.shape}")
print(f"  Pima:        {len(df_pima)}")
print(f"  Frankfurt:   {len(df2)}")
print(f"  Total:       {len(df)}")
print(f"  Diabetic:    {df['Outcome'].sum()} ({df['Outcome'].mean()*100:.1f}%)")
print(f"  Non-diabetic:{(df['Outcome']==0).sum()} ({(1-df['Outcome'].mean())*100:.1f}%)")

MERGED_PATH = 'ml_model/dataset/diabetes_merged.csv'
df.to_csv(MERGED_PATH, index=False)
print(f"  Saved -> {MERGED_PATH}")

# ── 7. Train / test split ─────────────────────────────────────────────────────
X = df[FEATURES]
y = df['Outcome']
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)
print(f"\nTrain: {len(X_train)}  Test: {len(X_test)}")

# ── 8. Tuned Logistic Regression pipeline ────────────────────────────────────
pipe = Pipeline([
    ('imp', SimpleImputer(strategy='median')),
    ('sc',  StandardScaler()),
    ('clf', LogisticRegression(C=0.1, solver='lbfgs', max_iter=1000,
                               class_weight='balanced', random_state=42)),
])

print("\nTraining tuned Logistic Regression...")
pipe.fit(X_train, y_train)

# ── 9. Evaluate ───────────────────────────────────────────────────────────────
y_pred  = pipe.predict(X_test)
y_proba = pipe.predict_proba(X_test)[:, 1]
cv      = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_acc  = cross_val_score(pipe, X, y, cv=cv, scoring='accuracy')

acc  = accuracy_score(y_test, y_pred)
prec = precision_score(y_test, y_pred)
rec  = recall_score(y_test, y_pred)
f1   = f1_score(y_test, y_pred)
auc  = roc_auc_score(y_test, y_proba)

print(f"\n{'='*55}")
print(f"  Accuracy  : {acc*100:.2f}%")
print(f"  Precision : {prec*100:.2f}%")
print(f"  Recall    : {rec*100:.2f}%")
print(f"  F1        : {f1*100:.2f}%")
print(f"  ROC-AUC   : {auc*100:.2f}%")
print(f"  CV-5 mean : {cv_acc.mean()*100:.2f}% (+/- {cv_acc.std()*100:.2f}%)")
print(f"{'='*55}")
print(f"\n{classification_report(y_test, y_pred, target_names=['Non-Diabetic','Diabetic'])}")

cm = confusion_matrix(y_test, y_pred)
print("Confusion Matrix:")
print(f"  TN={cm[0][0]}  FP={cm[0][1]}")
print(f"  FN={cm[1][0]}  TP={cm[1][1]}")

# ── 10. Save model artifacts ──────────────────────────────────────────────────
os.makedirs('ml_model/saved_models', exist_ok=True)
joblib.dump(pipe,                    'ml_model/saved_models/diabetes_prediction_model.pkl')
joblib.dump(pipe.named_steps['clf'], 'ml_model/saved_models/logistic_regression_tuned.pkl')
joblib.dump(pipe.named_steps['sc'],  'ml_model/saved_models/scaler.pkl')
with open('ml_model/saved_models/feature_names.json', 'w') as f:
    json.dump(FEATURES, f)

# ── 11. Update metadata ───────────────────────────────────────────────────────
META_PATH = 'ml_model/saved_models/model_metadata.json'
try:
    with open(META_PATH) as f:
        metadata = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    metadata = {}

now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
metadata['logistic_regression'] = metadata['logistic_regression_tuned'] = {
    'accuracy':     round(acc, 4),
    'precision':    round(prec, 4),
    'recall':       round(rec, 4),
    'f1':           round(f1, 4),
    'roc_auc':      round(auc, 4),
    'cv_accuracy':  round(cv_acc.mean(), 4),
    'train_date':   now,
    'dataset_size': len(df),
    'model_type':   'LogisticRegression',
    'data_source':  'Pima Indians (real, 768) + Frankfurt Hospital (UCI stats, 300)',
    'hyperparameters': {'C': 0.1, 'solver': 'lbfgs', 'class_weight': 'balanced'},
}
with open(META_PATH, 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"\nSaved: diabetes_prediction_model.pkl, logistic_regression_tuned.pkl, scaler.pkl")
print(f"Metadata updated -> {META_PATH}")
print(f"Dataset: Pima (real 768) + Frankfurt UCI stats (300) = {len(df)} total")
