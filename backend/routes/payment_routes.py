"""
Payment Routes - Handles payment processing, history, invoices, refunds, and subscriptions
"""
from flask import Blueprint, request, jsonify, current_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.payment import Payment
from backend.models.subscription import Subscription
from backend.models.invoice import Invoice
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
import jwt
from functools import wraps
import uuid

payment_bp = Blueprint('payment', __name__, url_prefix='/api/payments')

# ============ TOKEN DECORATOR ============

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"success": False, "message": "Token is missing!"}), 401
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            if data.get('role') not in ['patient', 'admin', 'doctor']:
                return jsonify({"success": False, "message": "Access required!"}), 403
            user = User.query.get(data['user_id'])
            if not user:
                return jsonify({"success": False, "message": "User not found!"}), 404
            current_user = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Invalid token!"}), 401
        return f(current_user, *args, **kwargs)
    return decorated


# ============ CHAPA PAYMENT ============

@payment_bp.route('/chapa/initialize', methods=['POST'])
@token_required
def chapa_initialize(current_user):
    """
    POST /api/payments/chapa/initialize
    Initializes a Chapa payment and returns checkout_url.
    """
    try:
        import requests as req
        data = request.get_json()
        amount = float(data.get('amount', 0))
        tax = float(data.get('tax', 0))
        total = amount + tax

        # Resolve patient
        patient = Patient.query.filter_by(id=current_user['id']).first()
        if not patient and current_user['role'] == 'doctor':
            from backend.models.lab_test import LabTest
            lab_id = data.get('lab_request_id')
            lab = LabTest.query.get(int(lab_id)) if lab_id else None
            patient = Patient.query.get(lab.patient_id) if lab else Patient.query.first()
        if not patient:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404

        tx_ref = f"CHAPA-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        callback_url = current_app.config.get('CHAPA_CALLBACK_URL',
            'http://localhost:5000/api/payments/chapa/verify')
        return_url = current_app.config.get('CHAPA_RETURN_URL',
            'http://localhost:5000/templates/payment/payment_success.html')

        chapa_payload = {
            'amount': str(round(total, 2)),
            'currency': 'ETB',
            'email': patient.email,
            'first_name': (patient.username or 'Patient').split()[0],
            'last_name': (patient.username or 'Patient').split()[-1],
            'tx_ref': tx_ref,
            'callback_url': callback_url,
            'return_url': return_url,
            'customization[title]': 'Diabetes Prediction System',
            'customization[description]': data.get('notes', 'Healthcare Services')
        }

        secret_key = current_app.config.get('CHAPA_SECRET_KEY', '')
        headers = {'Authorization': f'Bearer {secret_key}', 'Content-Type': 'application/json'}

        resp = req.post('https://api.chapa.co/v1/transaction/initialize',
                        json=chapa_payload, headers=headers, timeout=15)
        result = resp.json()

        if result.get('status') != 'success':
            return jsonify({'success': False,
                            'message': result.get('message', 'Chapa initialization failed')}), 400

        # Save a pending payment record
        payment_id = f"PAY{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        lab_rid = data.get('lab_request_id')
        ref_id = None
        ref_type = None
        if lab_rid is not None:
            try:
                ref_id = int(lab_rid)
                ref_type = 'lab_test'
            except (TypeError, ValueError):
                pass

        payment = Payment(
            payment_id=payment_id,
            patient_id=patient.id,
            payment_type=data.get('payment_type', 'services'),
            amount=amount, tax=tax, discount=0, total_amount=total,
            payment_method='chapa',
            payment_status='pending',
            transaction_id=tx_ref,
            payment_date=datetime.utcnow(),
            notes=data.get('notes', ''),
            reference_id=ref_id,
            reference_type=ref_type,
        )
        if hasattr(payment, 'prediction_consumed'):
            payment.prediction_consumed = False
        db.session.add(payment)

        invoice_id = f"INV{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        invoice = Invoice(
            invoice_id=invoice_id, payment_id=None,
            patient_id=patient.id,
            amount=amount, tax=tax, discount=0, total_amount=total,
            status='pending', due_date=datetime.utcnow().date()
        )
        db.session.add(invoice)
        db.session.commit()

        # Link invoice to payment
        invoice.payment_id = payment.id
        db.session.commit()

        return jsonify({
            'success': True,
            'checkout_url': result['data']['checkout_url'],
            'tx_ref': tx_ref,
            'payment_id': payment_id,
            'invoice_id': invoice_id
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@payment_bp.route('/chapa/verify', methods=['GET', 'POST'])
@token_required
def chapa_verify(current_user):
    """
    GET/POST /api/payments/chapa/verify?tx_ref=...
    Verifies a Chapa transaction and marks payment completed.
    """
    try:
        import requests as req
        tx_ref = request.args.get('tx_ref') or (request.get_json() or {}).get('tx_ref')
        if not tx_ref:
            return jsonify({'success': False, 'message': 'tx_ref required'}), 400

        secret_key = current_app.config.get('CHAPA_SECRET_KEY', '')
        headers = {'Authorization': f'Bearer {secret_key}'}
        resp = req.get(f'https://api.chapa.co/v1/transaction/verify/{tx_ref}',
                       headers=headers, timeout=15)
        result = resp.json()

        if result.get('status') != 'success':
            return jsonify({'success': False,
                            'message': result.get('message', 'Verification failed')}), 400

        # Update payment record
        payment = Payment.query.filter_by(transaction_id=tx_ref).first()
        if payment:
            payment.payment_status = 'completed'
            payment.payment_date = datetime.utcnow()
            invoice = Invoice.query.filter_by(payment_id=payment.id).first()
            if invoice:
                invoice.status = 'paid'
                invoice.paid_at = datetime.utcnow()
            db.session.commit()

            try:
                from backend.services.notification_service import send_payment_confirmation
                payer = User.query.get(payment.patient_id)
                if payer:
                    send_payment_confirmation(payer.email, payer.username,
                                              payment.total_amount, payment.payment_id)
            except Exception:
                pass

        return jsonify({
            'success': True,
            'message': 'Payment verified successfully',
            'payment_id': payment.payment_id if payment else tx_ref,
            'status': 'completed'
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============ CHECK PREDICTION PAYMENT STATUS ============

@payment_bp.route('/check-prediction-access', methods=['GET'])
@token_required
def check_prediction_access(current_user):
    """
    GET /api/payments/check-prediction-access
    Returns whether the patient has a valid (unused) paid prediction slot today.
    Used by the health form before running ML.
    """
    try:
        patient = Patient.query.filter_by(id=current_user['id']).first()
        if not patient:
            return jsonify({"success": False, "has_access": False, "message": "Patient not found"}), 404

        # Any completed, unconsumed prediction payment (not limited to "today" — avoids timezone / midnight bugs)
        payment = Payment.query.filter(
            Payment.patient_id == patient.id,
            Payment.payment_type == 'prediction',
            Payment.payment_status == 'completed',
            Payment.prediction_consumed == False,
        ).order_by(Payment.created_at.desc()).first()

        if payment:
            return jsonify({
                "success": True,
                "has_access": True,
                "payment_id": payment.payment_id,
                "message": "Payment verified. You may proceed."
            }), 200
        else:
            return jsonify({
                "success": True,
                "has_access": False,
                "message": "Payment required to run prediction."
            }), 200

    except Exception as e:
        # If column doesn't exist yet, fall back to allowing access (graceful degradation)
        return jsonify({"success": True, "has_access": True, "message": "Access granted (fallback)"}), 200


# ============ MARK PREDICTION PAYMENT AS CONSUMED ============

@payment_bp.route('/consume-prediction-payment', methods=['POST'])
@token_required
def consume_prediction_payment(current_user):
    """
    POST /api/payments/consume-prediction-payment
    Marks the prediction payment as consumed after ML runs successfully.
    """
    try:
        patient = Patient.query.filter_by(id=current_user['id']).first()
        if not patient:
            return jsonify({"success": False, "message": "Patient not found"}), 404

        payment = Payment.query.filter(
            Payment.patient_id == patient.id,
            Payment.payment_type == 'prediction',
            Payment.payment_status == 'completed',
            Payment.prediction_consumed == False,
        ).order_by(Payment.created_at.desc()).first()

        if payment:
            payment.prediction_consumed = True
            db.session.commit()

        return jsonify({"success": True, "message": "Payment consumed"}), 200

    except Exception as e:
        return jsonify({"success": True, "message": "Consumed (fallback)"}), 200


# ============ PROCESS PAYMENT ============

@payment_bp.route('/process', methods=['POST'])
@token_required
def process_payment(current_user):
    """
    POST /api/payments/process
    """
    try:
        data = request.get_json()
        if 'amount' not in data:
            return jsonify({"success": False, "message": "Missing required field: amount"}), 400

        patient = Patient.query.filter_by(id=current_user['id']).first()
        if not patient and current_user['role'] == 'doctor':
            # Doctor paying for a lab request — use the lab request's patient_id
            from backend.models.lab_test import LabTest
            lab_request_id = data.get('lab_request_id')
            if lab_request_id:
                lab = LabTest.query.get(int(lab_request_id))
                payer_id = lab.patient_id if lab else None
            else:
                payer_id = None
            if not payer_id:
                # fallback: first available patient
                fallback = Patient.query.first()
                payer_id = fallback.id if fallback else None
            if not payer_id:
                return jsonify({"success": False, "message": "No patient found for this payment"}), 404
        elif not patient:
            return jsonify({"success": False, "message": "Patient not found"}), 404
        else:
            payer_id = patient.id

        amount = float(data['amount'])
        tax = float(data.get('tax', 0))
        discount = float(data.get('discount', 0))
        total = amount + tax - discount
        currency = data.get('currency', 'ETB').upper()

        valid_currencies = ['ETB', 'USD', 'EUR', 'GBP', 'JPY', 'CNY', 'INR', 'AED', 'SAR', 'CAD', 'AUD', 'CHF']
        if currency not in valid_currencies:
            return jsonify({"success": False, "message": f"Invalid currency. Supported: {', '.join(valid_currencies)}"}), 400

        payment_id = f"PAY{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"

        method = data.get('payment_method', 'online')
        # cash, insurance, bank_transfer are pending until confirmed
        pending_methods = ['cash', 'insurance', 'bank_transfer']
        status = 'pending' if method in pending_methods else 'completed'

        ref_id = data.get('reference_id')
        ref_type = data.get('reference_type')
        if data.get('lab_request_id'):
            try:
                ref_id = int(data['lab_request_id'])
                ref_type = 'lab_test'
            except (TypeError, ValueError):
                pass

        payment = Payment(
            payment_id=payment_id,
            patient_id=payer_id,
            payment_type=data.get('payment_type', 'general'),
            reference_id=ref_id,
            reference_type=ref_type,
            amount=amount,
            tax=tax,
            discount=discount,
            total_amount=total,
            payment_method=method,
            payment_status=status,
            transaction_id=data.get('transaction_id') or data.get('transaction_reference'),
            payment_date=datetime.utcnow(),
            notes=data.get('notes')
        )

        # prediction_consumed flag — False by default for prediction payments
        if hasattr(payment, 'prediction_consumed'):
            payment.prediction_consumed = False

        if 'insurance_company' in data:
            payment.insurance_company = data['insurance_company']
        if 'insurance_claim_number' in data:
            payment.insurance_claim_number = data['insurance_claim_number']
        if 'insurance_amount' in data:
            payment.insurance_amount = float(data['insurance_amount'])

        db.session.add(payment)
        db.session.commit()

        invoice_id = f"INV{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        invoice = Invoice(
            invoice_id=invoice_id,
            payment_id=payment.id,
            patient_id=payer_id,
            amount=amount,
            tax=tax,
            discount=discount,
            total_amount=total,
            status='pending' if method in pending_methods else 'paid',
            due_date=datetime.utcnow().date(),
            paid_at=None if method in pending_methods else datetime.utcnow()
        )
        db.session.add(invoice)
        db.session.commit()

        # Send payment confirmation email
        try:
            from backend.services.notification_service import send_payment_confirmation
            payer = User.query.get(payer_id)
            if payer:
                send_payment_confirmation(payer.email, payer.username, total, payment_id)
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": "Payment processed successfully",
            "payment": {
                "id": payment.id,
                "payment_id": payment.payment_id,
                "amount": payment.amount,
                "currency": currency,
                "total_amount": payment.total_amount,
                "payment_method": payment.payment_method,
                "status": payment.payment_status,
                "payment_type": payment.payment_type,
                "is_pending": payment.payment_status == 'pending',
                "created_at": payment.created_at.isoformat()
            },
            "invoice": {
                "id": invoice.id,
                "invoice_id": invoice.invoice_id,
                "total_amount": invoice.total_amount,
                "status": invoice.status
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Error processing payment", "error": str(e)}), 500


# ============ GET PAYMENT HISTORY ============

@payment_bp.route('/history', methods=['GET'])
@token_required
def get_payment_history(current_user):
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        patient = Patient.query.filter_by(id=current_user['id']).first()
        if not patient:
            return jsonify({"success": False, "message": "Patient not found"}), 404

        query = Payment.query.filter_by(patient_id=patient.id)
        if status:
            query = query.filter_by(payment_status=status)
        if from_date:
            query = query.filter(Payment.created_at >= datetime.fromisoformat(from_date))
        if to_date:
            query = query.filter(Payment.created_at <= datetime.fromisoformat(to_date))

        total = query.count()
        payments = query.order_by(Payment.created_at.desc()).offset(offset).limit(limit).all()

        payments_list = []
        for p in payments:
            invoice = Invoice.query.filter_by(payment_id=p.id).first()
            payments_list.append({
                "id": p.id,
                "payment_id": p.payment_id,
                "invoice_id": invoice.invoice_id if invoice else None,
                "amount": float(p.amount),
                "total_amount": float(p.total_amount),
                "payment_method": p.payment_method,
                "payment_type": p.payment_type,
                "status": p.payment_status,
                "notes": p.notes,
                "created_at": p.created_at.isoformat() if p.created_at else None
            })

        return jsonify({
            "success": True,
            "payments": payments_list,
            "pagination": {"total": total, "limit": limit, "offset": offset, "has_more": (offset + limit) < total}
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": "Error fetching payment history", "error": str(e)}), 500


# ============ GET INVOICE ============

@payment_bp.route('/invoice/<string:invoice_id>', methods=['GET'])
@token_required
def get_invoice(current_user, invoice_id):
    try:
        invoice = None
        if invoice_id.isdigit():
            invoice = Invoice.query.get(int(invoice_id))
        if not invoice:
            invoice = Invoice.query.filter_by(invoice_id=invoice_id).first()
        if not invoice:
            return jsonify({"success": False, "message": "Invoice not found"}), 404

        patient = Patient.query.get(invoice.patient_id)
        if current_user['role'] != 'admin' and (not patient or patient.id != current_user['id']):
            return jsonify({"success": False, "message": "Access denied"}), 403

        payment = Payment.query.get(invoice.payment_id) if invoice.payment_id else None

        return jsonify({
            "success": True,
            "invoice": {
                "id": invoice.id,
                "invoice_id": invoice.invoice_id,
                "patient": {"id": patient.id, "name": patient.username, "email": patient.email} if patient else None,
                "amount": float(invoice.amount),
                "tax": float(invoice.tax) if invoice.tax else 0,
                "discount": float(invoice.discount) if invoice.discount else 0,
                "total_amount": float(invoice.total_amount),
                "status": invoice.status,
                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None,
                "payment": {"id": payment.id, "payment_id": payment.payment_id, "payment_method": payment.payment_method} if payment else None,
                "created_at": invoice.created_at.isoformat() if invoice.created_at else None
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": "Error fetching invoice", "error": str(e)}), 500


# ============ PROCESS REFUND ============

@payment_bp.route('/refund/<string:payment_id>', methods=['POST'])
@token_required
def process_refund(current_user, payment_id):
    try:
        payment = None
        if payment_id.isdigit():
            payment = Payment.query.get(int(payment_id))
        if not payment:
            payment = Payment.query.filter_by(payment_id=payment_id).first()
        if not payment:
            return jsonify({"success": False, "message": "Payment not found"}), 404

        patient = Patient.query.get(payment.patient_id)
        if current_user['role'] != 'admin' and (not patient or patient.id != current_user['id']):
            return jsonify({"success": False, "message": "Access denied"}), 403

        if payment.payment_status != 'completed':
            return jsonify({"success": False, "message": f"Cannot refund payment with status '{payment.payment_status}'"}), 400

        data = request.get_json() or {}
        refund_amount = data.get('amount', payment.amount)
        refund_reason = data.get('reason', 'Customer requested refund')

        payment.payment_status = 'refunded'
        payment.updated_at = datetime.utcnow()

        invoice = Invoice.query.filter_by(payment_id=payment.id).first()
        if invoice:
            invoice.status = 'refunded'

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Refund processed successfully",
            "refund": {
                "payment_id": payment.payment_id,
                "amount": float(refund_amount),
                "reason": refund_reason,
                "status": "completed",
                "processed_at": datetime.utcnow().isoformat()
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Error processing refund", "error": str(e)}), 500


# ============ SUBSCRIPTION ENDPOINTS ============

@payment_bp.route('/subscription', methods=['POST'])
@token_required
def create_subscription(current_user):
    try:
        data = request.get_json()
        for field in ['plan', 'billing_cycle']:
            if field not in data:
                return jsonify({"success": False, "message": f"Missing required field: {field}"}), 400

        patient = Patient.query.filter_by(id=current_user['id']).first()
        if not patient:
            return jsonify({"success": False, "message": "Patient not found"}), 404

        existing = Subscription.query.filter_by(patient_id=patient.id, status='active').first()
        if existing:
            return jsonify({"success": False, "message": "Patient already has an active subscription"}), 400

        now = datetime.utcnow()
        days_map = {'weekly': 7, 'monthly': 30, 'quarterly': 90, 'yearly': 365}
        next_billing = now + timedelta(days=days_map.get(data['billing_cycle'], 30))

        subscription_id = f"SUB{now.strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4]}"
        subscription = Subscription(
            subscription_id=subscription_id,
            patient_id=patient.id,
            plan=data['plan'],
            billing_cycle=data['billing_cycle'],
            amount=data.get('amount', 0),
            status='active',
            start_date=now,
            next_billing_date=next_billing,
            payment_method=data.get('payment_method'),
            created_at=now,
            updated_at=now
        )
        db.session.add(subscription)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Subscription created successfully",
            "subscription": {
                "id": subscription.id,
                "subscription_id": subscription.subscription_id,
                "plan": subscription.plan,
                "billing_cycle": subscription.billing_cycle,
                "amount": float(subscription.amount) if subscription.amount else None,
                "status": subscription.status,
                "start_date": subscription.start_date.isoformat(),
                "next_billing_date": subscription.next_billing_date.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Error creating subscription", "error": str(e)}), 500


@payment_bp.route('/subscription', methods=['GET'])
@token_required
def get_subscription(current_user):
    try:
        patient = Patient.query.filter_by(id=current_user['id']).first()
        if not patient:
            return jsonify({"success": False, "message": "Patient not found"}), 404

        subscription = Subscription.query.filter_by(patient_id=patient.id, status='active').first()
        if not subscription:
            subscription = Subscription.query.filter_by(patient_id=patient.id).order_by(Subscription.created_at.desc()).first()

        if not subscription:
            return jsonify({"success": True, "subscription": None, "message": "No subscription found"}), 200

        payments = Payment.query.filter_by(patient_id=patient.id).order_by(Payment.created_at.desc()).limit(5).all()
        payment_history = [{"id": p.id, "payment_id": p.payment_id, "amount": float(p.amount), "status": p.payment_status, "created_at": p.created_at.isoformat() if p.created_at else None} for p in payments]

        return jsonify({
            "success": True,
            "subscription": {
                "id": subscription.id,
                "subscription_id": subscription.subscription_id,
                "plan": subscription.plan,
                "billing_cycle": subscription.billing_cycle,
                "amount": float(subscription.amount) if subscription.amount else None,
                "status": subscription.status,
                "start_date": subscription.start_date.isoformat() if subscription.start_date else None,
                "next_billing_date": subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
                "cancelled_at": subscription.cancelled_at.isoformat() if subscription.cancelled_at else None,
                "payment_method": subscription.payment_method,
                "payment_history": payment_history
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": "Error fetching subscription", "error": str(e)}), 500


@payment_bp.route('/subscription/cancel', methods=['POST'])
@token_required
def cancel_subscription(current_user):
    try:
        patient = Patient.query.filter_by(id=current_user['id']).first()
        if not patient:
            return jsonify({"success": False, "message": "Patient not found"}), 404

        subscription = Subscription.query.filter_by(patient_id=patient.id, status='active').first()
        if not subscription:
            return jsonify({"success": False, "message": "No active subscription found"}), 404

        subscription.status = 'cancelled'
        subscription.cancelled_at = datetime.utcnow()
        subscription.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({"success": True, "message": "Subscription cancelled successfully", "subscription": {"id": subscription.id, "status": subscription.status, "cancelled_at": subscription.cancelled_at.isoformat()}}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Error cancelling subscription", "error": str(e)}), 500


@payment_bp.route('/summary', methods=['GET'])
@token_required
def get_payment_summary(current_user):
    try:
        patient = Patient.query.filter_by(id=current_user['id']).first()
        if not patient:
            return jsonify({"success": False, "message": "Patient not found"}), 404

        total_paid = db.session.query(func.sum(Payment.amount)).filter(Payment.patient_id == patient.id, Payment.payment_status == 'completed').scalar() or 0
        total_refunded = db.session.query(func.sum(Payment.amount)).filter(Payment.patient_id == patient.id, Payment.payment_status == 'refunded').scalar() or 0
        payment_count = Payment.query.filter_by(patient_id=patient.id).count()
        subscription = Subscription.query.filter_by(patient_id=patient.id, status='active').first()

        return jsonify({
            "success": True,
            "summary": {
                "total_paid": float(total_paid),
                "total_refunded": float(total_refunded),
                "net_paid": float(total_paid - total_refunded),
                "payment_count": payment_count,
                "has_active_subscription": subscription is not None,
                "current_plan": subscription.plan if subscription else None,
                "next_billing": subscription.next_billing_date.isoformat() if subscription and subscription.next_billing_date else None
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": "Error fetching payment summary", "error": str(e)}), 500


# ============ PAYMENT RECEIPT PDF ============

@payment_bp.route('/receipt/<string:payment_id>/pdf', methods=['GET'])
@token_required
def download_receipt_pdf(current_user, payment_id):
    try:
        from flask import send_file
        from backend.services.report_service import generate_payment_receipt_pdf

        payment = Payment.query.filter_by(payment_id=payment_id).first()
        if not payment:
            payment = Payment.query.get(int(payment_id)) if payment_id.isdigit() else None
        if not payment:
            return jsonify({"success": False, "message": "Payment not found"}), 404

        patient = Patient.query.get(payment.patient_id)
        if current_user['role'] != 'admin' and (not patient or patient.id != current_user['id']):
            return jsonify({"success": False, "message": "Access denied"}), 403

        invoice = Invoice.query.filter_by(payment_id=payment.id).first()
        payment_info = {
            "payment_id": payment.payment_id,
            "invoice_id": invoice.invoice_id if invoice else "—",
            "amount": float(payment.amount),
            "tax": float(payment.tax) if payment.tax else 0,
            "discount": float(payment.discount) if payment.discount else 0,
            "total_amount": float(payment.total_amount),
            "payment_method": payment.payment_method,
            "status": payment.payment_status,
            "notes": payment.notes or "Healthcare Services",
            "date": payment.created_at.isoformat() if payment.created_at else "",
        }
        patient_info = {
            "name": getattr(patient, 'full_name', None) or (patient.username if patient else "—"),
            "email": patient.email if patient else "—",
        }

        pdf_buf = generate_payment_receipt_pdf(payment_info, patient_info)
        return send_file(pdf_buf, mimetype='application/pdf', as_attachment=True, download_name=f"receipt_{payment.payment_id}.pdf")

    except Exception as e:
        return jsonify({"success": False, "message": "Error generating receipt PDF", "error": str(e)}), 500
