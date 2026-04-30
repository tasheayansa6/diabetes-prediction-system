"""
Model Comparison and Ablation Study
Compares Logistic Regression, Random Forest, and Gradient Boosting
on the same train/test split with statistical significance testing.
"""

import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, 
    f1_score, roc_auc_score, classification_report,
    confusion_matrix, McNemar
)
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, 'dataset', 'diabetes.csv')
RESULTS_DIR = os.path.join(BASE_DIR, 'comparison_results')
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Load and preprocess data ──────────────────────────────────────────────────
print("=" * 70)
print("MODEL COMPARISON STUDY")
print("=" * 70)

df = pd.read_csv(DATA_PATH)
print(f"Dataset shape: {df.shape}")

# Per-class median imputation for zero-value columns
zero_cols = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']
for col in zero_cols:
    for cls in [0, 1]:
        median = df.loc[(df['Outcome'] == cls) & (df[col] != 0), col].median()
        df.loc[(df['Outcome'] == cls) & (df[col] == 0), col] = median

X = df.drop('Outcome', axis=1)
y = df['Outcome']
feature_names = list(X.columns)

# ── Define models ─────────────────────────────────────────────────────────────
models = {
    'Logistic Regression': LogisticRegression(
        max_iter=1000, random_state=42, C=1.0, solver='lbfgs'
    ),
    'Random Forest': RandomForestClassifier(
        n_estimators=200, max_depth=10, min_samples_split=5,
        min_samples_leaf=2, random_state=42, n_jobs=-1
    ),
    'Gradient Boosting': GradientBoostingClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=4,
        min_samples_split=10, min_samples_leaf=4, subsample=0.8,
        random_state=42
    )
}

# ── Multiple split evaluation for statistical testing ────────────────────────
print("\nRunning 30 repeated hold-out evaluations for statistical testing...")
n_splits = 30
split_results = {name: {'accuracies': [], 'f1s': [], 'aucs': []} for name in models}

for i in range(n_splits):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=i, stratify=y
    )
    
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    
    for name, model in models.items():
        model.fit(X_train_s, y_train)
        y_pred = model.predict(X_test_s)
        y_proba = model.predict_proba(X_test_s)[:, 1]
        
        split_results[name]['accuracies'].append(accuracy_score(y_test, y_pred))
        split_results[name]['f1s'].append(f1_score(y_test, y_pred))
        split_results[name]['aucs'].append(roc_auc_score(y_test, y_proba))

# ── Final evaluation on a fixed split ─────────────────────────────────────────
print("\nFinal evaluation on fixed train/test split...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

print(f"Train: {len(X_train)}  |  Test: {len(X_test)}")

comparison_results = []

for name, model in models.items():
    print(f"\n{'─' * 30} {name} {'─' * 30}")
    model.fit(X_train_s, y_train)
    
    y_pred = model.predict(X_test_s)
    y_proba = model.predict_proba(X_test_s)[:, 1]
    
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)
    
    # Cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X_train_s, y_train, cv=cv, scoring='accuracy')
    
    # Feature importance
    feature_importance = None
    if hasattr(model, 'feature_importances_'):
        feature_importance = dict(zip(feature_names, model.feature_importances_.tolist()))
    elif hasattr(model, 'coef_'):
        importance = np.abs(model.coef_[0])
        feature_importance = dict(zip(feature_names, importance.tolist()))
    
    result = {
        'model': name,
        'accuracy': round(accuracy * 100, 2),
        'precision': round(precision * 100, 2),
        'recall': round(recall * 100, 2),
        'f1_score': round(f1 * 100, 2),
        'roc_auc': round(auc * 100, 2),
        'cv_accuracy_mean': round(cv_scores.mean() * 100, 2),
        'cv_accuracy_std': round(cv_scores.std() * 100, 2),
        'feature_importance': feature_importance,
        'classification_report': classification_report(y_test, y_pred, target_names=['Non-Diabetic', 'Diabetic'], output_dict=True),
        'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
    }
    comparison_results.append(result)
    
    print(f"  Accuracy  : {accuracy*100:.2f}%")
    print(f"  Precision : {precision*100:.2f}%")
    print(f"  Recall    : {recall*100:.2f}%")
    print(f"  F1 Score  : {f1*100:.2f}%")
    print(f"  ROC-AUC   : {auc*100:.2f}%")
    print(f"  CV-5 Acc  : {cv_scores.mean()*100:.2f}% (+/- {cv_scores.std()*200:.2f}%)")

# ── Statistical Significance Testing ──────────────────────────────────────────
print("\n" + "=" * 70)
print("STATISTICAL SIGNIFICANCE TESTING")
print("=" * 70)

# Paired t-tests on accuracy across splits
model_names = list(models.keys())
stat_results = []

for i in range(len(model_names)):
    for j in range(i + 1, len(model_names)):
        name1, name2 = model_names[i], model_names[j]
        acc1 = split_results[name1]['accuracies']
        acc2 = split_results[name2]['accuracies']
        
        t_stat, p_value = stats.ttest_rel(acc1, acc2)
        
        stat_results.append({
            'model_1': name1,
            'model_2': name2,
            't_statistic': round(t_stat, 4),
            'p_value': round(p_value, 6),
            'significant': p_value < 0.05,
            'mean_diff': round(np.mean(acc1) - np.mean(acc2), 4)
        })
        
        print(f"\n{name1} vs {name2}:")
        print(f"  t-statistic: {t_stat:.4f}, p-value: {p_value:.6f}")
        print(f"  Significant (α=0.05): {'Yes' if p_value < 0.05 else 'No'}")
        print(f"  Mean accuracy difference: {np.mean(acc1) - np.mean(acc2):.4f}")

# ── Ablation Study ────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("ABLATION STUDY - Feature Importance")
print("=" * 70)

# Use the best model (Gradient Boosting) for ablation
best_model = GradientBoostingClassifier(
    n_estimators=200, learning_rate=0.05, max_depth=4,
    min_samples_split=10, min_samples_leaf=4, subsample=0.8,
    random_state=42
)
best_model.fit(X_train_s, y_train)

# Full model baseline
y_pred_full = best_model.predict(X_test_s)
baseline_accuracy = accuracy_score(y_test, y_pred_full)
print(f"\nBaseline (all features): {baseline_accuracy*100:.2f}%")

ablation_results = []

for feature in feature_names:
    # Train without this feature
    X_train_reduced = X_train_s[:, [i for i, f in enumerate(feature_names) if f != feature]]
    X_test_reduced = X_test_s[:, [i for i, f in enumerate(feature_names) if f != feature]]
    
    model_reduced = GradientBoostingClassifier(
        n_estimators=200, learning_rate=0.05, max_depth=4,
        min_samples_split=10, min_samples_leaf=4, subsample=0.8,
        random_state=42
    )
    model_reduced.fit(X_train_reduced, y_train)
    y_pred_reduced = model_reduced.predict(X_test_reduced)
    
    accuracy_reduced = accuracy_score(y_test, y_pred_reduced)
    drop = baseline_accuracy - accuracy_reduced
    
    ablation_results.append({
        'feature': feature,
        'accuracy_without': round(accuracy_reduced * 100, 2),
        'accuracy_drop': round(drop * 100, 2),
        'importance_rank': ''
    })
    
    print(f"  Without {feature:30s}: {accuracy_reduced*100:.2f}% (drop: {drop*100:.2f}%)")

# Rank features by importance
ablation_results.sort(key=lambda x: x['accuracy_drop'], reverse=True)
for i, result in enumerate(ablation_results):
    result['importance_rank'] = f"#{i+1}"
    
print("\nFeature Importance Ranking (by ablation):")
for result in ablation_results:
    print(f"  {result['importance_rank']}: {result['feature']} (drop: {result['accuracy_drop']:.2f}%)")

# ── Save Results ──────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SAVING RESULTS")
print("=" * 70)

# Comparison report
report = {
    'study_date': datetime.now().isoformat(),
    'dataset': str(DATA_PATH),
    'dataset_size': len(df),
    'train_size': len(X_train),
    'test_size': len(X_test),
    'features': feature_names,
    'model_comparison': comparison_results,
    'statistical_tests': stat_results,
    'ablation_study': ablation_results,
    'best_model': max(comparison_results, key=lambda x: x['f1_score'])['model']
}

report_path = os.path.join(RESULTS_DIR, 'model_comparison_report.json')
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2, default=str)
print(f"  Comparison report saved to: {report_path}")

# Create comparison table
comparison_df = pd.DataFrame([{
    'Model': r['model'],
    'Accuracy': r['accuracy'],
    'Precision': r['precision'],
    'Recall': r['recall'],
    'F1 Score': r['f1_score'],
    'ROC-AUC': r['roc_auc'],
    'CV Accuracy': f"{r['cv_accuracy_mean']:.2f} ± {r['cv_accuracy_std']:.2f}"
} for r in comparison_results])

csv_path = os.path.join(RESULTS_DIR, 'model_comparison_table.csv')
comparison_df.to_csv(csv_path, index=False)
print(f"  Comparison table saved to: {csv_path}")

# Visualization
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Model Comparison Study', fontsize=16)

metrics = ['accuracy', 'precision', 'recall', 'f1_score']
titles = ['Accuracy', 'Precision', 'Recall', 'F1 Score']

for ax, metric, title in zip(axes.flat[:4], metrics, titles):
    values = [r[metric] for r in comparison_results]
    colors = ['#3b82f6', '#10b981', '#f59e0b']
    bars = ax.bar([r['model'] for r in comparison_results], values, color=colors)
    ax.set_ylabel('Score (%)')
    ax.set_title(title)
    ax.set_ylim(0, 100)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=10)

plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, 'model_comparison_chart.png'), dpi=150, bbox_inches='tight')
print(f"  Chart saved to: {os.path.join(RESULTS_DIR, 'model_comparison_chart.png')}")

# Ablation chart
fig, ax = plt.subplots(figsize=(10, 6))
ablation_df = pd.DataFrame(ablation_results)
colors = plt.cm.Reds(np.linspace(0.3, 0.9, len(ablation_df)))
bars = ax.barh(ablation_df['feature'], ablation_df['accuracy_drop'], color=colors)
ax.set_xlabel('Accuracy Drop (%)')
ax.set_title('Feature Importance - Ablation Study')
for bar, val in zip(bars, ablation_df['accuracy_drop']):
    ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
            f'{val:.1f}%', ha='left', va='center', fontsize=10)

plt.tight_layout()
plt.savefig(os.path.join(RESULTS_DIR, 'ablation_study_chart.png'), dpi=150, bbox_inches='tight')
print(f"  Ablation chart saved to: {os.path.join(RESULTS_DIR, 'ablation_study_chart.png')}")

print("\n" + "=" * 70)
print("STUDY COMPLETE!")
print("=" * 70)