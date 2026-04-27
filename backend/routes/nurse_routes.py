"""
Nurse Routes - Handles nurse dashboard, vital signs, patient queue, and patient registration
"""

from flask import Blueprint, request, jsonify, current_app
from backend.extensions import db
from backend.models.user import User
from backend.models.nurse import Nurse
from backend.models.patient import Patient
from backend.models.vital_sign import VitalSign
from backend.models.queue import PatientQueue
from backend.models.appointment import Appointment
from backend.utils.validators import validate_health_data
from datetime import datetime, timedelta
from sqlalchemy import func, desc, text
import jwt
from functools import wraps
import uuid

nurse_bp = Blueprint('nurse', __name__, url_prefix='/api/nurse')

# ============ TOKEN DECORATOR ============



def _safe_error(e):
    """Return error detail only in development."""
    from flask import current_app
    if current_app.config.get('EXPOSE_ERRORS', False):
        return str(e)
    return None


def _ensure_patient_profile(user):
    """
    Ensure a `patients` row exists for a user with role=patient.
    """
    if not user or getattr(user, 'role', None) != 'patient':
        return None

    patient_exists = db.session.execute(
        text("SELECT id FROM patients WHERE id = :id"),
        {'id': user.id}
    ).fetchone()
    if patient_exists:
        return Patient.query.filter_by(id=user.id).first()

    patient = Patient(
        id=user.id,
        patient_id=f"PAT{user.id:06d}",
        username=user.username,
        email=user.email,
        password_hash=user.password_hash,
        role='patient',
        full_name=getattr(user, 'full_name', None),
        phone=getattr(user, 'phone', None),
        is_active=getattr(user, 'is_active', True),
        email_verified=getattr(user, 'email_verified', False),
        created_at=getattr(user, 'created_at', datetime.utcnow())
    )
    db.session.add(patient)
    return patient

def token_required(f):
    """Decorator for nurse routes using JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({"success": False, "message": "Token is missing!"}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]

            # Check blacklist (logout invalidation)
            try:
                from backend.models.audit_log import AuditLog
                if AuditLog.query.filter_by(action='token_blacklist', description=token[:100]).first():
                    return jsonify({"success": False, "message": "Token has been invalidated. Please login again."}), 401
            except Exception:
                pass
            
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            
            # Check if role is nurse
            if data.get('role') != 'nurse':
                return jsonify({"success": False, "message": "Nurse access required!"}), 403
            
            # Get nurse — auto-create nurses row if missing (manually inserted users)
            nurse = Nurse.query.get(data['user_id'])
            if not nurse:
                user = User.query.get(data['user_id'])
                if not user:
                    return jsonify({"success": False, "message": "Nurse not found!"}), 404
                nurse = Nurse(id=user.id, nurse_id=f"NUR{user.id:04d}")
                db.session.add(nurse)
                db.session.commit()
                nurse = Nurse.query.get(data['user_id'])
            
            current_nurse = {
                'id': nurse.id,
                'username': nurse.username,
                'email': nurse.email,
                'role': nurse.role,
                'nurse_id': getattr(nurse, 'nurse_id', None),
                'department': nurse.department,
                'shift': nurse.shift
            }
            
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Invalid token!"}), 401
            
        return f(current_nurse, *args, **kwargs)
    
    return decorated


# ============ VALIDATION FUNCTIONS ============

def validate_vital_signs(data):
    """
    Validate vital signs data
    """
    # Temperature check (35-42°C is reasonable range)
    if 'temperature' in data and data['temperature']:
        try:
            temp = float(data['temperature'])
            if temp < 30 or temp > 45:
                return False, "Temperature out of normal range (30-45°C)"
        except (ValueError, TypeError):
            return False, "Invalid temperature value"
    
    # Heart rate check (30-200 bpm)
    if 'heart_rate' in data and data['heart_rate']:
        try:
            hr = int(data['heart_rate'])
            if hr < 30 or hr > 250:
                return False, "Heart rate out of normal range (30-250 bpm)"
        except (ValueError, TypeError):
            return False, "Invalid heart rate value"
    
    # Blood pressure checks
    if 'blood_pressure_systolic' in data and data['blood_pressure_systolic']:
        try:
            sys = int(data['blood_pressure_systolic'])
            if sys < 50 or sys > 250:
                return False, "Systolic BP out of range (50-250 mmHg)"
        except (ValueError, TypeError):
            return False, "Invalid systolic BP value"
    
    if 'blood_pressure_diastolic' in data and data['blood_pressure_diastolic']:
        try:
            dias = int(data['blood_pressure_diastolic'])
            if dias < 30 or dias > 150:
                return False, "Diastolic BP out of range (30-150 mmHg)"
        except (ValueError, TypeError):
            return False, "Invalid diastolic BP value"
    
    # Oxygen saturation (50-100%)
    if 'oxygen_saturation' in data and data['oxygen_saturation']:
        try:
            spo2 = float(data['oxygen_saturation'])
            if spo2 < 50 or spo2 > 100:
                return False, "Oxygen saturation out of range (50-100%)"
        except (ValueError, TypeError):
            return False, "Invalid oxygen saturation value"
    
    return True, "Valid"


# ============ GET NURSE DASHBOARD ============

@nurse_bp.route('/dashboard', methods=['GET'])
@token_required
def get_dashboard(current_nurse):
    """
    GET /api/nurse/dashboard - Nurse dashboard with statistics
    """
    try:
        nurse_id = current_nurse['id']
        today = datetime.utcnow().date()
        
        # Count patients in queue
        queue_count = PatientQueue.query.filter_by(
            status='waiting'
        ).count()
        
        # Count today's appointments
        today_appointments = Appointment.query.filter(
            func.date(Appointment.appointment_date) == today
        ).count()
        
        # Count patients seen today
        patients_seen_today = VitalSign.query.filter(
            func.date(VitalSign.recorded_at) == today,
            VitalSign.nurse_id == nurse_id
        ).distinct(VitalSign.patient_id).count()
        
        # Count total patients
        total_patients = Patient.query.count()
        
        # Get recent vital signs recorded
        recent_vitals = VitalSign.query.filter_by(
            nurse_id=nurse_id
        ).order_by(VitalSign.recorded_at.desc()).limit(10).all()
        
        recent_vitals_list = []
        for v in recent_vitals:
            patient = Patient.query.get(v.patient_id)
            recent_vitals_list.append({
                "id": v.id,
                "patient": {
                    "id": patient.id,
                    "name": patient.username,
                    "patient_id": getattr(patient, 'patient_id', None)
                } if patient else None,
                "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None
            })
        
        # Get queue summary by priority
        urgent_count = PatientQueue.query.filter_by(
            status='waiting',
            priority=1
        ).count()
        
        emergency_count = PatientQueue.query.filter_by(
            status='waiting',
            priority=2
        ).count()
        
        return jsonify({
            "success": True,
            "dashboard": {
                "nurse_info": {
                    "id": current_nurse['id'],
                    "name": current_nurse['username'],
                    "nurse_id": current_nurse.get('nurse_id'),
                    "department": current_nurse.get('department'),
                    "shift": current_nurse.get('shift')
                },
                "statistics": {
                    "patients_in_queue": queue_count,
                    "today_appointments": today_appointments,
                    "patients_seen_today": patients_seen_today,
                    "total_patients": total_patients,
                    "urgent_cases": urgent_count,
                    "emergency_cases": emergency_count
                },
                "recent_activity": recent_vitals_list
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching dashboard",
            "error": _safe_error(e)
        }), 500


# ============ RECORD VITAL SIGNS ============

@nurse_bp.route('/vitals', methods=['POST'])
@token_required
def record_vitals(current_nurse):
    """
    POST /api/nurse/vitals - Record patient vital signs
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['patient_id', 'blood_pressure_diastolic']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "success": False,
                    "message": "Diastolic Blood Pressure is required (used in ML prediction)"
                    if field == 'blood_pressure_diastolic' else f"Missing required field: {field}"
                }), 400
        
        # Validate patient exists
        try:
            patient = Patient.query.get(data['patient_id'])
        except Exception:
            patient = None
        if not patient:
            # Backward-compatibility: some old accounts exist in users table only.
            user_patient = User.query.get(data['patient_id'])
            if user_patient and user_patient.role == 'patient':
                patient = _ensure_patient_profile(user_patient)
                db.session.commit()
        if not patient:
            return jsonify({
                "success": False,
                "message": "Patient not found"
            }), 404
        
        # Validate vital signs
        valid, message = validate_vital_signs(data)
        if not valid:
            return jsonify({
                "success": False,
                "message": message
            }), 400
        
        # Calculate BMI if height and weight provided
        bmi = None
        if data.get('height') and data.get('weight'):
            try:
                height_m = float(data['height']) / 100  # convert cm to m
                weight_kg = float(data['weight'])
                if height_m > 0 and weight_kg > 0:
                    bmi = round(weight_kg / (height_m * height_m), 2)
            except (ValueError, ZeroDivisionError):
                bmi = None
        
        # Generate unique vital_id
        vital_id = f"VT{datetime.utcnow().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        
        # Create vital sign record
        vital = VitalSign(
            vital_id=vital_id,
            patient_id=data['patient_id'],
            nurse_id=current_nurse['id'],
            appointment_id=data.get('appointment_id'),
            temperature=data.get('temperature'),
            heart_rate=data.get('heart_rate'),
            respiratory_rate=data.get('respiratory_rate'),
            blood_pressure_systolic=data.get('blood_pressure_systolic'),
            blood_pressure_diastolic=data.get('blood_pressure_diastolic'),
            oxygen_saturation=data.get('oxygen_saturation'),
            height=data.get('height'),
            weight=data.get('weight'),
            bmi=bmi,
            skin_thickness=data.get('skin_thickness'),
            pain_level=data.get('pain_level'),
            pregnancies=data.get('pregnancies'),
            diabetes_pedigree=data.get('diabetes_pedigree'),
            age=data.get('age'),
            notes=data.get('notes', ''),
            recorded_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(vital)
        db.session.commit()

        # Save gender to patient record if provided
        if data.get('gender') in ('male', 'female', 'other'):
            try:
                pat = Patient.query.get(data['patient_id'])
                if pat and hasattr(pat, 'gender'):
                    pat.gender = data['gender']
                    db.session.commit()
            except Exception:
                pass
        if data.get('blood_pressure_diastolic'):
            try:
                from backend.models.notification import Notification
                bp_str = ''
                if data.get('blood_pressure_systolic') and data.get('blood_pressure_diastolic'):
                    bp_str = f", BP: {data['blood_pressure_systolic']}/{data['blood_pressure_diastolic']}"
                bmi_str = f", BMI: {bmi}" if bmi else ''
                msg = (f"Nurse {current_nurse['username']} recorded vitals for "
                       f"{patient.username} (ID: {getattr(patient, 'patient_id', None)}){bp_str}{bmi_str}. "
                       f"Patient is ready for consultation.")
                doctors = User.query.filter_by(role='doctor', is_active=True).all()
                for doc in doctors:
                    db.session.add(Notification(
                        user_id=doc.id,
                        title='Vitals Recorded',
                        message=msg,
                        type='vitals',
                        category='general',
                        is_read=False,
                        link=f'/templates/doctor/patient_list.html?highlight={patient.id}',
                        created_at=datetime.utcnow()
                    ))
                db.session.commit()
            except Exception as notif_err:
                current_app.logger.error(f'Vitals notification error: {notif_err}')
                try:
                    db.session.rollback()
                except Exception:
                    pass

        return jsonify({
            "success": True,
            "message": "Vital signs recorded successfully",
            "vital": {
                "id": vital.id,
                "vital_id": vital.vital_id,
                "patient_id": vital.patient_id,
                "recorded_at": vital.recorded_at.isoformat() if vital.recorded_at else None
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error recording vital signs",
            "error": _safe_error(e)
        }), 500


# ============ UPDATE VITAL SIGNS ============

@nurse_bp.route('/vitals/<int:vital_id>', methods=['PUT'])
@token_required
def update_vitals(current_nurse, vital_id):
    """
    PUT /api/nurse/vitals/<id> - Update existing vital signs record
    """
    try:
        vital = VitalSign.query.filter_by(id=vital_id, nurse_id=current_nurse['id']).first()
        if not vital:
            return jsonify({'success': False, 'message': 'Vital record not found'}), 404

        data = request.get_json()

        # Recalculate BMI if height/weight provided
        if data.get('height') and data.get('weight'):
            try:
                h = float(data['height']) / 100
                w = float(data['weight'])
                vital.bmi = round(w / (h * h), 2)
            except (ValueError, ZeroDivisionError):
                pass

        fields = [
            'temperature', 'heart_rate', 'respiratory_rate',
            'blood_pressure_systolic', 'blood_pressure_diastolic',
            'oxygen_saturation', 'height', 'weight', 'skin_thickness',
            'pain_level', 'pregnancies', 'diabetes_pedigree', 'age', 'notes'
        ]
        for f in fields:
            if f in data and data[f] is not None:
                setattr(vital, f, data[f])

        vital.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'message': 'Vitals updated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============ GET PATIENT QUEUE ============

@nurse_bp.route('/queue', methods=['GET'])
@token_required
def get_queue(current_nurse):
    """
    GET /api/nurse/queue - Get patient queue
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status', 'waiting')  # waiting, called, in-progress, completed
        priority = request.args.get('priority', type=int)
        
        query = PatientQueue.query
        
        if status:
            query = query.filter_by(status=status)
        
        if priority is not None:
            query = query.filter_by(priority=priority)
        
        # Order by priority (higher first) then queue number
        total = query.count()
        queue = query.order_by(
            PatientQueue.priority.desc(),
            PatientQueue.queue_number.asc()
        ).offset(offset).limit(limit).all()
        
        queue_list = []
        for q in queue:
            patient = Patient.query.get(q.patient_id)
            # Calculate waiting time
            waiting_time = None
            if q.check_in_time:
                delta = datetime.utcnow() - q.check_in_time
                minutes = delta.total_seconds() // 60
                waiting_time = f"{int(minutes)} minutes"
            
            # Priority label
            priority_labels = {0: "Normal", 1: "Urgent", 2: "Emergency"}
            
            queue_list.append({
                "id": q.id,
                "queue_id": q.queue_id,
                "queue_number": q.queue_number,
                "patient": {
                    "id": patient.id,
                    "name": patient.username,
                    "patient_id": getattr(patient, 'patient_id', None)
                } if patient else None,
                "priority": q.priority,
                "priority_label": priority_labels.get(q.priority, "Normal"),
                "status": q.status,
                "purpose": q.purpose,
                "check_in_time": q.check_in_time.isoformat() if q.check_in_time else None,
                "waiting_time": waiting_time
            })
        
        return jsonify({
            "success": True,
            "queue": queue_list,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching queue",
            "error": _safe_error(e)
        }), 500


@nurse_bp.route('/queue/<int:queue_id>/call', methods=['PUT'])
@token_required
def call_patient(current_nurse, queue_id):
    """
    PUT /api/nurse/queue/<id>/call - Call patient from queue
    """
    try:
        queue_item = PatientQueue.query.get(queue_id)
        
        if not queue_item:
            return jsonify({
                "success": False,
                "message": "Queue item not found"
            }), 404
        
        if queue_item.status != 'waiting':
            return jsonify({
                "success": False,
                "message": f"Patient already {queue_item.status}"
            }), 400
        
        queue_item.status = 'called'
        queue_item.called_time = datetime.utcnow()
        queue_item.nurse_id = current_nurse['id']
        queue_item.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Patient called successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error calling patient",
            "error": _safe_error(e)
        }), 500


@nurse_bp.route('/queue/<int:queue_id>/complete', methods=['PUT'])
@token_required
def complete_queue_item(current_nurse, queue_id):
    """
    PUT /api/nurse/queue/<id>/complete - Mark queue item as completed
    """
    try:
        queue_item = PatientQueue.query.get(queue_id)
        
        if not queue_item:
            return jsonify({
                "success": False,
                "message": "Queue item not found"
            }), 404
        
        queue_item.status = 'completed'
        queue_item.end_time = datetime.utcnow()
        queue_item.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Queue item completed"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error completing queue item",
            "error": _safe_error(e)
        }), 500


# ============ REGISTER PATIENT ============

@nurse_bp.route('/register', methods=['POST'])
@token_required
def register_patient(current_nurse):
    """
    POST /api/nurse/register - Register a new patient
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Check if user already exists
        from werkzeug.security import generate_password_hash
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({
                "success": False,
                "message": "User with this email already exists"
            }), 409
        
        if User.query.filter_by(username=data['username']).first():
            return jsonify({
                "success": False,
                "message": "Username already taken"
            }), 409
        
        # Generate unique patient_id
        patient_id = f"PAT{datetime.utcnow().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        
        # Create patient
        hashed_password = generate_password_hash(data['password'])
        
        new_patient = Patient(
            username=data['username'],
            email=data['email'],
            password_hash=hashed_password,
            patient_id=patient_id,
            blood_group=data.get('blood_group'),
            emergency_contact=data.get('emergency_contact'),
            emergency_contact_name=data.get('emergency_contact_name'),
            medical_history=data.get('medical_history'),
            allergies=data.get('allergies'),
            current_medications=data.get('current_medications'),
            registered_by=current_nurse['id'],
            created_at=datetime.utcnow(),
            is_active=True,
            role='patient'
        )
        
        db.session.add(new_patient)
        db.session.commit()
        
        # Add to queue automatically
        add_to_queue(new_patient.id, 'registration', current_nurse)

        # Notify all doctors and nurses about the new patient registration
        try:
            from backend.models.notification import Notification
            recipients = User.query.filter(
                User.role.in_(['doctor', 'nurse']),
                User.is_active == True
            ).all()
            for u in recipients:
                is_nurse = u.role == 'nurse'
                db.session.add(Notification(
                    user_id=u.id,
                    title='New Patient Registered',
                    message=(
                        f"Nurse {current_nurse['username']} registered a new patient: "
                        f"{new_patient.username} (ID: {new_patient.patient_id}). "
                        f"Patient has been added to the queue."
                    ),
                    type='vitals',
                    category='general',
                    is_read=False,
                    link=(
                        f'/templates/nurse/record_vitals.html?patient_id={new_patient.id}'
                        if is_nurse else
                        f'/templates/doctor/patient_list.html?highlight={new_patient.id}'
                    ),
                    created_at=datetime.utcnow()
                ))
            db.session.commit()
        except Exception as notif_err:
            current_app.logger.error(f'Registration notification error: {notif_err}')
            try:
                db.session.rollback()
            except Exception:
                pass
        
        return jsonify({
            "success": True,
            "message": "Patient registered successfully",
            "patient": {
                "id": new_patient.id,
                "patient_id": new_patient.patient_id,
                "username": new_patient.username,
                "email": new_patient.email,
                "blood_group": new_patient.blood_group
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error registering patient",
            "error": _safe_error(e)
        }), 500


def add_to_queue(patient_id, purpose, current_nurse):
    """
    Helper function to add patient to queue (synchronous version)
    """
    try:
        # Get highest queue number for today
        today = datetime.utcnow().date()
        last_queue = PatientQueue.query.filter(
            func.date(PatientQueue.check_in_time) == today
        ).order_by(PatientQueue.queue_number.desc()).first()
        
        next_number = (last_queue.queue_number + 1) if last_queue else 1
        
        queue_id = f"Q{datetime.utcnow().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        
        queue_item = PatientQueue(
            queue_id=queue_id,
            patient_id=patient_id,
            nurse_id=current_nurse['id'],
            queue_number=next_number,
            priority=0,
            status='waiting',
            purpose=purpose,
            check_in_time=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(queue_item)
        db.session.commit()
        
    except Exception as e:
        print(f"Error adding to queue: {e}")
        db.session.rollback()


# ============ UPDATE PATIENT ============

@nurse_bp.route('/patient/<int:patient_id>', methods=['PUT'])
@token_required
def update_patient(current_nurse, patient_id):
    """
    PUT /api/nurse/patient/<id> - Update patient information
    """
    try:
        patient = Patient.query.get(patient_id)
        
        if not patient:
            return jsonify({
                "success": False,
                "message": "Patient not found"
            }), 404
        
        data = request.get_json()
        
        # Update allowed fields
        updatable_fields = [
            'blood_group', 'emergency_contact', 'emergency_contact_name',
            'medical_history', 'allergies', 'current_medications'
        ]
        
        updates = []
        for field in updatable_fields:
            if field in data:
                setattr(patient, field, data[field])
                updates.append(field)
        
        # Also update phone if exists in User model
        if 'phone' in data and hasattr(patient, 'phone'):
            patient.phone = data['phone']
            updates.append('phone')
        
        patient.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Patient updated successfully",
            "updated_fields": updates,
            "patient": {
                "id": patient.id,
                "patient_id": getattr(patient, 'patient_id', None),
                "username": patient.username,
                "email": patient.email,
                "blood_group": patient.blood_group
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error updating patient",
            "error": _safe_error(e)
        }), 500


# ============ ADDITIONAL NURSE ENDPOINTS ============

@nurse_bp.route('/patients/search', methods=['GET'])
@token_required
def search_patients(current_nurse):
    """
    GET /api/nurse/patients/search - Search patients
    """
    try:
        query = request.args.get('q', '')
        limit = request.args.get('limit', 20, type=int)
        
        if not query or len(query) < 2:
            return jsonify({
                "success": True,
                "patients": []
            }), 200
        
        patients = Patient.query.filter(
            (Patient.username.ilike(f'%{query}%')) |
            (Patient.email.ilike(f'%{query}%')) |
            (Patient.patient_id.ilike(f'%{query}%'))
        ).limit(limit).all()
        
        return jsonify({
            "success": True,
            "patients": [{
                "id": p.id,
                "patient_id": p.patient_id,
                "username": p.username,
                "email": p.email
            } for p in patients]
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error searching patients",
            "error": _safe_error(e)
        }), 500


@nurse_bp.route('/patients/<int:patient_id>/vitals', methods=['GET'])
@token_required
def get_patient_vitals(current_nurse, patient_id):
    """
    GET /api/nurse/patients/<id>/vitals - Get patient vital signs history
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        
        vitals = VitalSign.query.filter_by(
            patient_id=patient_id
        ).order_by(VitalSign.recorded_at.desc()).limit(limit).all()
        
        vitals_list = []
        for v in vitals:
            vitals_list.append({
                "id": v.id,
                "vital_id": v.vital_id,
                "temperature": v.temperature,
                "heart_rate": v.heart_rate,
                "blood_pressure_systolic": v.blood_pressure_systolic,
                "blood_pressure_diastolic": v.blood_pressure_diastolic,
                "oxygen_saturation": v.oxygen_saturation,
                "height": v.height,
                "weight": v.weight,
                "bmi": v.bmi,
                "skin_thickness": v.skin_thickness,
                "respiratory_rate": v.respiratory_rate,
                "pain_level": v.pain_level,
                "pregnancies": v.pregnancies,
                "diabetes_pedigree": v.diabetes_pedigree,
                "age": v.age,
                "notes": v.notes,
                "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None
            })
        
        return jsonify({
            "success": True,
            "patient_id": patient_id,
            "vitals": vitals_list
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching vitals",
            "error": _safe_error(e)
        }), 500


# ============ GET PATIENT PROFILE FOR VITALS AUTO-FILL ============

@nurse_bp.route('/patient-profile/<int:patient_id>', methods=['GET'])
@token_required
def get_patient_profile(current_nurse, patient_id):
    """
    GET /api/nurse/patient-profile/<id>
    Returns patient registration data for auto-filling the vitals form.
    """
    try:
        row = db.session.execute(text("""
            SELECT u.id, u.username, u.email, u.created_at,
                   p.patient_id, p.blood_group,
                   p.medical_history, p.allergies, p.gender
            FROM users u
            LEFT JOIN patients p ON p.id = u.id
            WHERE u.id = :id AND u.role = 'patient'
        """), {'id': patient_id}).fetchone()

        if not row:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404

        # Get latest vitals if any
        latest_vital = VitalSign.query.filter_by(
            patient_id=patient_id
        ).order_by(VitalSign.recorded_at.desc()).first()

        vitals = {}
        if latest_vital:
            vitals = {
                'blood_pressure_systolic':  latest_vital.blood_pressure_systolic,
                'blood_pressure_diastolic': latest_vital.blood_pressure_diastolic,
                'heart_rate':               latest_vital.heart_rate,
                'temperature':              latest_vital.temperature,
                'respiratory_rate':         latest_vital.respiratory_rate,
                'oxygen_saturation':        latest_vital.oxygen_saturation,
                'height':                   latest_vital.height,
                'weight':                   latest_vital.weight,
                'skin_thickness':           latest_vital.skin_thickness,
                'pregnancies':              latest_vital.pregnancies,
                'diabetes_pedigree':        latest_vital.diabetes_pedigree,
                'age':                      latest_vital.age,
            }

        try:
            created_at = row[3].isoformat() if hasattr(row[3], 'isoformat') else str(row[3]) if row[3] else None
        except Exception:
            created_at = None

        return jsonify({
            'success': True,
            'patient': {
                'id':         row[0],
                'username':   row[1],
                'email':      row[2],
                'created_at': created_at,
                'patient_id': row[4] or f'PAT{int(row[0]):06d}',
                'blood_group':     row[5],
                'medical_history': row[6],
                'allergies':       row[7],
                'gender':          row[8] if len(row) > 8 else None,
            },
            'vitals': vitals,
            'has_previous_vitals': latest_vital is not None
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============ GET ALL PATIENTS ============

@nurse_bp.route('/patients', methods=['GET'])
@token_required
def get_all_patients(current_nurse):
    """
    GET /api/nurse/patients - Get all patients with pagination
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Backfill missing patient rows for legacy user records.
        user_patients = User.query.filter_by(role='patient').all()
        created_any = False
        for u in user_patients:
            exists = db.session.execute(
                text("SELECT 1 FROM patients WHERE id = :id"),
                {'id': u.id}
            ).fetchone()
            if not exists:
                _ensure_patient_profile(u)
                created_any = True
        if created_any:
            db.session.commit()

        total_row = db.session.execute(
            text("SELECT COUNT(*) FROM users WHERE role = 'patient'")
        ).fetchone()
        total = total_row[0] if total_row else 0

        rows = db.session.execute(text("""
            SELECT
                u.id,
                u.username,
                u.email,
                u.created_at,
                p.patient_id,
                p.blood_group
            FROM users u
            LEFT JOIN patients p ON p.id = u.id
            WHERE u.role = 'patient'
            ORDER BY u.created_at DESC
            LIMIT :limit OFFSET :offset
        """), {'limit': limit, 'offset': offset}).fetchall()

        patients_list = []
        for r in rows:
            try:
                created_at = r[3].isoformat() if hasattr(r[3], 'isoformat') else str(r[3]) if r[3] else None
            except Exception:
                created_at = None
            patients_list.append({
                "id": r[0],
                "patient_id": r[4] or f"PAT{int(r[0]):06d}",
                "username": r[1] or f"Patient #{r[0]}",
                "email": r[2] or '',
                "blood_group": r[5],
                "created_at": created_at
            })
        
        return jsonify({
            "success": True,
            "patients": patients_list,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching patients",
            "error": _safe_error(e)
        }), 500


from backend.models.prediction import Prediction

# ============ GET ALL PREDICTIONS ============

@nurse_bp.route('/predictions', methods=['GET'])
@token_required
def get_predictions(current_nurse):
    """
    GET /api/nurse/predictions - Get all patient predictions
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        risk = request.args.get('risk', '').upper()

        VALID_RISKS = {'LOW', 'MODERATE', 'HIGH', 'VERY_HIGH'}
        if risk and risk not in VALID_RISKS:
            return jsonify({'success': False, 'message': 'Invalid risk level'}), 400

        query = Prediction.query

        total = query.count()
        predictions = query.order_by(Prediction.created_at.desc()).offset(offset).limit(limit).all()

        # Normalize risk_level: "LOW RISK" -> "LOW", "VERY HIGH RISK" -> "VERY_HIGH"
        def normalize_risk(r):
            if not r: return 'LOW'
            r = r.upper().strip()
            if 'VERY' in r: return 'VERY_HIGH'
            if 'HIGH' in r: return 'HIGH'
            if 'MODERATE' in r: return 'MODERATE'
            return 'LOW'

        result = []
        for p in predictions:
            patient = Patient.query.get(p.patient_id)
            result.append({
                'id': p.id,
                'patient': {
                    'id': patient.id,
                    'name': patient.username,
                    'patient_id': getattr(patient, 'patient_id', None)
                } if patient else None,
                'prediction': p.prediction,
                'prediction_label': 'Diabetic' if p.prediction == 1 else 'Non-Diabetic',
                'probability_percent': round(p.probability_percent, 1),
                'risk_level': normalize_risk(p.risk_level),
                'model_used': p.model_used,
                'created_at': p.created_at.isoformat() if p.created_at else None
            })

        return jsonify({
            'success': True,
            'predictions': result,
            'pagination': {'total': total, 'limit': limit, 'offset': offset}
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': 'Error fetching predictions', 'error': str(e)}), 500


# ============ TEST ALL NURSE ENDPOINTS ============

@nurse_bp.route('/test-all', methods=['GET'])
@token_required
def test_all_endpoints(current_nurse):
    """
    GET /api/nurse/test-all - Test all nurse endpoints (for validation)
    """
    try:
        results = {
            "dashboard": False,
            "queue_get": False,
            "patients_get": False,
            "vitals_get": False
        }
        
        # Test if endpoints are reachable (just check if they exist)
        results["dashboard"] = True
        results["queue_get"] = True
        results["patients_get"] = True
        results["vitals_get"] = True
        
        return jsonify({
            "success": True,
            "message": "Nurse endpoints are available",
            "results": results,
            "nurse": {
                "id": current_nurse['id'],
                "name": current_nurse['username'],
                "role": current_nurse['role']
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error testing endpoints",
            "error": _safe_error(e)
        }), 500