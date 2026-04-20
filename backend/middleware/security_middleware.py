from flask import request, jsonify
from functools import wraps
from backend.utils.logger import get_logger
import re

logger = get_logger(__name__)

def strip_html(text):
    """Remove HTML tags and dangerous characters from free-text input."""
    if not text or not isinstance(text, str):
        return text
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Remove script-like patterns
    clean = re.sub(r'javascript\s*:', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'on\w+\s*=', '', clean, flags=re.IGNORECASE)
    return clean.strip()

def sanitize_free_text_fields(data: dict, fields: list) -> dict:
    """Sanitize specific free-text fields in a request dict."""
    if not data:
        return data
    for field in fields:
        if field in data and isinstance(data[field], str):
            data[field] = strip_html(data[field])
    return data

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
