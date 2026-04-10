"""
Retrain ALL models with venv sklearn 1.2.2 — fixes incompatibility.
Run: venv\Scripts\python.exe retrain_all.py
"""
import joblib, json, warnings
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
from pathlib import Path

warnings.filterwarnings('ignore')

DATA   = Path('ml_model/dataset/diabetes.csv')
MODELS = Path('ml_model/saved_models')

print('Loading data...')
df = pd.read_csv(DATA)
print(f'  Shape: {df.shape}')

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

joblib.dump(scaler, MODELS / 'scaler.pkl')
joblib.dump(scaler, MODELS / 'scaler_rf.pkl')
with open(MODELS / 'feature_names.json', 'w') as f:
    json.dump(features, f)

# 1. Gradient Boosting
print('Training Gradient Boosting...')
gb = GradientBoostingClassifier(
    n_estimators=200, learning_rate=0.05, max_depth=4,
    min_samples_split=10, min_samples_leaf=4,
    subsample=0.8, random_state=42)
gb.fit(Xs, y_train)
acc = accuracy_score(y_test, gb.predict(Xt))
auc = roc_auc_score(y_test, gb.predict_proba(Xt)[:,1])
print(f'  Accuracy={acc*100:.2f}%  AUC={auc*100:.2f}%')
joblib.dump(gb, MODELS / 'gradient_boosting.pkl')

# 2. Random Forest
print('Training Random Forest...')
rf = RandomForestClassifier(
    n_estimators=100, max_depth=10, min_samples_split=5,
    min_samples_leaf=2, random_state=42, n_jobs=-1)
rf.fit(Xs, y_train)
acc = accuracy_score(y_test, rf.predict(Xt))
auc = roc_auc_score(y_test, rf.predict_proba(Xt)[:,1])
print(f'  Accuracy={acc*100:.2f}%  AUC={auc*100:.2f}%')
joblib.dump(rf, MODELS / 'random_forest.pkl')

# 3. Logistic Regression
print('Training Logistic Regression...')
lr = LogisticRegression(
    C=0.1, max_iter=1000, solver='lbfgs',
    class_weight='balanced', random_state=42)
lr.fit(Xs, y_train)
acc = accuracy_score(y_test, lr.predict(Xt))
auc = roc_auc_score(y_test, lr.predict_proba(Xt)[:,1])
print(f'  Accuracy={acc*100:.2f}%  AUC={auc*100:.2f}%')
joblib.dump(lr, MODELS / 'logistic_regression.pkl')
joblib.dump(lr, MODELS / 'logistic_regression_tuned.pkl')

print()
print('All 3 models saved with sklearn 1.2.2')
print('Restart server: venv\\Scripts\\python.exe run.py')
