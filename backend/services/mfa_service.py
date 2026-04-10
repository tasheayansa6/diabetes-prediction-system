"""
Multi-Factor Authentication (MFA) Service

Provides Time-based One-Time Password (TOTP) and SMS-based MFA
for enhanced security in healthcare applications.
"""

import os
import pyotp
import qrcode
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
from flask import current_app
import base64
from io import BytesIO

logger = logging.getLogger(__name__)

class MFAService:
    """Multi-Factor Authentication Service"""
    
    def __init__(self):
        self.totp_issuer = "Diabetes Prediction System"
        self.backup_codes_count = 10
        
    def generate_totp_secret(self, user_id: int) -> str:
        """Generate a new TOTP secret for a user"""
        return pyotp.random_base32()
    
    def generate_qr_code(self, user_email: str, secret: str) -> str:
        """Generate QR code for TOTP setup"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user_email,
            issuer_name=self.totp_issuer
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_totp_token(self, secret: str, token: str, window: int = 1) -> bool:
        """Verify TOTP token"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=window)
        except Exception as e:
            logger.error(f"TOTP verification failed: {e}")
            return False
    
    def generate_backup_codes(self, count: int = None) -> List[str]:
        """Generate backup codes for MFA"""
        if count is None:
            count = self.backup_codes_count
        
        codes = []
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            codes.append(code)
        
        return codes
    
    def verify_backup_codes(self, stored_codes: List[str], provided_code: str) -> Tuple[bool, List[str]]:
        """Verify and consume backup code"""
        return self.verify_backup_code(stored_codes, provided_code)

    def verify_backup_code(self, stored_codes: List[str], provided_code: str) -> Tuple[bool, List[str]]:
        """Verify and consume backup code"""
        normalized_provided = provided_code.replace('-', '').replace(' ', '').upper()
        
        for i, code in enumerate(stored_codes):
            normalized_code = code.replace('-', '').replace(' ', '').upper()
            if normalized_code == normalized_provided:
                # Remove used code
                remaining_codes = stored_codes[:i] + stored_codes[i+1:]
                return True, remaining_codes
        
        return False, stored_codes
    
    def generate_sms_code(self, length: int = 6) -> str:
        """Generate SMS verification code"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    
    def hash_sms_code(self, code: str, user_id: int) -> str:
        """Hash SMS code for storage"""
        salt = f"salt_{user_id}"
        return hashlib.sha256((code + salt).encode()).hexdigest()
    
    def verify_sms_code(self, stored_hash: str, provided_code: str, user_id: int) -> bool:
        """Verify SMS code"""
        salt = f"salt_{user_id}"
        computed_hash = hashlib.sha256((provided_code + salt).encode()).hexdigest()
        return secrets.compare_digest(stored_hash, computed_hash)
    
    def create_mfa_session(self, user_id: int, method: str) -> Dict[str, Any]:
        """Create MFA verification session"""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'method': method,  # 'totp', 'sms', 'backup'
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': expires_at.isoformat(),
            'attempts': 0,
            'max_attempts': 3
        }
        
        return session_data
    
    def is_mfa_session_valid(self, session_data: Dict[str, Any]) -> bool:
        """Check if MFA session is still valid"""
        if session_data['attempts'] >= session_data['max_attempts']:
            return False
        
        try:
            expires_at = datetime.fromisoformat(session_data['expires_at'].replace('Z', '+00:00'))
            return datetime.utcnow() < expires_at
        except:
            return False
    
    def increment_mfa_attempts(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Increment MFA attempt counter"""
        session_data['attempts'] += 1
        return session_data
    
    def get_mfa_status(self, user_mfa_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Get user's MFA status"""
        status = {
            'enabled': False,
            'methods': [],
            'primary_method': None,
            'setup_required': []
        }
        
        if user_mfa_settings.get('totp_enabled'):
            status['enabled'] = True
            status['methods'].append('totp')
        
        if user_mfa_settings.get('sms_enabled'):
            status['enabled'] = True
            status['methods'].append('sms')
        
        if user_mfa_settings.get('backup_codes'):
            status['enabled'] = True
            status['methods'].append('backup')
        
        status['primary_method'] = user_mfa_settings.get('primary_method', 'totp')
        
        # Check setup requirements
        if not user_mfa_settings.get('totp_enabled'):
            status['setup_required'].append('totp')
        
        if not user_mfa_settings.get('backup_codes'):
            status['setup_required'].append('backup_codes')
        
        return status
    
    def enforce_mfa_for_role(self, user_role: str) -> bool:
        """Check if MFA is required for user role"""
        mfa_required_roles = ['doctor', 'nurse', 'lab_technician', 'pharmacist', 'admin']
        return user_role in mfa_required_roles
    
    def get_mfa_method_priority(self) -> List[str]:
        """Get MFA method priority order"""
        return ['totp', 'sms', 'backup']

# Global instance
mfa_service = MFAService()
