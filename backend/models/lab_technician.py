from backend.extensions import db
from backend.models.user import User

class LabTechnician(User):
    __tablename__ = 'lab_technicians'
    
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    technician_id = db.Column(db.String(50), unique=True)
    qualification = db.Column(db.String(200))
    license_number = db.Column(db.String(50), unique=True)
    specialization = db.Column(db.String(100))  
    
    
    # Relationships
    lab_tests_processed = db.relationship('LabTest', backref='technician', lazy=True,
                                         foreign_keys='LabTest.technician_id')
    
    __mapper_args__ = {
        'polymorphic_identity': 'lab_technician',
    }
    
    def to_dict(self):
        data = super().to_dict()
        data.update({
            'technician_id': self.technician_id,
            'qualification': self.qualification,
            'license_number': self.license_number,
            'specialization': self.specialization,
           
        })
        return data
