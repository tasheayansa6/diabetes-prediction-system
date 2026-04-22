"""
Subscription Model - Handles patient subscriptions
"""
from backend.extensions import db
from datetime import datetime

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.String(50), unique=True, nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    
    plan = db.Column(db.String(50))  # basic, premium, enterprise
    billing_cycle = db.Column(db.String(50))  # monthly, yearly, weekly
    amount = db.Column(db.Float)
    
    status = db.Column(db.String(50), default='active')  # active, cancelled, expired
    
    start_date = db.Column(db.DateTime)
    next_billing_date = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    payment_method = db.Column(db.String(50))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        if 'subscription_id' not in kwargs or not kwargs['subscription_id']:
            import uuid
            kwargs['subscription_id'] = f"SUB{datetime.utcnow().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        super(Subscription, self).__init__(**kwargs)
    
    def to_dict(self):
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "patient_id": self.patient_id,
            "plan": self.plan,
            "billing_cycle": self.billing_cycle,
            "amount": self.amount,
            "status": self.status,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "next_billing_date": self.next_billing_date.isoformat() if self.next_billing_date else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }