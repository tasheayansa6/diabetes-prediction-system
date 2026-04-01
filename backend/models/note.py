"""
Note Model - Represents clinical notes added by doctors about patients
"""

from backend.extensions import db
from datetime import datetime

class Note(db.Model):
    __tablename__ = 'notes'
    
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.String(20), unique=True, nullable=True)
    
    # Relationships
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    
    # Note content
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')  # general, follow-up, prescription, lab, etc.
    
    # Metadata
    is_private = db.Column(db.Boolean, default=False)  # True for doctor's private notes
    is_important = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional: link to related records
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=True)
    lab_test_id = db.Column(db.Integer, db.ForeignKey('lab_tests.id'), nullable=True)
    
    def __repr__(self):
        return f'<Note {self.id}: {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'note_id': self.note_id or f'NOTE{self.id:04d}',
            'patient_id': self.patient_id,
            'doctor_id': self.doctor_id,
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'is_private': self.is_private,
            'is_important': self.is_important,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'appointment_id': self.appointment_id,
            'prescription_id': self.prescription_id,
            'lab_test_id': self.lab_test_id
        }