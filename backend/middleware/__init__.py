"""
Middleware package - Request/response processing layer
Centralized exports for all middleware components
"""

from .auth_middleware import require_auth, token_required, login_required
from .error_handler import register_error_handlers
from .request_logger import log_request
from .cors_middleware import setup_cors
from .rate_limiter import rate_limit, setup_rate_limiting
from .role_middleware import (  # Updated to match actual function names
    require_role, require_permission, require_role_or_higher,
    require_self_or_role, patient_only, doctor_only, admin_only,
    medical_staff_only, staff_only, is_admin, is_doctor,
    can_access_patient_data
)

__all__ = [
    'require_auth', 'token_required', 'login_required',
    'register_error_handlers',
    'log_request',
    'setup_cors',
    'rate_limit', 'setup_rate_limiting',
    # Role middleware exports - matching actual function names
    'require_role', 'require_permission', 'require_role_or_higher',
    'require_self_or_role', 'patient_only', 'doctor_only', 'admin_only',
    'medical_staff_only', 'staff_only', 'is_admin', 'is_doctor',
    'can_access_patient_data'
]

def init_middleware(app):
    setup_cors(app)
    register_error_handlers(app)
    app.before_request(log_request)
    print(" Middleware initialized")
    return app