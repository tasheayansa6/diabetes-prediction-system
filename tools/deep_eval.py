import pandas as pd, numpy as np, joblib, warnings
warnings.filterwarnings('ignore')
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score, learning_curve
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, brier_score_loss, confusion_matrix,
    matthews_corrcoef, log_loss, classification_report)
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier

df = pd.read_csv('ml_model/dataset/diabetes.csv')
zero_cols = ['Glucose','BloodPressure','SkinThickness','Insulin','BMI']
for col in zero_cols:
    df[col] = df[col].astype(float)
    df.loc[df[col]==0, col] = np.nan
for col in zero_cols:
    df.loc[(df['Outcome']==0)&df[col].isna(),col] = df[df['Outcome']==0][col].median()
    df.loc[(df['Outcome']==1)&df[col].isna(),col] = df[df['Outcome']==1][col].median()

X = df.drop('Outcome',axis=1); y = df['Outcome']
X_tr,X_te,y_tr,y_te = train_test_split(X,y,test_size=0.2,random_state=42,stratify=y)
model  = joblib.load('ml_model/saved_models/gradient_boosting.pkl')
scaler = joblib.load('ml_model/saved_models/scaler.pkl')
X_tr_s = scaler.transform(X_tr)
X_te_s = scaler.transform(X_te)
X_s    = scaler.transform(X)

y_pred  = model.predict(X_te_s)
y_proba = model.predict_proba(X_te_s)[:,1]
y_tr_pred = model.predict(X_tr_s)

print("=== DATASET ===")
print("Total:", len(df), "| Train:", len(X_tr), "| Test:", len(X_te))
print("Non-diabetic:", sum(y==0), "(%.1f%%)" % (sum(y==0)/len(y)*100))
print("Diabetic:", sum(y==1), "(%.1f%%)" % (sum(y==1)/len(y)*100))
print("Zeros imputed per column:")
orig = pd.read_csv('ml_model/dataset/diabetes.csv')
for c in zero_cols:
    print("  %s: %d zeros (%.1f%%)" % (c, sum(orig[c]==0), sum(orig[c]==0)/len(orig)*100))

print("\n=== TEST SET METRICS ===")
print("Accuracy:  %.4f" % accuracy_score(y_te,y_pred))
print("Precision: %.4f" % precision_score(y_te,y_pred))
print("Recall:    %.4f" % recall_score(y_te,y_pred))
print("F1:        %.4f" % f1_score(y_te,y_pred))
print("ROC-AUC:   %.4f" % roc_auc_score(y_te,y_proba))
print("Avg Prec:  %.4f" % average_precision_score(y_te,y_proba))
print("Brier:     %.4f" % brier_score_loss(y_te,y_proba))
print("Log Loss:  %.4f" % log_loss(y_te,y_proba))
print("MCC:       %.4f" % matthews_corrcoef(y_te,y_pred))
print("Train acc: %.4f" % accuracy_score(y_tr,y_tr_pred))
print("Overfit:   %.4f" % (accuracy_score(y_tr,y_tr_pred)-accuracy_score(y_te,y_pred)))

cm = confusion_matrix(y_te,y_pred); tn,fp,fn,tp = cm.ravel()
print("\n=== CONFUSION MATRIX ===")
print("TN=%d FP=%d FN=%d TP=%d" % (tn,fp,fn,tp))
print("Sensitivity (Recall): %.4f" % (tp/(tp+fn)))
print("Specificity:          %.4f" % (tn/(tn+fp)))
print("PPV (Precision):      %.4f" % (tp/(tp+fp)))
print("NPV:                  %.4f" % (tn/(tn+fn)))
print("Balanced Accuracy:    %.4f" % ((tp/(tp+fn)+tn/(tn+fp))/2))

print("\n=== CROSS-VALIDATION (5-fold) ===")
cv = StratifiedKFold(5,shuffle=True,random_state=42)
for metric in ['accuracy','precision','recall','f1','roc_auc']:
    s = cross_val_score(model,X_s,y,cv=cv,scoring=metric)
    print("  %s: %.4f +/- %.4f" % (metric,s.mean(),s.std()))

print("\n=== FEATURE IMPORTANCE ===")
fi = sorted(zip(X.columns,model.feature_importances_),key=lambda x:-x[1])
for n,i in fi:
    bar = '#'*int(i*50)
    print("  %-30s %.4f (%.1f%%) %s" % (n,i,i*100,bar))

print("\n=== HYPERPARAMETERS ===")
p = model.get_params()
for k in ['n_estimators','learning_rate','max_depth','min_samples_split',
          'min_samples_leaf','subsample','max_features','random_state']:
    print("  %s: %s" % (k,p[k]))
print("  n_features_in: %d" % model.n_features_in_)
print("  n_classes: %d" % model.n_classes_)

print("\n=== BASELINE COMPARISON ===")
baselines = [
    ('Dummy (majority)', DummyClassifier(strategy='most_frequent')),
    ('Logistic Regression', LogisticRegression(max_iter=1000,random_state=42)),
    ('Random Forest', RandomForestClassifier(n_estimators=100,random_state=42)),
    ('Gradient Boosting (ours)', model),
]
for name,m in baselines:
    s = cross_val_score(m,X_s,y,cv=cv,scoring='roc_auc')
    print("  %-30s %.4f +/- %.4f" % (name,s.mean(),s.std()))

print("\n=== LEARNING CURVE ===")
sizes,tr_s,val_s = learning_curve(model,X_s,y,cv=cv,scoring='roc_auc',
    train_sizes=np.linspace(0.2,1.0,5),random_state=42)
for sz,tr,va in zip(sizes,tr_s.mean(axis=1),val_s.mean(axis=1)):
    print("  n=%-4d  train_auc=%.4f  val_auc=%.4f" % (sz,tr,va))

print("\n=== THRESHOLD ANALYSIS ===")
for t in [0.2,0.3,0.4,0.5,0.6,0.7]:
    yp = (y_proba>=t).astype(int)
    fn_t = sum((y_te==1)&(yp==0))
    fp_t = sum((y_te==0)&(yp==1))
    rec  = recall_score(y_te,yp,zero_division=0)
    prec = precision_score(y_te,yp,zero_division=0)
    f1   = f1_score(y_te,yp,zero_division=0)
    print("  t=%.1f  recall=%.3f  prec=%.3f  f1=%.3f  FN=%d  FP=%d" % (t,rec,prec,f1,fn_t,fp_t))

print("\n=== SCALER INFO ===")
print("  Mean:", [round(m,2) for m in scaler.mean_])
print("  Std: ", [round(s,2) for s in scaler.scale_])
print("  Features:", list(X.columns))
