from backend.extensions import db
from backend.models.user import User

class Patient(User):
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    patient_id = db.Column(db.String(50), unique=True)
    gender = db.Column(db.String(10), nullable=True)  # 'male' | 'female' | 'other'
    blood_group = db.Column(db.String(5))
    emergency_contact = db.Column(db.String(50))
    emergency_contact_name = db.Column(db.String(120))
    medical_history = db.Column(db.Text)
    allergies = db.Column(db.Text)
    current_medications = db.Column(db.Text)
    registered_by = db.Column(db.Integer, db.ForeignKey('nurses.id'), nullable=True)
    # Consent & GDPR/HIPAA compliance
    consent_given = db.Column(db.Boolean, default=False, nullable=False)
    consent_given_at = db.Column(db.DateTime, nullable=True)
    data_deletion_requested = db.Column(db.Boolean, default=False, nullable=False)
    data_deletion_requested_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    health_records = db.relationship(
        'HealthRecord',
        backref='patient',
        lazy=True,
        foreign_keys='HealthRecord.patient_id',
        cascade='all, delete-orphan'
    )

    predictions = db.relationship(
        'Prediction',  # ← CHANGED from 'PredictionResult' to 'Prediction'
        backref='patient',
        lazy=True,
        foreign_keys='Prediction.patient_id',  # ← CHANGED
        cascade='all, delete-orphan'
    )

    prescriptions = db.relationship(
        'Prescription',
        backref='patient',
        lazy=True,
        foreign_keys='Prescription.patient_id',
        cascade='all, delete-orphan'
    )

    lab_tests = db.relationship(
        'LabTest',
        backref='patient',
        lazy=True,
        foreign_keys='LabTest.patient_id',
        cascade='all, delete-orphan'
    )

    payments = db.relationship(
        'Payment',
        backref='patient',
        lazy=True,
        foreign_keys='Payment.patient_id',
        cascade='all, delete-orphan'
    )

    __mapper_args__ = {
        'polymorphic_identity': 'patient',
    }

    def to_dict(self):
        data = super().to_dict()
        data.update({
            'patient_id': self.patient_id,
            'blood_group': self.blood_group,
            'emergency_contact': self.emergency_contact,
            'emergency_contact_name': self.emergency_contact_name,
            'medical_history': self.medical_history,
            'allergies': self.allergies,
            'current_medications': self.current_medications
        })
        return data
