from functools import wraps
from flask import request, jsonify
from flask_login import current_user

def require_auth(f):
    """Require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ✅ ADD THIS FUNCTION
def token_required(f):
    """Require valid JWT token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token required'}), 401
        
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Here you would validate the token
        # For now, just check if token exists
        if not token:
            return jsonify({'error': 'Invalid token'}), 401
            
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    """Alias for require_auth"""
    return require_auth(f)

def optional_auth(f):
    """Optional authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function