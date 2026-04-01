import os
import pandas as pd
import numpy as np
import json
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix, 
                             precision_score, recall_score, f1_score, roc_auc_score)
import joblib
import matplotlib.pyplot as plt
import seaborn as sns

def train_model(model_type='logistic_regression', save_artifacts=True):
    """
    Enhanced diabetes prediction model training
    
    Args:
        model_type: 'logistic_regression' or 'random_forest'
        save_artifacts: whether to save model and scaler
    """
    print("="*60)
    print("DIABETES PREDICTION MODEL TRAINING")
    print("="*60)
    
    # Create directories if they don't exist
    os.makedirs('ml_model/saved_models', exist_ok=True)
    os.makedirs('ml_model/dataset', exist_ok=True)
    os.makedirs('ml_model/visualizations', exist_ok=True)
    
    # Load dataset
    print("\n📂 Loading dataset...")
    dataset_path = 'ml_model/dataset/diabetes.csv'
    
    if not os.path.exists(dataset_path):
        # Try alternative path if not found
        alt_paths = [
            'diabetes.csv',
            '../diabetes.csv',
            '/content/drive/MyDrive/Diabetes_Prediction_System/dataset/diabetes.csv'
        ]
        for path in alt_paths:
            if os.path.exists(path):
                dataset_path = path
                break
    
    df = pd.read_csv(dataset_path)
    print(f"✅ Dataset loaded: {df.shape[0]} samples, {df.shape[1]} features")
    print(f"   Features: {', '.join(df.columns[:-1])}")
    
    # Data overview
    print("\n📊 Dataset Overview:")
    print(df.head())
    
    # Check for missing values
    print("\n🔍 Missing Values:")
    print(df.isnull().sum())
    
    # Handle zero values in medical features (optional, depending on your approach)
    zero_features = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']
    print("\n🔄 Checking for zero values in medical features...")
    for feature in zero_features:
        if feature in df.columns:
            zero_count = (df[feature] == 0).sum()
            zero_percent = (zero_count / len(df)) * 100
            print(f"   {feature}: {zero_count} zeros ({zero_percent:.2f}%)")
    
    # Prepare features and target
    feature_columns = ['Pregnancies', 'Glucose', 'BloodPressure', 'SkinThickness', 
                       'Insulin', 'BMI', 'DiabetesPedigreeFunction', 'Age']
    
    # Ensure all required features exist
    missing_features = [f for f in feature_columns if f not in df.columns]
    if missing_features:
        print(f"\n❌ Missing features: {missing_features}")
        return
    
    X = df[feature_columns]
    y = df['Outcome']
    
    # Target distribution
    print("\n🎯 Target Distribution:")
    outcome_counts = y.value_counts()
    print(f"   No Diabetes (0): {outcome_counts[0]} samples ({outcome_counts[0]/len(y)*100:.2f}%)")
    print(f"   Diabetes (1): {outcome_counts[1]} samples ({outcome_counts[1]/len(y)*100:.2f}%)")
    
    # Split data with stratification
    print("\n✂️ Splitting data...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"   Training set: {X_train.shape[0]} samples")
    print(f"   Testing set: {X_test.shape[0]} samples")
    
    # Scale features
    print("\n⚖️ Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    print("✅ Features scaled")
    
    # Train model
    print(f"\n🤖 Training {model_type.replace('_', ' ').title()} model...")
    
    if model_type == 'logistic_regression':
        model = LogisticRegression(
            C=1.0,
            max_iter=1000,
            random_state=42,
            class_weight='balanced',
            solver='liblinear'
        )
    elif model_type == 'random_forest':
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            class_weight='balanced'
        )
    else:
        print(f"❌ Unknown model type: {model_type}")
        return
    
    # Train
    model.fit(X_train_scaled, y_train)
    print("✅ Model training complete!")
    
    # Predictions
    y_train_pred = model.predict(X_train_scaled)
    y_test_pred = model.predict(X_test_scaled)
    
    # Probabilities
    y_train_proba = model.predict_proba(X_train_scaled)[:, 1]
    y_test_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    # Calculate metrics
    train_accuracy = accuracy_score(y_train, y_train_pred)
    test_accuracy = accuracy_score(y_test, y_test_pred)
    test_precision = precision_score(y_test, y_test_pred)
    test_recall = recall_score(y_test, y_test_pred)
    test_f1 = f1_score(y_test, y_test_pred)
    test_roc_auc = roc_auc_score(y_test, y_test_proba)
    
    # Cross-validation
    cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='accuracy')
    
    print("\n" + "="*60)
    print("TRAINING RESULTS")
    print("="*60)
    print(f"\n📊 Model Performance:")
    print(f"   Training Accuracy:   {train_accuracy:.4f} ({train_accuracy*100:.2f}%)")
    print(f"   Testing Accuracy:    {test_accuracy:.4f} ({test_accuracy*100:.2f}%)")
    print(f"   Precision:           {test_precision:.4f} ({test_precision*100:.2f}%)")
    print(f"   Recall:              {test_recall:.4f} ({test_recall*100:.2f}%)")
    print(f"   F1-Score:            {test_f1:.4f} ({test_f1*100:.2f}%)")
    print(f"   ROC-AUC:             {test_roc_auc:.4f} ({test_roc_auc*100:.2f}%)")
    print(f"\n📈 Cross-Validation (5-fold):")
    print(f"   Mean Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std()*2:.4f})")
    
    print("\n📋 Classification Report:")
    print(classification_report(y_test, y_test_pred, target_names=['No Diabetes', 'Diabetes']))
    
    print("\n🔢 Confusion Matrix:")
    cm = confusion_matrix(y_test, y_test_pred)
    print(cm)
    
    # Feature importance
    print("\n📊 Feature Importance:")
    if model_type == 'logistic_regression':
        importance = np.abs(model.coef_[0])
        feature_imp = pd.DataFrame({
            'feature': feature_columns,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        for i, row in feature_imp.iterrows():
            print(f"   {row['feature']}: {row['importance']:.4f}")
    else:
        feature_imp = pd.DataFrame({
            'feature': feature_columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        for i, row in feature_imp.iterrows():
            print(f"   {row['feature']}: {row['importance']:.4f}")
    
    # Save artifacts if requested
    if save_artifacts:
        print("\n💾 Saving model and artifacts...")
        
        # Save model
        model_filename = f'ml_model/saved_models/{model_type}.pkl'
        joblib.dump(model, model_filename)
        print(f"   ✅ Model saved: {model_filename}")
        
        # Save scaler
        scaler_filename = 'ml_model/saved_models/scaler.pkl'
        joblib.dump(scaler, scaler_filename)
        print(f"   ✅ Scaler saved: {scaler_filename}")
        
        # Save feature names
        feature_names_path = 'ml_model/saved_models/feature_names.json'
        with open(feature_names_path, 'w') as f:
            json.dump(feature_columns, f)
        print(f"   ✅ Feature names saved: {feature_names_path}")
        
        # Save model metadata
        metadata = {
            'model_type': model_type,
            'training_date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'dataset_size': len(df),
            'features': feature_columns,
            'performance': {
                'accuracy': test_accuracy,
                'precision': test_precision,
                'recall': test_recall,
                'f1': test_f1,
                'roc_auc': test_roc_auc,
                'cv_mean': cv_scores.mean(),
                'cv_std': cv_scores.std()
            },
            'risk_thresholds': {
                'low_risk': '<30%',
                'moderate_risk': '30-59%',
                'high_risk': '60-79%',
                'very_high_risk': '≥80%'
            }
        }
        
        metadata_path = 'ml_model/saved_models/model_metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"   ✅ Metadata saved: {metadata_path}")
        
        # Save training results as CSV
        # Create test set predictions with risk levels
        test_results = X_test.copy()
        test_results['True_Outcome'] = y_test
        test_results['Predicted_Outcome'] = y_test_pred
        test_results['Probability'] = y_test_proba
        
        # Add risk levels
        def get_risk_level(prob):
            if prob < 0.3:
                return 'LOW RISK'
            elif prob < 0.6:
                return 'MODERATE RISK'
            elif prob < 0.8:
                return 'HIGH RISK'
            else:
                return 'VERY HIGH RISK'
        
        test_results['Risk_Level'] = test_results['Probability'].apply(get_risk_level)
        
        results_path = 'ml_model/saved_models/test_predictions.csv'
        test_results.to_csv(results_path, index=False)
        print(f"   ✅ Test predictions saved: {results_path}")
        
        print("\n✅ All artifacts saved successfully!")
    
    # Plot confusion matrix
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=['No Diabetes', 'Diabetes'],
                yticklabels=['No Diabetes', 'Diabetes'])
    plt.title(f'Confusion Matrix - {model_type.replace("_", " ").title()}')
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.tight_layout()
    
    # Save plot
    plot_path = f'ml_model/visualizations/confusion_matrix_{model_type}.png'
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    print(f"\n📊 Confusion matrix saved: {plot_path}")
    plt.show()
    
    # Return model and artifacts for immediate use
    return {
        'model': model,
        'scaler': scaler,
        'feature_names': feature_columns,
        'X_test': X_test,
        'y_test': y_test,
        'y_pred': y_test_pred,
        'y_proba': y_test_proba,
        'accuracy': test_accuracy
    }


def train_both_models():
    """
    Train both Logistic Regression and Random Forest for comparison
    """
    print("="*60)
    print("TRAINING BOTH MODELS FOR COMPARISON")
    print("="*60)
    
    # Train Logistic Regression
    print("\n" + "="*60)
    lr_results = train_model('logistic_regression', save_artifacts=True)
    
    # Train Random Forest
    print("\n" + "="*60)
    rf_results = train_model('random_forest', save_artifacts=True)
    
    # Compare
    print("\n" + "="*60)
    print("MODEL COMPARISON")
    print("="*60)
    print(f"\nLogistic Regression Accuracy: {lr_results['accuracy']:.4f}")
    print(f"Random Forest Accuracy:      {rf_results['accuracy']:.4f}")
    
    if lr_results['accuracy'] > rf_results['accuracy']:
        print("\n🏆 Logistic Regression performs better!")
        best_model = 'logistic_regression'
    else:
        print("\n🏆 Random Forest performs better!")
        best_model = 'random_forest'
    
    # Save best model indicator
    with open('ml_model/saved_models/best_model.txt', 'w') as f:
        f.write(best_model)
    
    print(f"\n✅ Best model: {best_model}")
    print("\n💡 Use this model for predictions:")
    print(f'   predictor = DiabetesPredictor("ml_model/saved_models/{best_model}.pkl")')
    
    return lr_results, rf_results


def quick_train():
    """
    Quick training with minimal output (for testing)
    """
    print("Quick training mode...")
    
    # Load data
    df = pd.read_csv('ml_model/dataset/diabetes.csv')
    
    # Prepare
    X = df.drop('Outcome', axis=1)
    y = df['Outcome']
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train
    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    accuracy = accuracy_score(y_test, model.predict(X_test_scaled))
    print(f"Accuracy: {accuracy:.4f}")
    
    # Save
    os.makedirs('ml_model/saved_models', exist_ok=True)
    joblib.dump(model, 'ml_model/saved_models/logistic_regression.pkl')
    joblib.dump(scaler, 'ml_model/saved_models/scaler.pkl')
    
    # Save feature names
    with open('ml_model/saved_models/feature_names.json', 'w') as f:
        json.dump(list(X.columns), f)
    
    print("✅ Model saved successfully!")
    return model, scaler


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'quick':
            quick_train()
        elif sys.argv[1] == 'both':
            train_both_models()
        elif sys.argv[1] == 'rf':
            train_model('random_forest')
        else:
            train_model(sys.argv[1])
    else:
        # Default: train logistic regression
        train_model('logistic_regression')