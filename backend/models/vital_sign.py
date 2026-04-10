"""
Vital Signs Model - Represents patient vital signs recorded by nurses
"""

from backend.extensions import db
from datetime import datetime

class VitalSign(db.Model):
    __tablename__ = 'vital_signs'
    
    id = db.Column(db.Integer, primary_key=True)
    vital_id = db.Column(db.String(20), unique=True)
    
    # Foreign Keys
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    nurse_id = db.Column(db.Integer, db.ForeignKey('nurses.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    
    # Vital Signs
    temperature = db.Column(db.Float, nullable=True)  # in Celsius
    heart_rate = db.Column(db.Integer, nullable=True)  # bpm
    respiratory_rate = db.Column(db.Integer, nullable=True)  # breaths per minute
    blood_pressure_systolic = db.Column(db.Integer, nullable=True)
    blood_pressure_diastolic = db.Column(db.Integer, nullable=True)
    oxygen_saturation = db.Column(db.Float, nullable=True)  # SpO2 percentage
    height = db.Column(db.Float, nullable=True)  # in cm
    weight = db.Column(db.Float, nullable=True)  # in kg
    bmi = db.Column(db.Float, nullable=True)
    skin_thickness = db.Column(db.Float, nullable=True)  # triceps skinfold in mm
    pain_level = db.Column(db.Integer, nullable=True)  # 0-10 scale

    # ML prediction fields collected by nurse
    pregnancies = db.Column(db.Integer, nullable=True)           # 0 if male
    diabetes_pedigree = db.Column(db.Float, nullable=True)       # family history score
    age = db.Column(db.Integer, nullable=True)                   # patient age in years
    
    # Additional Info
    notes = db.Column(db.Text, nullable=True)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'vital_id': self.vital_id,
            'patient_id': self.patient_id,
            'nurse_id': self.nurse_id,
            'appointment_id': self.appointment_id,
            'temperature': self.temperature,
            'heart_rate': self.heart_rate,
            'respiratory_rate': self.respiratory_rate,
            'blood_pressure_systolic': self.blood_pressure_systolic,
            'blood_pressure_diastolic': self.blood_pressure_diastolic,
            'oxygen_saturation': self.oxygen_saturation,
            'height': self.height,
            'weight': self.weight,
            'bmi': self.bmi,
            'skin_thickness': self.skin_thickness,
            'pain_level': self.pain_level,
            'pregnancies': self.pregnancies,
            'diabetes_pedigree': self.diabetes_pedigree,
            'age': self.age,
            'notes': self.notes,
            'recorded_at': self.recorded_at.isoformat() if self.recorded_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<VitalSign {self.id}: Patient {self.patient_id}>'