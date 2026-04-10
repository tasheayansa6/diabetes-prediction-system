"""
Retrain and save a fresh gradient_boosting.pkl compatible with current sklearn.
Run: venv\Scripts\python.exe fix_model_now.py
"""
import joblib, json, numpy as np, pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from pathlib import Path

BASE   = Path(__file__).parent
DATA   = BASE / 'ml_model/dataset/diabetes.csv'
MODELS = BASE / 'ml_model/saved_models'

print("Loading data...")
df = pd.read_csv(DATA)
print(f"  Shape: {df.shape}")

# Impute zeros
for col in ['Glucose','BloodPressure','SkinThickness','Insulin','BMI']:
    for cls in [0,1]:
        med = df.loc[(df['Outcome']==cls)&(df[col]!=0), col].median()
        df.loc[(df['Outcome']==cls)&(df[col]==0), col] = med

X = df.drop('Outcome', axis=1)
y = df['Outcome']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

scaler = StandardScaler()
Xs = scaler.fit_transform(X_train)
Xt = scaler.transform(X_test)

print("Training...")
model = GradientBoostingClassifier(n_estimators=200, learning_rate=0.05, max_depth=4,
                                    min_samples_split=10, min_samples_leaf=4,
                                    subsample=0.8, random_state=42)
model.fit(Xs, y_train)

acc = (model.predict(Xt) == y_test).mean()
print(f"  Accuracy: {acc*100:.2f}%")

joblib.dump(model,  MODELS / 'gradient_boosting.pkl')
joblib.dump(scaler, MODELS / 'scaler.pkl')
with open(MODELS / 'feature_names.json', 'w') as f:
    json.dump(list(X.columns), f)

print("Saved. Now restart the server: venv\\Scripts\\python.exe run.py")
