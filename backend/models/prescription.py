from datetime import datetime
from backend.extensions import db

class Prescription(db.Model):
    __tablename__ = 'prescriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.String(20), unique=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    prediction_id = db.Column(db.Integer, nullable=True)
    
    medication = db.Column(db.Text, nullable=False)
    dosage = db.Column(db.String(100))
    frequency = db.Column(db.String(50))
    duration = db.Column(db.String(50))
    instructions = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    status = db.Column(db.String(20), default='pending')
    verified_by = db.Column(db.Integer, db.ForeignKey('pharmacists.id'))
    verified_at = db.Column(db.DateTime)
    dispensed_by = db.Column(db.Integer, db.ForeignKey('pharmacists.id'))
    dispensed_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'prescription_id': self.prescription_id,
            'patient_id': self.patient_id,
            'doctor_id': self.doctor_id,
            'prediction_id': self.prediction_id,
            'medication': self.medication,
            'dosage': self.dosage,
            'frequency': self.frequency,
            'duration': self.duration,
            'instructions': self.instructions,
            'notes': self.notes,
            'status': self.status,
            'verified_by': self.verified_by,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'dispensed_by': self.dispensed_by,
            'dispensed_at': self.dispensed_at.isoformat() if self.dispensed_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
