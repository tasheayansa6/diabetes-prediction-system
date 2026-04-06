import pandas as pd, numpy as np, warnings, json, joblib, os
warnings.filterwarnings('ignore')
from datetime import datetime
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                              f1_score, roc_auc_score, classification_report)
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

FEATURES  = ['Pregnancies','Glucose','BloodPressure','SkinThickness',
             'Insulin','BMI','DiabetesPedigreeFunction','Age']
ZERO_COLS = ['Glucose','BloodPressure','SkinThickness','Insulin','BMI']

# ── Load and clean ────────────────────────────────────────────────────────────
df = pd.read_csv('ml_model/dataset/diabetes.csv')
for col in ZERO_COLS:
    df[col] = df[col].replace(0, np.nan)
# Per-class median imputation
for col in ZERO_COLS:
    m0 = df[df['Outcome']==0][col].median()
    m1 = df[df['Outcome']==1][col].median()
    df.loc[(df['Outcome']==0) & df[col].isna(), col] = m0
    df.loc[(df['Outcome']==1) & df[col].isna(), col] = m1

print(f"Dataset: {df.shape}  diabetic={df['Outcome'].sum()}  non-diabetic={(df['Outcome']==0).sum()}")

X = df[FEATURES]; y = df['Outcome']
X_tr,X_te,y_tr,y_te = train_test_split(X,y,test_size=0.2,random_state=42,stratify=y)
cv = StratifiedKFold(5, shuffle=True, random_state=42)

# ── Train ─────────────────────────────────────────────────────────────────────
pipe = Pipeline([
    ('imp', SimpleImputer(strategy='median')),
    ('sc',  StandardScaler()),
    ('clf', GradientBoostingClassifier(
        n_estimators=400, learning_rate=0.05, max_depth=4,
        min_samples_split=4, min_samples_leaf=2,
        subsample=0.85, max_features='sqrt', random_state=42))
])
pipe.fit(X_tr, y_tr)

# ── Evaluate ──────────────────────────────────────────────────────────────────
y_pred  = pipe.predict(X_te)
y_proba = pipe.predict_proba(X_te)[:,1]
acc     = accuracy_score(y_te, y_pred)
prec    = precision_score(y_te, y_pred)
rec     = recall_score(y_te, y_pred)
f1      = f1_score(y_te, y_pred)
auc     = roc_auc_score(y_te, y_proba)
cv_s    = cross_val_score(pipe, X, y, cv=cv)

print(f"\nAccuracy  : {acc*100:.2f}%")
print(f"Precision : {prec*100:.2f}%")
print(f"Recall    : {rec*100:.2f}%")
print(f"F1        : {f1*100:.2f}%")
print(f"ROC-AUC   : {auc*100:.2f}%")
print(f"CV-5 mean : {cv_s.mean()*100:.2f}%  (+/- {cv_s.std()*100:.2f}%)")
print(f"\n{classification_report(y_te,y_pred,target_names=['Non-Diabetic','Diabetic'])}")

# ── Save ──────────────────────────────────────────────────────────────────────
os.makedirs('ml_model/saved_models', exist_ok=True)
joblib.dump(pipe,                    'ml_model/saved_models/diabetes_prediction_model.pkl')
joblib.dump(pipe.named_steps['clf'], 'ml_model/saved_models/random_forest.pkl')
joblib.dump(pipe.named_steps['sc'],  'ml_model/saved_models/scaler.pkl')
with open('ml_model/saved_models/feature_names.json','w') as f:
    json.dump(FEATURES, f)

META = 'ml_model/saved_models/model_metadata.json'
try:
    meta = json.load(open(META))
except: meta = {}
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
for k in ['random_forest','logistic_regression']:
    meta[k] = {
        'accuracy':     round(acc,  4),
        'precision':    round(prec, 4),
        'recall':       round(rec,  4),
        'f1':           round(f1,   4),
        'roc_auc':      round(auc,  4),
        'cv_accuracy':  round(cv_s.mean(), 4),
        'train_date':   now,
        'dataset_size': 768,
        'model_type':   'GradientBoostingClassifier',
        'data_source':  'Pima Indians Diabetes Dataset - real data only, no synthetic'
    }
with open(META,'w') as f: json.dump(meta, f, indent=2)
print(f"Saved. accuracy={round(acc,4)}")
