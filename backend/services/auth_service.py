

import jwt
import bcrypt
import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
import os
import json


class AuthService:
   
    
    def __init__(self, db_session=None, secret_key=None, token_expiry_hours=24):
       
        self.db_session = db_session
        self.secret_key = secret_key or os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
        self.token_expiry_hours = token_expiry_hours
        self.users = []  
        self.valid_roles = ['patient', 'doctor', 'nurse', 'lab_technician', 'pharmacist', 'admin']
        
        # Role-based permissions
        self.role_permissions = {
            'patient': ['view_own_data', 'request_prediction', 'view_results', 'make_payment'],
            'doctor': ['view_patients', 'perform_diagnosis', 'interpret_prediction', 'prescribe_medication'],
            'nurse': ['view_patients', 'record_vitals', 'enter_measurements'],
            'lab_technician': ['view_lab_requests', 'enter_results', 'validate_results'],
            'pharmacist': ['view_prescriptions', 'check_medication', 'approve_medication'],
            'admin': ['manage_users', 'manage_models', 'view_logs', 'system_config']
        }
    
    def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
       
        try:
            # Validate required fields
            required_fields = ['email', 'password', 'full_name', 'role']
            for field in required_fields:
                if field not in user_data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            # Validate email format
            if not self._validate_email(user_data['email']):
                return {
                    'success': False,
                    'error': 'Invalid email format'
                }
            
            # Validate password strength
            password_validation = self._validate_password_strength(user_data['password'])
            if not password_validation['valid']:
                return {
                    'success': False,
                    'error': password_validation['message']
                }
            
            # Validate role
            if user_data['role'].lower() not in self.valid_roles:
                return {
                    'success': False,
                    'error': f'Invalid role. Must be one of: {", ".join(self.valid_roles)}'
                }
            
            # Check if email already exists
            if self._get_user_by_email(user_data['email']):
                return {
                    'success': False,
                    'error': 'Email already registered'
                }
            
            # Hash password
            hashed_password = self._hash_password(user_data['password'])
            
            # Create user object
            user = {
                'user_id': str(uuid.uuid4()),
                'email': user_data['email'].lower(),
                'password_hash': hashed_password,
                'full_name': user_data['full_name'],
                'role': user_data['role'].lower(),
                'phone': user_data.get('phone', ''),
                'date_of_birth': user_data.get('date_of_birth'),
                'address': user_data.get('address', ''),
                'is_active': True,
                'email_verified': False,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'last_login': None,
                'login_attempts': 0,
                'profile_completed': False
            }
            
            # Add role-specific fields
            if user['role'] == 'patient':
                user['emergency_contact'] = user_data.get('emergency_contact', '')
                user['blood_group'] = user_data.get('blood_group', '')
                user['medical_history'] = user_data.get('medical_history', [])
            elif user['role'] == 'doctor':
                user['specialization'] = user_data.get('specialization', 'General')
                user['license_number'] = user_data.get('license_number', '')
                user['experience_years'] = user_data.get('experience_years', 0)
            elif user['role'] == 'nurse':
                user['license_number'] = user_data.get('license_number', '')
                user['department'] = user_data.get('department', '')
            elif user['role'] == 'lab_technician':
                user['certification'] = user_data.get('certification', '')
                user['lab_id'] = user_data.get('lab_id', '')
            elif user['role'] == 'pharmacist':
                user['license_number'] = user_data.get('license_number', '')
                user['pharmacy_id'] = user_data.get('pharmacy_id', '')
            
            # Store user (in production, save to database)
            self.users.append(user)
            
            # Generate email verification token
            verification_token = self._generate_verification_token(user['user_id'])
            
            # In production, send verification email here
            print(f"📧 Verification email would be sent to {user['email']} with token: {verification_token}")
            
            # Remove sensitive data before returning
            user_response = {k: v for k, v in user.items() if k != 'password_hash'}
            
            return {
                'success': True,
                'message': 'User registered successfully',
                'user': user_response,
                'requires_verification': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Registration failed: {str(e)}'
            }
    
    def login(self, email: str, password: str, ip_address: str = None) -> Dict[str, Any]:
        """
        Authenticate user and generate JWT token
        
        Args:
            email: User email
            password: User password
            ip_address: Optional IP address for logging
        
        Returns:
            Dictionary with login result and JWT token
        """
        try:
            # Find user by email
            user = self._get_user_by_email(email)
            
            if not user:
                return {
                    'success': False,
                    'error': 'Invalid email or password'
                }
            
            # Check if user is active
            if not user.get('is_active', True):
                return {
                    'success': False,
                    'error': 'Account is deactivated. Contact administrator.'
                }
            
            # Check if email is verified (optional - can be disabled for testing)
            if not user.get('email_verified', False) and os.environ.get('REQUIRE_EMAIL_VERIFICATION', 'false').lower() == 'true':
                return {
                    'success': False,
                    'error': 'Email not verified. Please verify your email first.',
                    'requires_verification': True
                }
            
            # Verify password
            if not self._verify_password(password, user['password_hash']):
                # Increment login attempts
                user['login_attempts'] = user.get('login_attempts', 0) + 1
                
                # Check for too many attempts
                if user['login_attempts'] >= 5:
                    user['is_active'] = False
                    return {
                        'success': False,
                        'error': 'Account locked due to too many failed attempts. Contact administrator.'
                    }
                
                return {
                    'success': False,
                    'error': f'Invalid email or password. Attempts remaining: {5 - user["login_attempts"]}'
                }
            
            # Reset login attempts on successful login
            user['login_attempts'] = 0
            user['last_login'] = datetime.now().isoformat()
            user['last_login_ip'] = ip_address
            
            # Generate JWT token
            token = self._generate_jwt_token(user)
            refresh_token = self._generate_refresh_token(user)
            
            # Remove sensitive data
            user_response = {k: v for k, v in user.items() if k != 'password_hash'}
            
            return {
                'success': True,
                'message': 'Login successful',
                'token': token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': self.token_expiry_hours * 3600,  # in seconds
                'user': user_response
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Login failed: {str(e)}'
            }
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Generate new access token using refresh token
        
        Args:
            refresh_token: Valid refresh token
        
        Returns:
            Dictionary with new token
        """
        try:
            # Decode refresh token
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=['HS256'])
            
            if payload.get('type') != 'refresh':
                return {
                    'success': False,
                    'error': 'Invalid token type'
                }
            
            user_id = payload.get('user_id')
            user = self._get_user_by_id(user_id)
            
            if not user or not user.get('is_active', True):
                return {
                    'success': False,
                    'error': 'User not found or inactive'
                }
            
            # Generate new access token
            new_token = self._generate_jwt_token(user)
            
            return {
                'success': True,
                'token': new_token,
                'token_type': 'Bearer',
                'expires_in': self.token_expiry_hours * 3600
            }
            
        except jwt.ExpiredSignatureError:
            return {
                'success': False,
                'error': 'Refresh token expired'
            }
        except jwt.InvalidTokenError:
            return {
                'success': False,
                'error': 'Invalid refresh token'
            }
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token and return user info
        
        Args:
            token: JWT token to verify
        
        Returns:
            Dictionary with verification result
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            user_id = payload.get('user_id')
            user = self._get_user_by_id(user_id)
            
            if not user or not user.get('is_active', True):
                return {
                    'valid': False,
                    'error': 'User not found or inactive'
                }
            
            return {
                'valid': True,
                'user_id': user_id,
                'email': payload.get('email'),
                'role': payload.get('role'),
                'permissions': payload.get('permissions', []),
                'exp': payload.get('exp')
            }
            
        except jwt.ExpiredSignatureError:
            return {
                'valid': False,
                'error': 'Token expired'
            }
        except jwt.InvalidTokenError:
            return {
                'valid': False,
                'error': 'Invalid token'
            }
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
        """
        Change user password
        
        Args:
            user_id: User identifier
            old_password: Current password
            new_password: New password
        
        Returns:
            Dictionary with result
        """
        user = self._get_user_by_id(user_id)
        
        if not user:
            return {
                'success': False,
                'error': 'User not found'
            }
        
        # Verify old password
        if not self._verify_password(old_password, user['password_hash']):
            return {
                'success': False,
                'error': 'Current password is incorrect'
            }
        
        # Validate new password
        password_validation = self._validate_password_strength(new_password)
        if not password_validation['valid']:
            return {
                'success': False,
                'error': password_validation['message']
            }
        
        # Update password
        user['password_hash'] = self._hash_password(new_password)
        user['updated_at'] = datetime.now().isoformat()
        
        return {
            'success': True,
            'message': 'Password changed successfully'
        }
    
    def reset_password_request(self, email: str) -> Dict[str, Any]:
        """
        Request password reset (sends reset token)
        
        Args:
            email: User email
        
        Returns:
            Dictionary with result
        """
        user = self._get_user_by_email(email)
        
        if not user:
            # Return success even if user not found (security best practice)
            return {
                'success': True,
                'message': 'If email exists, reset instructions will be sent'
            }
        
        # Generate reset token
        reset_token = str(uuid.uuid4())
        user['reset_token'] = reset_token
        user['reset_token_expiry'] = (datetime.now() + timedelta(hours=1)).isoformat()
        
        # In production, send email here
        print(f"📧 Password reset email would be sent to {email} with token: {reset_token}")
        
        return {
            'success': True,
            'message': 'Password reset instructions sent to your email'
        }
    
    def reset_password(self, email: str, reset_token: str, new_password: str) -> Dict[str, Any]:
        """
        Reset password using reset token
        
        Args:
            email: User email
            reset_token: Reset token from email
            new_password: New password
        
        Returns:
            Dictionary with result
        """
        user = self._get_user_by_email(email)
        
        if not user:
            return {
                'success': False,
                'error': 'Invalid request'
            }
        
        # Check reset token
        if user.get('reset_token') != reset_token:
            return {
                'success': False,
                'error': 'Invalid reset token'
            }
        
        # Check expiry
        if 'reset_token_expiry' in user:
            expiry = datetime.fromisoformat(user['reset_token_expiry'])
            if datetime.now() > expiry:
                return {
                    'success': False,
                    'error': 'Reset token expired'
                }
        
        # Validate new password
        password_validation = self._validate_password_strength(new_password)
        if not password_validation['valid']:
            return {
                'success': False,
                'error': password_validation['message']
            }
        
        # Update password
        user['password_hash'] = self._hash_password(new_password)
        user['reset_token'] = None
        user['reset_token_expiry'] = None
        user['updated_at'] = datetime.now().isoformat()
        
        return {
            'success': True,
            'message': 'Password reset successful'
        }
    
    def verify_email(self, user_id: str, verification_token: str) -> Dict[str, Any]:
        """
        Verify user email
        
        Args:
            user_id: User identifier
            verification_token: Verification token
        
        Returns:
            Dictionary with result
        """
        user = self._get_user_by_id(user_id)
        
        if not user:
            return {
                'success': False,
                'error': 'Invalid verification request'
            }
        
        if user.get('email_verified'):
            return {
                'success': True,
                'message': 'Email already verified'
            }
        
        # In production, validate token properly
        user['email_verified'] = True
        user['updated_at'] = datetime.now().isoformat()
        
        return {
            'success': True,
            'message': 'Email verified successfully'
        }
    
    def logout(self, user_id: str, token: str) -> Dict[str, Any]:
        """
        Logout user (invalidate token)
        
        Args:
            user_id: User identifier
            token: JWT token to invalidate
        
        Returns:
            Dictionary with result
        """
        # In production, add token to blacklist
        return {
            'success': True,
            'message': 'Logged out successfully'
        }
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get user profile information
        
        Args:
            user_id: User identifier
        
        Returns:
            Dictionary with user profile
        """
        user = self._get_user_by_id(user_id)
        
        if not user:
            return {
                'success': False,
                'error': 'User not found'
            }
        
        # Remove sensitive data
        user_profile = {k: v for k, v in user.items() if k not in ['password_hash', 'reset_token']}
        
        return {
            'success': True,
            'profile': user_profile
        }
    
    def update_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user profile
        
        Args:
            user_id: User identifier
            profile_data: Profile fields to update
        
        Returns:
            Dictionary with result
        """
        user = self._get_user_by_id(user_id)
        
        if not user:
            return {
                'success': False,
                'error': 'User not found'
            }
        
        # Fields that cannot be updated
        forbidden_fields = ['user_id', 'email', 'password_hash', 'role', 'created_at']
        
        for field, value in profile_data.items():
            if field not in forbidden_fields:
                user[field] = value
        
        user['updated_at'] = datetime.now().isoformat()
        user['profile_completed'] = True
        
        return {
            'success': True,
            'message': 'Profile updated successfully'
        }
    
    def check_permission(self, user_id: str, required_permission: str) -> bool:
        """
        Check if user has specific permission
        
        Args:
            user_id: User identifier
            required_permission: Permission to check
        
        Returns:
            True if user has permission
        """
        user = self._get_user_by_id(user_id)
        
        if not user or not user.get('is_active', True):
            return False
        
        role = user.get('role', '').lower()
        permissions = self.role_permissions.get(role, [])
        
        return required_permission in permissions
    
    def get_users_by_role(self, role: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all users with specific role
        
        Args:
            role: User role
            active_only: Only return active users
        
        Returns:
            List of users
        """
        users = [u for u in self.users if u.get('role') == role]
        
        if active_only:
            users = [u for u in users if u.get('is_active', True)]
        
        # Remove sensitive data
        for user in users:
            user.pop('password_hash', None)
            user.pop('reset_token', None)
        
        return users
    
    def deactivate_user(self, admin_id: str, user_id: str, reason: str = None) -> Dict[str, Any]:
        """
        Deactivate user account (admin only)
        
        Args:
            admin_id: Admin user identifier
            user_id: User to deactivate
            reason: Reason for deactivation
        
        Returns:
            Dictionary with result
        """
        # Check if admin has permission
        if not self.check_permission(admin_id, 'manage_users'):
            return {
                'success': False,
                'error': 'Unauthorized'
            }
        
        user = self._get_user_by_id(user_id)
        
        if not user:
            return {
                'success': False,
                'error': 'User not found'
            }
        
        user['is_active'] = False
        user['deactivation_reason'] = reason
        user['deactivated_by'] = admin_id
        user['deactivated_at'] = datetime.now().isoformat()
        
        return {
            'success': True,
            'message': f'User {user_id} deactivated'
        }
    
    def activate_user(self, admin_id: str, user_id: str) -> Dict[str, Any]:
        """
        Activate user account (admin only)
        
        Args:
            admin_id: Admin user identifier
            user_id: User to activate
        
        Returns:
            Dictionary with result
        """
        # Check if admin has permission
        if not self.check_permission(admin_id, 'manage_users'):
            return {
                'success': False,
                'error': 'Unauthorized'
            }
        
        user = self._get_user_by_id(user_id)
        
        if not user:
            return {
                'success': False,
                'error': 'User not found'
            }
        
        user['is_active'] = True
        user['activated_at'] = datetime.now().isoformat()
        
        return {
            'success': True,
            'message': f'User {user_id} activated'
        }
    
    # ========== Helper Methods ==========
    
    def _generate_jwt_token(self, user: Dict[str, Any]) -> str:
        """Generate JWT token for authenticated user"""
        payload = {
            'user_id': user['user_id'],
            'email': user['email'],
            'role': user['role'],
            'permissions': self.role_permissions.get(user['role'], []),
            'exp': datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def _generate_refresh_token(self, user: Dict[str, Any]) -> str:
        """Generate refresh token"""
        payload = {
            'user_id': user['user_id'],
            'type': 'refresh',
            'exp': datetime.utcnow() + timedelta(days=30),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def _generate_verification_token(self, user_id: str) -> str:
        """Generate email verification token"""
        payload = {
            'user_id': user_id,
            'type': 'verification',
            'exp': datetime.utcnow() + timedelta(days=7),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except:
            return False
    
    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _validate_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Validate password strength
        
        Returns:
            Dictionary with validation result and message
        """
        if len(password) < 8:
            return {
                'valid': False,
                'message': 'Password must be at least 8 characters long'
            }
        
        if not re.search(r'[A-Z]', password):
            return {
                'valid': False,
                'message': 'Password must contain at least one uppercase letter'
            }
        
        if not re.search(r'[a-z]', password):
            return {
                'valid': False,
                'message': 'Password must contain at least one lowercase letter'
            }
        
        if not re.search(r'[0-9]', password):
            return {
                'valid': False,
                'message': 'Password must contain at least one number'
            }
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return {
                'valid': False,
                'message': 'Password must contain at least one special character'
            }
        
        return {
            'valid': True,
            'message': 'Password strength: Strong'
        }
    
    def _get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        email_lower = email.lower()
        for user in self.users:
            if user.get('email') == email_lower:
                return user
        return None
    
    def _get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        for user in self.users:
            if user.get('user_id') == user_id:
                return user
        return None



_auth_service_instance = None


def get_auth_service(db_session=None) -> AuthService:
    """
    Get or create the global auth service instance
    """
    global _auth_service_instance
    if _auth_service_instance is None:
        _auth_service_instance = AuthService(db_session=db_session)
    return _auth_service_instance


# ========== Decorators for Route Protection ==========

def login_required(func):
    """
    Decorator to require authentication for routes
    """
    def wrapper(*args, **kwargs):
        # Implementation depends on your web framework
        # This is a placeholder
        return func(*args, **kwargs)
    return wrapper


def role_required(*allowed_roles):
    """
    Decorator to require specific roles for routes
    
    Args:
        *allowed_roles: List of allowed roles
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Implementation depends on your web framework
            # This is a placeholder
            return func(*args, **kwargs)
        return wrapper
    return decorator


def permission_required(permission: str):
    """
    Decorator to require specific permission for routes
    
    Args:
        permission: Required permission
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Implementation depends on your web framework
            # This is a placeholder
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ========== Test Function ==========

def test_auth_service():
    """Test the authentication service"""
    print("="*60)
    print("TESTING AUTHENTICATION SERVICE")
    print("="*60)
    
    auth = AuthService()
    
    # Test 1: Register user
    print("\nTest 1: Register Patient")
    user_data = {
        'email': 'john.doe@example.com',
        'password': 'Test@123456',
        'full_name': 'John Doe',
        'role': 'patient',
        'phone': '+1234567890',
        'date_of_birth': '1990-01-01',
        'blood_group': 'O+'
    }
    
    result = auth.register_user(user_data)
    print(f"   Success: {result['success']}")
    if result['success']:
        print(f"   User ID: {result['user']['user_id']}")
        print(f"   Role: {result['user']['role']}")
    
    # Test 2: Register Doctor
    print("\nTest 2: Register Doctor")
    doctor_data = {
        'email': 'dr.smith@hospital.com',
        'password': 'Doc@123456',
        'full_name': 'Dr. Sarah Smith',
        'role': 'doctor',
        'specialization': 'Endocrinology',
        'license_number': 'MED12345',
        'experience_years': 10
    }
    
    result = auth.register_user(doctor_data)
    print(f"   Success: {result['success']}")
    if result['success']:
        print(f"   Doctor ID: {result['user']['user_id']}")
        print(f"   Specialization: {result['user'].get('specialization')}")
    
    # Test 3: Login
    print("\nTest 3: Login")
    login_result = auth.login('john.doe@example.com', 'Test@123456')
    print(f"   Success: {login_result['success']}")
    if login_result['success']:
        print(f"   Token: {login_result['token'][:20]}...")
        print(f"   Role: {login_result['user']['role']}")
        
        # Test 4: Verify Token
        print("\nTest 4: Verify Token")
        verify_result = auth.verify_token(login_result['token'])
        print(f"   Valid: {verify_result['valid']}")
        print(f"   User ID: {verify_result.get('user_id')}")
        print(f"   Role: {verify_result.get('role')}")
    
    # Test 5: Check Permissions
    print("\n Test 5: Check Permissions")
    patient_id = auth.users[0]['user_id']
    
    can_view_own = auth.check_permission(patient_id, 'view_own_data')
    can_prescribe = auth.check_permission(patient_id, 'prescribe_medication')
    
    print(f"   Patient can view own data: {can_view_own}")
    print(f"   Patient can prescribe: {can_prescribe}")
    
    # Test 6: Get Users by Role
    print("\nTest 6: Get Users by Role")
    patients = auth.get_users_by_role('patient')
    doctors = auth.get_users_by_role('doctor')
    
    print(f"   Patients: {len(patients)}")
    print(f"   Doctors: {len(doctors)}")
    
    # Test 7: Password Validation
    print("\nTest 7: Password Validation")
    weak_passwords = ['password', '12345678', 'Password', 'Pass@123']
    for pwd in weak_passwords:
        validation = auth._validate_password_strength(pwd)
        print(f"   '{pwd}': {validation['valid']} - {validation['message']}")
    
    print("\n" + "="*60)
    print("Auth Service Test Complete")
    print("="*60)
    
    return auth


if __name__ == '__main__':
    # Run tests
    test_auth_service()