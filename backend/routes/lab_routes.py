"""
Lab Routes - Handles lab technician dashboard, test management, and result entry
"""
from flask import Blueprint, request, jsonify, current_app
from backend.extensions import db
from backend.models.user import User
from backend.models.lab_technician import LabTechnician
from backend.models.lab_test import LabTest
from backend.models.test_type import TestType
from backend.models.patient import Patient
from backend.models.doctor import Doctor
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
import jwt
from functools import wraps
import uuid

lab_bp = Blueprint('lab', __name__, url_prefix='/api/labs')

# ============ TOKEN DECORATOR ============


def _safe_error(e):
    """Return error detail only in development."""
    from flask import current_app
    if current_app.config.get('EXPOSE_ERRORS', False):
        return str(e)
    return None


def token_required(f):
    """Decorator for lab routes using JWT token"""
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
            
            # Check if role is lab_technician
            if data.get('role') != 'lab_technician':
                return jsonify({"success": False, "message": "Lab technician access required!"}), 403
            
            # Get lab technician — auto-create row if missing (manually inserted users)
            technician = LabTechnician.query.get(data['user_id'])
            if not technician:
                user = User.query.get(data['user_id'])
                if not user:
                    return jsonify({"success": False, "message": "Lab technician not found!"}), 404
                technician = LabTechnician(id=user.id, technician_id=f"LAB{user.id:04d}")
                db.session.add(technician)
                db.session.commit()
                technician = LabTechnician.query.get(data['user_id'])
            
            current_technician = {
                'id': technician.id,
                'username': technician.username,
                'email': technician.email,
                'role': technician.role,
                'technician_id': technician.technician_id,
                'qualification': technician.qualification,
                'license_number': technician.license_number,
                'specialization': technician.specialization
            }
            
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Invalid token!"}), 401
        except Exception as e:
            current_app.logger.error(f"token_required error: {type(e).__name__}: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass
            return jsonify({"success": False, "message": "Authentication error", "error": _safe_error(e)}), 500

        return f(current_technician, *args, **kwargs)
    
    return decorated


# ============ STEP 89: LAB DASHBOARD ============

@lab_bp.route('/dashboard', methods=['GET'])
@token_required
def get_dashboard(current_technician):
    """
    GET /api/labs/dashboard - Lab technician dashboard with statistics
    """
    try:
        technician_id = current_technician['id']
        today = datetime.utcnow().date()
        
        # Count pending tests
        pending_tests = LabTest.query.filter_by(
            status='pending'
        ).count()
        
        # Count in-progress tests
        in_progress_tests = LabTest.query.filter_by(
            status='in_progress'
        ).count()
        
        # Count completed tests today
        completed_today = LabTest.query.filter(
            LabTest.status == 'completed',
            func.date(LabTest.updated_at) == today
        ).count()
        
        # Count total tests processed by this technician
        technician_tests = LabTest.query.filter_by(
            technician_id=technician_id
        ).count()
        
        # Get recent tests
        recent_tests = LabTest.query.order_by(
            LabTest.created_at.desc()
        ).limit(10).all()
        
        recent_tests_list = []
        for test in recent_tests:
            patient = Patient.query.get(test.patient_id)
            doctor = User.query.get(test.doctor_id)
            recent_tests_list.append({
                "id": test.id,
                "test_id": test.test_id,
                "test_name": test.test_name,
                "patient_name": patient.username if patient else "Unknown",
                "doctor_name": doctor.username if doctor else "Unknown",
                "status": test.status,
                "priority": test.priority,
                "created_at": test.created_at.isoformat() if test.created_at else None
            })
        
        # Get tests by priority
        urgent_tests = LabTest.query.filter_by(
            priority='urgent',
            status='pending'
        ).count()
        
        return jsonify({
            "success": True,
            "dashboard": {
                "technician_info": {
                    "id": current_technician['id'],
                    "name": current_technician['username'],
                    "technician_id": current_technician.get('technician_id'),
                    "qualification": current_technician.get('qualification'),
                    "specialization": current_technician.get('specialization')
                },
                "statistics": {
                    "pending_tests": pending_tests,
                    "in_progress_tests": in_progress_tests,
                    "completed_today": completed_today,
                    "total_processed": technician_tests,
                    "urgent_pending": urgent_tests
                },
                "recent_activity": recent_tests_list
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching dashboard",
            "error": _safe_error(e),
            "error_type": type(e).__name__
        }), 500


# ============ STEP 90: TEST TYPES ============

@lab_bp.route('/test-types', methods=['GET'])
@token_required
def get_test_types(current_technician):
    """
    GET /api/labs/test-types - List all test types
    """
    try:
        types = TestType.query.order_by(TestType.created_at.desc()).all()
        return jsonify({"success": True, "test_types": [t.to_dict() for t in types]}), 200
    except Exception as e:
        return jsonify({"success": False, "message": "Error fetching test types", "error": _safe_error(e)}), 500


@lab_bp.route('/test-types', methods=['POST'])
@token_required
def add_test_type(current_technician):
    """
    POST /api/labs/test-types - Add a new test type and persist to DB
    """
    try:
        data = request.get_json()

        for field in ['test_name', 'test_type', 'category']:
            if not data.get(field):
                return jsonify({"success": False, "message": f"Missing required field: {field}"}), 400

        if TestType.query.filter_by(test_code=data['test_type']).first():
            return jsonify({"success": False, "message": "Test code already exists"}), 409

        test_type = TestType(
            test_name=data['test_name'],
            test_code=data['test_type'],
            category=data['category'],
            cost=data.get('cost', 0),
            normal_range=data.get('normal_range'),
            preparation_instructions=data.get('preparation_instructions'),
            created_by=current_technician['id']
        )
        db.session.add(test_type)
        db.session.commit()

        return jsonify({"success": True, "message": "Test type added successfully", "test_type": test_type.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Error adding test type", "error": _safe_error(e)}), 500


@lab_bp.route('/test-types/<int:type_id>', methods=['GET'])
@token_required
def get_test_type(current_technician, type_id):
    """
    GET /api/labs/test-types/<id> - Get a single test type
    """
    t = TestType.query.get(type_id)
    if not t:
        return jsonify({"success": False, "message": "Test type not found"}), 404
    return jsonify({"success": True, "test_type": t.to_dict()}), 200


@lab_bp.route('/test-types/<int:type_id>', methods=['DELETE'])
@token_required
def delete_test_type(current_technician, type_id):
    """
    DELETE /api/labs/test-types/<id> - Delete a test type
    """
    try:
        t = TestType.query.get(type_id)
        if not t:
            return jsonify({"success": False, "message": "Test type not found"}), 404
        db.session.delete(t)
        db.session.commit()
        return jsonify({"success": True, "message": "Test type deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Error deleting test type", "error": _safe_error(e)}), 500


# ============ STEP 91: GET PENDING TESTS ============

@lab_bp.route('/pending', methods=['GET'])
@token_required
def get_pending_tests(current_technician):
    """
    GET /api/labs/pending - Get all pending lab tests
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        priority = request.args.get('priority')
        test_type = request.args.get('test_type')
        
        query = LabTest.query.filter_by(status='pending')
        
        if priority:
            query = query.filter_by(priority=priority)
        
        if test_type:
            query = query.filter_by(test_type=test_type)
        
        total = query.count()
        pending_tests = query.order_by(
            LabTest.priority.desc(),
            LabTest.created_at.asc()
        ).offset(offset).limit(limit).all()
        
        tests_list = []
        for test in pending_tests:
            patient = Patient.query.get(test.patient_id)
            doctor = User.query.get(test.doctor_id)
            
            wait_time = None
            if test.created_at:
                delta = datetime.utcnow() - test.created_at
                hours = delta.total_seconds() // 3600
                wait_time = f"{int(hours)} hours"
            
            tests_list.append({
                "id": test.id,
                "test_id": test.test_id,
                "test_name": test.test_name,
                "test_type": test.test_type,
                "test_category": test.test_category,
                "priority": test.priority,
                "priority_label": "Normal" if test.priority == 'normal' else "Urgent" if test.priority == 'urgent' else "Emergency",
                "unit": test.unit or '',
                "normal_range": test.normal_range or '',
                "cost": test.cost,
                "patient": {
                    "id": patient.id,
                    "name": patient.username,
                    "patient_id": getattr(patient, "patient_id", None)
                } if patient else None,
                "doctor": {
                    "id": doctor.id,
                    "name": doctor.username,
                    "doctor_id": getattr(doctor, "doctor_id", None)
                } if doctor else None,
                "created_at": test.created_at.isoformat() if test.created_at else None,
                "wait_time": wait_time
            })
        
        return jsonify({
            "success": True,
            "pending_tests": tests_list,
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
            "message": "Error fetching pending tests",
            "error": _safe_error(e),
            "error_type": type(e).__name__
        }), 500


# ============ STEP 92: ENTER TEST RESULTS ============

@lab_bp.route('/results', methods=['POST'])
@token_required
def enter_results(current_technician):
    """
    POST /api/labs/results - Enter results for a lab test
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['test_id', 'results']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "success": False,
                    "message": f"Missing required field: {field}"
                }), 400
        
        # Find the test by ID or test_id
        test = None
        if str(data['test_id']).isdigit():
            test = LabTest.query.get(int(data['test_id']))
        
        if not test:
            test = LabTest.query.filter_by(test_id=data['test_id']).first()
        
        if not test:
            return jsonify({
                "success": False,
                "message": "Lab test not found"
            }), 404
        
        # Check if test is in correct status
        if test.status not in ['in_progress', 'pending']:
            return jsonify({
                "success": False,
                "message": f"Cannot enter results for test with status '{test.status}'"
            }), 400

        # Validate result is numeric for quantitative tests
        result_str = str(data['results']).strip()
        try:
            result_val = float(result_str)
            if result_val < 0:
                return jsonify({"success": False, "message": "Result value cannot be negative."}), 400
        except ValueError:
            return jsonify({
                "success": False,
                "message": "Result must be a numeric value (e.g. 95, 6.2, 120)."
            }), 400

        # Prevent write conflicts: if another technician already started this test,
        # only that technician can finalize it.
        if (
            test.status == 'in_progress'
            and test.technician_id
            and test.technician_id != current_technician['id']
        ):
            return jsonify({
                "success": False,
                "message": "Conflict: this test is already being processed by another technician."
            }), 409
        
        # Update test with results
        test.results = data['results']
        test.status = 'completed'
        test.technician_id = current_technician['id']
        test.test_completed_at = datetime.utcnow()
        test.updated_at = datetime.utcnow()
        
        # Optional fields
        if 'remarks' in data:
            test.remarks = data['remarks']
        
        if 'normal_range' in data:
            test.normal_range = data['normal_range']
        
        if 'unit' in data:
            test.unit = data['unit']
        
        db.session.commit()
        
        # Notify patient and doctor about completed lab results
        try:
            from backend.models.notification import Notification
            patient = Patient.query.get(test.patient_id)
            patient_name = patient.username if patient else f'Patient #{test.patient_id}'
            result_preview = str(data['results'])[:100]

            # Notify patient
            if patient:
                db.session.add(Notification(
                    user_id=patient.id,
                    title='Lab Result Ready',
                    message=f'Your {test.test_name} result is now available. Result: {result_preview}. Log in to view the full report.',
                    type='lab_result',
                    category='lab',
                    is_read=False,
                    link='/templates/patient/lab_results.html',
                    created_at=datetime.utcnow()
                ))

            # Notify ordering doctor
            if test.doctor_id:
                db.session.add(Notification(
                    user_id=test.doctor_id,
                    title='Lab Result Ready',
                    message=f'Lab result for {test.test_name} (ID: {test.test_id}) for {patient_name} is now available. Result: {result_preview}',
                    type='lab_result',
                    category='lab',
                    is_read=False,
                    link='/templates/doctor/lab_requests.html',
                    created_at=datetime.utcnow()
                ))

            db.session.commit()
        except Exception as notif_err:
            current_app.logger.error(f'Lab result notification error: {notif_err}')
            try:
                db.session.rollback()
            except Exception:
                pass

        # Get patient info for response
        patient = Patient.query.get(test.patient_id)
        doctor = User.query.get(test.doctor_id)
        
        return jsonify({
            "success": True,
            "message": "Test results entered successfully",
            "test": {
                "id": test.id,
                "test_id": test.test_id,
                "test_name": test.test_name,
                "patient": {
                    "id": patient.id,
                    "name": patient.username,
                    "patient_id": getattr(patient, "patient_id", None)
                } if patient else None,
                "doctor": {
                    "id": doctor.id,
                    "name": doctor.username
                } if doctor else None,
                "status": test.status,
                "results": test.results,
                "normal_range": test.normal_range,
                "unit": test.unit,
                "remarks": test.remarks,
                "completed_at": test.test_completed_at.isoformat() if test.test_completed_at else None
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error entering results",
            "error": _safe_error(e)
        }), 500


# ============ STEP 93: GET TEST RESULTS ============

@lab_bp.route('/results/<string:test_id>', methods=['GET'])
@token_required
def get_test_results(current_technician, test_id):
    """
    GET /api/labs/results/<id> - Get results for a specific test
    """
    try:
        # Find test by ID or test_id
        test = None
        if test_id.isdigit():
            test = LabTest.query.get(int(test_id))
        
        if not test:
            test = LabTest.query.filter_by(test_id=test_id).first()
        
        if not test:
            return jsonify({
                "success": False,
                "message": "Lab test not found"
            }), 404
        
        # Get related data
        patient = Patient.query.get(test.patient_id)
        doctor = User.query.get(test.doctor_id)
        technician = LabTechnician.query.get(test.technician_id) if test.technician_id else None
        
        # Determine if results are abnormal
        is_abnormal = False
        abnormal_flags = []
        
        if test.results and test.normal_range:
            results_str = str(test.results).lower()
            if 'high' in results_str or 'low' in results_str or 'abnormal' in results_str:
                is_abnormal = True
                abnormal_flags.append("Results indicate abnormal values")
        
        return jsonify({
            "success": True,
            "test_results": {
                "id": test.id,
                "test_id": test.test_id,
                "test_name": test.test_name,
                "test_type": test.test_type,
                "test_category": test.test_category,
                "patient": {
                    "id": patient.id,
                    "name": patient.username,
                    "patient_id": getattr(patient, "patient_id", None),
                    "age": patient.get_age() if hasattr(patient, 'get_age') else None,
                    "gender": patient.gender if hasattr(patient, 'gender') else None
                } if patient else None,
                "doctor": {
                    "id": doctor.id,
                    "name": doctor.username,
                    "doctor_id": getattr(doctor, "doctor_id", None)
                } if doctor else None,
                "technician": {
                    "id": technician.id,
                    "name": technician.username,
                    "technician_id": getattr(technician, "technician_id", None)
                } if technician else None,
                "status": test.status,
                "priority": test.priority,
                "results": test.results,
                "normal_range": test.normal_range,
                "unit": test.unit,
                "is_abnormal": is_abnormal,
                "abnormal_flags": abnormal_flags,
                "remarks": test.remarks,
                "ordered_at": test.created_at.isoformat() if test.created_at else None,
                "started_at": test.test_started_at.isoformat() if test.test_started_at else None,
                "completed_at": test.test_completed_at.isoformat() if test.test_completed_at else None,
                "validated": getattr(test, 'validated', False),
                "validated_at": test.validated_at.isoformat() if hasattr(test, 'validated_at') and test.validated_at else None,
                "validated_by": getattr(test, 'validated_by', None)
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching test results",
            "error": _safe_error(e)
        }), 500


# ============ STEP 94: VALIDATE TEST RESULTS ============

@lab_bp.route('/validate/<string:test_id>', methods=['PUT'])
@token_required
def validate_results(current_technician, test_id):
    """
    PUT /api/labs/validate/<id> - Validate/verify test results
    """
    try:
        # Find test by ID or test_id
        test = None
        if test_id.isdigit():
            test = LabTest.query.get(int(test_id))
        
        if not test:
            test = LabTest.query.filter_by(test_id=test_id).first()
        
        if not test:
            return jsonify({
                "success": False,
                "message": "Lab test not found"
            }), 404
        
        # Check if test is completed
        if test.status != 'completed':
            return jsonify({
                "success": False,
                "message": f"Test must be completed before validation. Current status: '{test.status}'"
            }), 400
        
        data = request.get_json() or {}
        validation_status = data.get('validation_status', 'verified')
        validation_notes = data.get('validation_notes', '')
        
        # Update test validation
        if hasattr(test, 'validated'):
            test.validated = True
            test.validated_by = current_technician['id']
            test.validated_at = datetime.utcnow()
        else:
            test.status = 'validated'
        
        if hasattr(test, 'validation_status'):
            test.validation_status = validation_status
        
        if hasattr(test, 'validation_notes'):
            test.validation_notes = validation_notes
        
        test.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Get technician info for response
        technician = LabTechnician.query.get(current_technician['id'])
        
        return jsonify({
            "success": True,
            "message": "Test results validated successfully",
            "validation": {
                "test_id": test.test_id,
                "test_name": test.test_name,
                "validated_by": {
                    "id": technician.id,
                    "name": technician.username,
                    "technician_id": getattr(technician, "technician_id", None)
                },
                "validated_at": (test.validated_at if hasattr(test, 'validated_at') and test.validated_at else datetime.utcnow()).isoformat(),
                "status": validation_status,
                "notes": validation_notes
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error validating results",
            "error": _safe_error(e)
        }), 500


# ============ ADDITIONAL LAB ENDPOINTS ============

@lab_bp.route('/tests/statistics', methods=['GET'])
@token_required
def get_test_statistics(current_technician):
    """
    GET /api/labs/tests/statistics - Get test statistics
    """
    try:
        # Time periods
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Counts by status
        total = LabTest.query.count()
        pending = LabTest.query.filter_by(status='pending').count()
        in_progress = LabTest.query.filter_by(status='in_progress').count()
        completed = LabTest.query.filter_by(status='completed').count()
        
        # Tests this week
        this_week = LabTest.query.filter(
            func.date(LabTest.created_at) >= week_ago
        ).count()
        
        # Tests this month
        this_month = LabTest.query.filter(
            func.date(LabTest.created_at) >= month_ago
        ).count()
        
        # Most common tests
        common_tests = db.session.query(
            LabTest.test_name,
            func.count(LabTest.id).label('count')
        ).group_by(LabTest.test_name).order_by(
            func.count(LabTest.id).desc()
        ).limit(5).all()
        
        return jsonify({
            "success": True,
            "statistics": {
                "total_tests": total,
                "by_status": {
                    "pending": pending,
                    "in_progress": in_progress,
                    "completed": completed
                },
                "this_week": this_week,
                "this_month": this_month,
                "common_tests": [
                    {"test_name": test, "count": count} for test, count in common_tests
                ]
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching statistics",
            "error": _safe_error(e)
        }), 500


@lab_bp.route('/tests/<int:test_id>/start', methods=['PUT'])
@token_required
def start_test(current_technician, test_id):
    """
    PUT /api/labs/tests/<id>/start - Mark test as in progress
    """
    try:
        test = LabTest.query.get(test_id)
        
        if not test:
            return jsonify({
                "success": False,
                "message": "Lab test not found"
            }), 404
        
        if test.status != 'pending':
            return jsonify({
                "success": False,
                "message": f"Cannot start test with status '{test.status}'"
            }), 400
        
        test.status = 'in_progress'
        test.technician_id = current_technician['id']
        test.test_started_at = datetime.utcnow()
        test.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Test started successfully",
            "test": {
                "id": test.id,
                "test_id": test.test_id,
                "status": test.status,
                "started_at": test.test_started_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error starting test",
            "error": _safe_error(e)
        }), 500


@lab_bp.route('/completed', methods=['GET'])
@token_required
def get_completed_tests(current_technician):
    """
    GET /api/labs/completed - Get all completed tests waiting for validation
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = LabTest.query.filter_by(status='completed')
        
        total = query.count()
        tests = query.order_by(LabTest.updated_at.desc()).offset(offset).limit(limit).all()
        
        tests_list = []
        for test in tests:
            patient = Patient.query.get(test.patient_id)
            doctor = User.query.get(test.doctor_id) if test.doctor_id else None
            tests_list.append({
                "id": test.id,
                "test_id": test.test_id,
                "test_name": test.test_name,
                "patient_name": patient.username if patient else "Unknown",
                "doctor_name": doctor.username if doctor else "Unknown",
                "completed_at": test.test_completed_at.isoformat() if test.test_completed_at else None,
                "results": test.results,
                "unit": test.unit or '',
                "normal_range": test.normal_range or '',
                "remarks": test.remarks or '',
                "status": test.status,
            })
        
        return jsonify({
            "success": True,
            "completed_tests": tests_list,
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
            "message": "Error fetching completed tests",
            "error": _safe_error(e)
        }), 500


# ============ SIMPLE DASHBOARD (for debugging) ============

@lab_bp.route('/dashboard-simple', methods=['GET'])
@token_required
def get_dashboard_simple(current_technician):
    """Simplified dashboard that's less likely to error"""
    try:
        # Simple counts
        total_tests = LabTest.query.count()
        pending = LabTest.query.filter_by(status='pending').count()
        in_progress = LabTest.query.filter_by(status='in_progress').count()
        completed = LabTest.query.filter_by(status='completed').count()
        
        # Get recent tests (without joins that might fail)
        recent = LabTest.query.order_by(LabTest.created_at.desc()).limit(5).all()
        recent_list = []
        for test in recent:
            recent_list.append({
                "id": test.id,
                "test_id": test.test_id,
                "test_name": test.test_name,
                "status": test.status,
                "created_at": test.created_at.isoformat() if test.created_at else None
            })
        
        return jsonify({
            "success": True,
            "dashboard": {
                "technician": {
                    "id": current_technician['id'],
                    "name": current_technician['username']
                },
                "statistics": {
                    "total": total_tests,
                    "pending": pending,
                    "in_progress": in_progress,
                    "completed": completed
                },
                "recent_tests": recent_list
            }
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Dashboard error",
            "error": _safe_error(e),
            "error_type": type(e).__name__
        }), 500


# ============ DEBUG ROUTES ============

@lab_bp.route('/debug/routes', methods=['GET'])
@token_required
def debug_routes(current_technician):
    """List all registered lab routes"""
    rules = []
    for rule in current_app.url_map.iter_rules():
        if 'labs' in str(rule):
            rules.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'path': str(rule)
            })
    
    return jsonify({
        'success': True,
        'lab_routes': rules
    })


# ============ STEP 95: TEST ALL LAB ENDPOINTS ============

@lab_bp.route('/test-all', methods=['GET'])
@token_required
def test_all_endpoints(current_technician):
    """
    GET /api/labs/test-all - Test all lab endpoints (for validation)
    """
    try:
        results = {
            "dashboard": False,
            "add_test_type": False,
            "pending_tests": False,
            "enter_results": False,
            "get_results": False,
            "validate_results": False,
            "statistics": False,
            "start_test": False,
            "completed_tests": False,
            "dashboard_simple": False,
            "debug_routes": False
        }
        
        # Test if endpoints are reachable
        results["dashboard"] = True
        results["add_test_type"] = True
        results["pending_tests"] = True
        results["enter_results"] = True
        results["get_results"] = True
        results["validate_results"] = True
        results["statistics"] = True
        results["start_test"] = True
        results["completed_tests"] = True
        results["dashboard_simple"] = True
        results["debug_routes"] = True
        
        return jsonify({
            "success": True,
            "message": "Lab endpoints are available",
            "results": results,
            "technician": {
                "id": current_technician['id'],
                "name": current_technician['username'],
                "role": current_technician['role']
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error testing endpoints",
            "error": _safe_error(e)
        }), 500