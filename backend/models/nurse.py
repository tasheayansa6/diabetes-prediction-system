from backend.extensions import db
from backend.models.user import User

class Nurse(User):
    __tablename__ = 'nurses'
    
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    nurse_id = db.Column(db.String(50), unique=True)
    qualification = db.Column(db.String(200))
    license_number = db.Column(db.String(50), unique=True)
    department = db.Column(db.String(100))
    shift = db.Column(db.String(50))  # morning, evening, night
    years_of_experience = db.Column(db.Integer)
    
    __mapper_args__ = {
        'polymorphic_identity': 'nurse',
    }
    
    def to_dict(self):
        data = super().to_dict()
        data.update({
            'nurse_id': self.nurse_id,
            'qualification': self.qualification,
            'license_number': self.license_number,
            'department': self.department,
            'shift': self.shift,
            'years_of_experience': self.years_of_experience
        })
        return data
