from datetime import datetime
from backend.extensions import db

class Prediction(db.Model):  # Changed from PredictionResult for consistency
    __tablename__ = 'predictions'  # Simpler table name
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys - Fixed to match your Patient model
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)  # Changed from user_id
    health_record_id = db.Column(db.Integer, db.ForeignKey('health_records.id'))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'))  # Optional: who reviewed
    
    # ML Prediction Results
    prediction = db.Column(db.Integer, nullable=False)  # 0 = Non-Diabetic, 1 = Diabetic
    probability = db.Column(db.Float, nullable=False)  # 0.00 to 1.00
    probability_percent = db.Column(db.Float, nullable=False)  # 0.00 to 100.00
    
    # Risk Level (4 levels as per your ML model)
    risk_level = db.Column(db.String(50), nullable=False)  # LOW, MODERATE, HIGH, VERY_HIGH
    
    # ML Model Metadata
    model_version = db.Column(db.String(50), default="1.0.0")
    model_used = db.Column(db.String(50), default="Logistic Regression")
    
    # Explanation from ML model
    explanation = db.Column(db.Text)  # Why this prediction?
    
    # Input data snapshot (store what was used for prediction)
    input_data = db.Column(db.JSON)  # Stores the health metrics used

    # Audit / compliance
    ip_address = db.Column(db.String(50), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'health_record_id': self.health_record_id,
            'doctor_id': self.doctor_id,
            
            # Prediction results
            'prediction': self.prediction,
            'prediction_label': 'Diabetic' if self.prediction == 1 else 'Non-Diabetic',
            'probability': round(self.probability, 4),
            'probability_percent': round(self.probability_percent, 2),
            'risk_level': self.risk_level,
            
            # ML info
            'model_version': self.model_version,
            'model_used': self.model_used,
            'explanation': self.explanation,
            'input_data': self.input_data,
            
            # Timestamp
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Prediction {self.id}: {self.risk_level} ({self.probability_percent:.1f}%)>'