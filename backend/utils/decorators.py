"""
Shared decorators for all route blueprints.
Single source of truth — no duplication across route files.
"""
from functools import wraps
from flask import request, jsonify, current_app
from flask_login import current_user
import jwt


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            if current_user.role not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def _is_token_blacklisted(token):
    """Check if token is blacklisted (logged out) via AuditLog."""
    try:
        from backend.models.audit_log import AuditLog
        return AuditLog.query.filter_by(
            action='token_blacklist',
            description=token[:100]
        ).first() is not None
    except Exception:
        return False


def token_required(allowed_roles=None):
    """
    JWT token decorator.

    Usage:
        @token_required()                          # any authenticated role
        @token_required(['patient'])               # patient only
        @token_required(['patient', 'admin'])      # patient or admin

    The decorated function receives `current_user` as its first argument:
        {'id', 'username', 'email', 'role'}
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get('Authorization', '')
            if not auth_header:
                return jsonify({"success": False, "message": "Token is missing!"}), 401

            token = auth_header[7:] if auth_header.startswith('Bearer ') else auth_header

            try:
                if _is_token_blacklisted(token):
                    return jsonify({"success": False,
                                    "message": "Token has been invalidated. Please login again."}), 401

                data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])

                if allowed_roles and data.get('role') not in allowed_roles:
                    return jsonify({"success": False, "message": "Access denied."}), 403

                from backend.models.user import User
                user = User.query.get(data.get('user_id'))
                if not user:
                    return jsonify({"success": False, "message": "User not found!"}), 401

                current_user_dict = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                }
            except jwt.ExpiredSignatureError:
                return jsonify({"success": False, "message": "Token has expired!"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"success": False, "message": "Invalid token!"}), 401

            return f(current_user_dict, *args, **kwargs)
        return decorated
    return decorator
