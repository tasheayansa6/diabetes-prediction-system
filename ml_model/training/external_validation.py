"""
External Validation Script
Tests the trained model on a second independent dataset to evaluate generalization.
Supports multiple external datasets for robustness testing.
"""

import os
import json
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, 
    f1_score, roc_auc_score, classification_report,
    confusion_matrix
)
import matplotlib.pyplot as plt
import seaborn as sns

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'saved_models')
EXTERNAL_DIR = os.path.join(BASE_DIR, 'dataset', 'external')
RESULTS_DIR = os.path.join(BASE_DIR, 'external_validation_results')
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(EXTERNAL_DIR, exist_ok=True)

# ── Load the trained model and scaler ─────────────────────────────────────────
print("=" * 70)
print("EXTERNAL VALIDATION STUDY")
print("=" * 70)

# Determine active model from registry
registry_path = os.path.join(MODELS_DIR, '..', 'model_registry.json')
active_model_file = 'gradient_boosting.pkl'

if os.path.exists(registry_path):
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    active = next((m for m in registry if m.get('status') == 'active'), None)
    if active:
        active_model_file = active.get('filename', 'gradient_boosting.pkl')
        print(f"\nActive model from registry: {active.get('algorithm')}")

model_path = os.path.join(MODELS_DIR, active_model_file)
scaler_path = os.path.join(MODELS_DIR, 'scaler.pkl')
feature_path = os.path.join(MODELS_DIR, 'feature_names.json')

print(f"\nLoading model: {model_path}")
print(f"Loading scaler: {scaler_path}")

model = joblib.load(model_path)
scaler = joblib.load(scaler_path)

with open(feature_path, 'r') as f:
    feature_names = json.load(f)

print(f"Features: {feature_names}")

# ── Function to validate on a dataset ─────────────────────────────────────────
def validate_on_dataset(df, dataset_name, feature_names, model, scaler):
    """
    Validate model on an external dataset.
    
    Args:
        df: DataFrame with features and 'Outcome' column
        dataset_name: Name of the dataset for reporting
        feature_names: List of feature column names expected by the model
        model: Trained sklearn model
        scaler: Fitted StandardScaler
        
    Returns:
        Dictionary with validation results
    """
    print(f"\n{'=' * 50}")
    print(f"Validating on: {dataset_name}")
    print(f"{'=' * 50}")
    print(f"Dataset shape: {df.shape}")
    
    # Check for required columns
    missing_cols = [col for col in feature_names if col not in df.columns]
    if missing_cols:
        print(f"WARNING: Missing columns: {missing_cols}")
        # Try to find similar columns
        col_mapping = {}
        for col in missing_cols:
            # Try case-insensitive match
            for df_col in df.columns:
                if df_col.lower() == col.lower():
                    col_mapping[col] = df_col
                    break
        if col_mapping:
            print(f"Found mappings: {col_mapping}")
            for model_col, df_col in col_mapping.items():
                df[model_col] = df[df_col]
    
    # Check for Outcome column
    if 'Outcome' not in df.columns:
        print("ERROR: 'Outcome' column not found in dataset")
        return None
    
    # Prepare features
    X = df[feature_names].copy()
    y = df['Outcome']
    
    # Handle missing values (simple imputation with median)
    for col in feature_names:
        if X[col].isnull().any():
            median = X[col].median()
            X[col] = X[col].fillna(median)
            print(f"  Imputed {X[col].isnull().sum()} missing values in {col} with median {median:.2f}")
    
    # Scale features
    X_scaled = scaler.transform(X)
    
    # Make predictions
    y_pred = model.predict(X_scaled)
    y_proba = model.predict_proba(X_scaled)[:, 1]
    
    # Calculate metrics
    accuracy = accuracy_score(y, y_pred)
    precision = precision_score(y, y_pred, zero_division=0)
    recall = recall_score(y, y_pred, zero_division=0)
    f1 = f1_score(y, y_pred, zero_division=0)
    auc = roc_auc_score(y, y_proba)
    
    print(f"\nResults:")
    print(f"  Samples: {len(y)}")
    print(f"  Positive cases: {y.sum()} ({y.mean()*100:.1f}%)")
    print(f"  Negative cases: {(~y.astype(bool)).sum()} ({(1-y.mean())*100:.1f}%)")
    print(f"  Accuracy  : {accuracy*100:.2f}%")
    print(f"  Precision : {precision*100:.2f}%")
    print(f"  Recall    : {recall*100:.2f}%")
    print(f"  F1 Score  : {f1*100:.2f}%")
    print(f"  ROC-AUC   : {auc*100:.2f}%")
    print(f"\n{classification_report(y, y_pred, target_names=['Non-Diabetic', 'Diabetic'])}")
    
    cm = confusion_matrix(y, y_pred)
    print(f"Confusion Matrix:")
    print(f"  TN={cm[0,0]}  FP={cm[0,1]}")
    print(f"  FN={cm[1,0]}  TN={cm[1,1]}")
    
    return {
        'dataset': dataset_name,
        'samples': len(y),
        'positive_cases': int(y.sum()),
        'negative_cases': int((~y.astype(bool)).sum()),
        'positive_rate': round(float(y.mean()) * 100, 2),
        'accuracy': round(accuracy * 100, 2),
        'precision': round(precision * 100, 2),
        'recall': round(recall * 100, 2),
        'f1_score': round(f1 * 100, 2),
        'roc_auc': round(auc * 100, 2),
        'confusion_matrix': cm.tolist(),
        'classification_report': classification_report(y, y_pred, target_names=['Non-Diabetic', 'Diabetic'], output_dict=True)
    }


# ── Create sample external datasets for demonstration ────────────────────────
def create_sample_external_datasets():
    """
    Create sample external datasets for demonstration.
    In a real study, these would be loaded from actual external sources.
    """
    np.random.seed(42)
    
    # Dataset 1: "NHANES-like" - Different population characteristics
    n_samples = 200
    data1 = {
        'Pregnancies': np.random.poisson(2, n_samples),
        'Glucose': np.random.normal(100, 30, n_samples).clip(50, 250),
        'BloodPressure': np.random.normal(70, 15, n_samples).clip(40, 120),
        'SkinThickness': np.random.normal(25, 10, n_samples).clip(5, 60),
        'Insulin': np.random.exponential(80, n_samples).clip(5, 500),
        'BMI': np.random.normal(28, 7, n_samples).clip(15, 50),
        'DiabetesPedigreeFunction': np.random.exponential(0.5, n_samples).clip(0.01, 2.5),
        'Age': np.random.normal(35, 15, n_samples).clip(18, 80),
    }
    df1 = pd.DataFrame(data1)
    # Generate Outcome based on different thresholds (simulating different population)
    risk_score = (df1['Glucose'] / 140 + df1['BMI'] / 30 + df1['Age'] / 50) / 3
    df1['Outcome'] = (risk_score > 0.8).astype(int)
    
    # Dataset 2: "Bangladesh-like" - Different feature distributions
    n_samples = 150
    data2 = {
        'Pregnancies': np.random.poisson(3, n_samples),
        'Glucose': np.random.normal(95, 25, n_samples).clip(50, 220),
        'BloodPressure': np.random.normal(72, 12, n_samples).clip(50, 110),
        'SkinThickness': np.random.normal(20, 8, n_samples).clip(5, 50),
        'Insulin': np.random.exponential(60, n_samples).clip(5, 400),
        'BMI': np.random.normal(24, 5, n_samples).clip(15, 45),
        'DiabetesPedigreeFunction': np.random.exponential(0.4, n_samples).clip(0.01, 2.0),
        'Age': np.random.normal(40, 12, n_samples).clip(21, 75),
    }
    df2 = pd.DataFrame(data2)
    risk_score = (df2['Glucose'] / 130 + df2['BMI'] / 25 + df2['DiabetesPedigreeFunction']) / 3
    df2['Outcome'] = (risk_score > 0.7).astype(int)
    
    # Save to external directory
    df1.to_csv(os.path.join(EXTERNAL_DIR, 'nhanes_sample.csv'), index=False)
    df2.to_csv(os.path.join(EXTERNAL_DIR, 'bangladesh_sample.csv'), index=False)
    
    print(f"\nCreated sample external datasets in {EXTERNAL_DIR}:")
    print(f"  - nhanes_sample.csv ({len(df1)} samples)")
    print(f"  - bangladesh_sample.csv ({len(df2)} samples)")
    
    return [
        (os.path.join(EXTERNAL_DIR, 'nhanes_sample.csv'), 'NHANES Sample'),
        (os.path.join(EXTERNAL_DIR, 'bangladesh_sample.csv'), 'Bangladesh Sample')
    ]


# ── Main validation ───────────────────────────────────────────────────────────
def main():
    # Get external datasets
    external_datasets = []
    
    # Check for existing external datasets
    if os.path.exists(EXTERNAL_DIR):
        for file in os.listdir(EXTERNAL_DIR):
            if file.endswith('.csv'):
                external_datasets.append((
                    os.path.join(EXTERNAL_DIR, file),
                    file.replace('.csv', '').replace('_', ' ').title()
                ))
    
    # Create sample datasets if none exist
    if not external_datasets:
        print("\nNo external datasets found. Creating sample datasets for demonstration...")
        external_datasets = create_sample_external_datasets()
    
    # Validate on each dataset
    all_results = []
    original_dataset_results = None
    
    # First, get original dataset performance for comparison
    original_data_path = os.path.join(BASE_DIR, 'dataset', 'diabetes.csv')
    if os.path.exists(original_data_path):
        df_original = pd.read_csv(original_data_path)
        # Apply same preprocessing as training
        zero_cols = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']
        for col in zero_cols:
            for cls in [0, 1]:
                if cls in df_original['Outcome'].values:
                    median = df_original.loc[(df_original['Outcome'] == cls) & (df_original[col] != 0), col].median()
                    df_original.loc[(df_original['Outcome'] == cls) & (df_original[col] == 0), col] = median
        
        original_dataset_results = validate_on_dataset(
            df_original, 'Original (Pima)', feature_names, model, scaler
        )
    
    # Validate on external datasets
    for dataset_path, dataset_name in external_datasets:
        if os.path.exists(dataset_path):
            df = pd.read_csv(dataset_path)
            results = validate_on_dataset(df, dataset_name, feature_names, model, scaler)
            if results:
                all_results.append(results)
    
    # ── Summary Report ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("EXTERNAL VALIDATION SUMMARY")
    print("=" * 70)
    
    summary = {
        'study_date': datetime.now().isoformat(),
        'model': active_model_file,
        'original_dataset': original_dataset_results,
        'external_datasets': all_results,
        'performance_drop': []
    }
    
    if original_dataset_results:
        print(f"\n{'Dataset':<25} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>10} {'AUC':>10}")
        print(f"{'─' * 75}")
        print(f"{'Original (Pima)':<25} {original_dataset_results['accuracy']:>9.2f}% {original_dataset_results['precision']:>9.2f}% {original_dataset_results['recall']:>9.2f}% {original_dataset_results['f1_score']:>9.2f}% {original_dataset_results['roc_auc']:>9.2f}%")
        
        for result in all_results:
            acc_drop = original_dataset_results['accuracy'] - result['accuracy']
            f1_drop = original_dataset_results['f1_score'] - result['f1_score']
            auc_drop = original_dataset_results['roc_auc'] - result['roc_auc']
            
            print(f"{result['dataset']:<25} {result['accuracy']:>9.2f}% {result['precision']:>9.2f}% {result['recall']:>9.2f}% {result['f1_score']:>9.2f}% {result['roc_auc']:>9.2f}%")
            
            summary['performance_drop'].append({
                'dataset': result['dataset'],
                'accuracy_drop': round(acc_drop, 2),
                'f1_drop': round(f1_drop, 2),
                'auc_drop': round(auc_drop, 2),
                'samples': result['samples']
            })
    
    # Save summary report
    report_path = os.path.join(RESULTS_DIR, 'external_validation_report.json')
    with open(report_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"\nFull report saved to: {report_path}")
    
    # Create comparison chart
    if all_results and original_dataset_results:
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        fig.suptitle('External Validation Results', fontsize=16)
        
        datasets = ['Original'] + [r['dataset'] for r in all_results]
        accuracies = [original_dataset_results['accuracy']] + [r['accuracy'] for r in all_results]
        f1s = [original_dataset_results['f1_score']] + [r['f1_score'] for r in all_results]
        aucs = [original_dataset_results['roc_auc']] + [r['roc_auc'] for r in all_results]
        
        x = np.arange(len(datasets))
        width = 0.25
        
        axes[0].bar(x, accuracies, width, label='Accuracy', color=['#3b82f6'] + ['#10b981'] * (len(datasets)-1))
        axes[0].set_ylabel('Score (%)')
        axes[0].set_title('Accuracy')
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(datasets, rotation=45, ha='right')
        axes[0].set_ylim(0, 100)
        
        axes[1].bar(x, f1s, width, label='F1 Score', color=['#3b82f6'] + ['#f59e0b'] * (len(datasets)-1))
        axes[1].set_ylabel('Score (%)')
        axes[1].set_title('F1 Score')
        axes[1].set_xticks(x)
        axes[1].set_xticklabels(datasets, rotation=45, ha='right')
        axes[1].set_ylim(0, 100)
        
        axes[2].bar(x, aucs, width, label='ROC-AUC', color=['#3b82f6'] + ['#8b5cf6'] * (len(datasets)-1))
        axes[2].set_ylabel('Score (%)')
        axes[2].set_title('ROC-AUC')
        axes[2].set_xticks(x)
        axes[2].set_xticklabels(datasets, rotation=45, ha='right')
        axes[2].set_ylim(0, 100)
        
        plt.tight_layout()
        plt.savefig(os.path.join(RESULTS_DIR, 'external_validation_chart.png'), dpi=150, bbox_inches='tight')
        print(f"Chart saved to: {os.path.join(RESULTS_DIR, 'external_validation_chart.png')}")
    
    print("\n" + "=" * 70)
    print("EXTERNAL VALIDATION COMPLETE!")
    print("=" * 70)
    
    return summary


if __name__ == '__main__':
    main()