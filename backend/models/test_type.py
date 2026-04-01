from datetime import datetime
from backend.extensions import db

class TestType(db.Model):
    __tablename__ = 'test_types'

    id = db.Column(db.Integer, primary_key=True)
    test_name = db.Column(db.String(100), nullable=False)
    test_code = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    cost = db.Column(db.Float, default=0.0)
    normal_range = db.Column(db.String(100))
    preparation_instructions = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('lab_technicians.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'test_name': self.test_name,
            'test_code': self.test_code,
            'category': self.category,
            'cost': self.cost,
            'normal_range': self.normal_range,
            'preparation_instructions': self.preparation_instructions,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
