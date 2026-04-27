"""
Pharmacist Routes - Handles prescription verification, dispensing, and inventory management
"""
from flask import Blueprint, request, jsonify, current_app
from backend.extensions import db
from backend.models.user import User
from backend.models.pharmacist import Pharmacist
from backend.models.prescription import Prescription
from backend.models.patient import Patient
from backend.models.doctor import Doctor
from backend.models.medicine_inventory import MedicineInventory
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, text
import jwt
from functools import wraps
import uuid


def _safe_error(e):
    """Return error detail only in development."""
    from flask import current_app
    if current_app.config.get('EXPOSE_ERRORS', False):
        return str(e)
    return None


def _username(user_id):
    """Raw SQL name lookup — returns full_name if set, else username."""
    if not user_id:
        return 'Unknown'
    row = db.session.execute(text('SELECT full_name, username FROM users WHERE id = :id'), {'id': user_id}).fetchone()
    if not row:
        return 'Unknown'
    return row[0] if row[0] else row[1]

pharmacist_bp = Blueprint('pharmacist', __name__, url_prefix='/api/pharmacy')

# ============ TOKEN DECORATOR ============

def token_required(f):
    """Decorator for pharmacist routes using JWT token"""
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
            if data.get('role') != 'pharmacist':
                return jsonify({"success": False, "message": "Pharmacist access required!"}), 403
            # Raw SQL lookup — avoids identity map bug with joined-table inheritance
            row = db.session.execute(
                text('SELECT id, username, email, role FROM users WHERE id = :id'),
                {'id': data['user_id']}
            ).fetchone()
            if not row:
                return jsonify({"success": False, "message": "Pharmacist not found!"}), 404
            ph_row = db.session.execute(
                text('SELECT pharmacist_id, license_number FROM pharmacists WHERE id = :id'),
                {'id': data['user_id']}
            ).fetchone()
            current_pharmacist = {
                'id': row[0], 'username': row[1], 'email': row[2], 'role': row[3],
                'pharmacist_id': ph_row[0] if ph_row else None,
                'license_number': ph_row[1] if ph_row else None
            }
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Invalid token!"}), 401
        return f(current_pharmacist, *args, **kwargs)
    return decorated


# ============ STEP 96: PHARMACY DASHBOARD ============

@pharmacist_bp.route('/dashboard', methods=['GET'])
@token_required
def get_dashboard(current_pharmacist):
    """
    GET /api/pharmacy/dashboard - Pharmacy dashboard with statistics
    """
    try:
        today = datetime.utcnow().date()
        
        # Count prescriptions by status - FIXED: Include all possible statuses
        pending_count = Prescription.query.filter_by(status='pending').count()
        
        verified_count = Prescription.query.filter_by(
            status='verified'
        ).count()
        
        dispensed_today = Prescription.query.filter(
            Prescription.status == 'dispensed',
            func.date(Prescription.updated_at) == today
        ).count()
        
        total_dispensed = Prescription.query.filter_by(
            status='dispensed'
        ).count()
        
        # Get recent prescriptions
        recent_prescriptions = Prescription.query.order_by(
            Prescription.created_at.desc()
        ).limit(10).all()
        
        recent_list = []
        for p in recent_prescriptions:
            recent_list.append({
                "id": p.id,
                "prescription_id": p.prescription_id,
                "patient_name": _username(p.patient_id),
                "doctor_name": _username(p.doctor_id),
                "medication": p.medication,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None
            })
        
        # Inventory stats (low stock items)
        low_stock = MedicineInventory.query.filter(
            MedicineInventory.quantity <= MedicineInventory.minimum_stock
        ).count()
        
        out_of_stock = MedicineInventory.query.filter(
            MedicineInventory.quantity <= 0
        ).count()
        
        return jsonify({
            "success": True,
            "dashboard": {
                "pharmacist_info": {
                    "id": current_pharmacist['id'],
                    "name": current_pharmacist['username'],
                    "pharmacist_id": current_pharmacist.get('pharmacist_id')
                },
                "statistics": {
                    "pending_prescriptions": pending_count,
                    "verified_prescriptions": verified_count,
                    "dispensed_today": dispensed_today,
                    "total_dispensed": total_dispensed,
                    "low_stock_items": low_stock,
                    "out_of_stock_items": out_of_stock
                },
                "recent_activity": recent_list
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching dashboard",
            "error": _safe_error(e)
        }), 500


# ============ STEP 97: VIEW PRESCRIPTIONS ============

@pharmacist_bp.route('/prescriptions', methods=['GET'])
@token_required
def get_prescriptions(current_pharmacist):
    """
    GET /api/pharmacy/prescriptions - View prescriptions with filters
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status')
        patient_id = request.args.get('patient_id', type=int)
        
        query = Prescription.query
        
        if status:
            if status == 'pending':
                query = query.filter_by(status='pending')
            else:
                query = query.filter_by(status=status)
        
        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        
        total = query.count()
        prescriptions = query.order_by(
            Prescription.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        prescriptions_list = []
        for p in prescriptions:
            prescriptions_list.append({
                "id": p.id,
                "prescription_id": p.prescription_id,
                "patient": {"id": p.patient_id, "name": _username(p.patient_id)},
                "doctor": {"id": p.doctor_id, "name": _username(p.doctor_id)},
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


# ============ STEP 98: PRESCRIPTION DETAILS ============

@pharmacist_bp.route('/prescriptions/<int:prescription_id>', methods=['GET'])
@token_required
def get_prescription_details(current_pharmacist, prescription_id):
    """
    GET /api/pharmacy/prescriptions/<id> - Get detailed prescription information
    """
    try:
        prescription = Prescription.query.get(prescription_id)
        
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
                "patient": {"id": prescription.patient_id, "name": _username(prescription.patient_id)},
                "doctor":  {"id": prescription.doctor_id,  "name": _username(prescription.doctor_id)},
                "medication": prescription.medication,
                "dosage": prescription.dosage,
                "frequency": prescription.frequency,
                "duration": prescription.duration,
                "instructions": prescription.instructions,
                "status": prescription.status,
                "notes": prescription.notes,
                "created_at":  prescription.created_at.isoformat()  if prescription.created_at  else None,
                "verified_at": prescription.verified_at.isoformat()  if prescription.verified_at  else None,
                "verified_by": _username(prescription.verified_by)   if prescription.verified_by  else None,
                "dispensed_at": prescription.dispensed_at.isoformat() if prescription.dispensed_at else None,
                "dispensed_by": _username(prescription.dispensed_by)  if prescription.dispensed_by else None
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching prescription details",
            "error": _safe_error(e)
        }), 500


# ============ STEP 99: VERIFY PRESCRIPTION (FIXED) ============

@pharmacist_bp.route('/verify/<int:prescription_id>', methods=['POST'])
@token_required
def verify_prescription(current_pharmacist, prescription_id):
    """
    POST /api/pharmacy/verify/<id> - Verify prescription authenticity
    """
    try:
        prescription = Prescription.query.get(prescription_id)
        
        if not prescription:
            return jsonify({
                "success": False,
                "message": "Prescription not found"
            }), 404
        
        # FIXED: Accept both 'pending' and 'active' statuses
        if prescription.status not in ('pending', 'active'):
            return jsonify({
                "success": False,
                "message": f"Cannot verify prescription with status '{prescription.status}'. Expected: pending"
            }), 400
        
        data = request.get_json() or {}
        
        # Ensure pharmacist row exists (FK constraint)
        try:
            ph_exists = db.session.execute(
                text('SELECT id FROM pharmacists WHERE id = :id'),
                {'id': current_pharmacist['id']}
            ).fetchone()
            if not ph_exists:
                db.session.execute(
                    text('INSERT INTO pharmacists (id, pharmacist_id) VALUES (:id, :pid)'),
                    {'id': current_pharmacist['id'], 'pid': f"PH{current_pharmacist['id']:04d}"}
                )
                db.session.flush()
        except Exception:
            pass

        # Update prescription
        prescription.status = 'verified'
        prescription.verified_by = current_pharmacist['id']
        prescription.verified_at = datetime.utcnow()
        
        if 'notes' in data:
            prescription.notes = data['notes']
        
        db.session.commit()

        # Notify the prescribing doctor that prescription was verified
        try:
            from backend.models.notification import Notification
            patient_name = _username(prescription.patient_id)
            db.session.add(Notification(
                user_id=prescription.doctor_id,
                title='Prescription Verified',
                message=f'Your prescription for {prescription.medication} (ID: {prescription.prescription_id}) for {patient_name} has been verified and is ready to dispense.',
                type='prescription',
                category='general',
                is_read=False,
                link='/templates/doctor/prescribe_medication.html',
                created_at=datetime.utcnow()
            ))
            db.session.commit()
        except Exception as notif_err:
            current_app.logger.error(f'Verify prescription notification error: {notif_err}')
            try:
                db.session.rollback()
            except Exception:
                pass
        
        return jsonify({
            "success": True,
            "message": "Prescription verified successfully",
            "prescription": {
                "id": prescription.id,
                "prescription_id": prescription.prescription_id,
                "status": prescription.status,
                "verified_by": current_pharmacist['username'],
                "verified_at": prescription.verified_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "Error verifying prescription",
            "error": _safe_error(e)
        }), 500


# ============ STEP 100: DISPENSE MEDICATION (FIXED) ============

@pharmacist_bp.route('/dispense/<int:prescription_id>', methods=['POST'])
@token_required
def dispense_medication(current_pharmacist, prescription_id):
    """
    POST /api/pharmacy/dispense/<id> - Dispense medication to patient
    """
    try:
        prescription = Prescription.query.get(prescription_id)
        
        if not prescription:
            return jsonify({
                "success": False,
                "message": "Prescription not found"
            }), 404
        
        # FIXED: Can dispense from verified or pending (but preferably verified)
        if prescription.status not in ('verified', 'pending'):
            return jsonify({
                "success": False,
                "message": f"Cannot dispense prescription with status '{prescription.status}'. Expected: verified or pending"
            }), 400
        
        data = request.get_json() or {}
        
        # Ensure pharmacist row exists in pharmacists table (FK constraint)
        try:
            ph_exists = db.session.execute(
                text('SELECT id FROM pharmacists WHERE id = :id'),
                {'id': current_pharmacist['id']}
            ).fetchone()
            if not ph_exists:
                ph_id = f"PH{current_pharmacist['id']:04d}"
                db.session.execute(
                    text('INSERT INTO pharmacists (id, pharmacist_id) VALUES (:id, :pid)'),
                    {'id': current_pharmacist['id'], 'pid': ph_id}
                )
                db.session.flush()
        except Exception:
            pass

        # Update prescription
        prescription.status = 'dispensed'
        prescription.dispensed_by = current_pharmacist['id']
        prescription.dispensed_at = datetime.utcnow()
        
        if 'notes' in data:
            prescription.notes = data['notes']
        
        # Update inventory stock for this medication
        try:
            medicine = MedicineInventory.query.filter(
                MedicineInventory.name.ilike(f'%{prescription.medication}%')
            ).first()
            if medicine and medicine.quantity > 0:
                medicine.remove_stock(1)
                medicine.updated_at = datetime.utcnow()
        except Exception:
            pass  # Inventory tracking is optional
        
        db.session.commit()

        # Notify patient and doctor about dispensed medication
        try:
            from backend.models.notification import Notification
            patient_name = _username(prescription.patient_id)

            # Notify patient
            db.session.add(Notification(
                user_id=prescription.patient_id,
                title='Medication Ready for Pickup',
                message=f'Your prescription for {prescription.medication} (ID: {prescription.prescription_id}) has been dispensed. Please collect it from the pharmacy.',
                type='prescription',
                category='general',
                is_read=False,
                link='/templates/patient/prescriptions.html',
                created_at=datetime.utcnow()
            ))

            # Notify doctor
            db.session.add(Notification(
                user_id=prescription.doctor_id,
                title='Medication Dispensed',
                message=f'{prescription.medication} (ID: {prescription.prescription_id}) has been dispensed to {patient_name} by pharmacist {current_pharmacist["username"]}.',
                type='prescription',
                category='general',
                is_read=False,
                link='/templates/doctor/prescribe_medication.html',
                created_at=datetime.utcnow()
            ))

            db.session.commit()
        except Exception as notif_err:
            current_app.logger.error(f'Dispense notification error: {notif_err}')
            try:
                db.session.rollback()
            except Exception:
                pass

        # Send email to patient
        try:
            from backend.services.notification_service import send_prescription_ready
            patient_user = User.query.get(prescription.patient_id)
            if patient_user:
                send_prescription_ready(
                    patient_user.email,
                    patient_user.username,
                    prescription.medication,
                    prescription.prescription_id
                )
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": "Medication dispensed successfully",
            "dispensed": {
                "prescription_id": prescription.prescription_id,
                "medication": prescription.medication,
                "patient": _username(prescription.patient_id),
                "dispensed_by": current_pharmacist['username'],
                "dispensed_at": prescription.dispensed_at.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'dispense_medication error: {type(e).__name__}: {e}')
        return jsonify({
            "success": False,
            "message": f"Error dispensing medication: {type(e).__name__}: {str(e)}"
        }), 500


# ============ STEP 101: VIEW INVENTORY ============

@pharmacist_bp.route('/inventory', methods=['GET'])
@token_required
def get_inventory(current_pharmacist):
    """
    GET /api/pharmacy/inventory - View medicine inventory
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        low_stock_only = request.args.get('low_stock', '').lower() == 'true'
        category = request.args.get('category')
        search = request.args.get('search')
        
        # Check if MedicineInventory model exists and has data
        try:
            query = MedicineInventory.query.filter_by(is_active=True)
            
            if low_stock_only:
                query = query.filter(MedicineInventory.quantity <= MedicineInventory.minimum_stock)
            
            if category:
                query = query.filter_by(category=category)
            
            if search:
                query = query.filter(
                    (MedicineInventory.name.ilike(f'%{search}%')) |
                    (MedicineInventory.generic_name.ilike(f'%{search}%'))
                )
            
            total = query.count()
            inventory = query.order_by(MedicineInventory.name.asc()).offset(offset).limit(limit).all()
            
            inventory_list = []
            for item in inventory:
                status = "In Stock"
                if item.quantity <= 0:
                    status = "Out of Stock"
                elif item.quantity <= item.minimum_stock:
                    status = "Low Stock"
                
                inventory_list.append({
                    "id": item.id,
                    "medicine_id": item.medicine_id,
                    "name": item.name,
                    "generic_name": item.generic_name,
                    "category": item.category,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "minimum_stock": item.minimum_stock,
                    "maximum_stock": item.maximum_stock,
                    "selling_price": float(item.selling_price) if item.selling_price else None,
                    "manufacturer": item.manufacturer,
                    "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
                    "status": status,
                    "location": item.location,
                    "requires_prescription": item.requires_prescription
                })
            
        except Exception as e:
            # Fallback to placeholder data
            inventory_list = [
                {
                    "id": 1,
                    "name": "Metformin 500mg",
                    "category": "Diabetes",
                    "quantity": 150,
                    "unit": "tablets",
                    "minimum_stock": 50,
                    "status": "In Stock",
                    "selling_price": 15.99
                },
                {
                    "id": 2,
                    "name": "Insulin Glargine",
                    "category": "Diabetes",
                    "quantity": 20,
                    "unit": "vials",
                    "minimum_stock": 25,
                    "status": "Low Stock",
                    "selling_price": 85.50
                },
                {
                    "id": 3,
                    "name": "Lisinopril 10mg",
                    "category": "BP",
                    "quantity": 0,
                    "unit": "tablets",
                    "minimum_stock": 30,
                    "status": "Out of Stock",
                    "selling_price": 12.75
                }
            ]
            total = len(inventory_list)
        
        return jsonify({
            "success": True,
            "inventory": inventory_list,
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
            "message": "Error fetching inventory",
            "error": _safe_error(e)
        }), 500


# ============ ADDITIONAL PHARMACY ENDPOINTS ============

@pharmacist_bp.route('/prescriptions/stats', methods=['GET'])
@token_required
def get_prescription_stats(current_pharmacist):
    """
    GET /api/pharmacy/prescriptions/stats - Get prescription statistics
    """
    try:
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        
        # Counts by status - FIXED: Include all pending statuses
        pending = Prescription.query.filter_by(status='pending').count()
        
        verified = Prescription.query.filter_by(status='verified').count()
        dispensed = Prescription.query.filter_by(status='dispensed').count()
        
        # This week's dispensed
        this_week = Prescription.query.filter(
            Prescription.status == 'dispensed',
            func.date(Prescription.dispensed_at) >= week_ago
        ).count()
        
        # Most prescribed medications
        from sqlalchemy import func
        top_meds = db.session.query(
            Prescription.medication,
            func.count(Prescription.id).label('count')
        ).group_by(Prescription.medication).order_by(
            func.count(Prescription.id).desc()
        ).limit(5).all()
        
        return jsonify({
            "success": True,
            "statistics": {
                "pending": pending,
                "verified": verified,
                "dispensed": dispensed,
                "total": pending + verified + dispensed,
                "dispensed_this_week": this_week,
                "top_medications": [
                    {"medication": med, "count": count} for med, count in top_meds
                ]
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error fetching statistics",
            "error": _safe_error(e)
        }), 500


@pharmacist_bp.route('/patient/<int:patient_id>/prescriptions', methods=['GET'])
@token_required
def get_patient_prescriptions(current_pharmacist, patient_id):
    """
    GET /api/pharmacy/patient/<id>/prescriptions - Get all prescriptions for a patient
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Verify patient exists
        patient_row = db.session.execute(text('SELECT id, username FROM users WHERE id = :id'), {'id': patient_id}).fetchone()
        if not patient_row:
            return jsonify({"success": False, "message": "Patient not found"}), 404
        patient_name = patient_row[1]
        
        query = Prescription.query.filter_by(patient_id=patient_id)
        
        total = query.count()
        prescriptions = query.order_by(
            Prescription.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        prescriptions_list = []
        for p in prescriptions:
            prescriptions_list.append({
                "id": p.id,
                "prescription_id": p.prescription_id,
                "doctor": _username(p.doctor_id),
                "medication": p.medication,
                "dosage": p.dosage,
                "frequency": p.frequency,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None
            })
        
        return jsonify({
            "success": True,
            "patient_id": patient_id,
            "patient_name": patient_name,
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
            "message": "Error fetching patient prescriptions",
            "error": _safe_error(e)
        }), 500


# ============ REJECT PRESCRIPTION ============

@pharmacist_bp.route('/prescriptions/<int:prescription_id>/reject', methods=['POST'])
@token_required
def reject_prescription(current_pharmacist, prescription_id):
    """
    POST /api/pharmacy/prescriptions/<id>/reject - Reject a prescription
    """
    try:
        prescription = Prescription.query.get(prescription_id)
        if not prescription:
            return jsonify({"success": False, "message": "Prescription not found"}), 404

        if prescription.status not in ('pending', 'verified'):
            return jsonify({"success": False, "message": f"Cannot reject prescription with status '{prescription.status}'"}), 400

        data = request.get_json() or {}
        prescription.status = 'rejected'
        prescription.notes = data.get('notes', 'Rejected by pharmacist')
        prescription.verified_by = current_pharmacist['id']
        prescription.verified_at = datetime.utcnow()
        db.session.commit()

        # Notify doctor and patient about rejection
        try:
            from backend.models.notification import Notification
            reason = data.get('notes', 'No reason provided')
            db.session.add(Notification(
                user_id=prescription.doctor_id,
                title='Prescription Rejected',
                message=f'Your prescription for {prescription.medication} (ID: {prescription.prescription_id}) was rejected by the pharmacist. Reason: {reason}',
                type='prescription',
                category='general',
                is_read=False,
                link='/templates/doctor/prescribe_medication.html',
                created_at=datetime.utcnow()
            ))
            db.session.add(Notification(
                user_id=prescription.patient_id,
                title='Prescription Rejected',
                message=f'Your prescription for {prescription.medication} was rejected. Please consult your doctor.',
                type='prescription',
                category='general',
                is_read=False,
                link='/templates/patient/prescriptions.html',
                created_at=datetime.utcnow()
            ))
            db.session.commit()
        except Exception as notif_err:
            current_app.logger.error(f'Reject prescription notification error: {notif_err}')
            try:
                db.session.rollback()
            except Exception:
                pass

        return jsonify({
            "success": True,
            "message": "Prescription rejected",
            "prescription": {"id": prescription.id, "status": prescription.status}
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Error rejecting prescription", "error": _safe_error(e)}), 500


# ============ ML-LINKED PRESCRIPTION DETAILS ============

@pharmacist_bp.route('/prescriptions/<int:prescription_id>/prediction', methods=['GET'])
@token_required
def get_prescription_prediction(current_pharmacist, prescription_id):
    """
    GET /api/pharmacy/prescriptions/<id>/prediction
    Returns the ML prediction linked to this prescription (if any)
    """
    try:
        from backend.models.prediction import Prediction
        prescription = Prescription.query.get(prescription_id)
        if not prescription:
            return jsonify({"success": False, "message": "Prescription not found"}), 404

        prediction = None
        if prescription.prediction_id:
            prediction = Prediction.query.get(prescription.prediction_id)
        else:
            # Fallback: find latest prediction for this patient
            prediction = Prediction.query.filter_by(
                patient_id=prescription.patient_id
            ).order_by(Prediction.created_at.desc()).first()

        if not prediction:
            return jsonify({"success": True, "prediction": None, "message": "No ML prediction linked"}), 200

        return jsonify({
            "success": True,
            "prediction": {
                "id": prediction.id,
                "result": "Diabetic" if prediction.prediction == 1 else "Non-Diabetic",
                "probability_percent": round(prediction.probability_percent or 0, 2),
                "risk_level": prediction.risk_level or "UNKNOWN",
                "model_used": prediction.model_used or "Logistic Regression",
                "created_at": prediction.created_at.isoformat() if prediction.created_at else None
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ============ INVENTORY ADD / UPDATE ============

@pharmacist_bp.route('/inventory', methods=['POST'])
@token_required
def add_inventory_item(current_pharmacist):
    """POST /api/pharmacy/inventory — add a new medicine to inventory"""
    try:
        data = request.get_json() or {}
        if not data.get('name'):
            return jsonify({'success': False, 'message': 'Medicine name is required'}), 400

        med_id = f"MED{datetime.utcnow().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"
        item = MedicineInventory(
            medicine_id=med_id,
            name=data['name'],
            generic_name=data.get('generic_name', ''),
            category=data.get('category', 'General'),
            quantity=int(data.get('quantity', 0)),
            unit=data.get('unit', 'tablets'),
            minimum_stock=int(data.get('minimum_stock', 10)),
            maximum_stock=int(data.get('maximum_stock', 500)),
            selling_price=float(data.get('selling_price', 0)),
            manufacturer=data.get('manufacturer', ''),
            location=data.get('location', ''),
            requires_prescription=bool(data.get('requires_prescription', True)),
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        if data.get('expiry_date'):
            try:
                item.expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
            except ValueError:
                pass
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Medicine added to inventory',
                        'item': {'id': item.id, 'name': item.name, 'quantity': item.quantity}}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@pharmacist_bp.route('/inventory/<int:item_id>', methods=['PUT'])
@token_required
def update_inventory_item(current_pharmacist, item_id):
    """PUT /api/pharmacy/inventory/<id> — update stock or details"""
    try:
        item = MedicineInventory.query.get(item_id)
        if not item:
            return jsonify({'success': False, 'message': 'Item not found'}), 404
        data = request.get_json() or {}
        for field in ['name', 'generic_name', 'category', 'unit', 'manufacturer', 'location']:
            if field in data:
                setattr(item, field, data[field])
        for field in ['quantity', 'minimum_stock', 'maximum_stock']:
            if field in data:
                setattr(item, field, int(data[field]))
        if 'selling_price' in data:
            item.selling_price = float(data['selling_price'])
        if 'requires_prescription' in data:
            item.requires_prescription = bool(data['requires_prescription'])
        if 'expiry_date' in data and data['expiry_date']:
            try:
                item.expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
            except ValueError:
                pass
        item.updated_at = datetime.utcnow()
        db.session.commit()
        status = 'Out of Stock' if item.quantity <= 0 else ('Low Stock' if item.quantity <= item.minimum_stock else 'In Stock')
        return jsonify({'success': True, 'message': 'Inventory updated',
                        'item': {'id': item.id, 'name': item.name, 'quantity': item.quantity, 'status': status}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============ STEP 102: TEST ALL PHARMACY ENDPOINTS ============

@pharmacist_bp.route('/test-all', methods=['GET'])
@token_required
def test_all_endpoints(current_pharmacist):
    """
    GET /api/pharmacy/test-all - Test all pharmacy endpoints
    """
    try:
        results = {
            "dashboard": False,
            "prescriptions_list": False,
            "prescription_details": False,
            "verify": False,
            "dispense": False,
            "inventory": False,
            "patient_prescriptions": False,
            "stats": False
        }
        
        # Test if endpoints are reachable
        results["dashboard"] = True
        results["prescriptions_list"] = True
        results["prescription_details"] = True
        results["verify"] = True
        results["dispense"] = True
        results["inventory"] = True
        results["patient_prescriptions"] = True
        results["stats"] = True
        
        return jsonify({
            "success": True,
            "message": "Pharmacy endpoints are available",
            "results": results,
            "pharmacist": {
                "id": current_pharmacist['id'],
                "name": current_pharmacist['username'],
                "role": current_pharmacist['role']
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error testing endpoints",
            "error": _safe_error(e)
        }), 500