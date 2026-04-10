"""
Enhanced Security Middleware for HIPAA Compliance

Provides database encryption, security headers, and audit logging
for healthcare data protection.
"""

import os
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from flask import Flask, request, g, jsonify
from functools import wraps
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import time
import json

logger = logging.getLogger(__name__)

class DatabaseEncryption:
    """Database-level encryption for sensitive fields"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        self.encryption_key = encryption_key or self._get_or_create_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self.encrypted_fields = [
            'medical_history', 'allergies', 'current_medications',
            'emergency_contact', 'emergency_contact_name', 'notes'
        ]
    
    def _get_or_create_key(self) -> bytes:
        """Get or create database encryption key"""
        key_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'db_encryption.key')
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate key from master password
            password = os.getenv('DB_ENCRYPTION_PASSWORD', 'default-change-me').encode()
            salt = b'diabetes_system_salt_2024'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            
            with open(key_file, 'wb') as f:
                f.write(key)
            
            logger.warning("Database encryption key generated - secure backup required")
            return key
    
    def encrypt_field(self, value: str) -> str:
        """Encrypt a database field"""
        if not value:
            return value
        try:
            encrypted = self.cipher_suite.encrypt(value.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Field encryption failed: {e}")
            raise ValueError("Encryption failed")
    
    def decrypt_field(self, encrypted_value: str) -> str:
        """Decrypt a database field"""
        if not encrypted_value:
            return encrypted_value
        try:
            decoded = base64.b64decode(encrypted_value.encode())
            decrypted = self.cipher_suite.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Field decryption failed: {e}")
            raise ValueError("Decryption failed")

class SecurityAuditLogger:
    """Enhanced security audit logging"""
    
    def __init__(self):
        self.security_log_file = os.path.join(
            os.path.dirname(__file__), '..', '..', 'logs', 'security.log'
        )
        self.ensure_log_directory()
    
    def ensure_log_directory(self):
        """Ensure log directory exists"""
        os.makedirs(os.path.dirname(self.security_log_file), exist_ok=True)
    
    def log_security_event(self, event_type: str, user_id: Optional[int] = None, 
                          details: Dict[str, Any] = None, severity: str = 'INFO'):
        """Log security event"""
        timestamp = datetime.utcnow().isoformat()
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        user_agent = request.headers.get('User-Agent', 'unknown')
        
        log_entry = {
            'timestamp': timestamp,
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'severity': severity,
            'details': details or {}
        }
        
        try:
            with open(self.security_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write security log: {e}")
    
    def detect_suspicious_activity(self, user_id: int, action: str) -> Dict[str, Any]:
        """Detect suspicious login/activity patterns"""
        # Check for rapid successive logins
        recent_logins = self._get_recent_logins(user_id, minutes=5)
        
        if len(recent_logins) > 3:
            return {
                'suspicious': True,
                'reason': 'Multiple login attempts in short time',
                'confidence': 0.8,
                'action': 'require_mfa'
            }
        
        # Check for unusual location
        current_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        usual_ips = self._get_user_usual_ips(user_id)
        
        if current_ip not in usual_ips and len(usual_ips) > 0:
            return {
                'suspicious': True,
                'reason': 'Login from unusual IP address',
                'confidence': 0.6,
                'action': 'notify_user'
            }
        
        return {'suspicious': False}
    
    def _get_recent_logins(self, user_id: int, minutes: int = 5) -> List[Dict[str, Any]]:
        """Get recent login attempts for user"""
        # This would typically query a database
        # For now, return empty list
        return []
    
    def _get_user_usual_ips(self, user_id: int) -> List[str]:
        """Get user's usual IP addresses"""
        # This would typically query a database
        # For now, return empty list
        return []

class RateLimiter:
    """Rate limiting for API endpoints"""
    
    def __init__(self):
        self.requests = {}  # In production, use Redis
        self.window_size = 900  # 15 minutes
        self.max_requests = {
            'login': 5,
            'register': 3,
            'password_reset': 3,
            'mfa': 10,
            'default': 100
        }
    
    def is_allowed(self, key: str, endpoint_type: str = 'default') -> Dict[str, Any]:
        """Check if request is allowed"""
        now = int(time.time())
        window_start = now - self.window_size
        
        # Clean old entries
        if key in self.requests:
            self.requests[key] = [req_time for req_time in self.requests[key] if req_time > window_start]
        else:
            self.requests[key] = []
        
        # Check current count
        max_requests = self.max_requests.get(endpoint_type, self.max_requests['default'])
        
        if len(self.requests[key]) >= max_requests:
            return {
                'allowed': False,
                'remaining': 0,
                'reset_time': window_start + self.window_size
            }
        
        # Add current request
        self.requests[key].append(now)
        
        return {
            'allowed': True,
            'remaining': max_requests - len(self.requests[key]),
            'reset_time': window_start + self.window_size
        }

# Global instances
db_encryption = DatabaseEncryption()
security_audit = SecurityAuditLogger()
rate_limiter = RateLimiter()

def rate_limit(endpoint_type: str = 'default'):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Create rate limit key
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
            key = f"{ip_address}:{request.endpoint}"
            
            # Check rate limit
            result = rate_limiter.is_allowed(key, endpoint_type)
            
            if not result['allowed']:
                security_audit.log_security_event(
                    'rate_limit_exceeded',
                    details={'endpoint': request.endpoint, 'ip': ip_address},
                    severity='WARNING'
                )
                return jsonify({
                    'success': False,
                    'message': 'Too many requests. Please try again later.',
                    'retry_after': result['reset_time'] - int(time.time())
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_mfa(f):
    """Decorator to require MFA verification"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user has MFA enabled
        if hasattr(g, 'current_user') and g.current_user:
            from backend.services.mfa_service import mfa_service
            
            if mfa_service.enforce_mfa_for_role(g.current_user.role):
                # Check if MFA is verified in session
                if not session.get('mfa_verified'):
                    return jsonify({
                        'success': False,
                        'message': 'MFA verification required',
                        'require_mfa': True
                    }), 403
        
        return f(*args, **kwargs)
    return decorated_function

def log_phi_access(resource_type: str, phi_fields: List[str]):
    """Decorator to log PHI access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Execute the function first
            result = f(*args, **kwargs)
            
            # Log PHI access if user is authenticated
            if hasattr(g, 'current_user') and g.current_user:
                from backend.services.hipaa_compliance import hipaa_manager
                
                audit_record = hipaa_manager.audit_phi_access(
                    user_id=g.current_user.id,
                    user_role=g.current_user.role,
                    action='read',
                    resource_type=resource_type,
                    resource_id=kwargs.get('id', 0),
                    phi_fields_accessed=phi_fields
                )
                
                security_audit.log_security_event(
                    'phi_access',
                    user_id=g.current_user.id,
                    details=audit_record,
                    severity='INFO'
                )
            
            return result
        return decorated_function
    return decorator

def setup_enhanced_security_headers(app: Flask):
    """Setup enhanced security headers"""
    @app.after_request
    def add_security_headers(response):
        # Basic security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # HIPAA-specific headers
        response.headers['X-HIPAA-Compliant'] = 'true'
        response.headers['X-Data-Protection'] = 'encrypted-in-transit'
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers['Content-Security-Policy'] = csp
        
        return response
