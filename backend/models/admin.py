from backend.extensions import db
from backend.models.user import User

class Admin(User):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    admin_id = db.Column(db.String(50), unique=True)
    department = db.Column(db.String(100))
    access_level = db.Column(db.Integer, default=1)  # 1=basic, 2=moderate, 3=full
    can_delete_users = db.Column(db.Boolean, default=False)
    can_modify_system = db.Column(db.Boolean, default=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'admin',
    }
    
    def to_dict(self):
        data = super().to_dict()
        data.update({
            'admin_id': self.admin_id,
            'department': self.department,
            'access_level': self.access_level,
            'can_delete_users': self.can_delete_users,
            'can_modify_system': self.can_modify_system
        })
        return data
