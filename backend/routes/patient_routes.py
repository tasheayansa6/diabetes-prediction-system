"""
Patient Routes - Handles health records, predictions, patient dashboard, prescriptions, lab results, appointments, and profile management
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.health_record import HealthRecord
from backend.models.prediction import Prediction
from backend.models.prescription import Prescription
from backend.models.lab_test import LabTest
from backend.models.appointment import Appointment
from backend.services.prediction_service import PredictionService
from backend.utils.validators import validate_health_data
from datetime import datetime, timedelta
import jwt
from functools import wraps
import re
from sqlalchemy import text, inspect

patient_bp = Blueprint('patient', __name__, url_prefix='/api/patient')
prediction_service = PredictionService()

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def token_required(f):
    """Decorator for patient routes using JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({"success": False, "message": "Token is missing!"}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            
            # Check if role is patient
            if data.get('role') != 'patient':
                return jsonify({"success": False, "message": "Patient access required!"}), 403
            
            # Create a current_user dict from token data
            current_user = {
                'id': data.get('user_id'),
                'username': data.get('username'),
                'email': data.get('email'),
                'role': data.get('role')
            }
            
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Invalid token!"}), 401
            
        return f(current_user, *args, **kwargs)
    
    return decorated


# ============ PATIENT VITALS ENDPOINT (for health form auto-fill) ============

@patient_bp.route('/vitals/latest', methods=['GET'])
@token_required
def get_my_latest_vitals(current_user):
    """
    GET /api/patient/vitals/latest
    Returns the most recent vital signs recorded by a nurse for this patient.
    Used by the health form to auto-fill BP and BMI.
    """
    try:
        from backend.models.vital_sign import VitalSign

        vital = VitalSign.query.filter(
            VitalSign.patient_id == current_user['id']
        ).order_by(VitalSign.recorded_at.desc()).first()

        if not vital:
            return jsonify({'success': False, 'message': 'No vitals found'}), 404

        # If diastolic BP is null, try to fill from last health record
        bp_diastolic = vital.blood_pressure_diastolic
        bp_source = 'nurse'
        if bp_diastolic is None:
            last_hr = HealthRecord.query.filter_by(patient_id=current_user['id'])\
                .order_by(HealthRecord.created_at.desc()).first()
            if last_hr and last_hr.blood_pressure:
                bp_diastolic = last_hr.blood_pressure
                bp_source = 'previous_record'
            else:
                bp_diastolic = 72  # safe clinical default
                bp_source = 'default'

        return jsonify({
            'success': True,
            'vitals': {
                'blood_pressure_diastolic': bp_diastolic,
                'blood_pressure_systolic':  vital.blood_pressure_systolic,
                'bp_source':                bp_source,
                'bmi':                      vital.bmi,
                'height':                   vital.height,
                'weight':                   vital.weight,
                'skin_thickness':           None,
                'recorded_at':              vital.recorded_at.isoformat() if vital.recorded_at else None
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============ LAST PREDICTION DATA (for health form auto-fill) ============

@patient_bp.route('/health-data/last', methods=['GET'])
@token_required
def get_last_health_data(current_user):
    """
    GET /api/patient/health-data/last
    Returns the input_data from the patient's most recent prediction.
    Used to auto-fill Pregnancies, Skin Thickness, Pedigree, Age on the health form.
    """
    try:
        last = Prediction.query.filter_by(patient_id=current_user['id'])\
            .order_by(Prediction.created_at.desc()).first()

        if not last or not last.input_data:
            return jsonify({'success': False, 'message': 'No previous prediction found'}), 404

        d = last.input_data
        return jsonify({
            'success': True,
            'data': {
                'pregnancies':       d.get('pregnancies', 0),
                'diabetes_pedigree': d.get('diabetes_pedigree', 0.5),
                'age':               d.get('age')
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============ HEALTH RECORDS ENDPOINTS ============

@patient_bp.route('/health-records', methods=['POST'])
@token_required
def create_health_record(current_user):
    """
    Create a new health record
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['glucose', 'blood_pressure', 'bmi', 'age']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Validate health data
        valid, message = validate_health_data(data)
        if not valid:
            return jsonify({
                "success": False,
                "message": message
            }), 400
        
        # Create health record
        health_record = HealthRecord(
            patient_id=current_user['id'],
            pregnancies=data.get('pregnancies', 0),
            glucose=float(data['glucose']),
            blood_pressure=float(data['blood_pressure']),
            skin_thickness=float(data.get('skin_thickness', 0)),
            insulin=float(data.get('insulin', 0)),
            bmi=float(data['bmi']),
            diabetes_pedigree=float(data.get('diabetes_pedigree', 0.5)),
            age=int(data['age']),
            created_at=datetime.utcnow()
        )
        
        db.session.add(health_record)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Health record created successfully",
            "health_record": {
                "id": health_record.id,
                "glucose": health_record.glucose,
                "bmi": health_record.bmi,
                "age": health_record.age,
                "created_at": health_record.created_at.isoformat() if health_record.created_at else None
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred",
            "error": str(e)
        }), 500


@patient_bp.route('/health-records', methods=['GET'])
@token_required
def get_health_records(current_user):
    """
    Get all health records for the current patient
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        records = HealthRecord.query.filter_by(patient_id=current_user['id'])\
            .order_by(HealthRecord.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        total = HealthRecord.query.filter_by(patient_id=current_user['id']).count()
        
        return jsonify({
            "success": True,
            "health_records": [
                {
                    "id": r.id,
                    "glucose": r.glucose,
                    "bmi": r.bmi,
                    "age": r.age,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                } for r in records
            ],
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
            "message": "An error occurred",
            "error": str(e)
        }), 500


# ============ PREDICTION ENDPOINTS ============

@patient_bp.route('/predict', methods=['POST'])
@token_required
def predict(current_user):
    """
    Make a diabetes prediction using current health data
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['glucose', 'blood_pressure', 'bmi', 'age']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Validate health data
        valid, message = validate_health_data(data)
        if not valid:
            return jsonify({
                "success": False,
                "message": message
            }), 400
        
        # Create health record first
        health_record = HealthRecord(
            patient_id=current_user['id'],
            pregnancies=data.get('pregnancies', 0),
            glucose=float(data['glucose']),
            blood_pressure=float(data['blood_pressure']),
            skin_thickness=float(data.get('skin_thickness', 0)),
            insulin=float(data.get('insulin', 0)),
            bmi=float(data['bmi']),
            diabetes_pedigree=float(data.get('diabetes_pedigree', 0.5)),
            age=int(data['age']),
            created_at=datetime.utcnow()
        )
        
        db.session.add(health_record)
        db.session.flush()
        
        # Make prediction using ML service
        prediction_result = prediction_service.predict_diabetes(data)
        
        if not prediction_result.get('success', False):
            db.session.rollback()
            return jsonify({
                "success": False,
                "message": "Prediction failed",
                "error": prediction_result.get('error', 'Unknown error')
            }), 500
        
        # Create prediction record
        prediction = Prediction(
            patient_id=current_user['id'],
            health_record_id=health_record.id,
            prediction=prediction_result.get('prediction_code', 0),
            probability=prediction_result.get('probability', 0),
            probability_percent=prediction_result.get('probability_percent', 0),
            risk_level=prediction_result.get('risk_level', 'UNKNOWN'),
            model_version=prediction_result.get('model_version', '1.0.0'),
            explanation=prediction_result.get('interpretation', ''),
            input_data=data,
            created_at=datetime.utcnow()
        )
        
        db.session.add(prediction)
        db.session.commit()

        from backend.utils.logger import log_prediction
        log_prediction(
            user_id=current_user['id'],
            username=current_user['username'],
            input_data=data,
            result={
                'prediction': prediction_result.get('prediction_code', 0),
                'probability': prediction_result.get('probability', 0),
                'risk_level': prediction_result.get('risk_level', 'UNKNOWN')
            },
            model_version=prediction_result.get('model_version', '1.0.0')
        )

        # Notify doctors about prediction result
        try:
            from backend.models.notification import Notification
            patient_name = current_user.get('username', 'A patient')
            risk_level = prediction_result.get('risk_level', '')
            is_high = 'HIGH' in risk_level
            prob = round(prediction_result.get('probability_percent', 0), 1)
            notif_title = f'HIGH RISK Alert - {patient_name}' if is_high else f'Prediction Result - {patient_name}'
            notif_msg = (
                f'{patient_name} completed a diabetes prediction: {risk_level} ({prob}%). '
                f'Glucose: {data.get("glucose", "N/A")} mg/dL, '
                f'BMI: {data.get("bmi", "N/A")}, '
                f'Age: {data.get("age", "N/A")}.'
                + (' Immediate review recommended.' if is_high else ' Review when available.')
            )
            doctors = User.query.filter_by(role='doctor', is_active=True).all()
            for doc in doctors:
                db.session.add(Notification(
                    user_id=doc.id,
                    title=notif_title,
                    message=notif_msg,
                    type='high_risk_alert' if is_high else 'prediction',
                    category='general',
                    is_read=False,
                    created_at=datetime.utcnow()
                ))
            db.session.commit()
        except Exception as notif_err:
            current_app.logger.error(f'Prediction notification error: {notif_err}')
            try:
                db.session.rollback()
            except Exception:
                pass

        return jsonify({
            "success": True,
            "message": "Prediction completed successfully",
            "prediction": {
                "id": prediction.id,
                "probability": prediction.probability,
                "probability_percent": prediction.probability_percent,
                "risk_level": prediction.risk_level,
                "risk_color": prediction_result.get('risk_color', '⚪'),
                "confidence": prediction_result.get('confidence', 0),
                "interpretation": prediction_result.get('interpretation', ''),
                "action": prediction_result.get('action', ''),
                "recommendation": prediction_result.get('recommendation', ''),
                "created_at": prediction.created_at.isoformat() if prediction.created_at else None
            },
            "health_record": {
                "id": health_record.id,
                "glucose": health_record.glucose,
                "bmi": health_record.bmi,
                "age": health_record.age,
                "created_at": health_record.created_at.isoformat() if health_record.created_at else None
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred during prediction",
            "error": str(e)
        }), 500


@patient_bp.route('/predictions', methods=['GET'])
@token_required
def get_predictions(current_user):
    """
    Get all predictions for the current patient
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        predictions = Prediction.query.filter_by(patient_id=current_user['id'])\
            .order_by(Prediction.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        total = Prediction.query.filter_by(patient_id=current_user['id']).count()
        
        return jsonify({
            "success": True,
            "predictions": [
                {
                    "id": p.id,
                    "probability_percent": p.probability_percent,
                    "risk_level": p.risk_level,
                    "input_data": p.input_data,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                } for p in predictions
            ],
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
            "message": "An error occurred",
            "error": str(e)
        }), 500


@patient_bp.route('/predictions/<int:prediction_id>', methods=['GET'])
@token_required
def get_prediction(current_user, prediction_id):
    """
    Get a specific prediction by ID
    """
    try:
        prediction = Prediction.query.filter_by(
            id=prediction_id, 
            patient_id=current_user['id']
        ).first()
        
        if not prediction:
            return jsonify({
                "success": False,
                "message": "Prediction not found"
            }), 404
        
        return jsonify({
            "success": True,
            "prediction": {
                "id": prediction.id,
                "probability": prediction.probability,
                "probability_percent": prediction.probability_percent,
                "risk_level": prediction.risk_level,
                "prediction": "Diabetic" if prediction.prediction == 1 else "Non-Diabetic",
                "explanation": prediction.explanation,
                "confidence": round(50.0 + (max(prediction.probability, 1 - prediction.probability) - 0.5) * 90.0, 1) if prediction.probability else 0,
                "input_data": prediction.input_data,
                "created_at": prediction.created_at.isoformat() if prediction.created_at else None,
                "health_record_id": prediction.health_record_id
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "An error occurred",
            "error": str(e)
        }), 500


# ============ DASHBOARD ENDPOINT ============

@patient_bp.route('/dashboard', methods=['GET'])
@token_required
def dashboard(current_user):
    """
    Get patient dashboard summary
    """
    try:
        # Get latest prediction
        latest_prediction = Prediction.query.filter_by(patient_id=current_user['id'])\
            .order_by(Prediction.created_at.desc())\
            .first()
        
        # Get counts
        prediction_count = Prediction.query.filter_by(patient_id=current_user['id']).count()
        health_record_count = HealthRecord.query.filter_by(patient_id=current_user['id']).count()
        
        # Get risk distribution
        risk_distribution = db.session.query(
            Prediction.risk_level, 
            db.func.count(Prediction.id)
        ).filter_by(patient_id=current_user['id'])\
         .group_by(Prediction.risk_level)\
         .all()
        
        # Helper function to get color from risk level
        def get_risk_color(risk_level):
            if not risk_level:
                return '⚪'
            if 'LOW' in risk_level:
                return '🟢'
            elif 'MODERATE' in risk_level:
                return '🟡'
            elif 'HIGH' in risk_level:
                return '🟠'
            elif 'VERY' in risk_level:
                return '🔴'
            return '⚪'
        
        return jsonify({
            "success": True,
            "dashboard": {
                "patient_info": {
                    "id": current_user['id'],
                    "username": current_user['username'],
                    "email": current_user['email'],
                    "role": current_user['role']
                },
                "latest_prediction": {
                    "probability_percent": latest_prediction.probability_percent if latest_prediction else None,
                    "risk_level": latest_prediction.risk_level if latest_prediction else None,
                    "risk_color": get_risk_color(latest_prediction.risk_level) if latest_prediction else None,
                    "created_at": latest_prediction.created_at.isoformat() if latest_prediction else None
                } if latest_prediction else None,
                "stats": {
                    "total_predictions": prediction_count,
                    "total_health_records": health_record_count,
                    "risk_distribution": {level: count for level, count in risk_distribution}
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "An error occurred",
            "error": str(e)
        }), 500


# ============ PRESCRIPTION ENDPOINTS ============

@patient_bp.route('/prescriptions', methods=['GET'])
@token_required
def get_prescriptions(current_user):
    """
    Get all prescriptions for the current patient
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        prescriptions = Prescription.query.filter_by(patient_id=current_user['id'])\
            .order_by(Prescription.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        total = Prescription.query.filter_by(patient_id=current_user['id']).count()
        
        # Format prescriptions for response
        prescriptions_list = []
        for p in prescriptions:
            doctor = User.query.get(p.doctor_id) if p.doctor_id else None
            dispensed_by_user = User.query.get(p.dispensed_by) if p.dispensed_by else None
            prescriptions_list.append({
                "id": p.id,
                "prescription_id": p.prescription_id,
                "medication": p.medication,
                "dosage": p.dosage,
                "frequency": p.frequency,
                "duration": p.duration,
                "instructions": p.instructions,
                "notes": p.notes,
                "status": p.status,
                "doctor_id": p.doctor_id,
                "doctor_name": doctor.username if doctor else "Unknown Doctor",
                "dispensed_by": dispensed_by_user.username if dispensed_by_user else None,
                "prediction_id": p.prediction_id,
                "dispensed_at": p.dispensed_at.isoformat() if p.dispensed_at else None,
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
            "message": "An error occurred fetching prescriptions",
            "error": str(e)
        }), 500


@patient_bp.route('/prescriptions/<int:prescription_id>', methods=['GET'])
@token_required
def get_prescription(current_user, prescription_id):
    """
    Get a specific prescription by ID
    """
    try:
        prescription = Prescription.query.filter_by(
            id=prescription_id,
            patient_id=current_user['id']
        ).first()
        
        if not prescription:
            return jsonify({
                "success": False,
                "message": "Prescription not found"
            }), 404
        
        return jsonify({
            "success": True,
            "prescription": {
                "id": prescription.id,
                "prescription_id": prescription.prescription_id,
                "medication": prescription.medication,
                "dosage": prescription.dosage,
                "frequency": prescription.frequency,
                "duration": prescription.duration,
                "instructions": prescription.instructions,
                "notes": prescription.notes,
                "status": prescription.status,
                "doctor_id": prescription.doctor_id,
                "patient_id": prescription.patient_id,
                "prediction_id": prescription.prediction_id,
                "dispensed_by": prescription.dispensed_by,
                "dispensed_at": prescription.dispensed_at.isoformat() if prescription.dispensed_at else None,
                "created_at": prescription.created_at.isoformat() if prescription.created_at else None,
                "updated_at": prescription.updated_at.isoformat() if prescription.updated_at else None
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "An error occurred",
            "error": str(e)
        }), 500


# ============ LAB RESULTS ENDPOINTS ============

@patient_bp.route('/lab-results', methods=['GET'])
@token_required
def get_lab_results(current_user):
    """
    Get all lab results for the current patient
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        lab_results = LabTest.query.filter_by(patient_id=current_user['id'])\
            .order_by(LabTest.created_at.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        total = LabTest.query.filter_by(patient_id=current_user['id']).count()
        
        # Format lab results for response
        results_list = []
        for r in lab_results:
            doctor = User.query.get(r.doctor_id) if r.doctor_id else None
            results_list.append({
                "id": r.id,
                "test_id": r.test_id,
                "test_name": r.test_name,
                "test_type": r.test_type,
                "test_category": r.test_category,
                "status": r.status or 'pending',
                "priority": r.priority,
                "results": r.results,
                "normal_range": r.normal_range,
                "unit": r.unit,
                "remarks": r.remarks,
                "cost": r.cost,
                "doctor_name": doctor.username if doctor else None,
                "test_completed_at": r.test_completed_at.isoformat() if r.test_completed_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None
            })
        
        return jsonify({
            "success": True,
            "lab_results": results_list,
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
            "message": "An error occurred fetching lab results",
            "error": str(e)
        }), 500


@patient_bp.route('/lab-results/<int:result_id>', methods=['GET'])
@token_required
def get_lab_result(current_user, result_id):
    """
    Get a specific lab result by ID
    """
    try:
        lab_result = LabTest.query.filter_by(
            id=result_id,
            patient_id=current_user['id']
        ).first()
        
        if not lab_result:
            return jsonify({
                "success": False,
                "message": "Lab result not found"
            }), 404
        
        doctor = User.query.get(lab_result.doctor_id) if lab_result.doctor_id else None
        return jsonify({
            "success": True,
            "lab_result": {
                "id": lab_result.id,
                "test_id": lab_result.test_id,
                "test_name": lab_result.test_name,
                "test_type": lab_result.test_type,
                "test_category": lab_result.test_category,
                "status": lab_result.status or 'pending',
                "priority": lab_result.priority,
                "results": lab_result.results,
                "normal_range": lab_result.normal_range,
                "unit": lab_result.unit,
                "remarks": lab_result.remarks,
                "cost": lab_result.cost,
                "doctor_name": doctor.username if doctor else None,
                "test_completed_at": lab_result.test_completed_at.isoformat() if lab_result.test_completed_at else None,
                "created_at": lab_result.created_at.isoformat() if lab_result.created_at else None
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "An error occurred",
            "error": str(e)
        }), 500


# ============ APPOINTMENT ENDPOINTS ============

@patient_bp.route('/appointments', methods=['GET'])
@token_required
def get_appointments(current_user):
    """
    Get all appointments for the current patient
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status')
        
        query = Appointment.query.filter_by(patient_id=current_user['id'])
        
        if status:
            query = query.filter_by(status=status)
        
        appointments = query.order_by(Appointment.appointment_date.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        total = query.count()
        
        from backend.models.user import User
        appointments_list = []
        for a in appointments:
            doctor_user = User.query.get(a.doctor_id)
            d = a.to_dict()
            d['doctor_name'] = doctor_user.username if doctor_user else f"Doctor #{a.doctor_id}"
            d['doctor_specialization'] = None
            if doctor_user:
                from backend.models.doctor import Doctor as DoctorModel
                doc = DoctorModel.query.get(a.doctor_id)
                d['doctor_specialization'] = doc.specialization if doc else None
            appointments_list.append(d)

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
            "message": "An error occurred fetching appointments",
            "error": str(e)
        }), 500


@patient_bp.route('/appointments', methods=['POST'])
@token_required
def create_appointment(current_user):
    """
    Create a new appointment
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['doctor_id', 'appointment_date', 'reason']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Convert appointment_date string to date object
        try:
            appointment_date = datetime.strptime(data['appointment_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                "success": False,
                "message": "Invalid date format. Use YYYY-MM-DD (e.g., 2026-03-15)"
            }), 400
        
        # Ensure doctor row exists in doctors table (for users registered directly)
        from backend.models.doctor import Doctor
        doc = Doctor.query.get(data['doctor_id'])
        if not doc:
            doctor_user = User.query.get(data['doctor_id'])
            if not doctor_user or doctor_user.role != 'doctor':
                return jsonify({"success": False, "message": "Doctor not found"}), 404
            doc = Doctor(id=doctor_user.id, doctor_id=f"DOC{doctor_user.id:04d}")
            db.session.add(doc)
            db.session.flush()

        # Create appointment
        appointment = Appointment(
            patient_id=current_user['id'],
            doctor_id=data['doctor_id'],
            appointment_date=appointment_date,
            appointment_time=data.get('appointment_time'),
            duration=data.get('duration', 30),
            type=data.get('type', 'consultation'),
            reason=data['reason'],
            notes=data.get('notes', ''),
            status='scheduled',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(appointment)
        db.session.commit()

        # Send appointment confirmation email
        try:
            from backend.services.notification_service import send_appointment_reminder
            patient_user = User.query.get(current_user['id'])
            doctor_user = User.query.get(data['doctor_id'])
            if patient_user and doctor_user:
                send_appointment_reminder(
                    patient_user.email,
                    patient_user.username,
                    str(appointment_date),
                    data.get('appointment_time', 'TBD'),
                    doctor_user.username
                )
        except Exception:
            pass  # Don't fail the booking if email fails

        # Notify doctor in-app
        try:
            from backend.models.notification import Notification
            patient_user = patient_user if 'patient_user' in dir() else User.query.get(current_user['id'])
            notif = Notification(
                user_id=data['doctor_id'],
                title='New Appointment Booked',
                message=f'{patient_user.username if patient_user else "A patient"} booked an appointment on {appointment_date} at {data.get("appointment_time", "TBD")}. Reason: {data["reason"]}',
                type='appointment',
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.session.add(notif)
            db.session.commit()
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": "Appointment created successfully",
            "appointment": appointment.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred creating appointment",
            "error": str(e)
        }), 500


@patient_bp.route('/appointments/<int:appointment_id>', methods=['GET'])
@token_required
def get_appointment(current_user, appointment_id):
    """
    Get a specific appointment by ID
    """
    try:
        appointment = Appointment.query.filter_by(
            id=appointment_id,
            patient_id=current_user['id']
        ).first()
        
        if not appointment:
            return jsonify({
                "success": False,
                "message": "Appointment not found"
            }), 404
        
        return jsonify({
            "success": True,
            "appointment": appointment.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "An error occurred",
            "error": str(e)
        }), 500


@patient_bp.route('/appointments/<int:appointment_id>', methods=['PUT'])
@token_required
def update_appointment(current_user, appointment_id):
    """
    Update an existing appointment
    """
    try:
        appointment = Appointment.query.filter_by(
            id=appointment_id,
            patient_id=current_user['id']
        ).first()
        
        if not appointment:
            return jsonify({
                "success": False,
                "message": "Appointment not found"
            }), 404
        
        data = request.get_json()
        
        # Update fields if provided
        if 'appointment_date' in data:
            try:
                appointment.appointment_date = datetime.strptime(data['appointment_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    "success": False,
                    "message": "Invalid date format. Use YYYY-MM-DD"
                }), 400
        
        if 'appointment_time' in data:
            appointment.appointment_time = data['appointment_time']
        
        if 'duration' in data:
            appointment.duration = data['duration']
        
        if 'type' in data:
            appointment.type = data['type']
        
        if 'reason' in data:
            appointment.reason = data['reason']
        
        if 'notes' in data:
            appointment.notes = data['notes']
        
        appointment.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Appointment updated successfully",
            "appointment": appointment.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred updating appointment",
            "error": str(e)
        }), 500


@patient_bp.route('/appointments/<int:appointment_id>/cancel', methods=['POST'])
@token_required
def cancel_appointment(current_user, appointment_id):
    """
    Cancel an appointment
    """
    try:
        appointment = Appointment.query.filter_by(
            id=appointment_id,
            patient_id=current_user['id']
        ).first()
        
        if not appointment:
            return jsonify({
                "success": False,
                "message": "Appointment not found"
            }), 404
        
        appointment.status = 'cancelled'
        appointment.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Appointment cancelled successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "An error occurred cancelling appointment",
            "error": str(e)
        }), 500


# ============ DOCTORS LIST (public to patients) ============

@patient_bp.route('/doctors', methods=['GET'])
@token_required
def get_doctors(current_user):
    """Get list of available doctors for appointment booking"""
    try:
        from backend.models.doctor import Doctor
        doctor_users = User.query.filter_by(role='doctor', is_active=True).all()
        result = []
        for u in doctor_users:
            doc = Doctor.query.get(u.id)
            if not doc:
                # Auto-create missing doctors table row
                doc = Doctor(id=u.id, doctor_id=f"DOC{u.id:04d}")
                db.session.add(doc)
                db.session.commit()
            result.append({
                "id": u.id,
                "name": u.username,
                "specialization": doc.specialization or 'General Practitioner',
                "available_days": doc.available_days or 'Mon-Fri',
                "available_hours": doc.available_hours or '08:00-17:00',
                "consultation_fee": doc.consultation_fee or 0
            })
        return jsonify({"success": True, "doctors": result}), 200
    except Exception as e:
        return jsonify({"success": False, "message": "Error fetching doctors", "error": str(e)}), 500


# ============ CHANGE PASSWORD ENDPOINT ============

@patient_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    try:
        data = request.get_json()
        current_pw = data.get('current_password')
        new_pw = data.get('new_password')
        confirm_pw = data.get('confirm_password')

        if not all([current_pw, new_pw, confirm_pw]):
            return jsonify({"success": False, "message": "All password fields are required"}), 400

        if new_pw != confirm_pw:
            return jsonify({"success": False, "message": "New passwords do not match"}), 400

        if len(new_pw) < 8:
            return jsonify({"success": False, "message": "Password must be at least 8 characters"}), 400

        user = User.query.get(current_user['id'])
        if not user or not check_password_hash(user.password_hash, current_pw):
            return jsonify({"success": False, "message": "Current password is incorrect"}), 401

        user.password_hash = generate_password_hash(new_pw)
        db.session.commit()
        return jsonify({"success": True, "message": "Password changed successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "An error occurred", "error": str(e)}), 500


# ============ PATIENT PROFILE ENDPOINTS (FIXED - only existing columns) ============

@patient_bp.route('/profile', methods=['GET'])
@token_required
def get_patient_profile(current_user):
    """
    Get detailed profile for the current patient
    Only includes columns that exist in the database
    """
    try:
        # Get user data
        user = db.session.execute(
            text("SELECT id, username, email, role, created_at, last_login FROM users WHERE id = :id"),
            {"id": current_user['id']}
        ).first()
        
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404
        
        # Helper function to format dates safely
        def format_date(date_value):
            if date_value is None:
                return None
            if isinstance(date_value, str):
                return date_value
            if hasattr(date_value, 'isoformat'):
                return date_value.isoformat()
            return str(date_value)
        
        # Check what columns exist in the patients table
        inspector = inspect(db.engine)
        patient_columns = [col['name'] for col in inspector.get_columns('patients')]
        
        # Build query dynamically based on existing columns
        select_fields = ['patient_id']
        for field in ['blood_group', 'emergency_contact', 'emergency_contact_name', 
                      'medical_history', 'allergies', 'current_medications']:
            if field in patient_columns:
                select_fields.append(field)
        
        query = f"SELECT {', '.join(select_fields)} FROM patients WHERE id = :id"
        patient = db.session.execute(text(query), {"id": current_user['id']}).first()
        
        # Get statistics
        health_count = db.session.execute(
            text("SELECT COUNT(*) FROM health_records WHERE patient_id = :id"),
            {"id": current_user['id']}
        ).scalar() or 0
        
        prediction_count = db.session.execute(
            text("SELECT COUNT(*) FROM predictions WHERE patient_id = :id"),
            {"id": current_user['id']}
        ).scalar() or 0
        
        # Build profile with safe date formatting
        profile = {
            "id": user[0],
            "username": user[1],
            "email": user[2],
            "role": user[3],
            "created_at": format_date(user[4]),
            "last_login": format_date(user[5]),
            "patient_id": patient[0] if patient else f"PAT{current_user['id']:03d}",
            "statistics": {
                "total_health_records": health_count,
                "total_predictions": prediction_count
            }
        }
        
        # Add optional fields if they exist
        if patient and len(patient) > 1:
            profile["blood_group"] = patient[1] if patient[1] else None
        if patient and len(patient) > 2:
            profile["emergency_contact"] = patient[2] if patient[2] else None
        if patient and len(patient) > 3:
            profile["emergency_contact_name"] = patient[3] if patient[3] else None
        if patient and len(patient) > 4:
            profile["medical_history"] = patient[4] if patient[4] else None
        if patient and len(patient) > 5:
            profile["allergies"] = patient[5] if patient[5] else None
        if patient and len(patient) > 6:
            profile["current_medications"] = patient[6] if patient[6] else None
        
        return jsonify({
            "success": True,
            "profile": profile
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "An error occurred fetching profile",
            "error": str(e)
        }), 500


# ============ UPDATE PATIENT PROFILE ENDPOINT (FIXED - only existing columns) ============

@patient_bp.route('/profile', methods=['PUT'])
@token_required
def update_patient_profile(current_user):
    """
    Update patient profile information
    Only updates fields that exist in the database
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
        
        # Get patient record
        patient = Patient.query.get(current_user['id'])
        if not patient:
            return jsonify({
                "success": False,
                "message": "Patient not found"
            }), 404
        
        # Check what columns exist in the patients table
        inspector = inspect(db.engine)
        patient_columns = [col['name'] for col in inspector.get_columns('patients')]
        
        updates = []
        
        # Update username if provided
        if 'username' in data and data['username'] != patient.username:
            if User.query.filter_by(username=data['username']).first():
                return jsonify({
                    "success": False,
                    "message": "Username already taken"
                }), 409
            patient.username = data['username']
            updates.append('username')
        
        # Update email if provided
        if 'email' in data and data['email'] != patient.email:
            if not validate_email(data['email']):
                return jsonify({
                    "success": False,
                    "message": "Invalid email format"
                }), 400
            if User.query.filter_by(email=data['email']).first():
                return jsonify({
                    "success": False,
                    "message": "Email already registered"
                }), 409
            patient.email = data['email']
            updates.append('email')
        
        # Patient-specific fields - only those that exist in the database
        patient_fields = []
        if 'blood_group' in data and 'blood_group' in patient_columns:
            patient.blood_group = data['blood_group']
            patient_fields.append('blood_group')
        
        if 'emergency_contact' in data and 'emergency_contact' in patient_columns:
            patient.emergency_contact = data['emergency_contact']
            patient_fields.append('emergency_contact')
        
        if 'emergency_contact_name' in data and 'emergency_contact_name' in patient_columns:
            patient.emergency_contact_name = data['emergency_contact_name']
            patient_fields.append('emergency_contact_name')
        
        if 'medical_history' in data and 'medical_history' in patient_columns:
            patient.medical_history = data['medical_history']
            patient_fields.append('medical_history')
        
        if 'allergies' in data and 'allergies' in patient_columns:
            patient.allergies = data['allergies']
            patient_fields.append('allergies')
        
        if 'current_medications' in data and 'current_medications' in patient_columns:
            patient.current_medications = data['current_medications']
            patient_fields.append('current_medications')
        
        updates.extend(patient_fields)
        
        # Update timestamp if patient has updated_at field
        if hasattr(patient, 'updated_at'):
            patient.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Generate new token if username/email changed
        new_token = None
        if 'username' in data or 'email' in data:
            new_token = jwt.encode({
                'user_id': patient.id,
                'email': patient.email,
                'username': patient.username,
                'role': patient.role,
                'exp': datetime.utcnow() + timedelta(days=1)
            }, current_app.config['SECRET_KEY'], algorithm="HS256")
        
        # Build profile response
        profile_response = {
            "id": patient.id,
            "username": patient.username,
            "email": patient.email,
            "role": patient.role,
            "patient_id": patient.patient_id
        }
        
        # Add optional fields if they exist
        if hasattr(patient, 'blood_group') and patient.blood_group:
            profile_response["blood_group"] = patient.blood_group
        if hasattr(patient, 'emergency_contact') and patient.emergency_contact:
            profile_response["emergency_contact"] = patient.emergency_contact
        if hasattr(patient, 'emergency_contact_name') and patient.emergency_contact_name:
            profile_response["emergency_contact_name"] = patient.emergency_contact_name
        if hasattr(patient, 'medical_history') and patient.medical_history:
            profile_response["medical_history"] = patient.medical_history
        if hasattr(patient, 'allergies') and patient.allergies:
            profile_response["allergies"] = patient.allergies
        if hasattr(patient, 'current_medications') and patient.current_medications:
            profile_response["current_medications"] = patient.current_medications
        if hasattr(patient, 'updated_at') and patient.updated_at:
            profile_response["updated_at"] = patient.updated_at.isoformat()
        
        return jsonify({
            "success": True,
            "message": "Profile updated successfully",
            "updated_fields": updates,
            "token": new_token,
            "profile": profile_response
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error updating profile",
            "error": str(e)
        }), 500


# ============ PATIENT REPORT GENERATION ============

@patient_bp.route('/report', methods=['GET'])
@token_required
def generate_patient_report(current_user):
    """
    Generate comprehensive patient health report
    """
    try:
        patient_id = current_user['id']
        
        # Get patient info
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({"success": False, "message": "Patient not found"}), 404

        if not _has_paid(patient_id):
            # Allow free access for HIGH/VERY HIGH risk patients
            latest = Prediction.query.filter_by(patient_id=patient_id)\
                .order_by(Prediction.created_at.desc()).first()
            is_high_risk = latest and ('HIGH' in (latest.risk_level or ''))
            if not is_high_risk:
                return jsonify({'success': False, 'message': 'Payment required to access your report.', 'payment_required': True}), 402
        
        # Get health records
        health_records = HealthRecord.query.filter_by(patient_id=patient_id)\
            .order_by(HealthRecord.created_at.desc()).limit(10).all()
        
        # Get predictions
        predictions = Prediction.query.filter_by(patient_id=patient_id)\
            .order_by(Prediction.created_at.desc()).limit(10).all()
        
        # Get prescriptions
        prescriptions = Prescription.query.filter_by(patient_id=patient_id)\
            .order_by(Prescription.created_at.desc()).limit(10).all()
        
        # Get lab results
        lab_results = LabTest.query.filter_by(patient_id=patient_id)\
            .order_by(LabTest.created_at.desc()).limit(10).all()
        
        # Get appointments
        appointments = Appointment.query.filter_by(patient_id=patient_id)\
            .order_by(Appointment.appointment_date.desc()).limit(10).all()
        
        # Build report
        report = {
            "report_id": f"RPT{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.utcnow().isoformat(),
            "patient_info": {
                "id": patient.id,
                "patient_id": patient.patient_id,
                "name": patient.username,
                "email": patient.email,
                "blood_group": patient.blood_group if hasattr(patient, 'blood_group') else None
            },
            "health_records": [{
                "date": hr.created_at.isoformat() if hr.created_at else None,
                "glucose": hr.glucose,
                "bmi": hr.bmi,
                "blood_pressure": hr.blood_pressure,
                "age": hr.age
            } for hr in health_records],
            "predictions": [{
                "date": p.created_at.isoformat() if p.created_at else None,
                "result": "Diabetic" if p.prediction == 1 else "Non-Diabetic",
                "probability_percent": p.probability_percent,
                "risk_level": p.risk_level
            } for p in predictions],
            "prescriptions": [{
                "date": rx.created_at.isoformat() if rx.created_at else None,
                "medication": rx.medication,
                "dosage": rx.dosage,
                "status": rx.status
            } for rx in prescriptions],
            "lab_results": [{
                "date": lab.created_at.isoformat() if lab.created_at else None,
                "test_name": lab.test_name,
                "status": lab.status,
                "results": lab.results
            } for lab in lab_results],
            "appointments": [{
                "date": str(apt.appointment_date),
                "time": apt.appointment_time,
                "status": apt.status,
                "reason": apt.reason
            } for apt in appointments],
            "summary": {
                "total_health_records": len(health_records),
                "total_predictions": len(predictions),
                "total_prescriptions": len(prescriptions),
                "total_lab_tests": len(lab_results),
                "total_appointments": len(appointments),
                "latest_risk": predictions[0].risk_level if predictions else "No data"
            }
        }
        
        return jsonify({
            "success": True,
            "report": report
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error generating report",
            "error": str(e)
        }), 500


# ============ PDF REPORT DOWNLOAD ============

@patient_bp.route('/report/pdf', methods=['GET'])
@token_required
def download_patient_pdf(current_user):
    """
    GET /api/patient/report/pdf
    Returns a downloadable PDF health report for the current patient.
    """
    try:
        from flask import send_file
        from backend.services.report_service import generate_patient_pdf

        patient_id = current_user['id']
        patient = Patient.query.get(patient_id)
        if not patient:
            return jsonify({"success": False, "message": "Patient not found"}), 404

        if not _has_paid(patient_id):
            latest = Prediction.query.filter_by(patient_id=patient_id)\
                .order_by(Prediction.created_at.desc()).first()
            is_high_risk = latest and ('HIGH' in (latest.risk_level or ''))
            if not is_high_risk:
                return jsonify({'success': False, 'message': 'Payment required to download your report.', 'payment_required': True}), 402

        predictions = Prediction.query.filter_by(patient_id=patient_id)\
            .order_by(Prediction.created_at.desc()).limit(10).all()
        prescriptions = Prescription.query.filter_by(patient_id=patient_id)\
            .order_by(Prescription.created_at.desc()).limit(10).all()
        lab_results = LabTest.query.filter_by(patient_id=patient_id)\
            .order_by(LabTest.created_at.desc()).limit(10).all()
        appointments = Appointment.query.filter_by(patient_id=patient_id)\
            .order_by(Appointment.appointment_date.desc()).limit(10).all()

        patient_info = {
            "patient_id": patient.patient_id,
            "name": getattr(patient, 'full_name', None) or patient.username,
            "email": patient.email,
            "blood_group": getattr(patient, 'blood_group', None),
        }

        pred_list = [{"date": p.created_at.isoformat() if p.created_at else "",
                      "result": "Diabetic" if p.prediction == 1 else "Non-Diabetic",
                      "risk_level": p.risk_level,
                      "probability_percent": p.probability_percent} for p in predictions]

        rx_list = [{"date": rx.created_at.isoformat() if rx.created_at else "",
                    "medication": rx.medication, "dosage": rx.dosage,
                    "status": rx.status} for rx in prescriptions]

        lab_list = [{"date": lab.created_at.isoformat() if lab.created_at else "",
                     "test_name": lab.test_name, "results": lab.results,
                     "status": lab.status} for lab in lab_results]

        apt_list = [{"date": str(apt.appointment_date), "time": apt.appointment_time,
                     "reason": apt.reason, "status": apt.status} for apt in appointments]

        pdf_buf = generate_patient_pdf(patient_info, pred_list, rx_list, lab_list, apt_list)

        filename = f"health_report_{patient.patient_id}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
        return send_file(
            pdf_buf,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({"success": False, "message": "Error generating PDF", "error": str(e)}), 500


# ============ PAYMENT LOCK HELPER ============

def _has_paid(patient_id):
    """Returns True if patient has at least one completed payment."""
    from backend.models.payment import Payment
    return Payment.query.filter_by(
        patient_id=patient_id,
        payment_status='completed'
    ).first() is not None


# ============ TIMELINE ENDPOINT ============

@patient_bp.route('/timeline', methods=['GET'])
@token_required
def get_timeline(current_user):
    """
    GET /api/patient/timeline
    Returns a chronological list of all patient events for the timeline UI.
    """
    try:
        patient_id = current_user['id']
        events = []

        # Predictions
        for p in Prediction.query.filter_by(patient_id=patient_id).all():
            events.append({
                'type': 'prediction',
                'icon': '🩺',
                'title': 'Prediction Completed',
                'detail': f"{p.risk_level} — {round(p.probability_percent or 0, 1)}%",
                'status': 'completed',
                'date': p.created_at.isoformat() if p.created_at else None
            })

        # Appointments
        for a in Appointment.query.filter_by(patient_id=patient_id).all():
            events.append({
                'type': 'appointment',
                'icon': '📅',
                'title': 'Appointment ' + a.status.capitalize(),
                'detail': a.reason or '',
                'status': a.status,
                'date': a.created_at.isoformat() if a.created_at else None
            })

        # Lab tests
        for l in LabTest.query.filter_by(patient_id=patient_id).all():
            events.append({
                'type': 'lab',
                'icon': '🔬',
                'title': f"Lab Test: {l.test_name}",
                'detail': l.status or 'pending',
                'status': l.status or 'pending',
                'date': (l.test_completed_at or l.created_at).isoformat() if (l.test_completed_at or l.created_at) else None
            })

        # Prescriptions
        for rx in Prescription.query.filter_by(patient_id=patient_id).all():
            events.append({
                'type': 'prescription',
                'icon': '💊',
                'title': f"Prescription: {rx.medication}",
                'detail': rx.status or 'pending',
                'status': rx.status or 'pending',
                'date': (rx.dispensed_at or rx.created_at).isoformat() if (rx.dispensed_at or rx.created_at) else None
            })

        # Payments
        from backend.models.payment import Payment
        for pay in Payment.query.filter_by(patient_id=patient_id).all():
            events.append({
                'type': 'payment',
                'icon': '✅',
                'title': 'Payment ' + (pay.payment_status or 'pending').capitalize(),
                'detail': f"ETB {pay.total_amount:.2f}" if pay.total_amount else '',
                'status': pay.payment_status or 'pending',
                'date': pay.created_at.isoformat() if pay.created_at else None
            })

        # Sort newest first, nulls last
        events.sort(key=lambda e: e['date'] or '', reverse=True)

        return jsonify({'success': True, 'timeline': events}), 200

    except Exception as e:
        return jsonify({'success': False, 'message': 'Error fetching timeline', 'error': str(e)}), 500


# ============ IN-APP NOTIFICATIONS ENDPOINTS ============

@patient_bp.route('/notifications', methods=['GET'])
@token_required
def get_notifications(current_user):
    """GET /api/patient/notifications — list in-app notifications."""
    try:
        from backend.models.notification import Notification
        notifs = Notification.query.filter_by(user_id=current_user['id'])\
            .order_by(Notification.created_at.desc()).limit(50).all()
        unread = Notification.query.filter_by(user_id=current_user['id'], is_read=False).count()
        return jsonify({
            'success': True,
            'notifications': [n.to_dict() for n in notifs],
            'unread_count': unread
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@patient_bp.route('/notifications/<int:notif_id>/read', methods=['PUT'])
@token_required
def mark_notification_read(current_user, notif_id):
    """PUT /api/patient/notifications/<id>/read — mark one notification as read."""
    try:
        from backend.models.notification import Notification
        n = Notification.query.filter_by(id=notif_id, user_id=current_user['id']).first()
        if not n:
            return jsonify({'success': False, 'message': 'Notification not found'}), 404
        n.is_read = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Marked as read'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@patient_bp.route('/notifications/read-all', methods=['PUT'])
@token_required
def mark_all_notifications_read(current_user):
    """PUT /api/patient/notifications/read-all — mark all notifications as read."""
    try:
        from backend.models.notification import Notification
        Notification.query.filter_by(user_id=current_user['id'], is_read=False)\
            .update({'is_read': True})
        db.session.commit()
        return jsonify({'success': True, 'message': 'All notifications marked as read'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============ PAYMENT-LOCKED REPORT ENDPOINTS ============

@patient_bp.route('/report/locked', methods=['GET'])
@token_required
def report_access_check(current_user):
    """
    GET /api/patient/report/locked
    Returns whether the patient can access the full report (requires payment).
    """
    paid = _has_paid(current_user['id'])
    return jsonify({
        'success': True,
        'has_access': paid,
        'message': 'Access granted.' if paid else 'Payment required to download your report.'
    }), 200
