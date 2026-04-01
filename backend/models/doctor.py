from backend.extensions import db
from backend.models.user import User

class Doctor(User):
    __tablename__ = 'doctors'
    
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    doctor_id = db.Column(db.String(20), unique=True)
    specialization = db.Column(db.String(100))
    qualification = db.Column(db.String(200))
    license_number = db.Column(db.String(50), unique=True)
    years_of_experience = db.Column(db.Integer)
    consultation_fee = db.Column(db.Float)
    available_days = db.Column(db.String(100))  # JSON string or comma-separated
    available_hours = db.Column(db.String(50))
    
    # Relationships
    prescriptions = db.relationship('Prescription', backref='doctor', lazy=True,
                                   foreign_keys='Prescription.doctor_id')
    lab_tests_ordered = db.relationship('LabTest', backref='doctor', lazy=True,
                                       foreign_keys='LabTest.doctor_id')
    
    __mapper_args__ = {
        'polymorphic_identity': 'doctor',
    }
    
    def to_dict(self):
        data = super().to_dict()
        data.update({
            'doctor_id': self.doctor_id,
            'specialization': self.specialization,
            'qualification': self.qualification,
            'license_number': self.license_number,
            'years_of_experience': self.years_of_experience,
            'consultation_fee': self.consultation_fee,
            'available_days': self.available_days,
            'available_hours': self.available_hours
        })
        return data
