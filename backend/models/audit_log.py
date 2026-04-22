from datetime import datetime
from backend.extensions import db

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    username = db.Column(db.String(80))
    user_role = db.Column(db.String(50))
    
    action = db.Column(db.String(50), nullable=False)  # login, logout, create, update, delete, view
    resource = db.Column(db.String(50))  # user, patient, prescription, etc.
    resource_id = db.Column(db.Integer)
    
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(200))
    
    status = db.Column(db.String(50))  # success, failed
    error_message = db.Column(db.Text)
    
    old_value = db.Column(db.Text)  
    new_value = db.Column(db.Text) 
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'user_role': self.user_role,
            'action': self.action,
            'resource': self.resource,
            'resource_id': self.resource_id,
            'description': self.description,
            'ip_address': self.ip_address,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat()
        }
    
    @staticmethod
    def log_action(user_id, username, user_role, action, resource, resource_id=None, 
                   description=None, ip_address=None, status='success', error_message=None):
        """Helper method to create audit log entries"""
        log = AuditLog(
            user_id=user_id,
            username=username,
            user_role=user_role,
            action=action,
            resource=resource,
            resource_id=resource_id,
            description=description,
            ip_address=ip_address,
            status=status,
            error_message=error_message
        )
        db.session.add(log)
        db.session.commit()
        return log