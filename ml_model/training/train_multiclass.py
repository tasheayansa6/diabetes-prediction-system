"""
Train 3-class diabetes model: Non-Diabetic / Pre-Diabetic / Diabetic
Using ADA clinical glucose thresholds to create the Pre-Diabetic class.
"""
import pandas as pd, numpy as np, joblib, json, warnings
warnings.filterwarnings('ignore')
from datetime import datetime
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler, label_binarize
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (accuracy_score, classification_report,
    confusion_matrix, roc_auc_score, f1_score, precision_score, recall_score)
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH   = os.path.join(BASE, 'dataset', 'diabetes.csv')
MODELS_DIR  = os.path.join(BASE, 'saved_models')
os.makedirs(MODELS_DIR, exist_ok=True)

# ── Load and clean ────────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
zero_cols = ['Glucose','BloodPressure','SkinThickness','Insulin','BMI']
for col in zero_cols:
    df[col] = df[col].astype(float)
    df.loc[df[col]==0, col] = np.nan

# Per-class median imputation using original binary Outcome
for col in zero_cols:
    m0 = df[df['Outcome']==0][col].median()
    m1 = df[df['Outcome']==1][col].median()
    df.loc[(df['Outcome']==0) & df[col].isna(), col] = m0
    df.loc[(df['Outcome']==1) & df[col].isna(), col] = m1

# ── Create 3-class labels (ADA clinical thresholds) ──────────────────────────
# Class 0 = Non-Diabetic:  Outcome=0 AND Glucose < 100 mg/dL
# Class 1 = Pre-Diabetic:  Outcome=0 AND Glucose >= 100 mg/dL (impaired fasting glucose)
# Class 2 = Diabetic:      Outcome=1 (confirmed diabetic)
def make_class(row):
    if row['Outcome'] == 1:
        return 2
    elif row['Glucose'] >= 100:
        return 1
    else:
        return 0

df['Class'] = df.apply(make_class, axis=1)

CLASS_NAMES = {0: 'Non-Diabetic', 1: 'Pre-Diabetic', 2: 'Diabetic'}

print("=" * 60)
print("3-CLASS DIABETES MODEL TRAINING")
print("=" * 60)
print("\nClass distribution:")
for c, label in CLASS_NAMES.items():
    n = sum(df['Class']==c)
    print("  Class %d (%s): %d samples (%.1f%%)" % (c, label, n, n/len(df)*100))

X = df.drop(['Outcome','Class'], axis=1)
y = df['Class']
feat_names = list(X.columns)

print("\nDataset: %d total | Features: %s" % (len(df), feat_names))

# ── Split ─────────────────────────────────────────────────────────────────────
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print("Train: %d | Test: %d" % (len(X_tr), len(X_te)))

# ── Scale ─────────────────────────────────────────────────────────────────────
scaler = StandardScaler()
X_tr_s = scaler.fit_transform(X_tr)
X_te_s  = scaler.transform(X_te)
X_s     = scaler.transform(X)

# ── Train ─────────────────────────────────────────────────────────────────────
model = GradientBoostingClassifier(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=3,
    min_samples_split=20,
    min_samples_leaf=10,
    subsample=0.8,
    max_features='sqrt',
    random_state=42
)
print("\nTraining Gradient Boosting (3-class)...")
model.fit(X_tr_s, y_tr)

# ── Evaluate ──────────────────────────────────────────────────────────────────
y_pred  = model.predict(X_te_s)
y_proba = model.predict_proba(X_te_s)

train_acc = accuracy_score(y_tr, model.predict(X_tr_s))
test_acc  = accuracy_score(y_te, y_pred)
gap       = (train_acc - test_acc) * 100

# Multiclass ROC-AUC (one-vs-rest macro average)
y_te_bin = label_binarize(y_te, classes=[0,1,2])
auc_ovr  = roc_auc_score(y_te_bin, y_proba, multi_class='ovr', average='macro')

macro_f1  = f1_score(y_te, y_pred, average='macro')
macro_pre = precision_score(y_te, y_pred, average='macro')
macro_rec = recall_score(y_te, y_pred, average='macro')

print("\n=== TEST SET RESULTS ===")
print("Train Accuracy : %.2f%%" % (train_acc*100))
print("Test Accuracy  : %.2f%%" % (test_acc*100))
print("Overfit Gap    : %.2f%%" % gap)
print("ROC-AUC (OvR)  : %.2f%%" % (auc_ovr*100))
print("Macro F1       : %.2f%%" % (macro_f1*100))
print("Macro Precision: %.2f%%" % (macro_pre*100))
print("Macro Recall   : %.2f%%" % (macro_rec*100))
print()
print(classification_report(y_te, y_pred,
    target_names=['Non-Diabetic','Pre-Diabetic','Diabetic']))

print("Confusion Matrix:")
cm = confusion_matrix(y_te, y_pred)
print("                Non-Diabetic  Pre-Diabetic  Diabetic")
for i, row in enumerate(cm):
    print("  %-14s %s" % (CLASS_NAMES[i], row))

# ── Cross-validation ──────────────────────────────────────────────────────────
cv = StratifiedKFold(5, shuffle=True, random_state=42)
cv_acc = cross_val_score(model, X_s, y, cv=cv, scoring='accuracy')
cv_f1  = cross_val_score(model, X_s, y, cv=cv, scoring='f1_macro')
print("\n=== 5-FOLD CROSS-VALIDATION ===")
print("CV Accuracy : %.2f%% +/- %.2f%%" % (cv_acc.mean()*100, cv_acc.std()*100))
print("CV F1 Macro : %.2f%% +/- %.2f%%" % (cv_f1.mean()*100, cv_f1.std()*100))

# ── Feature importance ────────────────────────────────────────────────────────
fi = sorted(zip(feat_names, model.feature_importances_), key=lambda x: -x[1])
print("\n=== FEATURE IMPORTANCE ===")
for name, imp in fi:
    bar = '#' * int(imp * 50)
    print("  %-30s %.1f%%  %s" % (name, imp*100, bar))

# ── Save ──────────────────────────────────────────────────────────────────────
model_path  = os.path.join(MODELS_DIR, 'gradient_boosting.pkl')
scaler_path = os.path.join(MODELS_DIR, 'scaler.pkl')
feat_path   = os.path.join(MODELS_DIR, 'feature_names.json')
meta_path   = os.path.join(MODELS_DIR, 'model_metadata.json')

joblib.dump(model,  model_path)
joblib.dump(scaler, scaler_path)
with open(feat_path, 'w') as f:
    json.dump(feat_names, f)

meta = {
    'algorithm': 'Gradient Boosting (3-Class)',
    'version': 'v3.0.0',
    'trained_at': datetime.utcnow().isoformat(),
    'sklearn_version': '1.8.0',
    'task': 'multiclass_classification',
    'classes': CLASS_NAMES,
    'class_thresholds': {
        'Non-Diabetic': 'Outcome=0 AND Glucose < 100 mg/dL',
        'Pre-Diabetic':  'Outcome=0 AND Glucose >= 100 mg/dL (ADA impaired fasting glucose)',
        'Diabetic':      'Outcome=1 (confirmed diabetic)'
    },
    'accuracy': round(test_acc*100, 2),
    'roc_auc_ovr': round(auc_ovr*100, 2),
    'macro_f1': round(macro_f1*100, 2),
    'macro_precision': round(macro_pre*100, 2),
    'macro_recall': round(macro_rec*100, 2),
    'train_accuracy': round(train_acc*100, 2),
    'overfitting_gap': round(gap, 2),
    'cv_accuracy': round(cv_acc.mean()*100, 2),
    'cv_accuracy_std': round(cv_acc.std()*100, 2),
    'cv_f1_macro': round(cv_f1.mean()*100, 2),
    'cv_f1_macro_std': round(cv_f1.std()*100, 2),
    'training_samples': len(X_tr),
    'test_samples': len(X_te),
    'features': feat_names,
    'n_features': len(feat_names),
    'n_classes': 3,
    'hyperparameters': {
        'n_estimators': 200, 'learning_rate': 0.05, 'max_depth': 3,
        'min_samples_split': 20, 'min_samples_leaf': 10,
        'subsample': 0.8, 'max_features': 'sqrt', 'random_state': 42
    }
}
with open(meta_path, 'w') as f:
    json.dump(meta, f, indent=2)

print("\n" + "=" * 60)
print("Saved v3.0.0 multiclass model")
print("  Model  ->", model_path)
print("  Scaler ->", scaler_path)
print("=" * 60)
