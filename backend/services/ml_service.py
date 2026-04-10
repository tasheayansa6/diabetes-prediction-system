"""
ML Service - Core machine learning model integration
Handles all interactions with trained ML models for diabetes prediction
"""

import joblib
import numpy as np
import pandas as pd
import json
import os
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MLService:
    """
    Machine Learning Service for Diabetes Prediction
    Handles model loading, predictions, and risk assessment
    """
    
    # Risk thresholds as class constants for easy modification
    RISK_THRESHOLDS = {
        'low': {'min': 0, 'max': 30, 'level': 'LOW RISK', 'color': 'green'},
        'moderate': {'min': 30, 'max': 60, 'level': 'MODERATE RISK', 'color': 'yellow'},
        'high': {'min': 60, 'max': 80, 'level': 'HIGH RISK', 'color': 'orange'},
        'very_high': {'min': 80, 'max': 100, 'level': 'VERY HIGH RISK', 'color': 'red'}
    }
    
    # Default values for missing features
    DEFAULT_FEATURE_VALUES = {
        'Pregnancies': 0,
        'Glucose': 100,
        'BloodPressure': 70,
        'SkinThickness': 20,
        'Insulin': 80,
        'BMI': 25,
        'DiabetesPedigreeFunction': 0.5,
        'Age': 30
    }
    
    # Feature name mapping for common input variations
    FEATURE_MAPPING = {
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
    
    def __init__(self, model_dir: Union[str, Path] = None):
        """
        Initialize ML service with model directory
        
        Args:
            model_dir: Directory containing trained models (optional)
                      If not provided, will automatically find the models
        """
        if model_dir is None:
            # Automatically find the model directory
            # Get the location of this file
            current_file = Path(__file__).absolute()  # .../backend/services/ml_service.py
            
            # Go up to project root (3 levels: services/backend/root)
            project_root = current_file.parent.parent.parent  # .../diabetes-prediction-system/
            
            # Set the correct path to ml_model/saved_models
            self.model_dir = project_root / 'ml_model' / 'saved_models'
            
            print(f"Auto-detected model directory: {self.model_dir}")
        else:
            self.model_dir = Path(model_dir)
            print(f"Using provided model directory: {self.model_dir}")
        
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.model_metadata = None
        self.active_model_file = None
        self.active_model_entry = None
        self.load_successful = False
        
        # Try to load artifacts on initialization
        self._load_artifacts()
        
        if self.load_successful:
            logger.info(f"ML Service initialized successfully from {self.model_dir}")
        else:
            logger.warning(f"ML Service initialized but model not loaded from {self.model_dir}")
    
    def _load_artifacts(self) -> bool:
        """
        Load model, scaler, and feature names from disk.
        Reads model_registry.json to determine which model is active.
        """
        try:
            # ── Determine active model file from registry ──
            registry_path = self.model_dir.parent / 'model_registry.json'
            active_file = 'logistic_regression.pkl'  # default fallback

            if registry_path.exists():
                import json as _json
                with open(registry_path, 'r') as f:
                    registry = _json.load(f)
                active = next((m for m in registry if m.get('status') == 'active'), None)
                if active:
                    self.active_model_entry = active
                    algo = active.get('algorithm', '').lower().replace(' ', '_')
                    # If registry has explicit filename, use it directly
                    if active.get('filename'):
                        active_file = active['filename']
                    else:
                        # Map algorithm name to pkl filename
                        algo_file_map = {
                            'logistic_regression':       'logistic_regression.pkl',
                            'random_forest':             'random_forest.pkl',
                            'logistic_regression_tuned': 'logistic_regression_tuned.pkl',
                            'diabetes_prediction_model': 'diabetes_prediction_model.pkl',
                            'gradient_boosting':         'gradient_boosting.pkl',
                            'xgboost':                   'xgboost.pkl',
                            'svm':                       'svm.pkl',
                            'neural_network':            'neural_network.pkl',
                        }
                        active_file = algo_file_map.get(algo, 'logistic_regression.pkl')
                    print(f"Active model from registry: {active.get('algorithm')} -> {active_file}")

            model_path   = self.model_dir / active_file
            scaler_path  = self.model_dir / 'scaler.pkl'
            feature_path = self.model_dir / 'feature_names.json'
            metadata_path= self.model_dir / 'model_metadata.json'

            print(f"\nLooking for model files in: {self.model_dir}")
            print(f"   Model file ({active_file}) exists: {model_path.exists()}")
            print(f"   Scaler file exists: {scaler_path.exists()}")
            print(f"   Features file exists: {feature_path.exists()}")

            # Fallback to logistic_regression if active model file missing
            if not model_path.exists():
                fallback = self.model_dir / 'logistic_regression.pkl'
                if fallback.exists():
                    logger.warning(f"{active_file} not found, falling back to logistic_regression.pkl")
                    model_path = fallback
                else:
                    # Final fallback: first available .pkl model in saved_models directory
                    candidates = sorted(self.model_dir.glob('*.pkl'))
                    # Prefer non-scaler artifacts
                    candidates = [c for c in candidates if c.name.lower() != 'scaler.pkl']
                    if candidates:
                        model_path = candidates[0]
                        logger.warning(f"{active_file} not found, using first available model: {model_path.name}")
                    else:
                        logger.error(f"Model file not found: {model_path}")
                        return False

            if not scaler_path.exists():
                logger.error(f"Scaler file not found: {scaler_path}")
                return False

            # Load model and scaler with compatibility fallback
            import warnings
            model_candidates = [model_path]
            # Add fallback files while preserving order and uniqueness
            for candidate in sorted(self.model_dir.glob('*.pkl')):
                if candidate.name.lower() == 'scaler.pkl':
                    continue
                if candidate not in model_candidates:
                    model_candidates.append(candidate)

            load_error = None
            loaded_model_path = None
            for candidate in model_candidates:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        _model = joblib.load(candidate)
                        _scaler = joblib.load(scaler_path)
                    self.model = _model
                    self.scaler = _scaler
                    loaded_model_path = candidate
                    break
                except Exception as e:
                    load_error = e
                    logger.warning(f"Failed loading model candidate {candidate.name}: {e}")

            if loaded_model_path is None:
                logger.error(f"Failed to load any model artifact: {load_error}")
                return False

            self.active_model_file = loaded_model_path.name
            # Keep active model metadata aligned with the actual loaded file.
            if registry_path.exists():
                try:
                    with open(registry_path, 'r') as f:
                        registry = json.load(f)
                    matched = next((m for m in registry if m.get('filename') == self.active_model_file), None)
                    if matched:
                        self.active_model_entry = matched
                    else:
                        self.active_model_entry = {
                            'version': 'fallback',
                            'algorithm': type(self.model).__name__,
                            'filename': self.active_model_file,
                            'status': 'fallback_active'
                        }
                except Exception:
                    pass

            print(f"Loaded model: {type(self.model).__name__} from {self.active_model_file}")

            # Load feature names
            if feature_path.exists():
                with open(feature_path, 'r') as f:
                    self.feature_names = json.load(f)
                print(f"Loaded feature names: {self.feature_names}")
            else:
                self.feature_names = list(self.DEFAULT_FEATURE_VALUES.keys())
                logger.warning(f"Feature names file not found, using defaults: {self.feature_names}")

            # Load metadata
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.model_metadata = json.load(f)
                print(f"Loaded model metadata")

            self.load_successful = True
            return True

        except Exception as e:
            logger.error(f"Failed to load artifacts: {e}")
            return False
    
    def is_ready(self) -> bool:
        """Check if the service is ready to make predictions"""
        return self.model is not None and self.scaler is not None
    
    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make diabetes prediction for a single patient
        
        Args:
            features: Dictionary with patient features
        
        Returns:
            Dictionary with comprehensive prediction results
        """
        # Check if model is loaded
        if not self.is_ready():
            success = self._load_artifacts()
            if not success:
                return {
                    'success': False,
                    'error': 'Model not loaded',
                    'error_code': 'MODEL_NOT_LOADED'
                }
        
        try:
            # Validate input
            if not features:
                return {
                    'success': False,
                    'error': 'Empty features provided',
                    'error_code': 'EMPTY_FEATURES'
                }

            # Basic clinical validation
            validation_errors = []
            glucose = float(features.get('glucose', features.get('Glucose', 0)))
            bmi     = float(features.get('bmi', features.get('BMI', 0)))
            age     = float(features.get('age', features.get('Age', 0)))
            bp      = float(features.get('blood_pressure', features.get('BloodPressure', 0)))
            if glucose <= 0:   validation_errors.append('Glucose must be greater than 0')
            if bmi <= 0:       validation_errors.append('BMI must be greater than 0')
            if age <= 0:       validation_errors.append('Age must be greater than 0')
            if age > 120:      validation_errors.append('Age must be realistic (≤ 120)')
            if glucose > 600:  validation_errors.append('Glucose value seems unrealistic (> 600)')
            if bmi > 100:      validation_errors.append('BMI value seems unrealistic (> 100)')
            if bp > 300:       validation_errors.append('Blood pressure seems unrealistic (> 300)')
            if validation_errors:
                return {
                    'success': False,
                    'error': '; '.join(validation_errors),
                    'error_code': 'INVALID_INPUT'
                }
            
            # Prepare feature array in correct order
            feature_values = []
            missing_features = []
            
            for feat_name in self.feature_names:
                value = self._extract_feature_value(features, feat_name)
                
                if value is None:
                    # Use default value
                    value = self.DEFAULT_FEATURE_VALUES.get(feat_name, 0)
                    missing_features.append(feat_name)
                
                feature_values.append(float(value))
            
            # Convert to numpy array and scale
            feature_array = np.array([feature_values])
            feature_scaled = self.scaler.transform(feature_array)
            
            # Make prediction
            prediction = self.model.predict(feature_scaled)[0]
            probability = self._get_probability(feature_scaled, prediction)
            
            # Get risk level
            risk_info = self._get_risk_level(probability)
            
            # Calculate confidence — capped at 95% to reflect real-world model uncertainty
            raw_confidence = max(probability, 1 - probability)
            # Apply calibration: scale [0.5, 1.0] → [50%, 95%] to avoid misleading 100%
            confidence = 50.0 + (raw_confidence - 0.5) * 90.0
            
            # Prepare result
            result = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'prediction': 'Diabetic' if prediction == 1 else 'Non-Diabetic',
                'prediction_code': int(prediction),
                'probability': round(float(probability), 4),
                'probability_percent': round(float(probability * 100), 2),
                'risk_level': risk_info['level'],
                'risk_color': risk_info['color'],
                'risk_category': risk_info['category'],
                'interpretation': risk_info['interpretation'],
                'action': risk_info['action'],
                'recommendation': risk_info['recommendation'],
                'confidence': round(confidence, 1),
                'features_used': dict(zip(self.feature_names, feature_values)),
                'model_version': (self.active_model_entry or {}).get('version', '1.0.0'),
                'model_algorithm': (self.active_model_entry or {}).get('algorithm', type(self.model).__name__),
                'model_file': self.active_model_file
            }
            
            # Add warning if features were missing
            if missing_features:
                result['warning'] = f"Missing features: {', '.join(missing_features)}. Default values used."
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'error_code': 'PREDICTION_FAILED'
            }

    def _get_probability(self, feature_scaled: np.ndarray, prediction: Any) -> float:
        """
        Return positive-class probability in [0,1] for models with/without predict_proba.
        """
        # Preferred path
        if hasattr(self.model, 'predict_proba'):
            proba = self.model.predict_proba(feature_scaled)
            # Typical binary shape: (n,2)
            if len(proba.shape) == 2 and proba.shape[1] >= 2:
                return float(proba[0][1])
            # Some wrappers may return single column
            return float(proba[0][0])

        # Fallback: use decision_function and sigmoid mapping
        if hasattr(self.model, 'decision_function'):
            score = float(self.model.decision_function(feature_scaled)[0])
            return float(1 / (1 + np.exp(-score)))

        # Last-resort fallback: map class prediction to coarse probability
        pred = int(prediction)
        return 0.8 if pred == 1 else 0.2
    
    def _extract_feature_value(self, features: Dict[str, Any], target_feature: str) -> Optional[float]:
        """Extract feature value from input dictionary using multiple matching strategies"""
        # Try exact match
        if target_feature in features:
            return features[target_feature]
        
        # Try case-insensitive match
        target_lower = target_feature.lower()
        for key, value in features.items():
            if key.lower() == target_lower:
                return value
        
        # Try mapped names
        for input_key, mapped_name in self.FEATURE_MAPPING.items():
            if mapped_name == target_feature:
                if input_key in features:
                    return features[input_key]
                if input_key.title() in features:
                    return features[input_key.title()]
        
        return None
    
    def _get_risk_level(self, probability: float) -> Dict[str, str]:
        """Determine risk level based on probability (4-tier system)"""
        prob_percent = probability * 100
        
        if prob_percent < 30:
            return {
                'level': 'LOW RISK', 'color': 'green', 'category': 'Low Risk',
                'interpretation': 'Very unlikely to have diabetes',
                'action': 'Maintain healthy lifestyle',
                'recommendation': 'Regular checkups every 2-3 years'
            }
        elif prob_percent < 60:
            return {
                'level': 'MODERATE RISK', 'color': 'yellow', 'category': 'Moderate Risk',
                'interpretation': 'Needs lifestyle monitoring',
                'action': 'Consider dietary changes and exercise',
                'recommendation': 'Annual checkup recommended'
            }
        elif prob_percent < 80:
            return {
                'level': 'HIGH RISK', 'color': 'orange', 'category': 'High Risk',
                'interpretation': 'Medical consultation recommended',
                'action': 'Consult healthcare provider',
                'recommendation': 'Schedule appointment within 1 month'
            }
        else:
            return {
                'level': 'VERY HIGH RISK', 'color': 'red', 'category': 'Very High Risk',
                'interpretation': 'Strong likelihood of diabetes',
                'action': 'Immediate medical attention needed',
                'recommendation': 'Consult doctor within 1 week'
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        if self.model is None:
            return {
                'success': False,
                'error': 'Model not loaded',
                'status': 'unavailable'
            }

        return {
            'success': True,
            'status': 'loaded',
            'model_type': type(self.model).__name__,
            'model_file': self.active_model_file,
            'active_model_version': (self.active_model_entry or {}).get('version'),
            'active_model_algorithm': (self.active_model_entry or {}).get('algorithm'),
            'features': self.feature_names,
            'n_features': len(self.feature_names),
            'model_dir': str(self.model_dir),
            'risk_classification': {
                'low_risk': '0% - 30%',
                'moderate_risk': '30% - 60%',
                'high_risk': '60% - 80%',
                'very_high_risk': '80% - 100%'
            }
        }


# Global instance for easy access
_ml_service_instance = None


def get_ml_service(force_reload: bool = False) -> MLService:
    """Get or create the global ML service instance"""
    global _ml_service_instance
    if _ml_service_instance is None or force_reload:
        _ml_service_instance = MLService()
        logger.info("Created new MLService instance")
    return _ml_service_instance