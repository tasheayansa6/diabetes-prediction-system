from datetime import datetime
from backend.extensions import db

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.String(50), unique=True, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    
    payment_type = db.Column(db.String(50), nullable=False)  # consultation, lab_test, prescription, etc.
    reference_id = db.Column(db.Integer)  # ID of related record (prescription_id, lab_test_id, etc.)
    reference_type = db.Column(db.String(50))  # prescription, lab_test, etc.
    
    amount = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, nullable=False)
    
    payment_method = db.Column(db.String(50))  # cash, card, insurance, online
    payment_status = db.Column(db.String(50), default='pending')  # pending, completed, failed, refunded
    
    transaction_id = db.Column(db.String(100))
    payment_date = db.Column(db.DateTime)
    
    insurance_company = db.Column(db.String(100))
    insurance_claim_number = db.Column(db.String(50))
    insurance_amount = db.Column(db.Float, default=0)
    
    notes = db.Column(db.Text)
    # Tracks whether a prediction payment has been used to run ML
    prediction_consumed = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'patient_id': self.patient_id,
            'payment_type': self.payment_type,
            'reference_id': self.reference_id,
            'reference_type': self.reference_type,
            'amount': self.amount,
            'tax': self.tax,
            'discount': self.discount,
            'total_amount': self.total_amount,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'transaction_id': self.transaction_id,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'insurance_company': self.insurance_company,
            'insurance_claim_number': self.insurance_claim_number,
            'insurance_amount': self.insurance_amount,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }
