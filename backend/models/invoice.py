"""
Invoice Model - Handles invoice generation
"""
from backend.extensions import db
from datetime import datetime

class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.String(20), unique=True, nullable=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    
    amount = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, nullable=False)
    
    status = db.Column(db.String(20), default='pending')  # pending, paid, overdue, cancelled
    due_date = db.Column(db.Date)
    paid_at = db.Column(db.DateTime)
    
    # Invoice items stored as JSON
    items = db.Column(db.JSON)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        if 'invoice_id' not in kwargs or not kwargs['invoice_id']:
            import uuid
            kwargs['invoice_id'] = f"INV{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        super(Invoice, self).__init__(**kwargs)
    
    def to_dict(self):
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "payment_id": self.payment_id,
            "patient_id": self.patient_id,
            "amount": self.amount,
            "tax": self.tax,
            "discount": self.discount,
            "total_amount": self.total_amount,
            "status": self.status,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }