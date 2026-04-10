"""
Prediction Service - Manages prediction requests and history with database storage
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from .ml_service import get_ml_service
from backend.models.prediction import Prediction
from backend.extensions import db
import json


class PredictionService:
    """
    Prediction Service - Manages prediction requests and history
    """
    
    def __init__(self, db_session=None):
        """
        Initialize prediction service
        
        Args:
            db_session: Optional database session for saving predictions
        """
        self.ml_service = get_ml_service()
        self.db_session = db_session or db.session
        self.prediction_history = []  # In-memory cache
    
    def predict_diabetes(self, patient_data: Dict[str, Any], 
                        patient_id: Optional[int] = None,
                        health_record_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Predict diabetes risk for a patient.
        NOTE: Does NOT save to DB — the calling route handles persistence.
        """
        result = self.ml_service.predict(patient_data)
        
        if result.get('success'):
            result['timestamp'] = datetime.now().isoformat()
            result['patient_id'] = patient_id
        
        return result
    
    def get_patient_history(self, patient_id: int, 
                           limit: int = 10, 
                           offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get prediction history for a patient from database
        
        Args:
            patient_id: Patient identifier
            limit: Number of records to return
            offset: Offset for pagination
        
        Returns:
            List of past predictions
        """
        predictions = Prediction.query.filter_by(patient_id=patient_id)\
            .order_by(Prediction.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        return [self._prediction_to_dict(p) for p in predictions]
    
    def get_patient_history_count(self, patient_id: int) -> int:
        """Get total count of predictions for a patient"""
        return Prediction.query.filter_by(patient_id=patient_id).count()
    
    def get_prediction_by_id(self, prediction_id: int, 
                            patient_id: Optional[int] = None) -> Optional[Dict]:
        """
        Get prediction by ID
        
        Args:
            prediction_id: Prediction ID
            patient_id: Optional patient filter for security
        
        Returns:
            Prediction dict or None
        """
        query = Prediction.query.filter_by(id=prediction_id)
        
        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        
        prediction = query.first()
        
        if prediction:
            return self._prediction_to_dict(prediction)
        return None
    
    def compare_predictions(self, prediction_ids: List[int]) -> Dict[str, Any]:
        """
        Compare multiple predictions
        
        Args:
            prediction_ids: List of prediction IDs to compare
        
        Returns:
            Comparison results
        """
        predictions = []
        for pid in prediction_ids:
            pred = self.get_prediction_by_id(pid)
            if pred:
                predictions.append(pred)
        
        if len(predictions) < 2:
            return {'error': 'Need at least 2 predictions for comparison'}
        
        # Calculate trends
        probabilities = [p['probability'] for p in predictions]
        trend = 'increasing' if probabilities[-1] > probabilities[0] else 'decreasing'
        
        return {
            'success': True,
            'predictions': predictions,
            'trend': trend,
            'change': round(abs(probabilities[-1] - probabilities[0]) * 100, 2),
            'first_probability': round(probabilities[0] * 100, 2),
            'last_probability': round(probabilities[-1] * 100, 2)
        }
    
    def get_risk_statistics(self, patient_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get risk statistics
        
        Args:
            patient_id: Optional patient filter
        
        Returns:
            Statistics dictionary
        """
        query = Prediction.query
        
        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        
        predictions = query.all()
        
        if not predictions:
            return {
                'success': True,
                'total_predictions': 0,
                'message': 'No predictions found'
            }
        
        probabilities = [p.probability for p in predictions]
        
        return {
            'success': True,
            'total_predictions': len(predictions),
            'average_risk': round(sum(probabilities) / len(probabilities) * 100, 2),
            'min_risk': round(min(probabilities) * 100, 2),
            'max_risk': round(max(probabilities) * 100, 2),
            'latest_risk': round(probabilities[-1] * 100, 2),
            'risk_distribution': self._get_risk_distribution(predictions)
        }
    
    def _get_risk_distribution(self, predictions: List[Prediction]) -> Dict[str, int]:
        """Calculate risk distribution from database records"""
        distribution = {
            'LOW RISK': 0,
            'MODERATE RISK': 0,
            'HIGH RISK': 0,
            'VERY HIGH RISK': 0
        }
        
        for pred in predictions:
            risk_level = pred.risk_level
            if risk_level in distribution:
                distribution[risk_level] += 1
        
        return distribution
    
    def _save_to_database(self, prediction_result: Dict[str, Any], 
                         patient_id: int,
                         health_record_id: Optional[int] = None) -> Optional[Prediction]:
        """
        Save prediction to database
        
        Args:
            prediction_result: Prediction result from ML service
            patient_id: Patient ID
            health_record_id: Optional health record ID
        
        Returns:
            Prediction record or None
        """
        try:
            # Create new prediction record
            prediction = Prediction(
                patient_id=patient_id,
                health_record_id=health_record_id,
                prediction=prediction_result.get('prediction_code', 0),
                probability=prediction_result.get('probability', 0),
                probability_percent=prediction_result.get('probability_percent', 0),
                risk_level=prediction_result.get('risk_level', 'UNKNOWN'),
                # Note: risk_color is not stored in database
                model_version=prediction_result.get('model_version', '1.0.0'),
                explanation=prediction_result.get('interpretation', ''),
                input_data=prediction_result.get('features_used', {}),
                created_at=datetime.utcnow()
            )
            
            self.db_session.add(prediction)
            self.db_session.commit()
            
            return prediction
            
        except Exception as e:
            self.db_session.rollback()
            print(f"Error saving prediction to database: {e}")
            return None
    
    def _prediction_to_dict(self, prediction: Prediction) -> Dict[str, Any]:
        """Convert Prediction model to dictionary"""
        return {
            'id': prediction.id,
            'patient_id': prediction.patient_id,
            'health_record_id': prediction.health_record_id,
            'prediction': 'Diabetic' if prediction.prediction == 1 else 'Non-Diabetic',
            'prediction_code': prediction.prediction,
            'probability': prediction.probability,
            'probability_percent': prediction.probability_percent,
            'risk_level': prediction.risk_level,
            'model_version': prediction.model_version,
            'explanation': prediction.explanation,
            'input_data': prediction.input_data,
            'created_at': prediction.created_at.isoformat() if prediction.created_at else None
        }