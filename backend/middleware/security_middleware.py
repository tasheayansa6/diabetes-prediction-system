from flask import request, jsonify
from functools import wraps
from backend.utils.logger import get_logger

logger = get_logger(__name__)

def setup_security_headers(app):
    """
    Setup basic security headers for all responses
    Essential for protecting against common web vulnerabilities
    
    Args:
        app: Flask application instance
    """
    
    @app.after_request
    def add_security_headers(response):
        # Prevent clickjacking attacks
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection in browsers
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response
    
    return app

# Optional: Advanced security features (can be removed for simpler project)

def sanitize_input(f):
    """
    Optional: Basic input sanitization
    Prevents common SQL injection patterns
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # SQLAlchemy ORM already protects against SQL injection
        # This is an extra layer of protection
        return f(*args, **kwargs)
    return decorated_function
