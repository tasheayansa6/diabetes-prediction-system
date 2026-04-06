import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
import joblib

def train_improved_model():
   
  
    os.makedirs('ml_model/saved_models', exist_ok=True)
    
    # Load dataset
    print("Loading dataset...")
    df = pd.read_csv('ml_model/dataset/diabetes.csv')
    
    # Data preprocessing
    print("Preprocessing data...")
    # Replace zeros with NaN for specific columns
    zero_not_valid = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']
    for col in zero_not_valid:
        if col in df.columns:
            df[col] = df[col].replace(0, np.nan)
            df[col] = df[col].fillna(df[col].median())
    
    # Prepare features and target
    X = df.drop('Outcome', axis=1)
    y = df['Outcome']
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Scale features
    print("Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train multiple models
    print("\nTraining Logistic Regression...")
    lr = LogisticRegression(max_iter=1000, random_state=42, C=0.1)
    lr.fit(X_train_scaled, y_train)
    
    print("Training Random Forest...")
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42
    )
    rf.fit(X_train_scaled, y_train)
    
    print("Training Gradient Boosting...")
    gb = GradientBoostingClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        random_state=42
    )
    gb.fit(X_train_scaled, y_train)
    
    # Create ensemble model
    print("\nCreating Ensemble Model...")
    ensemble = VotingClassifier(
        estimators=[
            ('lr', lr),
            ('rf', rf),
            ('gb', gb)
        ],
        voting='soft'
    )
    ensemble.fit(X_train_scaled, y_train)
    
    # Evaluate all models
    models = {
        'Logistic Regression': lr,
        'Random Forest': rf,
        'Gradient Boosting': gb,
        'Ensemble': ensemble
    }
    
    print("\n" + "="*60)
    print("MODEL EVALUATION RESULTS")
    print("="*60)
    
    best_model = None
    best_accuracy = 0
    best_name = ''
    
    for name, model in models.items():
        y_pred = model.predict(X_test_scaled)
        y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
        
        accuracy = accuracy_score(y_test, y_pred)
        roc_auc = roc_auc_score(y_test, y_pred_proba)
        
        print(f"\n{name}:")
        print(f"  Accuracy:  {accuracy:.4f}")
        print(f"  ROC AUC:   {roc_auc:.4f}")
        
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_model = model
            best_name = name
    
    print("\n" + "="*60)
    print(f"Best Model: {best_name} with accuracy {best_accuracy:.4f}")
    print("="*60)
    
    # Detailed evaluation of best model
    y_pred = best_model.predict(X_test_scaled)
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Non-Diabetic', 'Diabetic']))
    
    print("\nConfusion Matrix:")
    cm = confusion_matrix(y_test, y_pred)
    print(cm)
    print(f"\nTrue Negatives:  {cm[0][0]}")
    print(f"False Positives: {cm[0][1]}")
    print(f"False Negatives: {cm[1][0]}")
    print(f"True Positives:  {cm[1][1]}")
    
    # Feature importance (if available)
    if hasattr(best_model, 'feature_importances_'):
        print("\nFeature Importance:")
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': best_model.feature_importances_
        }).sort_values('importance', ascending=False)
        print(feature_importance)
    
    # Save best model and scaler
    print("\nSaving best model and scaler...")
    joblib.dump(best_model, 'ml_model/saved_models/best_model.pkl')
    joblib.dump(scaler, 'ml_model/saved_models/best_scaler.pkl')
    
    # Also save as default model
    joblib.dump(best_model, 'ml_model/saved_models/logistic_regression.pkl')
    joblib.dump(scaler, 'ml_model/saved_models/scaler.pkl')

    # Update model_metadata.json with best model accuracy
    import json
    from datetime import datetime
    metadata_path = 'ml_model/saved_models/model_metadata.json'
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        metadata = {}
    metadata[best_name.lower().replace(' ', '_')] = {
        'accuracy': round(best_accuracy, 4),
        'train_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=4)

    print("\n✓ Model training completed successfully!")
    print(f"✓ Best model ({best_name}) saved to ml_model/saved_models/")
    
    return best_model, scaler, best_accuracy

if __name__ == '__main__':
    model, scaler, accuracy = train_improved_model()
    print(f"\nFinal Model Accuracy: {accuracy:.2%}")
