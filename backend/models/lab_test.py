from datetime import datetime
from backend.extensions import db

class LabTest(db.Model):
    __tablename__ = 'lab_tests'
    
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.String(20), unique=True, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctors.id'))
    technician_id = db.Column(db.Integer, db.ForeignKey('lab_technicians.id'))
    
    test_name = db.Column(db.String(100), nullable=False)
    test_type = db.Column(db.String(50))  # Blood, Urine, etc.
    test_category = db.Column(db.String(50))  # Hematology, Biochemistry, etc.
    
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, cancelled
    priority = db.Column(db.String(20), default='normal')  # urgent, high, normal, low
    
    sample_collected_at = db.Column(db.DateTime)
    test_started_at = db.Column(db.DateTime)
    test_completed_at = db.Column(db.DateTime)
    
    results = db.Column(db.Text)  # JSON string with test results
    normal_range = db.Column(db.String(100))
    unit = db.Column(db.String(20))
    remarks = db.Column(db.Text)
    
    cost = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'test_id': self.test_id,
            'patient_id': self.patient_id,
            'doctor_id': self.doctor_id,
            'technician_id': self.technician_id,
            'test_name': self.test_name,
            'test_type': self.test_type,
            'test_category': self.test_category,
            'status': self.status,
            'priority': self.priority,
            'results': self.results,
            'normal_range': self.normal_range,
            'unit': self.unit,
            'remarks': self.remarks,
            'cost': self.cost,
            'sample_collected_at': self.sample_collected_at.isoformat() if self.sample_collected_at else None,
            'test_completed_at': self.test_completed_at.isoformat() if self.test_completed_at else None,
            'created_at': self.created_at.isoformat()
        }
