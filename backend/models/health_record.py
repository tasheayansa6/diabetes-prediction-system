from datetime import datetime
from backend.extensions import db

class HealthRecord(db.Model):
    __tablename__ = 'health_records'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)  # Changed from user_id
    pregnancies = db.Column(db.Integer, default=0)
    glucose = db.Column(db.Float, nullable=False)
    blood_pressure = db.Column(db.Float, nullable=False)
    skin_thickness = db.Column(db.Float, default=0)
    insulin = db.Column(db.Float, default=0)
    bmi = db.Column(db.Float, nullable=False)
    diabetes_pedigree = db.Column(db.Float, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,  # Changed
            'pregnancies': self.pregnancies,
            'glucose': self.glucose,
            'blood_pressure': self.blood_pressure,
            'skin_thickness': self.skin_thickness,
            'insulin': self.insulin,
            'bmi': self.bmi,
            'diabetes_pedigree': self.diabetes_pedigree,
            'age': self.age,
            'created_at': self.created_at.isoformat()
        }