"""
Appointment Model - Represents patient appointments with doctors
"""

from backend.extensions import db
from datetime import datetime

class Appointment(db.Model):
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.String(50), unique=True, nullable=True)
    
    # Relationships
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    
    # Appointment details
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.String(10), nullable=True)  # e.g., "10:30 AM"
    duration = db.Column(db.Integer, default=30)  # minutes
    
    # Type and reason
    type = db.Column(db.String(50), default='consultation')  # consultation, follow-up, checkup, etc.
    reason = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    # Status
    status = db.Column(db.String(50), default='scheduled')  # scheduled, completed, cancelled, no-show
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional: link to prescription or lab test
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=True)
    lab_test_id = db.Column(db.Integer, db.ForeignKey('lab_tests.id'), nullable=True)
    
    def __repr__(self):
        return f'<Appointment {self.id}: Patient {self.patient_id} with Doctor {self.doctor_id}>'
    
    def to_dict(self):
        """Convert appointment to dictionary"""
        return {
            'id': self.id,
            'appointment_id': self.appointment_id or f'APT{self.id:04d}',
            'patient_id': self.patient_id,
            'doctor_id': self.doctor_id,
            'appointment_date': self.appointment_date.isoformat() if self.appointment_date else None,
            'appointment_time': self.appointment_time,
            'duration': self.duration,
            'type': self.type,
            'reason': self.reason,
            'notes': self.notes,
            'status': self.status,
            'prescription_id': self.prescription_id,
            'lab_test_id': self.lab_test_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }