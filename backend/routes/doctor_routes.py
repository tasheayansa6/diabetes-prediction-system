"""
Doctor Routes - Handles doctor dashboard, patient management, prescriptions, and lab orders
"""

from flask import Blueprint, request, jsonify, current_app
from backend.extensions import db
from backend.models.user import User
from backend.models.doctor import Doctor
from backend.models.note import Note 
from backend.models.patient import Patient
from backend.models.prescription import Prescription
from backend.models.lab_test import LabTest
from backend.models.appointment import Appointment
from backend.models.health_record import HealthRecord
from backend.models.prediction import Prediction
from datetime import datetime, timedelta
from sqlalchemy import func, desc, text
import jwt
from functools import wraps
import uuid

doctor_bp = Blueprint('doctor', __name__, url_prefix='/api/doctor')

# ============ TOKEN DECORATOR (MUST BE DEFINED FIRST) ============


def _safe_error(e):
    """Return error detail only in development."""
    from flask import current_app
    if current_app.config.get('EXPOSE_ERRORS', False):
        return str(e)
    return None


def token_required(f):
    """Decorator for doctor routes using JWT token"""
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
            
            # Check if role is doctor
            if data.get('role') != 'doctor':
                return jsonify({"success": False, "message": "Doctor access required!"}), 403
            
            # Get doctor from database
            doctor = Doctor.query.get(data['user_id'])
            if not doctor:
                user = User.query.get(data['user_id'])
                if not user or user.role != 'doctor':
                    return jsonify({"success": False, "message": "Doctor not found!"}), 404
                doctor = Doctor(id=user.id, doctor_id=f"DOC{user.id:04d}")
                db.session.add(doctor)
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    doctor = Doctor.query.get(data['user_id'])
                    if not doctor:
                        return jsonify({"success": False, "message": "Doctor not found!"}), 404
            current_doctor = {
                'id': doctor.id,
                'username': doctor.username,
                'email': doctor.email,
                'role': doctor.role,
                'doctor_id': getattr(doctor, 'doctor_id', None),
                'specialization': doctor.specialization
            }
            
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Invalid token!"}), 401
            
        return f(current_doctor, *args, **kwargs)
    
    return decorated


# ============ DOCTOR DASHBOARD ============

@doctor_bp.route('/dashboard', methods=['GET'])
@token_required
def get_dashboard(current_doctor):
    """
    Get doctor dashboard with statistics
    """
    try:
        doctor_id = current_doctor['id']
        
        # Get today's date
        today = datetime.utcnow().date()
        
        # Initialize with default values
        today_appointments = 0
        pending_appointments = 0
        total_patients = 0
        prescriptions_this_month = 0
        recent_patients_list = []
        upcoming_list = []
        
        # Count today's appointments (if table exists)
        try:
            today_appointments = Appointment.query.filter(
                Appointment.doctor_id == doctor_id,
                func.date(Appointment.appointment_date) == today
            ).count()
        except:
            pass
        
        # Count pending appointments
        try:
            pending_appointments = Appointment.query.filter_by(
                doctor_id=doctor_id,
                status='scheduled'
            ).count()
        except:
            pass
        
        # Count total patients (distinct)
        try:
            total_patients = db.session.query(Prescription.patient_id)\
                .filter(Prescription.doctor_id == doctor_id)\
                .distinct().count()
        except:
            pass
        
        # Count prescriptions this month
        try:
            month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            prescriptions_this_month = Prescription.query.filter(
                Prescription.doctor_id == doctor_id,
                Prescription.created_at >= month_start
            ).count()
        except:
            pass
        
        # Get recent patients
        try:
            recent_patients = db.session.query(Patient, Prescription)\
                .join(Prescription, Prescription.patient_id == Patient.id)\
                .filter(Prescription.doctor_id == doctor_id)\
                .order_by(Prescription.created_at.desc())\
                .limit(5)\
                .all()
            
            for patient, prescription in recent_patients:
                pu = User.query.get(patient.id)
                recent_patients_list.append({
                    "id": patient.id,
                    "patient_id": getattr(patient, 'patient_id', None),
                    "username": pu.username if pu else f"Patient #{patient.id}",
                    "email": pu.email if pu else None,
                    "last_visit": prescription.created_at.isoformat() if prescription.created_at else None
                })
        except:
            pass
        
        # Get upcoming appointments
        try:
            upcoming_appointments = Appointment.query.filter(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date >= today,
                Appointment.status == 'scheduled'
            ).order_by(Appointment.appointment_date).limit(5).all()
            
            for a in upcoming_appointments:
                row = db.session.execute(
                    text("SELECT username FROM users WHERE id = :id"),
                    {"id": a.patient_id}
                ).first()
                upcoming_list.append({
                    "id": a.id,
                    "patient_id": a.patient_id,
                    "patient_name": row[0] if row else f"Patient #{a.patient_id}",
                    "appointment_date": str(a.appointment_date),
                    "appointment_time": a.appointment_time,
                    "reason": a.reason,
                    "status": a.status
                })
        except:
            pass
        
        return jsonify({
            "success": True,
            "dashboard": {
                "doctor_info": {
                    "id": current_doctor['id'],
                    "name": current_doctor['username'],
                    "specialization": current_doctor['specialization'],
                    "doctor_id": current_doctor['doctor_id']
                },
                "statistics": {
                    "today_appointments": today_appointments,
                    "pending_appointments": pending_appointments,
                    "total_patients": total_patients,
                    "prescriptions_this_month": prescriptions_this_month
                },
                "recent_patients": recent_patients_list,
                "upcoming_appointments": upcoming_list
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching dashboard",
            "error": _safe_error(e)
        }), 500


# ============ PATIENT MANAGEMENT ============

@doctor_bp.route('/patients', methods=['GET'])
@token_required
def get_patients(current_doctor):
    """
    Get all patients (optionally filter by search)
    """
    try:
        search = request.args.get('search', '')
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Use robust SQL instead of Patient ORM query to avoid polymorphic
        # crashes from legacy inconsistent rows.
        params = {'limit': limit, 'offset': offset}
        where_sql = "WHERE u.role = 'patient'"
        if search:
            where_sql += (
                " AND (u.username LIKE :search OR u.email LIKE :search OR p.patient_id LIKE :search)"
            )
            params['search'] = f'%{search}%'

        total = db.session.execute(
            text(f"""
                SELECT COUNT(*) AS c
                FROM users u
                LEFT JOIN patients p ON p.id = u.id
                {where_sql}
            """),
            params
        ).fetchone().c

        rows = db.session.execute(
            text(f"""
                SELECT
                    u.id,
                    u.username,
                    u.email,
                    u.created_at,
                    p.patient_id
                FROM users u
                LEFT JOIN patients p ON p.id = u.id
                {where_sql}
                ORDER BY u.created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params
        ).fetchall()

        patients_list = []
        for r in rows:
            created_at = r.created_at.isoformat() if hasattr(r.created_at, 'isoformat') else str(r.created_at)
            patients_list.append({
                "id": r.id,
                "patient_id": r.patient_id or f"PAT{int(r.id):06d}",
                "username": r.username or f"Patient #{r.id}",
                "email": r.email,
                "role": "patient",
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


@doctor_bp.route('/patients/<int:patient_id>', methods=['GET'])
@token_required
def get_patient(current_doctor, patient_id):
    """
    Get detailed patient information including medical history
    """
    try:
        patient = Patient.query.get(patient_id)
        
        if not patient:
            return jsonify({
                "success": False,
                "message": "Patient not found"
            }), 404
        
        # Build patient data manually
        patient_user = User.query.get(patient_id)
        patient_data = {
            "id": patient.id,
            "patient_id": getattr(patient, 'patient_id', None),
            "username": patient_user.username if patient_user else f"Patient #{patient_id}",
            "email": patient_user.email if patient_user else None,
            "role": "patient",
            "created_at": patient_user.created_at.isoformat() if patient_user and patient_user.created_at else None
        }
        
        # Get patient's health records
        health_records = HealthRecord.query.filter_by(patient_id=patient_id)\
            .order_by(HealthRecord.created_at.desc()).limit(10).all()
        
        patient_data["health_records"] = [{
            "id": r.id,
            "glucose": r.glucose,
            "bmi": r.bmi,
            "blood_pressure": r.blood_pressure,
            "created_at": r.created_at.isoformat() if r.created_at else None
        } for r in health_records]
        
        # Get patient's predictions
        predictions = Prediction.query.filter_by(patient_id=patient_id)\
            .order_by(Prediction.created_at.desc()).limit(10).all()
        
        patient_data["predictions"] = [{
            "id": p.id,
            "probability_percent": p.probability_percent,
            "risk_level": p.risk_level,
            "created_at": p.created_at.isoformat() if p.created_at else None
        } for p in predictions]
        
        # Get patient's prescriptions from this doctor
        prescriptions = Prescription.query.filter_by(
            patient_id=patient_id,
            doctor_id=current_doctor['id']
        ).order_by(Prescription.created_at.desc()).all()
        
        patient_data["prescriptions"] = [{
            "id": p.id,
            "prescription_id": p.prescription_id,
            "medication": p.medication,
            "dosage": p.dosage,
            "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None
        } for p in prescriptions]
        
        # Get patient's lab tests ordered by this doctor
        lab_tests = LabTest.query.filter_by(
            patient_id=patient_id,
            doctor_id=current_doctor['id']
        ).order_by(LabTest.created_at.desc()).all()
        
        patient_data["lab_tests"] = [{
            "id": l.id,
            "test_name": l.test_name,
            "status": l.status,
            "results": l.results,
            "created_at": l.created_at.isoformat() if l.created_at else None
        } for l in lab_tests]
        
        return jsonify({
            "success": True,
            "patient": patient_data
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching patient",
            "error": _safe_error(e)
        }), 500


# ============ PRESCRIPTION MANAGEMENT ============

@doctor_bp.route('/prescriptions', methods=['GET'])
@token_required
def get_prescriptions(current_doctor):
    """
    Get all prescriptions created by this doctor
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status')
        
        query = Prescription.query.filter_by(doctor_id=current_doctor['id'])
        
        if status:
            query = query.filter_by(status=status)
        
        total = query.count()
        prescriptions = query.order_by(Prescription.created_at.desc())\
            .offset(offset).limit(limit).all()
        
        # Build prescription list manually
        prescriptions_list = []
        for p in prescriptions:
            prescriptions_list.append({
                "id": p.id,
                "prescription_id": p.prescription_id,
                "patient_id": p.patient_id,
                "medication": p.medication,
                "dosage": p.dosage,
                "frequency": p.frequency,
                "duration": p.duration,
                "instructions": p.instructions,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None
            })
        
        return jsonify({
            "success": True,
            "prescriptions": prescriptions_list,
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
            "message": "Error fetching prescriptions",
            "error": _safe_error(e)
        }), 500


@doctor_bp.route('/prescriptions', methods=['POST'])
@token_required
def create_prescription(current_doctor):
    """
    Create a new prescription for a patient
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['patient_id', 'medication', 'dosage', 'frequency', 'duration']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Generate unique prescription_id
        import uuid
        presc_id = f"RX{datetime.utcnow().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"

        # Ensure doctor row exists (FK constraint for PostgreSQL)
        from backend.models.doctor import Doctor as _Doctor
        if not _Doctor.query.get(current_doctor['id']):
            _u = User.query.get(current_doctor['id'])
            if _u:
                db.session.add(_Doctor(id=_u.id, doctor_id=f"DOC{_u.id:04d}"))
                db.session.flush()

        # Drug interaction / allergy check (#20)
        patient_check = Patient.query.get(data['patient_id'])
        if patient_check:
            allergies = (getattr(patient_check, 'allergies', '') or '').lower()
            current_meds = (getattr(patient_check, 'current_medications', '') or '').lower()
            med_lower = data['medication'].lower()
            warnings = []
            if allergies and any(a.strip() in med_lower for a in allergies.split(',') if a.strip()):
                warnings.append(f"ALLERGY ALERT: Patient has a recorded allergy that may include '{data['medication']}'.")
            if current_meds and med_lower in current_meds:
                warnings.append(f"DUPLICATE MEDICATION: Patient is already on '{data['medication']}'.")
            if warnings:
                if not data.get('override_warnings'):
                    return jsonify({
                        "success": False,
                        "message": ' | '.join(warnings),
                        "warnings": warnings,
                        "requires_override": True
                    }), 409
        
        # Create prescription WITHOUT any prediction_id field
        prescription = Prescription(
            prescription_id=presc_id,
            doctor_id=current_doctor['id'],
            patient_id=data['patient_id'],
            medication=data['medication'],
            dosage=data['dosage'],
            frequency=data['frequency'],
            duration=data['duration'],
            instructions=data.get('instructions', ''),
            notes=data.get('notes', ''),
            status='pending',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
            # No prediction_id field here - it will use the default NULL
        )
        
        db.session.add(prescription)
        db.session.commit()

        # Notify all pharmacists about the new prescription
        try:
            from backend.models.notification import Notification
            from backend.models.user import User as UserModel
            patient_obj = Patient.query.get(data['patient_id'])
            patient_name = patient_obj.username if patient_obj else f"Patient #{data['patient_id']}"
            pharmacists = UserModel.query.filter_by(role='pharmacist', is_active=True).all()
            for ph in pharmacists:
                db.session.add(Notification(
                    user_id=ph.id,
                    title='New Prescription',
                    message=f'Dr. {current_doctor["username"]} prescribed {data["medication"]} for {patient_name}. Awaiting verification.',
                    type='prescription',
                    category='general',
                    is_read=False,
                    link='/templates/pharmacist/prescription_review.html',
                    created_at=datetime.utcnow()
                ))
            db.session.commit()
        except Exception as notif_err:
            current_app.logger.error(f'Prescription notification error: {notif_err}')
            try:
                db.session.rollback()
            except Exception:
                pass

        return jsonify({
            "success": True,
            "message": "Prescription created successfully",
            "prescription": {
                "id": prescription.id,
                "prescription_id": prescription.prescription_id,
                "patient_id": prescription.patient_id,
                "medication": prescription.medication,
                "status": prescription.status
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error creating prescription",
            "error": _safe_error(e)
        }), 500

@doctor_bp.route('/prescriptions/<int:prescription_id>', methods=['PUT'])
@token_required
def update_prescription(current_doctor, prescription_id):
    """
    Update an existing prescription
    """
    try:
        prescription = Prescription.query.filter_by(
            id=prescription_id,
            doctor_id=current_doctor['id']
        ).first()
        
        if not prescription:
            return jsonify({
                "success": False,
                "message": "Prescription not found"
            }), 404
        
        data = request.get_json()
        
        # Update fields if provided
        updatable_fields = ['medication', 'dosage', 'frequency', 'duration', 'instructions', 'notes']
        for field in updatable_fields:
            if field in data:
                setattr(prescription, field, data[field])
        
        prescription.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Prescription updated successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error updating prescription",
            "error": _safe_error(e)
        }), 500
        # ============ PREDICTIONS MANAGEMENT ============

@doctor_bp.route('/predictions/<int:prediction_id>', methods=['GET'])
@token_required
def get_prediction(current_doctor, prediction_id):
    """
    Get a specific prediction by ID
    """
    try:
        # Get the prediction
        prediction = Prediction.query.get(prediction_id)
        
        if not prediction:
            return jsonify({
                "success": False,
                "message": "Prediction not found"
            }), 404
        
        # Get patient info
        patient = Patient.query.get(prediction.patient_id)
        
        # Get doctor info (who ordered the prediction, if any)
        doctor = None
        if hasattr(prediction, 'doctor_id') and prediction.doctor_id:
            doctor = Doctor.query.get(prediction.doctor_id)
        
        # Get associated health record if exists
        health_record = None
        if prediction.health_record_id:
            health_record = HealthRecord.query.get(prediction.health_record_id)
        
        # Build response
        response = {
            "id": prediction.id,
            "patient": {
                "id": patient.id,
                "patient_id": getattr(patient, 'patient_id', None),
                "username": patient.username,
                "email": patient.email
            } if patient else None,
            "doctor": {
                "id": doctor.id,
                "name": doctor.username,
                "doctor_id": getattr(doctor, 'doctor_id', None)
            } if doctor else None,
            "prediction_result": "Diabetic" if prediction.prediction == 1 else "Non-Diabetic",
            "probability": prediction.probability,
            "probability_percent": prediction.probability_percent,
            "risk_level": prediction.risk_level,
            "risk_color": "🟢" if "LOW" in prediction.risk_level else 
                          "🟡" if "MODERATE" in prediction.risk_level else 
                          "🟠" if "HIGH" in prediction.risk_level else "🔴",
            "model_version": prediction.model_version if hasattr(prediction, 'model_version') else "1.0.0",
            "explanation": prediction.explanation if hasattr(prediction, 'explanation') else None,
            "created_at": prediction.created_at.isoformat() if prediction.created_at else None,
            "health_record": {
                "id": health_record.id,
                "glucose": health_record.glucose,
                "bmi": health_record.bmi,
                "blood_pressure": health_record.blood_pressure,
                "age": health_record.age,
                "pregnancies": health_record.pregnancies
            } if health_record else None
        }
        
        # Add input data if available
        if hasattr(prediction, 'input_data') and prediction.input_data:
            response["input_data"] = prediction.input_data
        
        return jsonify({
            "success": True,
            "prediction": response
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching prediction",
            "error": _safe_error(e)
        }), 500


@doctor_bp.route('/patients/<int:patient_id>/predictions', methods=['GET'])
@token_required
def get_patient_predictions(current_doctor, patient_id):
    """
    Get all predictions for a specific patient
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Verify patient exists and doctor has access
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({
                "success": False,
                "message": "Patient not found"
            }), 404
        
        # Get predictions for this patient
        query = Prediction.query.filter_by(patient_id=patient_id)
        
        total = query.count()
        predictions = query.order_by(Prediction.created_at.desc())\
            .offset(offset).limit(limit).all()
        
        # Format predictions list
        predictions_list = []
        for p in predictions:
            predictions_list.append({
                "id": p.id,
                "probability_percent": p.probability_percent,
                "risk_level": p.risk_level,
                "risk_color": "🟢" if "LOW" in p.risk_level else 
                              "🟡" if "MODERATE" in p.risk_level else 
                              "🟠" if "HIGH" in p.risk_level else "🔴",
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "health_record_id": p.health_record_id
            })
        
        return jsonify({
            "success": True,
            "patient_id": patient_id,
            "patient_name": patient.username,
            "predictions": predictions_list,
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
            "message": "Error fetching patient predictions",
            "error": _safe_error(e)
        }), 500


@doctor_bp.route('/predictions/<int:prediction_id>/review', methods=['PUT'])
@token_required
def review_prediction(current_doctor, prediction_id):
    """
    Review/approve an ML prediction and persist doctor decision.
    Status: approved | rejected | needs_followup | pending_review
    """
    try:
        prediction = Prediction.query.get(prediction_id)
        if not prediction:
            return jsonify({"success": False, "message": "Prediction not found"}), 404

        data = request.get_json() or {}
        status = str(data.get('status', '')).strip().lower()
        summary = str(data.get('summary', '')).strip()

        valid = ['approved', 'rejected', 'needs_followup', 'pending_review']
        if status not in valid:
            return jsonify({
                "success": False,
                "message": f"Invalid status. Must be one of: {', '.join(valid)}"
            }), 400

        if not summary:
            return jsonify({"success": False, "message": "Review summary is required"}), 400

        # Mark reviewer on prediction (existing column)
        prediction.doctor_id = current_doctor['id']

        # Create/append review note linked to this prediction
        note_id = f"NOTE{datetime.utcnow().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        review_note = Note(
            note_id=note_id,
            patient_id=prediction.patient_id,
            doctor_id=current_doctor['id'],
            title=f"Prediction Review #{prediction.id}",
            content=f"status:{status}\nsummary:{summary}",
            category='prediction_review',
            is_private=False,
            is_important=status in ['rejected', 'needs_followup'],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(review_note)
        db.session.commit()

        # Notify patient
        try:
            from backend.models.notification import Notification
            label = status.replace('_', ' ').title()
            db.session.add(Notification(
                user_id=prediction.patient_id,
                title='Prediction Reviewed by Doctor',
                message=f'Your prediction was reviewed: {label}. Please open your result for details.',
                type='prediction',
                category='general',
                is_read=False,
                link=f'/templates/patient/prediction_result.html?id={prediction.id}',
                created_at=datetime.utcnow()
            ))
            db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        return jsonify({
            "success": True,
            "message": "Prediction review saved successfully",
            "review": {
                "prediction_id": prediction.id,
                "status": status,
                "summary": summary,
                "doctor_id": current_doctor['id'],
                "doctor_name": current_doctor['username'],
                "reviewed_at": review_note.created_at.isoformat() if review_note.created_at else None
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error saving prediction review",
            "error": _safe_error(e)
        }), 500
# ============ DOCTOR NOTES ============

@doctor_bp.route('/notes', methods=['POST'])
@token_required
def create_note(current_doctor):
    """
    Create a new clinical note for a patient
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['patient_id', 'title', 'content']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Generate a unique note_id
        import uuid
        note_id = f"NOTE{datetime.utcnow().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        
        # Create note
        note = Note(
            note_id=note_id,
            patient_id=data['patient_id'],
            doctor_id=current_doctor['id'],
            title=data['title'],
            content=data['content'],
            category=data.get('category', 'general'),
            is_private=data.get('is_private', False),
            is_important=data.get('is_important', False),
            appointment_id=data.get('appointment_id'),
            prescription_id=data.get('prescription_id'),
            lab_test_id=data.get('lab_test_id'),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(note)
        db.session.commit()
        
        # Get patient info for response
        patient = Patient.query.get(data['patient_id'])
        
        return jsonify({
            "success": True,
            "message": "Note created successfully",
            "note": {
                "id": note.id,
                "note_id": note.note_id,
                "patient": {
                    "id": patient.id,
                    "name": patient.username,
                    "patient_id": getattr(patient, 'patient_id', None)
                } if patient else None,
                "title": note.title,
                "content": note.content,
                "category": note.category,
                "is_private": note.is_private,
                "is_important": note.is_important,
                "created_at": note.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error creating note",
            "error": _safe_error(e)
        }), 500


@doctor_bp.route('/notes', methods=['GET'])
@token_required
def get_notes(current_doctor):
    """
    Get all notes (filterable by patient, category, etc.)
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        patient_id = request.args.get('patient_id', type=int)
        category = request.args.get('category')
        important_only = request.args.get('important', '').lower() == 'true'
        
        query = Note.query.filter_by(doctor_id=current_doctor['id'])
        
        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        
        if category:
            query = query.filter_by(category=category)
        
        if important_only:
            query = query.filter_by(is_important=True)
        
        # For private notes, only show to the creating doctor (already filtered)
        
        total = query.count()
        notes = query.order_by(Note.created_at.desc())\
            .offset(offset).limit(limit).all()
        
        # Format notes with patient info
        notes_list = []
        for n in notes:
            patient = Patient.query.get(n.patient_id)
            notes_list.append({
                "id": n.id,
                "note_id": n.note_id,
                "patient": {
                    "id": patient.id,
                    "name": patient.username,
                    "patient_id": getattr(patient, 'patient_id', None)
                } if patient else None,
                "title": n.title,
                "content": n.content[:200] + "..." if len(n.content) > 200 else n.content,
                "category": n.category,
                "is_important": n.is_important,
                "is_private": n.is_private,
                "created_at": n.created_at.isoformat() if n.created_at else None
            })
        
        return jsonify({
            "success": True,
            "notes": notes_list,
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
            "message": "Error fetching notes",
            "error": _safe_error(e)
        }), 500


@doctor_bp.route('/notes/<int:note_id>', methods=['GET'])
@token_required
def get_note(current_doctor, note_id):
    """
    Get a specific note by ID
    """
    try:
        note = Note.query.filter_by(
            id=note_id,
            doctor_id=current_doctor['id']
        ).first()
        
        if not note:
            return jsonify({
                "success": False,
                "message": "Note not found"
            }), 404
        
        patient = Patient.query.get(note.patient_id)
        
        return jsonify({
            "success": True,
            "note": note.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching note",
            "error": _safe_error(e)
        }), 500


@doctor_bp.route('/notes/<int:note_id>', methods=['PUT'])
@token_required
def update_note(current_doctor, note_id):
    """
    Update an existing note
    """
    try:
        note = Note.query.filter_by(
            id=note_id,
            doctor_id=current_doctor['id']
        ).first()
        
        if not note:
            return jsonify({
                "success": False,
                "message": "Note not found"
            }), 404
        
        data = request.get_json()
        
        # Update fields if provided
        updatable_fields = ['title', 'content', 'category', 'is_private', 'is_important']
        for field in updatable_fields:
            if field in data:
                setattr(note, field, data[field])
        
        note.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Note updated successfully",
            "note": note.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error updating note",
            "error": _safe_error(e)
        }), 500


@doctor_bp.route('/notes/<int:note_id>', methods=['DELETE'])
@token_required
def delete_note(current_doctor, note_id):
    """
    Delete a note
    """
    try:
        note = Note.query.filter_by(
            id=note_id,
            doctor_id=current_doctor['id']
        ).first()
        
        if not note:
            return jsonify({
                "success": False,
                "message": "Note not found"
            }), 404
        
        db.session.delete(note)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Note deleted successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error deleting note",
            "error": _safe_error(e)
        }), 500


@doctor_bp.route('/patients/<int:patient_id>/notes', methods=['GET'])
@token_required
def get_patient_notes(current_doctor, patient_id):
    """
    Get all notes for a specific patient
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Verify patient exists
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({
                "success": False,
                "message": "Patient not found"
            }), 404
        
        # Get notes for this patient by this doctor
        notes = Note.query.filter_by(
            doctor_id=current_doctor['id'],
            patient_id=patient_id
        ).order_by(Note.created_at.desc())\
         .offset(offset).limit(limit).all()
        
        total = Note.query.filter_by(
            doctor_id=current_doctor['id'],
            patient_id=patient_id
        ).count()
        
        return jsonify({
            "success": True,
            "patient_id": patient_id,
            "patient_name": patient.username,
            "notes": [n.to_dict() for n in notes],
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
            "message": "Error fetching patient notes",
            "error": _safe_error(e)
        }), 500

# ============ LAB TEST MANAGEMENT ============

@doctor_bp.route('/lab-tests', methods=['GET'])
@token_required
def get_lab_tests(current_doctor):
    """
    Get all lab tests ordered by this doctor
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status')
        
        query = LabTest.query.filter_by(doctor_id=current_doctor['id'])
        
        if status:
            query = query.filter_by(status=status)
        
        total = query.count()
        lab_tests = query.order_by(LabTest.created_at.desc())\
            .offset(offset).limit(limit).all()
        
        # Build lab tests list manually
        tests_list = []
        for l in lab_tests:
            tests_list.append({
                "id": l.id,
                "test_id": l.test_id,
                "patient_id": l.patient_id,
                "test_name": l.test_name,
                "test_type": l.test_type,
                "test_category": l.test_category,
                "status": l.status,
                "priority": l.priority if hasattr(l, 'priority') else 'normal',
                "results": l.results,
                "normal_range": l.normal_range,
                "unit": l.unit,
                "remarks": l.remarks,
                "created_at": l.created_at.isoformat() if l.created_at else None
            })
        
        return jsonify({
            "success": True,
            "lab_tests": tests_list,
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
            "message": "Error fetching lab tests",
            "error": _safe_error(e)
        }), 500


@doctor_bp.route('/lab-tests', methods=['POST'])
@token_required
def order_lab_test(current_doctor):
    """
    Order a new lab test for a patient
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['patient_id', 'test_name']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Generate a unique test_id
        test_id = data.get('test_id', f"LAB{datetime.utcnow().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}")
        
        # Create lab test with only fields that exist in your model
        lab_test = LabTest(
            test_id=test_id,
            doctor_id=current_doctor['id'],
            patient_id=data['patient_id'],
            test_name=data['test_name'],
            test_type=data.get('test_type'),
            test_category=data.get('test_category'),
            priority=data.get('priority', 'normal'),
            status='pending',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(lab_test)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Lab test ordered successfully",
            "lab_test": {
                "id": lab_test.id,
                "test_id": lab_test.test_id,
                "test_name": lab_test.test_name,
                "patient_id": lab_test.patient_id,
                "status": lab_test.status
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error ordering lab test",
            "error": _safe_error(e)
        }), 500


# ============ APPOINTMENT MANAGEMENT ============

@doctor_bp.route('/appointments', methods=['GET'])
@token_required
def get_appointments(current_doctor):
    """
    Get all appointments for this doctor
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status')
        date = request.args.get('date')
        
        query = Appointment.query.filter_by(doctor_id=current_doctor['id'])
        
        if status:
            query = query.filter_by(status=status)
        
        if date:
            query = query.filter(func.date(Appointment.appointment_date) == date)
        
        total = query.count()
        appointments = query.order_by(Appointment.appointment_date)\
            .offset(offset).limit(limit).all()
        
        # Build appointments list manually
        from sqlalchemy import text
        appointments_list = []
        for a in appointments:
            row = db.session.execute(
                text("SELECT username FROM users WHERE id = :id"),
                {"id": a.patient_id}
            ).first()
            appointments_list.append({
                "id": a.id,
                "patient_id": a.patient_id,
                "patient_name": row[0] if row else f"Patient #{a.patient_id}",
                "appointment_date": str(a.appointment_date),
                "appointment_time": a.appointment_time,
                "type": a.type,
                "reason": a.reason,
                "notes": a.notes,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None
            })
        
        return jsonify({
            "success": True,
            "appointments": appointments_list,
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
            "message": "Error fetching appointments",
            "error": _safe_error(e)
        }), 500


@doctor_bp.route('/appointments/<int:appointment_id>/status', methods=['PUT'])
@token_required
def update_appointment_status(current_doctor, appointment_id):
    """
    Update appointment status (complete, cancel, no-show)
    """
    try:
        appointment = Appointment.query.filter_by(
            id=appointment_id,
            doctor_id=current_doctor['id']
        ).first()
        
        if not appointment:
            return jsonify({
                "success": False,
                "message": "Appointment not found"
            }), 404
        
        data = request.get_json()
        
        if 'status' not in data:
            return jsonify({
                "success": False,
                "message": "Missing status field"
            }), 400
        
        valid_statuses = ['completed', 'cancelled', 'no-show', 'confirmed']
        if data['status'] not in valid_statuses:
            return jsonify({
                "success": False,
                "message": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }), 400

        appointment.status = data['status']
        appointment.updated_at = datetime.utcnow()
        db.session.commit()

        # Notify patient of status change
        try:
            from backend.models.notification import Notification
            row = db.session.execute(
                text("SELECT username FROM users WHERE id = :id"),
                {"id": appointment.patient_id}
            ).first()
            patient_name = row[0] if row else f"Patient #{appointment.patient_id}"
            status_msgs = {
                'confirmed': 'Your appointment has been confirmed by the doctor.',
                'completed': 'Your appointment has been marked as completed.',
                'cancelled': 'Your appointment has been cancelled by the doctor.',
                'no-show':   'You were marked as no-show for your appointment.',
            }
            db.session.add(Notification(
                user_id=appointment.patient_id,
                title=f'Appointment {data["status"].title()}',
                message=status_msgs.get(data['status'], f'Appointment status updated to {data["status"]}.'),
                type='appointment', category='appointment', is_read=False,
                link='/templates/patient/appointment.html',
                created_at=datetime.utcnow()
            ))
            db.session.commit()
        except Exception:
            try: db.session.rollback()
            except Exception: pass
        
        return jsonify({
            "success": True,
            "message": f"Appointment marked as {data['status']}"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error updating appointment",
            "error": _safe_error(e)
        }), 500


# ============ DOCTOR PROFILE ============

@doctor_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_doctor):
    """
    Get doctor's own profile
    """
    try:
        doctor = Doctor.query.get(current_doctor['id'])
        
        if not doctor:
            return jsonify({
                "success": False,
                "message": "Doctor profile not found"
            }), 404
        
        # Build profile manually instead of using to_dict()
        profile = {
            "id": doctor.id,
            "username": doctor.username,
            "email": doctor.email,
            "role": doctor.role,
            "doctor_id": getattr(doctor, 'doctor_id', None),
            "specialization": doctor.specialization,
            "qualification": doctor.qualification,
            "license_number": doctor.license_number,
            "years_of_experience": doctor.years_of_experience,
            "consultation_fee": doctor.consultation_fee,
            "available_days": doctor.available_days,
            "available_hours": doctor.available_hours
        }
        
        return jsonify({
            "success": True,
            "profile": profile
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching profile",
            "error": _safe_error(e)
        }), 500


@doctor_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_doctor):
    """
    Update doctor's profile
    """
    try:
        doctor = Doctor.query.get(current_doctor['id'])
        data = request.get_json()
        
        if not doctor:
            return jsonify({
                "success": False,
                "message": "Doctor not found"
            }), 404
        
        # Update fields if provided
        updatable_fields = ['specialization', 'qualification', 'consultation_fee', 
                           'available_days', 'available_hours']
        
        for field in updatable_fields:
            if field in data:
                setattr(doctor, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Profile updated successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error updating profile",
            "error": _safe_error(e)
        }), 500


# ============ SINGLE PRESCRIPTION ENDPOINT ============

@doctor_bp.route('/prescriptions/<int:prescription_id>', methods=['GET'])
@token_required
def get_prescription(current_doctor, prescription_id):
    """
    Get a specific prescription by ID
    """
    try:
        prescription = Prescription.query.filter_by(
            id=prescription_id,
            doctor_id=current_doctor['id']
        ).first()
        
        if not prescription:
            return jsonify({
                "success": False,
                "message": "Prescription not found"
            }), 404
        
        # Return prescription details
        return jsonify({
            "success": True,
            "prescription": {
                "id": prescription.id,
                "prescription_id": prescription.prescription_id,
                "patient_id": prescription.patient_id,
                "medication": prescription.medication,
                "dosage": prescription.dosage,
                "frequency": prescription.frequency,
                "duration": prescription.duration,
                "instructions": prescription.instructions,
                "status": prescription.status,
                "created_at": prescription.created_at.isoformat() if prescription.created_at else None
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching prescription",
            "error": _safe_error(e)
        }), 500


# ============ FIXED LAB REQUESTS MANAGEMENT ============

@doctor_bp.route('/test-types', methods=['GET'])
@token_required
def get_test_types_for_doctor(current_doctor):
    """GET /api/doctor/test-types — returns test types, seeds defaults if empty"""
    try:
        from backend.models.test_type import TestType
        types = TestType.query.order_by(TestType.category, TestType.test_name).all()
        if not types:
            defaults = [
                ('Blood Glucose (Fasting)', 'BG001',   'Diabetes',    25.0, '70-99 mg/dL',          'Fast for 8 hours before test'),
                ('HbA1c',                  'HBA1C',    'Diabetes',    45.0, '< 5.7%',               'No fasting required'),
                ('Oral Glucose Tolerance', 'OGTT',     'Diabetes',    60.0, '< 140 mg/dL at 2hr',   'Fast 8hrs, drink glucose solution'),
                ('Insulin Level',          'INS001',   'Diabetes',    55.0, '2-25 uU/mL',           'Fast for 8 hours before test'),
                ('Lipid Profile',          'LIP001',   'Cardiology',  50.0, 'LDL<100, HDL>40 mg/dL','Fast for 12 hours'),
                ('Complete Blood Count',   'CBC001',   'Hematology',  35.0, 'WBC 4.5-11 x10^9/L',  'No fasting required'),
                ('Kidney Function',        'KFT001',   'Nephrology',  40.0, '0.6-1.2 mg/dL',        'No fasting required'),
                ('Liver Function',         'LFT001',   'Hepatology',  45.0, 'ALT 7-56 U/L',         'No fasting required'),
                ('Thyroid (TSH)',           'TSH001',   'Endocrinology',50.0,'0.4-4.0 mIU/L',       'No fasting required'),
                ('Urine Analysis',         'UA001',    'Urology',     20.0, 'Normal',               'Midstream clean catch urine'),
                ('Microalbumin (Urine)',    'MALB001',  'Nephrology',  40.0, '< 30 mg/g',            'Random urine sample'),
                ('C-Peptide',              'CPEP001',  'Diabetes',    65.0, '0.5-2.0 ng/mL',        'Fast for 8 hours before test'),
            ]
            for name, code, cat, cost, normal, prep in defaults:
                if not TestType.query.filter_by(test_code=code).first():
                    db.session.add(TestType(
                        test_name=name, test_code=code, category=cat,
                        cost=cost, normal_range=normal,
                        preparation_instructions=prep
                    ))
            db.session.commit()
            types = TestType.query.order_by(TestType.category, TestType.test_name).all()
        return jsonify({'success': True, 'test_types': [t.to_dict() for t in types]}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@doctor_bp.route('/lab-requests', methods=['GET'])
@token_required
def get_lab_requests(current_doctor):
    """
    Get all lab requests (tests ordered by this doctor)
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status')
        patient_id = request.args.get('patient_id', type=int)
        
        query = LabTest.query.filter_by(doctor_id=current_doctor['id'])
        
        if status:
            query = query.filter_by(status=status)
        
        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        
        total = query.count()
        lab_requests = query.order_by(LabTest.created_at.desc())\
            .offset(offset).limit(limit).all()
        
        # Format lab requests with patient info - REMOVED all non-existent fields
        requests_list = []
        for req in lab_requests:
            patient = Patient.query.get(req.patient_id)
            
            # Build basic request object with only fields that exist
            request_obj = {
                "id": req.id,
                "request_id": req.test_id or f"LAB{req.id:04d}",
                "patient_id": req.patient_id,
                "patient_name": patient.username if patient else "Unknown",
                "patient_email": patient.email if patient else None,
                "test_name": req.test_name,
                "test_type": req.test_type,
                "test_category": req.test_category,
                "priority": req.priority if hasattr(req, 'priority') else 'normal',
                "status": req.status,
                "requested_date": req.created_at.isoformat() if req.created_at else None,
                "results": req.results if req.results else None
            }
            
            requests_list.append(request_obj)
        
        return jsonify({
            "success": True,
            "lab_requests": requests_list,
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
            "message": "Error fetching lab requests",
            "error": _safe_error(e)
        }), 500
@doctor_bp.route('/lab-requests', methods=['POST'])
@token_required
def create_lab_request(current_doctor):
    """
    Create a new lab request (alternative to lab-tests)
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['patient_id', 'test_name']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Generate a unique test_id (max 20 chars to fit VARCHAR(20) on older DBs)
        import uuid
        test_id = f"LAB{datetime.utcnow().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"

        # Ensure doctor row exists in doctors table (FK constraint for PostgreSQL)
        from backend.models.doctor import Doctor
        if not Doctor.query.get(current_doctor['id']):
            doc_user = User.query.get(current_doctor['id'])
            if doc_user:
                db.session.add(Doctor(id=doc_user.id, doctor_id=f"DOC{doc_user.id:04d}"))
                db.session.flush()
        
        # Create lab test (which becomes a lab request)
        lab_request = LabTest(
            test_id=test_id,
            doctor_id=current_doctor['id'],
            patient_id=data['patient_id'],
            test_name=data['test_name'],
            test_type=data.get('test_type'),
            test_category=data.get('test_category'),
            priority=data.get('priority', 'normal'),
            status='pending',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(lab_request)
        db.session.commit()
        
        # Get patient info for response
        patient = Patient.query.get(data['patient_id'])

        # Notify all lab technicians about the new test order
        try:
            from backend.models.notification import Notification
            from backend.models.user import User as UserModel
            patient_name = patient.username if patient else f"Patient #{data['patient_id']}"
            priority = data.get('priority', 'normal').upper()
            lab_techs = UserModel.query.filter_by(role='lab_technician', is_active=True).all()
            for tech in lab_techs:
                db.session.add(Notification(
                    user_id=tech.id,
                    title=f'New Lab Test [{priority}]',
                    message=f'Dr. {current_doctor["username"]} ordered {data["test_name"]} for {patient_name}. Priority: {priority}.',
                    type='lab_order',
                    category='general',
                    is_read=False,
                    link=f'/templates/lab/enter_lab_results.html?test_id={test_id}',
                    created_at=datetime.utcnow()
                ))
            db.session.commit()
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass

        return jsonify({
            "success": True,
            "message": "Lab request created successfully",
            "lab_request": {
                "id": lab_request.id,
                "request_id": lab_request.test_id,
                "patient": {
                    "id": patient.id,
                    "name": patient.username,
                    "patient_id": getattr(patient, 'patient_id', None)
                } if patient else None,
                "test_name": lab_request.test_name,
                "test_type": lab_request.test_type,
                "priority": lab_request.priority,
                "status": lab_request.status,
                "requested_date": lab_request.created_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'create_lab_request error: {type(e).__name__}: {e}')
        return jsonify({
            "success": False,
            "message": f"Error creating lab request: {type(e).__name__}",
            "error": _safe_error(e)
        }), 500

@doctor_bp.route('/lab-requests/<int:request_id>', methods=['GET'])
@token_required
def get_lab_request(current_doctor, request_id):
    """
    Get details of a specific lab request
    """
    try:
        lab_request = LabTest.query.filter_by(
            id=request_id,
            doctor_id=current_doctor['id']
        ).first()
        
        if not lab_request:
            return jsonify({
                "success": False,
                "message": "Lab request not found"
            }), 404
        
        patient = Patient.query.get(lab_request.patient_id)
        
        # Build response with only fields that exist
        response = {
            "id": lab_request.id,
            "request_id": lab_request.test_id or f"LAB{lab_request.id:04d}",
            "patient": {
                "id": patient.id,
                "patient_id": getattr(patient, 'patient_id', None),
                "username": patient.username,
                "email": patient.email
            } if patient else None,
            "test_name": lab_request.test_name,
            "test_type": lab_request.test_type,
            "test_category": lab_request.test_category,
            "priority": lab_request.priority if hasattr(lab_request, 'priority') else 'normal',
            "status": lab_request.status,
            "requested_date": lab_request.created_at.isoformat() if lab_request.created_at else None,
            "results": lab_request.results if lab_request.results else None
        }
        
        return jsonify({
            "success": True,
            "lab_request": response
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching lab request",
            "error": _safe_error(e)
        }), 500


@doctor_bp.route('/lab-requests/statistics', methods=['GET'])
@token_required
def get_lab_request_statistics(current_doctor):
    """
    Get statistics about lab requests
    """
    try:
        doctor_id = current_doctor['id']
        
        # Total requests
        total = LabTest.query.filter_by(doctor_id=doctor_id).count()
        
        # Requests by status - use status values that exist in your model
        pending = LabTest.query.filter_by(doctor_id=doctor_id, status='pending').count()
        completed = LabTest.query.filter_by(doctor_id=doctor_id, status='completed').count()
        cancelled = LabTest.query.filter_by(doctor_id=doctor_id, status='cancelled').count()
        
        # Requests this month
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        this_month = LabTest.query.filter(
            LabTest.doctor_id == doctor_id,
            LabTest.created_at >= month_start
        ).count()
        
        # Most requested tests
        from sqlalchemy import func
        top_tests = db.session.query(
            LabTest.test_name, 
            func.count(LabTest.id).label('count')
        ).filter_by(doctor_id=doctor_id)\
         .group_by(LabTest.test_name)\
         .order_by(func.count(LabTest.id).desc())\
         .limit(5).all()
        
        return jsonify({
            "success": True,
            "statistics": {
                "total_requests": total,
                "by_status": {
                    "pending": pending,
                    "completed": completed,
                    "cancelled": cancelled
                },
                "this_month": this_month,
                "most_requested_tests": [
                    {"test_name": test, "count": count} for test, count in top_tests
                ]
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching statistics",
            "error": _safe_error(e)
        }), 500


@doctor_bp.route('/lab-requests/<int:request_id>/cancel', methods=['PUT'])
@token_required
def cancel_lab_request(current_doctor, request_id):
    """
    Cancel a pending lab request
    """
    try:
        lab_request = LabTest.query.filter_by(
            id=request_id,
            doctor_id=current_doctor['id']
        ).first()
        
        if not lab_request:
            return jsonify({
                "success": False,
                "message": "Lab request not found"
            }), 404
        
        if lab_request.status != 'pending':
            return jsonify({
                "success": False,
                "message": f"Cannot cancel request with status '{lab_request.status}'"
            }), 400
        
        lab_request.status = 'cancelled'
        lab_request.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Lab request cancelled successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error cancelling lab request",
            "error": _safe_error(e)
        }), 500


# ============ DOCTOR AVAILABILITY SETTINGS ============

@doctor_bp.route('/availability', methods=['GET'])
@token_required
def get_availability(current_doctor):
    """Get doctor's availability settings"""
    try:
        doctor = Doctor.query.get(current_doctor['id'])
        if not doctor:
            return jsonify({'success': False, 'message': 'Doctor not found'}), 404
        return jsonify({
            'success': True,
            'availability': {
                'available_days': doctor.available_days or 'Mon-Fri',
                'available_hours': doctor.available_hours or '08:00-17:00',
                'consultation_fee': doctor.consultation_fee or 0
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@doctor_bp.route('/availability', methods=['PUT'])
@token_required
def update_availability(current_doctor):
    """Update doctor's availability settings"""
    try:
        doctor = Doctor.query.get(current_doctor['id'])
        if not doctor:
            return jsonify({'success': False, 'message': 'Doctor not found'}), 404

        data = request.get_json() or {}
        if 'available_days' in data:
            doctor.available_days = data['available_days']
        if 'available_hours' in data:
            doctor.available_hours = data['available_hours']
        if 'consultation_fee' in data:
            doctor.consultation_fee = float(data['consultation_fee'])

        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Availability updated successfully',
            'availability': {
                'available_days': doctor.available_days,
                'available_hours': doctor.available_hours,
                'consultation_fee': doctor.consultation_fee
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============ PRESCRIPTION REFILL APPROVALS ============

@doctor_bp.route('/prescriptions/refills', methods=['GET'])
@token_required
def get_refill_requests(current_doctor):
    """GET /api/doctor/prescriptions/refills — list pending refill requests"""
    try:
        refills = Prescription.query.filter(
            Prescription.doctor_id == current_doctor['id'],
            Prescription.status == 'pending',
            Prescription.notes.like('REFILL REQUEST%')
        ).order_by(Prescription.created_at.desc()).all()

        result = []
        for rx in refills:
            patient = Patient.query.get(rx.patient_id)
            result.append({
                'id': rx.id,
                'prescription_id': rx.prescription_id,
                'medication': rx.medication,
                'dosage': rx.dosage,
                'patient_name': patient.username if patient else '—',
                'patient_id': rx.patient_id,
                'notes': rx.notes,
                'created_at': rx.created_at.isoformat() if rx.created_at else None
            })

        return jsonify({'success': True, 'refills': result, 'count': len(result)}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@doctor_bp.route('/prescriptions/<int:prescription_id>/approve-refill', methods=['POST'])
@token_required
def approve_refill(current_doctor, prescription_id):
    """POST /api/doctor/prescriptions/<id>/approve-refill — approve or reject refill"""
    try:
        rx = Prescription.query.filter_by(
            id=prescription_id,
            doctor_id=current_doctor['id']
        ).first()

        if not rx:
            return jsonify({'success': False, 'message': 'Prescription not found'}), 404

        data   = request.get_json() or {}
        action = data.get('action', 'approve')  # approve or reject

        if action == 'approve':
            rx.status = 'pending'  # ready for pharmacist
            rx.notes  = rx.notes + f" | Approved by Dr. {current_doctor['username']}"
            msg_patient = f"Your refill request for {rx.medication} has been approved by Dr. {current_doctor['username']}. Please visit the pharmacy."
        else:
            rx.status = 'rejected'
            rx.notes  = rx.notes + f" | Rejected by Dr. {current_doctor['username']}: {data.get('reason', '')}"
            msg_patient = f"Your refill request for {rx.medication} was not approved. Please book an appointment."

        rx.updated_at = datetime.utcnow()
        db.session.flush()

        # Notify patient
        from backend.models.notification import Notification
        db.session.add(Notification(
            user_id=rx.patient_id,
            title=f'Refill {"Approved" if action == "approve" else "Rejected"}',
            message=msg_patient,
            type='prescription',
            category='general',
            is_read=False,
            link='/templates/patient/prescriptions.html',
            created_at=datetime.utcnow()
        ))
        db.session.commit()

        return jsonify({'success': True, 'message': f'Refill {action}d successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
