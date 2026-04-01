import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, 
    f1_score, roc_auc_score, confusion_matrix,
    roc_curve, classification_report
)

def evaluate_model(model_path='ml_model/saved_models/logistic_regression.pkl',
                   scaler_path='ml_model/saved_models/scaler.pkl',
                   data_path='ml_model/data/diabetes.csv',
                   plot_results=True):
   
    print("="*60)
    print("MODEL EVALUATION")
    print("="*60)
    
    # Load dataset
    print("\nLoading dataset...")
    df = pd.read_csv(data_path)
    X = df.drop('Outcome', axis=1)
    y = df['Outcome']
    print(f"   Dataset shape: {df.shape}")
    
    # Split data (same split as training)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"   Test set size: {len(X_test)} samples")
    
    # Load model and scaler
    print("\nLoading model and scaler...")
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    print(f"   Model type: {type(model).__name__}")
    
    # Scale test data
    X_test_scaled = scaler.transform(X_test)
    
    # Make predictions
    print("\nMaking predictions...")
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba)
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    
    # Print results
    print("\n" + "="*60)
    print("MODEL PERFORMANCE METRICS")
    print("="*60)
    print(f"\nAccuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"Precision: {precision:.4f} ({precision*100:.2f}%)")
    print(f"Recall:    {recall:.4f} ({recall*100:.2f}%)")
    print(f"F1 Score:  {f1:.4f} ({f1*100:.2f}%)")
    print(f"ROC AUC:   {roc_auc:.4f} ({roc_auc*100:.2f}%)")
    
    print(f"\nConfusion Matrix:")
    print(f"              Predicted")
    print(f"              Neg   Pos")
    print(f"Actual Neg    {cm[0,0]:3d}   {cm[0,1]:3d}")
    print(f"       Pos    {cm[1,0]:3d}   {cm[1,1]:3d}")
    
    # Calculate additional metrics
    tn, fp, fn, tp = cm.ravel()
    sensitivity = tp / (tp + fn)  # Same as recall
    specificity = tn / (tn + fp)
    ppv = tp / (tp + fp)  # Same as precision
    npv = tn / (tn + fn)
    
    print(f"\n Detailed Metrics:")
    print(f"   Sensitivity (Recall): {sensitivity:.4f}")
    print(f"   Specificity:          {specificity:.4f}")
    print(f"   PPV (Precision):      {ppv:.4f}")
    print(f"   NPV:                  {npv:.4f}")
    
    # Plot results if requested
    if plot_results:
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Confusion Matrix Heatmap
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[0,0])
        axes[0,0].set_title('Confusion Matrix')
        axes[0,0].set_xlabel('Predicted')
        axes[0,0].set_ylabel('Actual')
        
        # ROC Curve
        fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
        axes[0,1].plot(fpr, tpr, 'b-', label=f'ROC (AUC = {roc_auc:.3f})')
        axes[0,1].plot([0, 1], [0, 1], 'r--', label='Random')
        axes[0,1].set_xlabel('False Positive Rate')
        axes[0,1].set_ylabel('True Positive Rate')
        axes[0,1].set_title('ROC Curve')
        axes[0,1].legend()
        axes[0,1].grid(True, alpha=0.3)
        
        # Metrics Bar Chart
        metrics = ['Accuracy', 'Precision', 'Recall', 'F1', 'ROC-AUC']
        values = [accuracy, precision, recall, f1, roc_auc]
        colors = ['#2ecc71' if v > 0.7 else '#e74c3c' for v in values]
        axes[1,0].bar(metrics, values, color=colors)
        axes[1,0].set_ylim([0, 1])
        axes[1,0].set_title('Performance Metrics')
        axes[1,0].set_ylabel('Score')
        for i, v in enumerate(values):
            axes[1,0].text(i, v + 0.02, f'{v:.3f}', ha='center')
        
        # Prediction Distribution
        axes[1,1].hist(y_pred_proba[y_test==0], bins=20, alpha=0.5, 
                      label='Actual Negative', color='green')
        axes[1,1].hist(y_pred_proba[y_test==1], bins=20, alpha=0.5,
                      label='Actual Positive', color='red')
        axes[1,1].axvline(x=0.5, color='black', linestyle='--', label='Threshold')
        axes[1,1].set_xlabel('Predicted Probability')
        axes[1,1].set_ylabel('Frequency')
        axes[1,1].set_title('Prediction Distribution')
        axes[1,1].legend()
        
        plt.tight_layout()
        plt.savefig('ml_model/plots/evaluation_results.png')
        plt.show()
        print("\nEvaluation plots saved to ml_model/plots/evaluation_results.png")
    
    # Return metrics dictionary
    metrics = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'roc_auc': roc_auc,
        'sensitivity': sensitivity,
        'specificity': specificity,
        'ppv': ppv,
        'npv': npv,
        'confusion_matrix': cm.tolist()
    }
    
    print("\n" + "="*60)
    print("Evaluation Complete!")
    print("="*60)
    
    return metrics

def compare_models():
    """
    Compare multiple trained models
    """
    models = [
        ('Logistic Regression', 'ml_model/saved_models/logistic_regression.pkl'),
        ('Random Forest', 'ml_model/saved_models/random_forest.pkl')
    ]
    
    results = []
    for name, path in models:
        print(f"\nEvaluating {name}...")
        try:
            metrics = evaluate_model(
                model_path=path,
                scaler_path='ml_model/saved_models/scaler.pkl',
                plot_results=False
            )
            metrics['model'] = name
            results.append(metrics)
        except Exception as e:
            print(f"Error evaluating {name}: {e}")
    
    # Comparison DataFrame
    df_results = pd.DataFrame(results)
    print("\n" + "="*60)
    print("MODEL COMPARISON")
    print("="*60)
    print(df_results[['model', 'accuracy', 'precision', 'recall', 'f1_score', 'roc_auc']].to_string())
    
    return df_results

if __name__ == '__main__':
    # Evaluate single model
    metrics = evaluate_model()
    
   