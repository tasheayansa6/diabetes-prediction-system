

from backend.extensions import db
from datetime import datetime

class PatientQueue(db.Model):
    __tablename__ = 'patient_queue'
    
    id = db.Column(db.Integer, primary_key=True)
    queue_id = db.Column(db.String(50), unique=True)
    
    # Foreign Keys
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    nurse_id = db.Column(db.Integer, db.ForeignKey('nurses.id'), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=True)
    
    # Queue Info
    queue_number = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.Integer, default=0)  # 0=normal, 1=urgent, 2=emergency
    status = db.Column(db.String(50), default='waiting')  # waiting, called, in-progress, completed, cancelled
    purpose = db.Column(db.String(100))  # checkup, medication, lab, consultation
    
    # Timestamps
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)
    called_time = db.Column(db.DateTime, nullable=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    
    # Additional Info
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'queue_id': self.queue_id,
            'patient_id': self.patient_id,
            'nurse_id': self.nurse_id,
            'doctor_id': self.doctor_id,
            'queue_number': self.queue_number,
            'priority': self.priority,
            'status': self.status,
            'purpose': self.purpose,
            'check_in_time': self.check_in_time.isoformat() if self.check_in_time else None,
            'called_time': self.called_time.isoformat() if self.called_time else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<PatientQueue {self.queue_number}: {self.status}>'
