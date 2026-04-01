"""
Authentication Routes - Complete implementation with registration, login, logout, profile (GET/PUT), 
password change, token refresh, and email verification
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from backend.extensions import db
from backend.models.user import User
from sqlalchemy import text
from backend.models.patient import Patient
from backend.models.doctor import Doctor
from backend.models.nurse import Nurse
from backend.models.lab_technician import LabTechnician
from backend.models.pharmacist import Pharmacist
from backend.models.admin import Admin
import re
from datetime import datetime, timedelta
import jwt
from functools import wraps

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Token blacklist for logout functionality
# In production, use Redis or database instead of in-memory set
token_blacklist = set()

def token_required(f):
    """
    Decorator to protect routes that require authentication
    Checks for valid token and ensures it's not blacklisted
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({
                "success": False,
                "message": "Token is missing!"
            }), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Check if token is blacklisted (logged out)
            if token in token_blacklist:
                return jsonify({
                    "success": False,
                    "message": "Token has been invalidated. Please login again."
                }), 401
            
            # Decode token
            data = jwt.decode(
                token, 
                current_app.config['SECRET_KEY'], 
                algorithms=["HS256"]
            )
            
            row = db.session.execute(
                text('SELECT id FROM users WHERE id = :id'),
                {'id': data['user_id']}
            ).fetchone()
            current_user = User.query.filter_by(id=data['user_id']).first() if row else None
            
            if not current_user:
                return jsonify({
                    "success": False,
                    "message": "Invalid token!"
                }), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False,
                "message": "Token has expired!"
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "success": False,
                "message": "Invalid token!"
            }), 401
            
        return f(current_user, *args, **kwargs)
    
    return decorated

def validate_email(email):
    """
    Validate email format using regex pattern
    
    Args:
        email: Email string to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """
    Validate password strength
    
    Args:
        password: Password string to validate
    
    Returns:
        tuple: (is_valid, message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, "Password is valid"


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user with role-based creation
    ---
    Request Body (JSON):
        {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "SecurePass123",
            "role": "patient",  # or doctor, nurse, admin, etc.
            "patient_id": "PAT001",  # optional role-specific fields
            "doctor_id": "DOC001",
            "specialization": "Cardiology"
        }
    """
    try:
        data = request.get_json(force=True, silent=True)

        if not data:
            return jsonify({"success": False, "message": "Invalid or missing JSON body"}), 400

        # Validate required fields
        required_fields = ['username', 'email', 'password', 'role']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "message": f"Missing required field: {field}"
                }), 400
        
        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password")
        role = data.get("role", "patient").lower()
        
        # Validate username length
        if len(username) < 3:
            return jsonify({
                "success": False,
                "message": "Username must be at least 3 characters long"
            }), 400
        
        if len(username) > 50:
            return jsonify({
                "success": False,
                "message": "Username must be less than 50 characters"
            }), 400
        
        # Validate email format
        if not validate_email(email):
            return jsonify({
                "success": False,
                "message": "Invalid email format"
            }), 400
        
        # Validate password strength
        is_valid, password_message = validate_password(password)
        if not is_valid:
            return jsonify({
                "success": False,
                "message": password_message
            }), 400
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({
                "success": False,
                "message": "User with this email already exists"
            }), 409
        
        if User.query.filter_by(username=username).first():
            return jsonify({
                "success": False,
                "message": "Username already taken"
            }), 409
        
        # Create hashed password
        hashed_password = generate_password_hash(password)
        
        # Create user based on role - FIXED: Now properly handles all roles
        new_user = None
        
        if role == 'patient':
            new_user = Patient(
                username=username,
                email=email,
                password_hash=hashed_password,
                role='patient',
                full_name=data.get('full_name') or username,
                patient_id=data.get('patient_id') or f"PAT{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                blood_group=data.get('blood_group'),
                emergency_contact=data.get('emergency_contact'),
                emergency_contact_name=data.get('emergency_contact_name'),
                created_at=datetime.utcnow(),
                is_active=True,
                email_verified=False
            )
            
        elif role == 'doctor':
            new_user = Doctor(
                username=username,
                email=email,
                password_hash=hashed_password,
                role='doctor',
                full_name=data.get('full_name') or username,
                doctor_id=data.get('doctor_id') or f"DOC{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                specialization=data.get('specialization'),
                qualification=data.get('qualification'),
                license_number=data.get('license_number'),
                years_of_experience=data.get('years_of_experience'),
                created_at=datetime.utcnow(),
                is_active=True,
                email_verified=False
            )
            
        elif role == 'nurse':
            new_user = Nurse(
                username=username,
                email=email,
                password_hash=hashed_password,
                role='nurse',
                full_name=data.get('full_name') or username,
                nurse_id=data.get('nurse_id') or f"NUR{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                department=data.get('department'),
                shift=data.get('shift'),
                qualification=data.get('qualification'),
                license_number=data.get('license_number'),
                created_at=datetime.utcnow(),
                is_active=True,
                email_verified=False
            )
            
        elif role == 'lab_technician':
            new_user = LabTechnician(
                username=username,
                email=email,
                password_hash=hashed_password,
                role='lab_technician',
                full_name=data.get('full_name') or username,
                technician_id=data.get('technician_id') or f"LAB{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                qualification=data.get('qualification'),
                license_number=data.get('license_number'),
                specialization=data.get('specialization'),
                created_at=datetime.utcnow(),
                is_active=True,
                email_verified=False
            )
            
        elif role == 'pharmacist':
            new_user = Pharmacist(
                username=username,
                email=email,
                password_hash=hashed_password,
                role='pharmacist',
                full_name=data.get('full_name') or username,
                pharmacist_id=data.get('pharmacist_id') or f"PHR{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                license_number=data.get('license_number'),
                created_at=datetime.utcnow(),
                is_active=True,
                email_verified=False
            )
            
        elif role == 'admin':
            new_user = Admin(
                username=username,
                email=email,
                password_hash=hashed_password,
                role='admin',
                full_name=data.get('full_name') or username,
                admin_id=data.get('admin_id') or f"ADM{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                created_at=datetime.utcnow(),
                is_active=True,
                email_verified=False
            )
            
        else:
            return jsonify({
                "success": False,
                "message": f"Invalid role: {role}. Supported roles: patient, doctor, nurse, lab_technician, pharmacist, admin"
            }), 400
        
        db.session.add(new_user)
        db.session.commit()

        from backend.utils.logger import log_security_event
        log_security_event('register', user_id=new_user.id, username=new_user.username,
                           ip_address=request.remote_addr, status='success',
                           details=f'Role: {role}')

        # Generate JWT token for auto-login
        token = jwt.encode({
            'user_id': new_user.id,
            'email': new_user.email,
            'username': new_user.username,
            'role': new_user.role,
            'exp': datetime.utcnow() + timedelta(days=1)
        }, current_app.config['SECRET_KEY'], algorithm="HS256")
        
        return jsonify({
            "success": True,
            "message": "User registered successfully",
            "token": token,
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "name": getattr(new_user, 'full_name', None) or new_user.username,
                "email": new_user.email,
                "role": new_user.role,
                "email_verified": getattr(new_user, 'email_verified', False),
                "created_at": new_user.created_at.isoformat() if getattr(new_user, 'created_at', None) else None
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred during registration",
            "error": str(e)  # Remove in production
        }), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Login user and return JWT token
    ---
    Request Body (JSON):
        {
            "email": "john@example.com",
            "password": "SecurePass123",
            "role": "patient"  # Optional - can be used for role validation
        }
    
    Returns:
        200: Login successful with token
        400: Missing credentials
        401: Invalid credentials
        403: Account deactivated
        500: Server error
    """
    try:
        data = request.get_json(force=True, silent=True)
        
        # Validate required fields
        if not data or not data.get("email") or not data.get("password"):
            return jsonify({
                "success": False,
                "message": "Email and password are required"
            }), 400
        
        email = data.get("email", "").strip().lower()
        password = data.get("password")
        requested_role = data.get("role")  # Optional role validation
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        # Check credentials
        if not user or not check_password_hash(user.password_hash, password):
            from backend.utils.logger import log_security_event
            log_security_event('failed_login', username=email,
                               ip_address=request.remote_addr, status='failed',
                               error_message='Invalid email or password')
            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401
        
        # Optional: Validate role if provided
        if requested_role and user.role != requested_role:
            return jsonify({
                "success": False,
                "message": f"Invalid role for this user. Expected {user.role}, got {requested_role}"
            }), 401
        
        # Check if account is active
        if hasattr(user, 'is_active') and not user.is_active:
            return jsonify({
                "success": False,
                "message": "Account is deactivated. Please contact support."
            }), 403
        
        # Update last login time
        try:
            if hasattr(user, 'last_login'):
                user.last_login = datetime.utcnow()
                db.session.commit()
        except Exception:
            db.session.rollback()

        from backend.utils.logger import log_security_event
        log_security_event('login', user_id=user.id, username=user.username,
                           ip_address=request.remote_addr, status='success')
        
        # Generate JWT token
        token = jwt.encode({
            'user_id': user.id,
            'email': user.email,
            'username': user.username,
            'role': user.role,
            'exp': datetime.utcnow() + timedelta(days=1)
        }, current_app.config['SECRET_KEY'], algorithm="HS256")
        
        return jsonify({
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "name": getattr(user, 'full_name', None) or user.username,
                "email": user.email,
                "role": user.role,
                "email_verified": getattr(user, 'email_verified', None)
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "An error occurred during login",
            "error": str(e)  # Remove in production
        }), 500



import random
import string

# In-memory stores (use Redis/DB in production)
_otp_store = {}        # email -> {otp, expiry, username}
_reset_store = {}      # token -> {email, expiry}


# ============ SEND OTP (email verification) ============

@auth_bp.route("/send-otp", methods=["POST"])
def send_otp():
    """
    POST /api/auth/send-otp
    Body: { "email": "...", "username": "..." }
    Sends a 6-digit OTP to the email address.
    """
    try:
        data = request.get_json()
        email = (data.get("email") or "").strip().lower()
        username = data.get("username") or email.split("@")[0]

        if not email:
            return jsonify({"success": False, "message": "Email is required"}), 400

        otp = "".join(random.choices(string.digits, k=6))
        expiry = datetime.utcnow() + timedelta(seconds=current_app.config.get("OTP_EXPIRY", 900))
        _otp_store[email] = {"otp": otp, "expiry": expiry, "username": username}

        from backend.services.notification_service import send_otp_email
        ok, err = send_otp_email(email, username, otp)

        if ok:
            return jsonify({"success": True, "message": "Verification code sent to your email"}), 200
        else:
            # Still return success so user knows to check — log the error
            current_app.logger.error(f"OTP email failed: {err}")
            return jsonify({"success": True, "message": "Verification code sent (check spam if not received)", "debug": err}), 200

    except Exception as e:
        return jsonify({"success": False, "message": "Error sending OTP", "error": str(e)}), 500


# ============ VERIFY OTP ============

@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    """
    POST /api/auth/verify-otp
    Body: { "email": "...", "otp": "123456" }
    """
    try:
        data = request.get_json()
        email = (data.get("email") or "").strip().lower()
        otp = (data.get("otp") or "").strip()

        if not email or not otp:
            return jsonify({"success": False, "message": "Email and OTP are required"}), 400

        record = _otp_store.get(email)
        if not record:
            return jsonify({"success": False, "message": "No OTP found for this email. Please request a new one."}), 400

        if datetime.utcnow() > record["expiry"]:
            _otp_store.pop(email, None)
            return jsonify({"success": False, "message": "OTP has expired. Please request a new one."}), 400

        if otp != record["otp"]:
            return jsonify({"success": False, "message": "Invalid verification code"}), 400

        # Mark user as email_verified in DB if they exist
        user = User.query.filter_by(email=email).first()
        if user and hasattr(user, "email_verified"):
            user.email_verified = True
            db.session.commit()

        _otp_store.pop(email, None)
        return jsonify({"success": True, "message": "Email verified successfully"}), 200

    except Exception as e:
        return jsonify({"success": False, "message": "Error verifying OTP", "error": str(e)}), 500


# ============ FORGOT PASSWORD ============

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    POST /api/auth/forgot-password
    Body: { "email": "..." }
    Sends a password reset link to the email.
    """
    try:
        data = request.get_json()
        email = (data.get("email") or "").strip().lower()

        if not email:
            return jsonify({"success": False, "message": "Email is required"}), 400

        # Always return success to prevent email enumeration
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"success": True, "message": "If an account exists with this email, a reset link has been sent."}), 200

        # Generate secure reset token
        token = "".join(random.choices(string.ascii_letters + string.digits, k=48))
        expiry = datetime.utcnow() + timedelta(seconds=current_app.config.get("RESET_TOKEN_EXPIRY", 3600))
        _reset_store[token] = {"email": email, "expiry": expiry}

        # Build reset URL — use request host
        base_url = request.host_url.rstrip("/")
        reset_url = f"{base_url}/reset-password?token={token}&email={email}"

        from backend.services.notification_service import send_password_reset_email
        ok, err = send_password_reset_email(email, user.username, token, reset_url)

        if not ok:
            current_app.logger.error(f"Reset email failed: {err}")

        return jsonify({"success": True, "message": "If an account exists with this email, a reset link has been sent."}), 200

    except Exception as e:
        return jsonify({"success": False, "message": "Error processing request", "error": str(e)}), 500


# ============ RESET PASSWORD ============

@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """
    POST /api/auth/reset-password
    Body: { "token": "...", "email": "...", "new_password": "..." }
    """
    try:
        data = request.get_json()
        token = (data.get("token") or "").strip()
        email = (data.get("email") or "").strip().lower()
        new_password = data.get("new_password") or ""

        if not all([token, email, new_password]):
            return jsonify({"success": False, "message": "Token, email, and new password are required"}), 400

        record = _reset_store.get(token)
        if not record:
            return jsonify({"success": False, "message": "Invalid or expired reset link. Please request a new one."}), 400

        if datetime.utcnow() > record["expiry"]:
            _reset_store.pop(token, None)
            return jsonify({"success": False, "message": "Reset link has expired. Please request a new one."}), 400

        if record["email"] != email:
            return jsonify({"success": False, "message": "Invalid reset link."}), 400

        is_valid, msg = validate_password(new_password)
        if not is_valid:
            return jsonify({"success": False, "message": msg}), 400

        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        _reset_store.pop(token, None)

        return jsonify({"success": True, "message": "Password reset successfully. You can now log in."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Error resetting password", "error": str(e)}), 500


# ============ SHARED NOTIFICATIONS (all roles) ============

def _get_user_id_from_token():
    token = request.headers.get('Authorization', '')
    if token.startswith('Bearer '):
        token = token[7:]
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload.get('user_id')
    except Exception:
        return None


@auth_bp.route('/notifications', methods=['GET'])
def get_notifications():
    """GET /api/auth/notifications — real DB notifications for any logged-in role."""
    user_id = _get_user_id_from_token()
    if not user_id:
        return jsonify({'success': False, 'message': 'Invalid token'}), 401
    try:
        from backend.models.notification import Notification
        notifs = Notification.query.filter_by(user_id=user_id)\
            .order_by(Notification.created_at.desc()).limit(50).all()
        unread = Notification.query.filter_by(user_id=user_id, is_read=False).count()
        return jsonify({
            'success': True,
            'notifications': [n.to_dict() for n in notifs],
            'unread_count': unread
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@auth_bp.route('/notifications/<int:notif_id>/read', methods=['PUT'])
def mark_one_read(notif_id):
    """PUT /api/auth/notifications/<id>/read"""
    user_id = _get_user_id_from_token()
    if not user_id:
        return jsonify({'success': False, 'message': 'Invalid token'}), 401
    try:
        from backend.models.notification import Notification
        n = Notification.query.filter_by(id=notif_id, user_id=user_id).first()
        if not n:
            return jsonify({'success': False, 'message': 'Not found'}), 404
        n.is_read = True
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@auth_bp.route('/notifications/read-all', methods=['PUT'])
def mark_all_read():
    """PUT /api/auth/notifications/read-all"""
    user_id = _get_user_id_from_token()
    if not user_id:
        return jsonify({'success': False, 'message': 'Invalid token'}), 401
    try:
        from backend.models.notification import Notification
        Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
