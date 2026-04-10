"""
HIPAA Compliance Module for Diabetes Prediction System

This module provides HIPAA compliance features including:
- PHI (Protected Health Information) encryption
- Data anonymization for research
- Audit trail enhancements
- Consent management
- Data retention policies
"""

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import re
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class HIPAAComplianceManager:
    """Manages HIPAA compliance features"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        self.encryption_key = encryption_key or self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self.phi_fields = {
            'patient': ['full_name', 'email', 'phone', 'address', 'emergency_contact', 
                       'emergency_contact_name', 'medical_history', 'allergies', 'current_medications'],
            'health_record': ['notes', 'symptoms'],
            'prescription': ['medication_name', 'dosage_instructions', 'notes'],
            'lab_test': ['test_name', 'results', 'notes'],
            'appointment': ['reason', 'notes']
        }
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for PHI data"""
        key_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'phi_key.key')
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            logger.warning("New PHI encryption key generated - secure backup required")
            return key
    
    def encrypt_phi(self, data: str) -> str:
        """Encrypt PHI data"""
        if not data:
            return data
        try:
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt PHI: {e}")
            raise ValueError("Encryption failed")
    
    def decrypt_phi(self, encrypted_data: str) -> str:
        """Decrypt PHI data"""
        if not encrypted_data:
            return encrypted_data
        try:
            decoded_data = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt PHI: {e}")
            raise ValueError("Decryption failed")
    
    def anonymize_patient_data(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize patient data for research/analytics"""
        anonymized = patient_data.copy()
        
        # Replace direct identifiers
        if 'full_name' in anonymized:
            anonymized['full_name'] = f"PATIENT_{hashlib.sha256(anonymized['full_name'].encode()).hexdigest()[:8]}"
        
        if 'email' in anonymized:
            anonymized['email'] = f"patient_{hashlib.sha256(anonymized['email'].encode()).hexdigest()[:12]}@example.com"
        
        if 'phone' in anonymized:
            anonymized['phone'] = f"+1-XXX-XXX-{hashlib.sha256(anonymized['phone'].encode()).hexdigest()[:4]}"
        
        if 'patient_id' in anonymized:
            anonymized['patient_id'] = f"PID_{hashlib.sha256(anonymized['patient_id'].encode()).hexdigest()[:8]}"
        
        # Generalize dates
        for date_field in ['created_at', 'last_login', 'date_of_birth']:
            if date_field in anonymized and anonymized[date_field]:
                try:
                    date_obj = datetime.fromisoformat(anonymized[date_field].replace('Z', '+00:00'))
                    anonymized[date_field] = date_obj.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
                except:
                    pass
        
        # Remove free text fields that could contain PHI
        for field in ['medical_history', 'allergies', 'current_medications', 'emergency_contact_name']:
            if field in anonymized:
                anonymized[field] = "[REDACTED_FOR_PRIVACY]"
        
        return anonymized
    
    def create_consent_record(self, patient_id: int, consent_type: str, 
                            consent_text: str, expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """Create a patient consent record"""
        consent_id = f"CONSENT_{secrets.token_urlsafe(16)}"
        
        consent_record = {
            'consent_id': consent_id,
            'patient_id': patient_id,
            'consent_type': consent_type,  # 'treatment', 'research', 'data_sharing'
            'consent_text': consent_text,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': expires_at.isoformat() if expires_at else None,
            'ip_address': None,  # Will be set by caller
            'user_agent': None,  # Will be set by caller
            'digital_signature': self._generate_digital_signature(consent_id, patient_id)
        }
        
        return consent_record
    
    def _generate_digital_signature(self, consent_id: str, patient_id: int) -> str:
        """Generate digital signature for consent"""
        signature_data = f"{consent_id}:{patient_id}:{datetime.utcnow().isoformat()}"
        return hashlib.sha256(signature_data.encode()).hexdigest()
    
    def verify_consent_valid(self, consent_record: Dict[str, Any]) -> bool:
        """Verify if consent is still valid"""
        if consent_record['status'] != 'active':
            return False
        
        if consent_record['expires_at']:
            try:
                expiry_date = datetime.fromisoformat(consent_record['expires_at'].replace('Z', '+00:00'))
                if datetime.utcnow() > expiry_date:
                    return False
            except:
                return False
        
        return True
    
    def audit_phi_access(self, user_id: int, user_role: str, action: str, 
                        resource_type: str, resource_id: int, phi_fields_accessed: List[str]) -> Dict[str, Any]:
        """Create audit record for PHI access"""
        audit_record = {
            'audit_id': f"AUDIT_{secrets.token_urlsafe(16)}",
            'user_id': user_id,
            'user_role': user_role,
            'action': action,  # 'read', 'write', 'delete', 'share'
            'resource_type': resource_type,  # 'patient', 'health_record', etc.
            'resource_id': resource_id,
            'phi_fields_accessed': phi_fields_accessed,
            'timestamp': datetime.utcnow().isoformat(),
            'ip_address': None,  # Will be set by caller
            'user_agent': None,  # Will be set by caller
            'session_id': None,  # Will be set by caller
            'compliance_check': self._check_compliance_rules(user_role, action, phi_fields_accessed)
        }
        
        return audit_record
    
    def _check_compliance_rules(self, user_role: str, action: str, phi_fields: List[str]) -> Dict[str, Any]:
        """Check if access complies with HIPAA rules"""
        compliance_result = {
            'compliant': True,
            'violations': [],
            'warnings': []
        }
        
        # Role-based access checks
        role_permissions = {
            'patient': ['read', 'write'],
            'doctor': ['read', 'write', 'delete'],
            'nurse': ['read', 'write'],
            'lab_technician': ['read', 'write'],
            'pharmacist': ['read', 'write'],
            'admin': ['read', 'write', 'delete', 'share']
        }
        
        if action not in role_permissions.get(user_role, []):
            compliance_result['compliant'] = False
            compliance_result['violations'].append(f"Role {user_role} not authorized for {action} action")
        
        # Minimum necessary access principle
        if len(phi_fields) > 5:
            compliance_result['warnings'].append("Access to multiple PHI fields - verify minimum necessary principle")
        
        return compliance_result
    
    def implement_data_retention(self, data_type: str, record_date: datetime) -> bool:
        """Check if data should be retained based on retention policies"""
        retention_periods = {
            'patient_records': timedelta(days=365 * 7),  # 7 years
            'health_records': timedelta(days=365 * 7),   # 7 years
            'predictions': timedelta(days=365 * 5),      # 5 years
            'prescriptions': timedelta(days=365 * 7),   # 7 years
            'lab_results': timedelta(days=365 * 7),      # 7 years
            'audit_logs': timedelta(days=365 * 6),       # 6 years
            'consent_records': timedelta(days=365 * 7)  # 7 years
        }
        
        retention_period = retention_periods.get(data_type, timedelta(days=365 * 7))
        expiry_date = record_date + retention_period
        
        return datetime.utcnow() < expiry_date
    
    def mask_phi_for_display(self, data: Dict[str, Any], user_role: str) -> Dict[str, Any]:
        """Mask PHI data based on user role for display"""
        masked_data = data.copy()
        
        # Define what each role can see
        role_visibility = {
            'patient': ['full_name', 'email', 'phone', 'blood_group'],
            'doctor': ['full_name', 'email', 'phone', 'medical_history', 'allergies', 'current_medications'],
            'nurse': ['full_name', 'phone', 'blood_group', 'emergency_contact'],
            'lab_technician': ['patient_id', 'blood_group'],
            'pharmacist': ['patient_id', 'allergies'],
            'admin': ['full_name', 'email', 'phone', 'medical_history', 'allergies', 'current_medications']
        }
        
        visible_fields = role_visibility.get(user_role, [])
        
        for field in data:
            if field in self.phi_fields.get('patient', []) and field not in visible_fields:
                if field in ['email', 'phone']:
                    # Partial masking for contact info
                    value = str(data[field])
                    if len(value) > 4:
                        masked_data[field] = value[:2] + '*' * (len(value) - 4) + value[-2:]
                    else:
                        masked_data[field] = '*' * len(value)
                else:
                    masked_data[field] = '[RESTRICTED]'
        
        return masked_data

# Global instance
hipaa_manager = HIPAAComplianceManager()
