from backend.extensions import db
from backend.models.user import User

class Pharmacist(User):
    __tablename__ = 'pharmacists'
    
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    pharmacist_id = db.Column(db.String(50), unique=True)
    qualification = db.Column(db.String(200))
    license_number = db.Column(db.String(50), unique=True)
    shift = db.Column(db.String(50))  # morning, evening, night
    
    __mapper_args__ = {
        'polymorphic_identity': 'pharmacist',
    }
    
    def to_dict(self):
        data = super().to_dict()
        data.update({
            'pharmacist_id': self.pharmacist_id,
            'qualification': self.qualification,
            'license_number': self.license_number,
            'shift': self.shift
        })
        return data
