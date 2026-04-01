import joblib
import numpy as np
import os
import json

import pandas as pd

class DiabetesPredictor:
    
    
    def __init__(self, model_path=None, scaler_path=None, features_path=None):
        
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.features_path = features_path
        
    def load_model(self):
        """Load the model and scaler from files"""
        try:
            # Use default paths if not specified
            if self.model_path is None:
                # Try multiple possible locations
                possible_paths = [
                    '/content/drive/MyDrive/Diabetes_Prediction_System/saved_models/logistic_regression.pkl',
                    'saved_models/logistic_regression.pkl',
                    '../saved_models/logistic_regression.pkl',
                    'ml_model/saved_models/logistic_regression.pkl'
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        self.model_path = path
                        break
                        
            if self.scaler_path is None:
                possible_scaler_paths = [
                    '/content/drive/MyDrive/Diabetes_Prediction_System/saved_models/scaler.pkl',
                    'saved_models/scaler.pkl',
                    '../saved_models/scaler.pkl',
                    'ml_model/saved_models/scaler.pkl'
                ]
                
                for path in possible_scaler_paths:
                    if os.path.exists(path):
                        self.scaler_path = path
                        break
            
            if self.features_path is None:
                possible_features_paths = [
                    '/content/drive/MyDrive/Diabetes_Prediction_System/saved_models/feature_names.json',
                    'saved_models/feature_names.json',
                    '../saved_models/feature_names.json',
                    'ml_model/saved_models/feature_names.json'
                ]
                
                for path in possible_features_paths:
                    if os.path.exists(path):
                        self.features_path = path
                        break
            
            # Load the files
            if self.model_path and os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                print(f"Model loaded from: {self.model_path}")
            else:
                raise FileNotFoundError("Model file not found!")
                
            if self.scaler_path and os.path.exists(self.scaler_path):
                self.scaler = joblib.load(self.scaler_path)
                print(f"Scaler loaded from: {self.scaler_path}")
            else:
                raise FileNotFoundError("Scaler file not found!")
                
            # Load feature names if available
            if self.features_path and os.path.exists(self.features_path):
                with open(self.features_path, 'r') as f:
                    self.feature_names = json.load(f)
                print(f"Feature names loaded from: {self.features_path}")
            else:
                # Default feature names (must match training order!)
                self.feature_names = ['Pregnancies', 'Glucose', 'BloodPressure', 
                                     'SkinThickness', 'Insulin', 'BMI', 
                                     'DiabetesPedigreeFunction', 'Age']
                print("⚠️ Using default feature names")
                
            return True
            
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def get_risk_level(self, probability):
       
        prob_percent = probability * 100
        
        if prob_percent < 30:
            return {
                'level': 'LOW RISK',
                'color': '🟢',
                'category': 'Low Risk',
                'interpretation': 'Very unlikely to have diabetes',
                'action': 'Maintain healthy lifestyle',
                'recommendation': 'Regular checkups every 2-3 years'
            }
        elif prob_percent < 60:
            return {
                'level': 'MODERATE RISK',
                'color': '🟡',
                'category': 'Moderate Risk',
                'interpretation': 'Needs lifestyle monitoring',
                'action': 'Consider dietary changes and exercise',
                'recommendation': 'Annual checkup recommended'
            }
        elif prob_percent < 80:
            return {
                'level': 'HIGH RISK',
                'color': '🟠',
                'category': 'High Risk',
                'interpretation': 'Medical consultation recommended',
                'action': 'Consult healthcare provider',
                'recommendation': 'Schedule appointment within 1 month'
            }
        else:
            return {
                'level': 'VERY HIGH RISK',
                'color': '🔴',
                'category': 'Very High Risk',
                'interpretation': 'Strong likelihood of diabetes',
                'action': 'Immediate medical attention needed',
                'recommendation': 'Consult doctor within 1 week'
            }
    
    def predict(self, features):
        """
        Predict diabetes risk
        
        Args:
            features: dict with keys matching feature names
                     (case-insensitive, can use simplified names)
        
        Returns:
            dict with complete prediction results
        """
        if self.model is None or self.scaler is None:
            success = self.load_model()
            if not success:
                return {'error': 'Model not loaded properly'}
        
        try:
            # Map input features to correct order (CRITICAL!)
            # Create array in the EXACT order the model was trained on
            feature_values = []
            
            # Map common input names to expected feature names
            feature_mapping = {
                'pregnancies': 'Pregnancies',
                'glucose': 'Glucose',
                'blood_pressure': 'BloodPressure',
                'bp': 'BloodPressure',
                'skin_thickness': 'SkinThickness',
                'skin': 'SkinThickness',
                'insulin': 'Insulin',
                'bmi': 'BMI',
                'diabetes_pedigree': 'DiabetesPedigreeFunction',
                'pedigree': 'DiabetesPedigreeFunction',
                'dpf': 'DiabetesPedigreeFunction',
                'age': 'Age'
            }
            
            # Create a standardized features dict
            standardized_features = {}
            for input_key, value in features.items():
                input_key_lower = input_key.lower().strip()
                if input_key_lower in feature_mapping:
                    std_name = feature_mapping[input_key_lower]
                    standardized_features[std_name] = value
                else:
                    # Try direct match
                    standardized_features[input_key] = value
            
            # Build array in correct order
            for feat_name in self.feature_names:
                if feat_name in standardized_features:
                    feature_values.append(standardized_features[feat_name])
                else:
                    # Use default values for missing features
                    defaults = {
                        'Pregnancies': 0,
                        'Glucose': 100,
                        'BloodPressure': 70,
                        'SkinThickness': 20,
                        'Insulin': 80,
                        'BMI': 25,
                        'DiabetesPedigreeFunction': 0.5,
                        'Age': 30
                    }
                    feature_values.append(defaults.get(feat_name, 0))
                    print(f"⚠️ Missing feature '{feat_name}', using default: {defaults.get(feat_name, 0)}")
            
            # Convert to numpy array and reshape
            feature_array = np.array([feature_values])
            
            # Scale features
            feature_scaled = self.scaler.transform(feature_array)
            
            # Make prediction
            prediction = self.model.predict(feature_scaled)[0]
            probability = self.model.predict_proba(feature_scaled)[0][1]
            
            # Get risk level
            risk_info = self.get_risk_level(probability)
            
            # Return comprehensive results
            return {
                'success': True,
                'prediction': 'Diabetic' if prediction == 1 else 'Non-Diabetic',
                'prediction_code': int(prediction),
                'probability': float(probability),
                'probability_percent': float(probability * 100),
                'risk_level': risk_info['level'],
                'risk_color': risk_info['color'],
                'risk_category': risk_info['category'],
                'interpretation': risk_info['interpretation'],
                'action': risk_info['action'],
                'recommendation': risk_info['recommendation'],
                'input_features': features,
                'features_used': dict(zip(self.feature_names, feature_values))
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def predict_batch(self, features_list):
        """
        Predict for multiple patients
        
        Args:
            features_list: list of feature dictionaries
        
        Returns:
            list of prediction results
        """
        results = []
        for i, features in enumerate(features_list):
            result = self.predict(features)
            result['patient_id'] = i + 1
            results.append(result)
        return results
    
    def explain_prediction(self, features):
        """
        Provide explanation for prediction (which features contributed most)
        """
        if self.model is None or self.scaler is None:
            self.load_model()
        
        try:
            # Get feature values in correct order
            feature_values = []
            for feat_name in self.feature_names:
                if feat_name.lower() in [k.lower() for k in features.keys()]:
                    # Find the matching key (case-insensitive)
                    for k, v in features.items():
                        if k.lower() == feat_name.lower():
                            feature_values.append(v)
                            break
                else:
                    feature_values.append(0)
            
            feature_array = np.array([feature_values])
            feature_scaled = self.scaler.transform(feature_array)
            
            # For Logistic Regression, get coefficients
            if hasattr(self.model, 'coef_'):
                coefficients = self.model.coef_[0]
                contributions = coefficients * feature_scaled[0]
                
                # Sort by absolute contribution
                contrib_df = pd.DataFrame({
                    'feature': self.feature_names,
                    'value': feature_values,
                    'coefficient': coefficients,
                    'contribution': contributions,
                    'abs_contribution': np.abs(contributions)
                }).sort_values('abs_contribution', ascending=False)
                
                return contrib_df[['feature', 'value', 'coefficient', 'contribution']].to_dict('records')
            else:
                return {"message": "Explanation not available for this model type"}
                
        except Exception as e:
            return {"error": str(e)}



_predictor = None

def get_predictor():
    """Get or create the global predictor instance"""
    global _predictor
    if _predictor is None:
        _predictor = DiabetesPredictor()
        _predictor.load_model()
    return _predictor

def quick_predict(features):
    
    predictor = get_predictor()
    result = predictor.predict(features)
    
    if result.get('success'):
        return {
            'prediction': result['prediction'],
            'probability': result['probability'],
            'risk_percent': result['probability_percent'],
            'risk_level': result['risk_level'],
            'risk_color': result['risk_color'],
            'interpretation': result['interpretation']
        }
    else:
        return {'error': result.get('error', 'Unknown error')}


if __name__ == '__main__':
    print("="*60)
    print("DIABETES PREDICTION SYSTEM - TEST")
    print("="*60)
    
    # Method 1: Using the class (recommended for production)
    print("\nMethod 1: Using the DiabetesPredictor class")
    predictor = DiabetesPredictor()
    
    # Sample data with simplified keys
    sample_data = {
        'pregnancies': 2,
        'glucose': 120,
        'blood_pressure': 70,
        'skin_thickness': 20,
        'insulin': 80,
        'bmi': 28.5,
        'diabetes_pedigree': 0.5,
        'age': 35
    }
    
    result = predictor.predict(sample_data)
    
    if result.get('success'):
        print(f"\n Prediction Successful!")
        print(f"   • Diabetes Probability: {result['probability_percent']:.1f}%")
        print(f"   • Prediction: {result['prediction']}")
        print(f"   • Risk Level: {result['risk_color']} {result['risk_level']}")
        print(f"   • Interpretation: {result['interpretation']}")
        print(f"   • Action: {result['action']}")
    else:
        print(f"Error: {result.get('error')}")
    
    # Method 2: Using the simplified function
    print("\nMethod 2: Using quick_predict function")
    
    # Test different risk levels
    test_cases = [
        {"name": "Low Risk", "data": {'pregnancies': 0, 'glucose': 85, 'blood_pressure': 65, 
                                       'bmi': 22.5, 'diabetes_pedigree': 0.2, 'age': 25}},
        {"name": "Moderate Risk", "data": {'pregnancies': 2, 'glucose': 120, 'blood_pressure': 70, 
                                           'bmi': 28.5, 'diabetes_pedigree': 0.5, 'age': 35}},
        {"name": "High Risk", "data": {'pregnancies': 5, 'glucose': 160, 'blood_pressure': 85, 
                                       'bmi': 35.5, 'diabetes_pedigree': 0.8, 'age': 45}},
        {"name": "Very High Risk", "data": {'pregnancies': 8, 'glucose': 200, 'blood_pressure': 95, 
                                            'bmi': 42.5, 'diabetes_pedigree': 1.5, 'age': 55}}
    ]
    
    for test in test_cases:
        quick_result = quick_predict(test['data'])
        if 'error' not in quick_result:
            print(f"\n   {test['name']}:")
            print(f"      Risk: {quick_result['risk_color']} {quick_result['risk_level']}")
            print(f"      Probability: {quick_result['risk_percent']:.1f}%")
            print(f"      {quick_result['interpretation']}")
    
    # Batch prediction example
    print("\nBatch Prediction Example:")
    batch_results = predictor.predict_batch([t['data'] for t in test_cases])
    for res in batch_results:
        if res.get('success'):
            print(f"   Patient {res['patient_id']}: {res['risk_color']} {res['risk_level']} ({res['probability_percent']:.1f}%)")