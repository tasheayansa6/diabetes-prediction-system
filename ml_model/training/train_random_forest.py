import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
import joblib
import matplotlib.pyplot as plt
import seaborn as sns

def train_random_forest(compare_with_lr=True):
    """
    Train Random Forest model and optionally compare with Logistic Regression
    """
    # Create directories
    os.makedirs('ml_model/saved_models', exist_ok=True)
    os.makedirs('ml_model/plots', exist_ok=True)
    
    # Load dataset
    print("="*60)
    print("RANDOM FOREST TRAINING")
    print("="*60)
    df = pd.read_csv('ml_model/data/diabetes.csv')
    print(f"Dataset shape: {df.shape}")
    
    # Prepare features and target
    X = df.drop('Outcome', axis=1)
    y = df['Outcome']
    feature_names = list(X.columns)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\nTrain set: {len(X_train)} samples")
    print(f"   Test set: {len(X_test)} samples")
    
    # Scale features (optional for RF but good for comparison)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train Random Forest
    print("\nTraining Random Forest...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train_scaled, y_train)
    
    # Evaluate Random Forest
    y_pred_rf = rf_model.predict(X_test_scaled)
    y_proba_rf = rf_model.predict_proba(X_test_scaled)[:, 1]
    
    rf_accuracy = accuracy_score(y_test, y_pred_rf)
    rf_auc = roc_auc_score(y_test, y_proba_rf)
    
    print(f"\nRandom Forest Performance:")
    print(f"   Accuracy: {rf_accuracy:.4f} ({rf_accuracy*100:.2f}%)")
    print(f"   ROC-AUC:  {rf_auc:.4f}")
    
    # Cross-validation
    cv_scores = cross_val_score(rf_model, X_train_scaled, y_train, cv=5)
    print(f"   5-Fold CV: {cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")
    
    # Feature Importance
    feature_importance = pd.DataFrame({
        'feature': feature_names,
        'importance': rf_model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\nFeature Importance:")
    for _, row in feature_importance.iterrows():
        print(f"   {row['feature']:25s}: {row['importance']:.4f}")
    
    # Plot feature importance
    plt.figure(figsize=(10, 6))
    plt.barh(feature_importance['feature'], feature_importance['importance'])
    plt.xlabel('Importance')
    plt.title('Random Forest Feature Importance')
    plt.tight_layout()
    plt.savefig('ml_model/plots/rf_feature_importance.png')
    print("\nFeature importance plot saved to ml_model/plots/rf_feature_importance.png")
    
    # Compare with Logistic Regression if requested
    if compare_with_lr:
        print("\n" + "="*60)
        print("COMPARING WITH LOGISTIC REGRESSION")
        print("="*60)
        
        lr_model = LogisticRegression(max_iter=1000, random_state=42)
        lr_model.fit(X_train_scaled, y_train)
        
        y_pred_lr = lr_model.predict(X_test_scaled)
        y_proba_lr = lr_model.predict_proba(X_test_scaled)[:, 1]
        
        lr_accuracy = accuracy_score(y_test, y_pred_lr)
        lr_auc = roc_auc_score(y_test, y_proba_lr)
        
        print(f"\nLogistic Regression:")
        print(f"   Accuracy: {lr_accuracy:.4f} ({lr_accuracy*100:.2f}%)")
        print(f"   ROC-AUC:  {lr_auc:.4f}")
        
        print(f"\nComparison:")
        improvement_acc = (rf_accuracy - lr_accuracy) * 100
        improvement_auc = (rf_auc - lr_auc) * 100
        print(f"   Random Forest vs Logistic Regression:")
        print(f"   Accuracy improvement: {improvement_acc:+.2f}%")
        print(f"   AUC improvement: {improvement_auc:+.2f}%")
    
    # Save model and scaler
    print("\nSaving model and scaler...")
    joblib.dump(rf_model, 'ml_model/saved_models/random_forest.pkl')
    joblib.dump(scaler, 'ml_model/saved_models/scaler_rf.pkl')
    
    # Save feature importance
    feature_importance.to_csv('ml_model/saved_models/rf_feature_importance.csv', index=False)
    
    print("\n Random Forest model training completed!")
    print(f"   Model saved to: ml_model/saved_models/random_forest.pkl")
    print(f"   Scaler saved to: ml_model/saved_models/scaler_rf.pkl")
    
    return rf_model, scaler, feature_importance

if __name__ == '__main__':
    model, scaler, importance = train_random_forest(compare_with_lr=True)