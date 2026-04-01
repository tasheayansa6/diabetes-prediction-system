from functools import wraps
from flask import request, jsonify
from flask_login import current_user
from backend.utils.logger import get_logger, log_security_event

logger = get_logger(__name__)

# Define role hierarchy (higher number = more permissions)
ROLE_HIERARCHY = {
    'patient': 1,
    'nurse': 2,
    'lab_technician': 2,
    'pharmacist': 2,
    'doctor': 3,
    'admin': 4
}

# Define role permissions
ROLE_PERMISSIONS = {
    'patient': [
        'view_own_records',
        'create_health_record',
        'view_own_predictions',
        'request_prediction'
    ],
    'nurse': [
        'view_own_records',
        'view_patient_records',
        'create_health_record',
        'update_patient_vitals'
    ],
    'lab_technician': [
        'view_lab_tests',
        'create_lab_test',
        'update_lab_results',
        'view_patient_records'
    ],
    'pharmacist': [
        'view_prescriptions',
        'dispense_medication',
        'view_patient_medications',
        'update_prescription_status'
    ],
    'doctor': [
        'view_all_patients',
        'view_patient_records',
        'create_prescription',
        'update_prescription',
        'view_predictions',
        'create_diagnosis',
        'update_health_record'
    ],
    'admin': [
        'manage_users',
        'delete_users',
        'view_statistics',
        'manage_system',
        'view_audit_logs',
        'manage_roles',
        'backup_database'
    ]
}

def require_role(*allowed_roles):
    """
    Decorator to require specific roles for accessing a route
    
    Args:
        allowed_roles: Tuple of role names that are allowed
    
    Usage:
        @app.route('/api/admin/users')
        @require_role('admin')
        def get_users():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated
            if not current_user.is_authenticated:
                log_security_event(
                    'unauthorized_access_attempt',
                    details=f"Unauthenticated access to {request.path}"
                )
                logger.warning(f"Unauthenticated access attempt to {request.path}")
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'You must be logged in to access this resource'
                }), 401
            
            # Check if user has required role
            if current_user.role not in allowed_roles:
                log_security_event(
                    'insufficient_permissions',
                    user_id=current_user.id,
                    details=f"User role '{current_user.role}' attempted to access {request.path} (requires: {allowed_roles})"
                )
                logger.warning(
                    f"User {current_user.id} with role '{current_user.role}' "
                    f"attempted to access {request.path} (requires: {allowed_roles})"
                )
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'This resource requires one of the following roles: {", ".join(allowed_roles)}'
                }), 403
            
            logger.info(f"User {current_user.id} ({current_user.role}) accessed {request.path}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_permission(*required_permissions):
    """
    Decorator to require specific permissions for accessing a route
    
    Args:
        required_permissions: Tuple of permission names required
    
    Usage:
        @app.route('/api/prescriptions')
        @require_permission('view_prescriptions', 'create_prescription')
        def prescriptions():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated
            if not current_user.is_authenticated:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'You must be logged in to access this resource'
                }), 401
            
            # Get user's permissions based on role
            user_permissions = ROLE_PERMISSIONS.get(current_user.role, [])
            
            # Check if user has all required permissions
            missing_permissions = [
                perm for perm in required_permissions 
                if perm not in user_permissions
            ]
            
            if missing_permissions:
                log_security_event(
                    'insufficient_permissions',
                    user_id=current_user.id,
                    details=f"Missing permissions: {missing_permissions}"
                )
                logger.warning(
                    f"User {current_user.id} lacks permissions: {missing_permissions}"
                )
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'Missing required permissions: {", ".join(missing_permissions)}'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_role_or_higher(minimum_role):
    """
    Decorator to require a minimum role level based on hierarchy
    
    Args:
        minimum_role: Minimum role required (e.g., 'doctor' allows doctor and admin)
    
    Usage:
        @app.route('/api/patients')
        @require_role_or_higher('doctor')
        def get_patients():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated
            if not current_user.is_authenticated:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'You must be logged in to access this resource'
                }), 401
            
            # Get role levels
            user_level = ROLE_HIERARCHY.get(current_user.role, 0)
            required_level = ROLE_HIERARCHY.get(minimum_role, 999)
            
            # Check if user's role level is sufficient
            if user_level < required_level:
                log_security_event(
                    'insufficient_role_level',
                    user_id=current_user.id,
                    details=f"Role '{current_user.role}' (level {user_level}) < required '{minimum_role}' (level {required_level})"
                )
                logger.warning(
                    f"User {current_user.id} with role '{current_user.role}' "
                    f"attempted to access {request.path} (requires: {minimum_role} or higher)"
                )
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'This resource requires {minimum_role} role or higher'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_self_or_role(*allowed_roles):
    """
    Decorator to allow access if user is accessing their own resource OR has specific role
    
    Args:
        allowed_roles: Tuple of roles that can access any user's resource
    
    Usage:
        @app.route('/api/user/<int:user_id>/profile')
        @require_self_or_role('admin', 'doctor')
        def get_profile(user_id):
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated
            if not current_user.is_authenticated:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'You must be logged in to access this resource'
                }), 401
            
            # Get user_id from route parameters
            target_user_id = kwargs.get('user_id') or kwargs.get('patient_id')
            
            # Allow if accessing own resource
            if target_user_id and current_user.id == target_user_id:
                return f(*args, **kwargs)
            
            # Allow if user has required role
            if current_user.role in allowed_roles:
                return f(*args, **kwargs)
            
            # Deny access
            log_security_event(
                'unauthorized_resource_access',
                user_id=current_user.id,
                details=f"Attempted to access user {target_user_id}'s resource"
            )
            logger.warning(
                f"User {current_user.id} attempted to access user {target_user_id}'s resource"
            )
            return jsonify({
                'error': 'Insufficient permissions',
                'message': 'You can only access your own resources'
            }), 403
        return decorated_function
    return decorator

def check_permission(permission_name):
    """
    Check if current user has a specific permission
    
    Args:
        permission_name: Name of the permission to check
    
    Returns:
        bool: True if user has permission, False otherwise
    """
    if not current_user.is_authenticated:
        return False
    
    user_permissions = ROLE_PERMISSIONS.get(current_user.role, [])
    return permission_name in user_permissions

def get_user_permissions():
    """
    Get all permissions for the current user
    
    Returns:
        list: List of permission names
    """
    if not current_user.is_authenticated:
        return []
    
    return ROLE_PERMISSIONS.get(current_user.role, [])

def has_role(*roles):
    """
    Check if current user has any of the specified roles
    
    Args:
        roles: Tuple of role names to check
    
    Returns:
        bool: True if user has any of the roles, False otherwise
    """
    if not current_user.is_authenticated:
        return False
    
    return current_user.role in roles

def is_admin():
    """
    Check if current user is an admin
    
    Returns:
        bool: True if user is admin, False otherwise
    """
    return has_role('admin')

def is_doctor():
    """
    Check if current user is a doctor
    
    Returns:
        bool: True if user is doctor, False otherwise
    """
    return has_role('doctor')

def is_patient():
    """
    Check if current user is a patient
    
    Returns:
        bool: True if user is patient, False otherwise
    """
    return has_role('patient')

def can_access_patient_data(patient_id):
    """
    Check if current user can access specific patient's data
    
    Args:
        patient_id: ID of the patient
    
    Returns:
        bool: True if user can access, False otherwise
    """
    if not current_user.is_authenticated:
        return False
    
    # Patient can access own data
    if current_user.id == patient_id:
        return True
    
    # Doctors and admins can access all patient data
    if current_user.role in ['doctor', 'admin', 'nurse']:
        return True
    
    return False

# Role-based route decorators for common scenarios
def patient_only(f):
    """Decorator for patient-only routes"""
    return require_role('patient')(f)

def doctor_only(f):
    """Decorator for doctor-only routes"""
    return require_role('doctor')(f)

def admin_only(f):
    """Decorator for admin-only routes"""
    return require_role('admin')(f)

def medical_staff_only(f):
    """Decorator for medical staff routes (doctor, nurse, admin)"""
    return require_role('doctor', 'nurse', 'admin')(f)

def staff_only(f):
    """Decorator for all staff routes (excludes patients)"""
    return require_role('doctor', 'nurse', 'lab_technician', 'pharmacist', 'admin')(f)

# Example usage
if __name__ == '__main__':
    print("Role Hierarchy:")
    for role, level in sorted(ROLE_HIERARCHY.items(), key=lambda x: x[1]):
        print(f"  {role}: Level {level}")
    
    print("\nRole Permissions:")
    for role, permissions in ROLE_PERMISSIONS.items():
        print(f"\n{role}:")
        for perm in permissions:
            print(f"  - {perm}")
