"""
Admin Routes - Handles admin dashboard, user management, and system statistics
"""

from flask import Blueprint, request, jsonify, current_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.doctor import Doctor
from backend.models.prediction import Prediction
from backend.utils.decorators import role_required
from datetime import datetime, timedelta
from sqlalchemy import func, desc
import jwt
from functools import wraps

import json
from pathlib import Path

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

MODEL_REGISTRY_PATH = Path(__file__).parent.parent.parent / 'ml_model' / 'model_registry.json'

def _load_registry():
    if MODEL_REGISTRY_PATH.exists():
        with open(MODEL_REGISTRY_PATH, 'r') as f:
            return json.load(f)
    # Seed from model_metadata.json on first run
    metadata_path = Path(__file__).parent.parent.parent / 'ml_model' / 'saved_models' / 'model_metadata.json'
    models = []
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            meta = json.load(f)
        algo_map = {'logistic_regression': 'Logistic Regression', 'random_forest': 'Random Forest'}
        for key, info in meta.items():
            if key in algo_map and isinstance(info, dict) and 'accuracy' in info:
                models.append({
                    'id': len(models) + 1,
                    'version': 'v1.0.' + str(len(models)),
                    'algorithm': algo_map[key],
                    'accuracy': round(info['accuracy'] * 100, 2),
                    'precision': round(info.get('precision', 0) * 100, 2),
                    'recall': round(info.get('recall', 0) * 100, 2),
                    'f1Score': round(info.get('f1', 0) * 100, 2),
                    'trainingSamples': 614,
                    'features': len(meta.get('features', [])) or 8,
                    'date': info.get('train_date', '')[:10],
                    'status': 'active' if key == 'logistic_regression' else 'archived',
                    'notes': 'Seeded from training metadata.'
                })
    if not models:
        models = [{'id': 1, 'version': 'v1.0.0', 'algorithm': 'Logistic Regression',
                   'accuracy': 84.5, 'precision': 82.1, 'recall': 80.6, 'f1Score': 81.3,
                   'trainingSamples': 614, 'features': 8,
                   'date': '2026-03-06', 'status': 'active', 'notes': 'Initial model.'}]
    _save_registry(models)
    return models

def _save_registry(models):
    MODEL_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_REGISTRY_PATH, 'w') as f:
        json.dump(models, f, indent=2)

def admin_token_required(f):
    """Decorator for admin routes using JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({"success": False, "message": "Token is missing!"}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            
            # Check if role is admin
            if data.get('role') != 'admin':
                return jsonify({"success": False, "message": "Admin access required!"}), 403
            
            current_admin = User.query.get(data['user_id'])
            
            if not current_admin:
                return jsonify({"success": False, "message": "Invalid token!"}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Invalid token!"}), 401
            
        return f(current_admin, *args, **kwargs)
    
    return decorated


@admin_bp.route('/dashboard', methods=['GET'])
@admin_token_required
def get_dashboard(current_admin):
    """Get admin dashboard with system statistics"""
    try:
        # Get counts
        total_users = User.query.count()
        total_patients = Patient.query.count()
        total_doctors = Doctor.query.count() if hasattr(Doctor, 'query') else 0
        total_predictions = Prediction.query.count()
        
        # Get recent users
        recent_users = User.query.order_by(desc(User.created_at)).limit(10).all()
        
        # Get user role distribution
        role_distribution = db.session.query(
            User.role, func.count(User.id)
        ).group_by(User.role).all()
        
        # Get average risk
        avg_risk = db.session.query(func.avg(Prediction.probability_percent)).scalar() or 0
        
        # Get today's activity
        today = datetime.utcnow().date()
        today_predictions = Prediction.query.filter(
            func.date(Prediction.created_at) == today
        ).count()
        
        today_registrations = User.query.filter(
            func.date(User.created_at) == today
        ).count()
        
        return jsonify({
            "success": True,
            "dashboard": {
                "statistics": {
                    "total_users": total_users,
                    "total_patients": total_patients,
                    "total_doctors": total_doctors,
                    "total_predictions": total_predictions,
                    "average_risk_percentage": round(avg_risk, 2)
                },
                "role_distribution": [
                    {"role": role, "count": count} for role, count in role_distribution
                ],
                "recent_users": [
                    {
                        "id": u.id,
                        "username": u.username,
                        "email": u.email,
                        "role": u.role,
                        "created_at": u.created_at.isoformat() if u.created_at else None
                    } for u in recent_users
                ],
                "today_activity": {
                    "predictions": today_predictions,
                    "new_registrations": today_registrations,
                    "date": today.isoformat()
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching dashboard",
            "error": str(e)
        }), 500


@admin_bp.route('/users', methods=['GET'])
@admin_token_required
def get_users(current_admin):
    """Get all users with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        role_filter = request.args.get('role')
        
        query = User.query
        
        if role_filter:
            query = query.filter_by(role=role_filter)
        
        paginated = query.order_by(desc(User.created_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            "success": True,
            "users": [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "role": u.role,
                    "is_active": getattr(u, 'is_active', True),
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                    "last_login": u.last_login.isoformat() if u.last_login else None
                } for u in paginated.items
            ],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": paginated.total,
                "pages": paginated.pages,
                "has_next": paginated.has_next,
                "has_prev": paginated.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching users",
            "error": str(e)
        }), 500


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_token_required
def get_user(current_admin, user_id):
    """Get detailed user information"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404
        
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": getattr(user, 'is_active', True),
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
        
        # Add patient-specific data if applicable
        if user.role == 'patient':
            patient = Patient.query.get(user.id)
            if patient:
                user_data['patient_details'] = {
                    "patient_id": getattr(patient, 'patient_id', None),
                    "blood_group": getattr(patient, 'blood_group', None),
                    "emergency_contact": getattr(patient, 'emergency_contact', None)
                }
        
        return jsonify({
            "success": True,
            "user": user_data
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching user",
            "error": str(e)
        }), 500


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_token_required
def delete_user(current_admin, user_id):
    """Delete a user by ID"""
    try:
        # Prevent admin from deleting themselves
        if user_id == current_admin.id:
            return jsonify({
                "success": False,
                "message": "Admin cannot delete their own account"
            }), 400
        
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"User {user.username} deleted successfully"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error deleting user",
            "error": str(e)
        }), 500


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_token_required
def toggle_user_status(current_admin, user_id):
    """Activate or deactivate a user"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404
        
        data = request.get_json() or {}
        
        if 'is_active' in data:
            user.is_active = data['is_active']
            db.session.commit()
            
            status = "activated" if user.is_active else "deactivated"
            
            return jsonify({
                "success": True,
                "message": f"User {status} successfully",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "is_active": user.is_active
                }
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Missing is_active field"
            }), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error updating user status",
            "error": str(e)
        }), 500


@admin_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@admin_token_required
def change_user_role(current_admin, user_id):
    """Change user role"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404
        
        data = request.get_json()
        
        if not data or 'role' not in data:
            return jsonify({
                "success": False,
                "message": "Missing role field"
            }), 400
        
        new_role = data['role']
        valid_roles = ['patient', 'doctor', 'nurse', 'lab_technician', 'pharmacist', 'admin']
        
        if new_role not in valid_roles:
            return jsonify({
                "success": False,
                "message": f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            }), 400
        
        old_role = user.role
        user.role = new_role
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"User role changed from {old_role} to {new_role}",
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error changing user role",
            "error": str(e)
        }), 500


@admin_bp.route('/statistics', methods=['GET'])
@admin_token_required
def get_statistics(current_admin):
    """Get system-wide statistics"""
    try:
        total_users = User.query.count()
        total_patients = Patient.query.count()
        total_doctors = Doctor.query.count() if hasattr(Doctor, 'query') else 0
        total_predictions = Prediction.query.count()
        
        # Risk distribution
        risk_distribution = db.session.query(
            Prediction.risk_level, func.count(Prediction.id)
        ).group_by(Prediction.risk_level).all()
        
        # Convert to dictionary with proper risk levels
        risk_counts = {level: count for level, count in risk_distribution}
        
        return jsonify({
            "success": True,
            "statistics": {
                "total_users": total_users,
                "total_patients": total_patients,
                "total_doctors": total_doctors,
                "total_predictions": total_predictions,
                "risk_distribution": {
                    "LOW RISK": risk_counts.get('LOW RISK', 0),
                    "MODERATE RISK": risk_counts.get('MODERATE RISK', 0),
                    "HIGH RISK": risk_counts.get('HIGH RISK', 0),
                    "VERY HIGH RISK": risk_counts.get('VERY HIGH RISK', 0)
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching statistics",
            "error": str(e)
        }), 500


@admin_bp.route('/models', methods=['GET'])
@admin_token_required
def get_models(current_admin):
    models = _load_registry()
    return jsonify({'success': True, 'models': models}), 200


@admin_bp.route('/models/upload', methods=['POST'])
@admin_token_required
def upload_model_file(current_admin):
    """Upload a new .pkl model file and register it"""
    try:
        import os
        from werkzeug.utils import secure_filename

        if 'model_file' not in request.files:
            return jsonify({'success': False, 'message': 'No model file provided'}), 400

        file = request.files['model_file']
        if not file.filename:
            return jsonify({'success': False, 'message': 'No file selected'}), 400

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ['.pkl', '.h5']:
            return jsonify({'success': False, 'message': 'Only .pkl or .h5 files allowed'}), 400

        version   = request.form.get('version', '').strip()
        algorithm = request.form.get('algorithm', 'Custom Model')
        accuracy  = float(request.form.get('accuracy', 0))
        precision = float(request.form.get('precision', 0))
        recall    = float(request.form.get('recall', 0))
        f1_score  = float(request.form.get('f1Score', 0))
        notes     = request.form.get('notes', '')
        set_active = request.form.get('setActive', 'false').lower() == 'true'

        if not version:
            return jsonify({'success': False, 'message': 'Version is required'}), 400

        models = _load_registry()
        if any(m['version'] == version for m in models):
            return jsonify({'success': False, 'message': f'Version {version} already exists'}), 400

        # Map algorithm name to filename
        SAVE_DIR = Path(__file__).parent.parent.parent / 'ml_model' / 'saved_models'
        algo_file_map = {
            'Logistic Regression':          'logistic_regression.pkl',
            'Logistic Regression Tuned':    'logistic_regression_tuned.pkl',
            'Random Forest':                'random_forest.pkl',
            'Gradient Boosting':            'gradient_boosting.pkl',
            'XGBoost':                      'xgboost.pkl',
            'SVM':                          'svm.pkl',
            'Neural Network':               'neural_network.pkl',
        }
        # Use mapped name or sanitize custom name
        save_filename = algo_file_map.get(algorithm)
        if not save_filename:
            safe = secure_filename(algorithm.lower().replace(' ', '_'))
            save_filename = f'{safe}{ext}'

        save_path = SAVE_DIR / save_filename
        file.save(str(save_path))

        # Validate the saved file loads correctly
        try:
            import joblib
            test_model = joblib.load(str(save_path))
            if not hasattr(test_model, 'predict'):
                os.remove(str(save_path))
                return jsonify({'success': False, 'message': 'Invalid model file — no predict() method found'}), 400
        except Exception as e:
            try: os.remove(str(save_path))
            except: pass
            return jsonify({'success': False, 'message': f'Model file is invalid or incompatible: {str(e)}'}), 400

        # Register the model
        if set_active:
            for m in models:
                m['status'] = 'archived'

        new_id = max((m['id'] for m in models), default=0) + 1
        new_model = {
            'id': new_id,
            'version': version,
            'algorithm': algorithm,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1Score': f1_score,
            'trainingSamples': int(request.form.get('trainingSamples', 0)),
            'features': int(request.form.get('features', 8)),
            'date': datetime.utcnow().date().isoformat(),
            'status': 'active' if set_active else 'archived',
            'notes': notes,
            'filename': save_filename
        }
        models.insert(0, new_model)
        _save_registry(models)

        # Reload ML service if set as active
        if set_active:
            try:
                from backend.services.ml_service import get_ml_service
                get_ml_service(force_reload=True)
            except Exception:
                pass

        return jsonify({
            'success': True,
            'message': f'{algorithm} v{version} uploaded and registered successfully',
            'model': new_model
        }), 201

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/models', methods=['POST'])
@admin_token_required
def create_model(current_admin):
    data = request.get_json()
    if not data or not data.get('version'):
        return jsonify({'success': False, 'message': 'Version is required'}), 400
    models = _load_registry()
    if any(m['version'] == data['version'] for m in models):
        return jsonify({'success': False, 'message': f"Version {data['version']} already exists"}), 400
    set_active = data.get('setActive', False)
    if set_active:
        for m in models:
            m['status'] = 'archived'
    new_id = max((m['id'] for m in models), default=0) + 1
    model = {
        'id': new_id,
        'version': data['version'],
        'algorithm': data.get('algorithm', 'Logistic Regression'),
        'accuracy': float(data.get('accuracy', 0)),
        'precision': float(data.get('precision', 0)),
        'recall': float(data.get('recall', 0)),
        'f1Score': float(data.get('f1Score', 0)),
        'trainingSamples': int(data.get('trainingSamples', 614)),
        'features': int(data.get('features', 8)),
        'date': data.get('date', datetime.utcnow().date().isoformat()),
        'status': 'active' if set_active else 'archived',
        'notes': data.get('notes', '')
    }
    models.insert(0, model)
    _save_registry(models)
    return jsonify({'success': True, 'model': model}), 201


@admin_bp.route('/models/<int:model_id>', methods=['PUT'])
@admin_token_required
def update_model(current_admin, model_id):
    data = request.get_json()
    models = _load_registry()
    idx = next((i for i, m in enumerate(models) if m['id'] == model_id), None)
    if idx is None:
        return jsonify({'success': False, 'message': 'Model not found'}), 404
    for field in ['version', 'algorithm', 'accuracy', 'precision', 'recall', 'f1Score',
                  'trainingSamples', 'features', 'date', 'notes']:
        if field in data:
            models[idx][field] = data[field]
    _save_registry(models)
    return jsonify({'success': True, 'model': models[idx]}), 200


@admin_bp.route('/models/<int:model_id>', methods=['DELETE'])
@admin_token_required
def delete_model(current_admin, model_id):
    models = _load_registry()
    model = next((m for m in models if m['id'] == model_id), None)
    if not model:
        return jsonify({'success': False, 'message': 'Model not found'}), 404
    if model['status'] == 'active':
        return jsonify({'success': False, 'message': 'Cannot delete the active model'}), 400
    models = [m for m in models if m['id'] != model_id]
    _save_registry(models)
    return jsonify({'success': True, 'message': 'Model deleted'}), 200


@admin_bp.route('/models/<int:model_id>/activate', methods=['POST'])
@admin_token_required
def activate_model(current_admin, model_id):
    models = _load_registry()
    if not any(m['id'] == model_id for m in models):
        return jsonify({'success': False, 'message': 'Model not found'}), 404
    for m in models:
        m['status'] = 'active' if m['id'] == model_id else 'archived'
    _save_registry(models)
    # Force ML service to reload with the newly activated model
    try:
        from backend.services.ml_service import get_ml_service
        get_ml_service(force_reload=True)
    except Exception:
        pass
    activated = next(m for m in models if m['id'] == model_id)
    return jsonify({'success': True, 'message': f"{activated['algorithm']} activated successfully"}), 200


@admin_bp.route('/reports/summary', methods=['GET'])
@admin_token_required
def get_reports_summary(current_admin):
    """Get summary stats for all report types"""
    try:
        from sqlalchemy import text
        today = datetime.utcnow().date()

        # User activity
        total_users = User.query.count()
        new_users_30d = User.query.filter(
            User.created_at >= datetime.utcnow() - timedelta(days=30)
        ).count()

        # Predictions
        total_predictions = Prediction.query.count()
        risk_dist = db.session.query(
            Prediction.risk_level, func.count(Prediction.id)
        ).group_by(Prediction.risk_level).all()

        # Financial - use raw SQL to avoid model import issues
        fin = db.session.execute(text(
            "SELECT COUNT(*), COALESCE(SUM(total_amount),0) FROM payments"
        )).fetchone()
        total_payments = fin[0]
        total_revenue = round(float(fin[1]), 2)

        # Security - audit logs
        sec = db.session.execute(text(
            "SELECT COUNT(*) FROM audit_logs"
        )).fetchone()
        total_audit = sec[0]
        failed_logins = db.session.execute(text(
            "SELECT COUNT(*) FROM audit_logs WHERE status='failed'"
        )).fetchone()[0]

        # Lab & prescriptions
        lab_count = db.session.execute(text("SELECT COUNT(*) FROM lab_tests")).fetchone()[0]
        rx_count = db.session.execute(text("SELECT COUNT(*) FROM prescriptions")).fetchone()[0]

        # Recent audit logs for security report
        recent_logs = db.session.execute(text(
            "SELECT username, user_role, action, resource, status, created_at "
            "FROM audit_logs ORDER BY created_at DESC LIMIT 10"
        )).fetchall()

        return jsonify({
            "success": True,
            "summary": {
                "user_activity": {
                    "total_users": total_users,
                    "new_users_30d": new_users_30d
                },
                "predictions": {
                    "total": total_predictions,
                    "risk_distribution": [
                        {"level": level, "count": count}
                        for level, count in risk_dist
                    ]
                },
                "financial": {
                    "total_payments": total_payments,
                    "total_revenue": total_revenue,
                    "lab_tests": lab_count,
                    "prescriptions": rx_count
                },
                "security": {
                    "total_audit_logs": total_audit,
                    "failed_logins": failed_logins,
                    "recent_logs": [
                        {
                            "username": r[0], "role": r[1], "action": r[2],
                            "resource": r[3], "status": r[4],
                            "date": r[5][:10] if r[5] else ""
                        } for r in recent_logs
                    ]
                }
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route('/system/health', methods=['GET'])
def system_health():
    """Public endpoint for system health check"""
    try:
        # Fix: Use text() for raw SQL in SQLAlchemy 2.0
        from sqlalchemy import text
        db.session.execute(text('SELECT 1')).fetchone()
        
        return jsonify({
            "success": True,
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }), 500


# ============ ADMIN SYSTEM REPORTS ============

# ============ ADMIN PAYMENT MANAGEMENT ============

@admin_bp.route('/payments', methods=['GET'])
@admin_token_required
def get_all_payments(current_admin):
    """List all payments with patient info, filters, pagination"""
    try:
        from backend.models.payment import Payment
        from backend.models.patient import Patient
        from backend.models.invoice import Invoice
        from sqlalchemy import text

        page      = request.args.get('page', 1, type=int)
        per_page  = request.args.get('per_page', 20, type=int)
        status    = request.args.get('status')
        method    = request.args.get('method')
        from_date = request.args.get('from_date')
        to_date   = request.args.get('to_date')
        search    = request.args.get('search', '').strip()

        query = Payment.query
        if status:
            query = query.filter(Payment.payment_status == status)
        if method:
            query = query.filter(Payment.payment_method == method)
        if from_date:
            query = query.filter(Payment.created_at >= datetime.fromisoformat(from_date))
        if to_date:
            query = query.filter(Payment.created_at <= datetime.fromisoformat(to_date + 'T23:59:59'))
        if search:
            query = query.filter(
                db.or_(
                    Payment.payment_id.ilike(f'%{search}%'),
                    Payment.transaction_id.ilike(f'%{search}%')
                )
            )

        total = query.count()
        payments = query.order_by(desc(Payment.created_at)).offset((page-1)*per_page).limit(per_page).all()

        result = []
        for p in payments:
            patient = Patient.query.get(p.patient_id)
            invoice = Invoice.query.filter_by(payment_id=p.id).first()
            result.append({
                'id': p.id,
                'payment_id': p.payment_id,
                'patient_id': p.patient_id,
                'patient_name': patient.username if patient else 'Unknown',
                'patient_email': patient.email if patient else '',
                'payment_type': p.payment_type,
                'amount': float(p.amount),
                'tax': float(p.tax or 0),
                'discount': float(p.discount or 0),
                'total_amount': float(p.total_amount),
                'payment_method': p.payment_method,
                'payment_status': p.payment_status,
                'transaction_id': p.transaction_id,
                'invoice_id': invoice.invoice_id if invoice else None,
                'notes': p.notes,
                'created_at': p.created_at.isoformat() if p.created_at else None,
                'payment_date': p.payment_date.isoformat() if p.payment_date else None,
            })

        # Summary totals
        total_revenue = db.session.query(func.sum(Payment.total_amount)).filter(
            Payment.payment_status == 'completed').scalar() or 0
        total_refunded = db.session.query(func.sum(Payment.total_amount)).filter(
            Payment.payment_status == 'refunded').scalar() or 0
        pending_count = Payment.query.filter_by(payment_status='pending').count()

        return jsonify({
            'success': True,
            'payments': result,
            'pagination': {
                'page': page, 'per_page': per_page,
                'total': total, 'pages': -(-total // per_page)
            },
            'summary': {
                'total_revenue': round(float(total_revenue), 2),
                'total_refunded': round(float(total_refunded), 2),
                'pending_count': pending_count
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/payments/<string:payment_id>/refund', methods=['POST'])
@admin_token_required
def admin_refund_payment(current_admin, payment_id):
    """Admin: refund a completed payment"""
    try:
        from backend.models.payment import Payment
        from backend.models.invoice import Invoice

        payment = Payment.query.filter_by(payment_id=payment_id).first()
        if not payment:
            payment = Payment.query.get(int(payment_id)) if payment_id.isdigit() else None
        if not payment:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404
        if payment.payment_status != 'completed':
            return jsonify({'success': False, 'message': f"Cannot refund a '{payment.payment_status}' payment"}), 400

        data = request.get_json() or {}
        payment.payment_status = 'refunded'
        payment.notes = (payment.notes or '') + f" | Refunded by admin: {data.get('reason', 'Admin refund')}"
        payment.updated_at = datetime.utcnow()

        invoice = Invoice.query.filter_by(payment_id=payment.id).first()
        if invoice:
            invoice.status = 'refunded'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Refund processed successfully',
            'payment_id': payment.payment_id,
            'status': 'refunded'
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/payments/<string:payment_id>/status', methods=['POST'])
@admin_token_required
def admin_update_payment_status(current_admin, payment_id):
    """Admin: manually override payment status"""
    try:
        from backend.models.payment import Payment
        from backend.models.invoice import Invoice

        payment = Payment.query.filter_by(payment_id=payment_id).first()
        if not payment:
            payment = Payment.query.get(int(payment_id)) if payment_id.isdigit() else None
        if not payment:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404

        data = request.get_json() or {}
        new_status = data.get('status')
        valid = ['pending', 'completed', 'failed', 'refunded']
        if new_status not in valid:
            return jsonify({'success': False, 'message': f'Invalid status. Use: {valid}'}), 400

        payment.payment_status = new_status
        payment.updated_at = datetime.utcnow()

        invoice = Invoice.query.filter_by(payment_id=payment.id).first()
        if invoice:
            invoice.status = 'paid' if new_status == 'completed' else new_status
        db.session.commit()

        return jsonify({'success': True, 'message': f'Status updated to {new_status}', 'payment_id': payment.payment_id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/reports/system', methods=['GET'])
@admin_token_required
def generate_system_report(current_admin):
    """
    Generate comprehensive system-wide report
    """
    try:
        from backend.models.patient import Patient
        from backend.models.doctor import Doctor
        from backend.models.nurse import Nurse
        from backend.models.lab_technician import LabTechnician
        from backend.models.pharmacist import Pharmacist
        from backend.models.prediction import Prediction
        from backend.models.prescription import Prescription
        from backend.models.lab_test import LabTest
        from backend.models.appointment import Appointment
        from sqlalchemy import func
        
        # User statistics
        total_patients = Patient.query.count()
        total_doctors = Doctor.query.count()
        total_nurses = Nurse.query.count()
        total_lab_techs = LabTechnician.query.count()
        total_pharmacists = Pharmacist.query.count()
        
        # Prediction statistics
        total_predictions = Prediction.query.count()
        risk_distribution = db.session.query(
            Prediction.risk_level,
            func.count(Prediction.id)
        ).group_by(Prediction.risk_level).all()
        
        # Prescription statistics
        total_prescriptions = Prescription.query.count()
        pending_prescriptions = Prescription.query.filter(
            Prescription.status.in_(['pending', 'pending_pharmacist'])
        ).count()
        dispensed_prescriptions = Prescription.query.filter_by(status='dispensed').count()
        
        # Lab test statistics
        total_lab_tests = LabTest.query.count()
        pending_tests = LabTest.query.filter_by(status='pending').count()
        completed_tests = LabTest.query.filter_by(status='completed').count()
        
        # Appointment statistics
        total_appointments = Appointment.query.count()
        scheduled_appointments = Appointment.query.filter_by(status='scheduled').count()
        completed_appointments = Appointment.query.filter_by(status='completed').count()
        
        # Build report
        report = {
            "report_id": f"SYS{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.utcnow().isoformat(),
            "generated_by": current_admin['username'],
            "user_statistics": {
                "total_patients": total_patients,
                "total_doctors": total_doctors,
                "total_nurses": total_nurses,
                "total_lab_technicians": total_lab_techs,
                "total_pharmacists": total_pharmacists,
                "total_users": total_patients + total_doctors + total_nurses + total_lab_techs + total_pharmacists
            },
            "prediction_statistics": {
                "total_predictions": total_predictions,
                "risk_distribution": {level: count for level, count in risk_distribution}
            },
            "prescription_statistics": {
                "total": total_prescriptions,
                "pending": pending_prescriptions,
                "dispensed": dispensed_prescriptions
            },
            "lab_test_statistics": {
                "total": total_lab_tests,
                "pending": pending_tests,
                "completed": completed_tests
            },
            "appointment_statistics": {
                "total": total_appointments,
                "scheduled": scheduled_appointments,
                "completed": completed_appointments
            }
        }
        
        return jsonify({
            "success": True,
            "report": report
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error generating system report",
            "error": str(e)
        }), 500
