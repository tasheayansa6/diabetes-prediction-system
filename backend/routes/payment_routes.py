"""
Payment Routes — Chapa gateway, cash/card/mobile processing, history, invoices, refunds, subscriptions.

Design principles:
  - token_required comes from backend.utils.decorators (single source of truth)
  - ID generation and pricing helpers come from backend.services.payment_service
  - No inline duplication of pending-method lists or ID generators
"""
from flask import Blueprint, request, jsonify, current_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.payment import Payment
from backend.models.subscription import Subscription
from backend.models.invoice import Invoice
from backend.services.payment_service import (
    generate_payment_id,
    generate_invoice_id,
    generate_tx_ref,
    payment_status_for_method,
    PENDING_METHODS,
)
from backend.utils.decorators import token_required
from datetime import datetime, timedelta
from sqlalchemy import func
import uuid

payment_bp = Blueprint('payment', __name__, url_prefix='/api/payments')

# ── helpers ───────────────────────────────────────────────────────────────────


def _safe_error(e):
    """Return error detail only in development."""
    from flask import current_app
    if current_app.config.get('EXPOSE_ERRORS', False):
        return str(e)
    return None


def _is_chapa_configured():
    key = current_app.config.get('CHAPA_SECRET_KEY', '')
    return bool(key) and 'your-' not in key.lower()


def _make_payment(patient_id, data, method, subtotal, tax, discount=0.0,
                  ref_id=None, ref_type=None):
    """Create and persist a Payment + Invoice pair. Returns (payment, invoice)."""
    total = subtotal + tax - discount
    status = payment_status_for_method(method)

    payment = Payment(
        payment_id=generate_payment_id(),
        patient_id=patient_id,
        payment_type=data.get('payment_type', 'general'),
        reference_id=ref_id,
        reference_type=ref_type,
        amount=subtotal,
        tax=tax,
        discount=discount,
        total_amount=total,
        payment_method=method,
        payment_status=status,
        transaction_id=data.get('transaction_id') or data.get('transaction_reference'),
        payment_date=datetime.utcnow(),
        notes=data.get('notes', ''),
    )
    if hasattr(payment, 'prediction_consumed'):
        payment.prediction_consumed = False
    if 'insurance_company' in data:
        payment.insurance_company = data['insurance_company']
    if 'insurance_claim_number' in data:
        payment.insurance_claim_number = data['insurance_claim_number']
    if 'insurance_amount' in data:
        payment.insurance_amount = float(data['insurance_amount'])

    db.session.add(payment)
    db.session.flush()   # get payment.id before invoice

    invoice = Invoice(
        invoice_id=generate_invoice_id(),
        payment_id=payment.id,
        patient_id=patient_id,
        amount=subtotal,
        tax=tax,
        discount=discount,
        total_amount=total,
        status='pending' if status == 'pending' else 'paid',
        due_date=datetime.utcnow().date(),
        paid_at=None if status == 'pending' else datetime.utcnow(),
    )
    db.session.add(invoice)
    db.session.commit()
    return payment, invoice


def _resolve_patient_id(current_user, data):
    """Return patient_id for the payer, supporting doctor-on-behalf-of-patient flows."""
    patient = Patient.query.filter_by(id=current_user['id']).first()
    if patient:
        return patient.id

    if current_user['role'] == 'doctor':
        lab_request_id = data.get('lab_request_id')
        if lab_request_id:
            from backend.models.lab_test import LabTest
            lab = LabTest.query.get(int(lab_request_id))
            if lab:
                return lab.patient_id
        fallback = Patient.query.first()
        if fallback:
            return fallback.id

    return None


def _ref_from_data(data):
    """Extract (reference_id, reference_type) from request data."""
    ref_id = data.get('reference_id')
    ref_type = data.get('reference_type')
    if data.get('lab_request_id'):
        try:
            ref_id = int(data['lab_request_id'])
            ref_type = 'lab_test'
        except (TypeError, ValueError):
            pass
    return ref_id, ref_type


def _send_confirmation(patient_id, total, payment_id):
    try:
        from backend.services.notification_service import send_payment_confirmation
        from backend.models.notification import Notification
        from backend.models.user import User as _User
        payer = _User.query.get(patient_id)
        if payer:
            # Email notification
            send_payment_confirmation(payer.email, payer.username, total, payment_id)
            # In-app notification
            db.session.add(Notification(
                user_id=patient_id,
                title='Payment Confirmed',
                message=f'Your payment of ETB {total:.2f} (ID: {payment_id}) has been processed successfully.',
                type='payment',
                category='general',
                is_read=False,
                link='/templates/payment/payment_history.html',
                created_at=datetime.utcnow()
            ))
            db.session.commit()
    except Exception:
        pass


# ── Chapa ─────────────────────────────────────────────────────────────────────

@payment_bp.route('/chapa/initialize', methods=['POST'])
@token_required(['patient', 'admin', 'doctor'])
def chapa_initialize(current_user):
    """
    POST /api/payments/chapa/initialize
    Initialises a Chapa payment and returns checkout_url.
    """
    if not _is_chapa_configured():
        return jsonify({
            'success': False,
            'message': 'Chapa payment is not configured. Please use Cash or contact admin.',
            'use_cash': True
        }), 503

    try:
        import requests as req
        data = request.get_json() or {}
        subtotal = float(data.get('amount', 0))
        tax = float(data.get('tax', 0))
        total = subtotal + tax

        patient_id = _resolve_patient_id(current_user, data)
        if not patient_id:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404
        patient = Patient.query.get(patient_id)

        tx_ref = generate_tx_ref()
        callback_url = current_app.config.get(
            'CHAPA_CALLBACK_URL', 'http://localhost:5000/api/payments/chapa/webhook')
        base_return = current_app.config.get(
            'CHAPA_RETURN_URL', 'http://localhost:5000/templates/payment/payment_success.html')
        # Append tx_ref so the success page can auto-verify without relying on localStorage
        return_url = f"{base_return}?tx_ref={tx_ref}"

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
            'customization[description]': data.get('notes', 'Healthcare Services'),
        }

        secret_key = current_app.config['CHAPA_SECRET_KEY']
        headers = {'Authorization': f'Bearer {secret_key}', 'Content-Type': 'application/json'}
        resp = req.post(
            f"{current_app.config.get('CHAPA_BASE_URL', 'https://api.chapa.co/v1')}/transaction/initialize",
            json=chapa_payload, headers=headers, timeout=15
        )
        result = resp.json()

        if result.get('status') != 'success':
            return jsonify({'success': False,
                            'message': result.get('message', 'Chapa initialization failed')}), 400

        ref_id, ref_type = _ref_from_data(data)
        payment, invoice = _make_payment(
            patient_id=patient_id,
            data={**data, 'payment_type': data.get('payment_type', 'services'),
                  'transaction_id': tx_ref},
            method='chapa',
            subtotal=subtotal,
            tax=tax,
            ref_id=ref_id,
            ref_type=ref_type,
        )
        # Chapa payments start as pending until webhook/verify confirms
        payment.payment_status = 'pending'
        db.session.commit()

        return jsonify({
            'success': True,
            'checkout_url': result['data']['checkout_url'],
            'tx_ref': tx_ref,
            'payment_id': payment.payment_id,
            'invoice_id': invoice.invoice_id,
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@payment_bp.route('/chapa/verify', methods=['GET', 'POST'])
@token_required(['patient', 'admin', 'doctor'])
def chapa_verify(current_user):
    """
    GET/POST /api/payments/chapa/verify?tx_ref=...
    Called by the frontend (with auth token) to verify and mark payment completed.
    """
    return _do_chapa_verify()


def _do_chapa_verify():
    """Shared logic: verify tx_ref with Chapa API and mark payment completed."""
    if not _is_chapa_configured():
        return jsonify({'success': False, 'message': 'Chapa not configured'}), 503

    try:
        import requests as req
        tx_ref = (request.args.get('tx_ref')
                  or request.args.get('trx_ref')
                  or (request.get_json(silent=True) or {}).get('tx_ref')
                  or (request.get_json(silent=True) or {}).get('trx_ref'))
        if not tx_ref:
            return jsonify({'success': False, 'message': 'tx_ref required'}), 400

        secret_key = current_app.config['CHAPA_SECRET_KEY']
        headers = {'Authorization': f'Bearer {secret_key}'}
        resp = req.get(
            f"{current_app.config.get('CHAPA_BASE_URL', 'https://api.chapa.co/v1')}/transaction/verify/{tx_ref}",
            headers=headers, timeout=15
        )
        result = resp.json()

        if result.get('status') != 'success':
            return jsonify({'success': False,
                            'message': result.get('message', 'Verification failed')}), 400

        payment = Payment.query.filter_by(transaction_id=tx_ref).first()
        if payment and payment.payment_status != 'completed':
            payment.payment_status = 'completed'
            payment.payment_date = datetime.utcnow()
            invoice = Invoice.query.filter_by(payment_id=payment.id).first()
            if invoice:
                invoice.status = 'paid'
                invoice.paid_at = datetime.utcnow()
            db.session.commit()
            _send_confirmation(payment.patient_id, payment.total_amount, payment.payment_id)

        return jsonify({
            'success': True,
            'message': 'Payment verified successfully',
            'payment_id': payment.payment_id if payment else tx_ref,
            'status': 'completed',
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@payment_bp.route('/chapa/status', methods=['GET'])
def chapa_status():
    """Public endpoint — frontend uses this to decide whether to show Chapa option."""
    key = current_app.config.get('CHAPA_SECRET_KEY', '')
    is_placeholder = not key or 'your-' in key.lower()
    is_test = key.startswith('CHASECK_TEST-')
    return jsonify({
        'success': True,
        'configured': not is_placeholder,
        'test_mode': is_test,
        'mode': 'disabled' if is_placeholder else ('test' if is_test else 'live'),
    }), 200


# ── Prediction payment access ─────────────────────────────────────────────────

@payment_bp.route('/check-prediction-access', methods=['GET'])
@token_required(['patient'])
def check_prediction_access(current_user):
    """Returns whether the patient has an unused paid prediction slot."""
    try:
        payment = Payment.query.filter(
            Payment.patient_id == current_user['id'],
            Payment.payment_type == 'prediction',
            Payment.payment_status == 'completed',
            Payment.prediction_consumed == False,
        ).order_by(Payment.created_at.desc()).first()

        if payment:
            return jsonify({
                'success': True, 'has_access': True,
                'payment_id': payment.payment_id,
                'message': 'Payment verified. You may proceed.',
            }), 200
        return jsonify({
            'success': True, 'has_access': False,
            'message': 'Payment required to run prediction.',
        }), 200

    except AttributeError:
        # prediction_consumed column missing — degrade gracefully
        # Fall back to checking any completed prediction payment
        try:
            payment = Payment.query.filter(
                Payment.patient_id == current_user['id'],
                Payment.payment_type == 'prediction',
                Payment.payment_status == 'completed',
            ).order_by(Payment.created_at.desc()).first()
            return jsonify({
                'success': True,
                'has_access': payment is not None,
                'message': 'Payment verified (fallback).' if payment else 'Payment required.',
            }), 200
        except Exception:
            return jsonify({'success': True, 'has_access': False,
                            'message': 'Payment required.'}), 200
    except Exception as e:
        current_app.logger.error(f'check-prediction-access error: {e}')
        return jsonify({'success': False, 'has_access': False,
                        'message': 'Could not verify payment. Please try again.'}), 500


@payment_bp.route('/consume-prediction-payment', methods=['POST'])
@token_required(['patient'])
def consume_prediction_payment(current_user):
    """Marks the prediction payment as consumed after ML runs successfully."""
    try:
        payment = Payment.query.filter(
            Payment.patient_id == current_user['id'],
            Payment.payment_type == 'prediction',
            Payment.payment_status == 'completed',
            Payment.prediction_consumed == False,
        ).order_by(Payment.created_at.desc()).first()

        if payment:
            payment.prediction_consumed = True
            db.session.commit()

        return jsonify({'success': True, 'message': 'Payment consumed'}), 200
    except Exception:
        return jsonify({'success': True, 'message': 'Consumed (fallback)'}), 200


# ── Process payment (cash / card / mobile / bank / insurance) ─────────────────

@payment_bp.route('/process', methods=['POST'])
@token_required(['patient', 'admin', 'doctor'])
def process_payment(current_user):
    """
    POST /api/payments/process
    Handles all non-Chapa payment methods.
    """
    try:
        data = request.get_json() or {}
        if 'amount' not in data:
            return jsonify({'success': False, 'message': 'Missing required field: amount'}), 400

        patient_id = _resolve_patient_id(current_user, data)
        if not patient_id:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404

        subtotal = float(data['amount'])
        tax = float(data.get('tax', 0))
        discount = float(data.get('discount', 0))
        method = data.get('payment_method', 'cash')

        valid_currencies = {'ETB', 'USD', 'EUR', 'GBP', 'JPY', 'CNY', 'INR',
                            'AED', 'SAR', 'CAD', 'AUD', 'CHF'}
        currency = data.get('currency', 'ETB').upper()
        if currency not in valid_currencies:
            return jsonify({'success': False,
                            'message': f"Invalid currency. Supported: {', '.join(sorted(valid_currencies))}"}), 400

        ref_id, ref_type = _ref_from_data(data)
        payment, invoice = _make_payment(
            patient_id=patient_id,
            data=data,
            method=method,
            subtotal=subtotal,
            tax=tax,
            discount=discount,
            ref_id=ref_id,
            ref_type=ref_type,
        )

        _send_confirmation(patient_id, payment.total_amount, payment.payment_id)

        return jsonify({
            'success': True,
            'message': 'Payment processed successfully',
            'payment': {
                'id': payment.id,
                'payment_id': payment.payment_id,
                'amount': payment.amount,
                'currency': currency,
                'total_amount': payment.total_amount,
                'payment_method': payment.payment_method,
                'status': payment.payment_status,
                'payment_type': payment.payment_type,
                'is_pending': payment.payment_status == 'pending',
                'created_at': payment.created_at.isoformat(),
            },
            'invoice': {
                'id': invoice.id,
                'invoice_id': invoice.invoice_id,
                'total_amount': invoice.total_amount,
                'status': invoice.status,
            },
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error processing payment',
                        'error': str(e)}), 500


# ── Payment history ───────────────────────────────────────────────────────────

@payment_bp.route('/history', methods=['GET'])
@token_required(['patient', 'admin', 'doctor'])
def get_payment_history(current_user):
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        # Admins can see all; patients/doctors see their own
        if current_user['role'] == 'admin':
            query = Payment.query
        else:
            patient = Patient.query.filter_by(id=current_user['id']).first()
            if not patient:
                return jsonify({'success': False, 'message': 'Patient not found'}), 404
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
                'id': p.id,
                'payment_id': p.payment_id,
                'invoice_id': invoice.invoice_id if invoice else None,
                'amount': float(p.amount),
                'total_amount': float(p.total_amount),
                'payment_method': p.payment_method,
                'payment_type': p.payment_type,
                'status': p.payment_status,
                'notes': p.notes,
                'created_at': p.created_at.isoformat() if p.created_at else None,
            })

        return jsonify({
            'success': True,
            'payments': payments_list,
            'pagination': {
                'total': total, 'limit': limit, 'offset': offset,
                'has_more': (offset + limit) < total,
            },
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': 'Error fetching payment history',
                        'error': str(e)}), 500


# ── Invoice ───────────────────────────────────────────────────────────────────

@payment_bp.route('/invoice/<string:invoice_id>', methods=['GET'])
@token_required(['patient', 'admin', 'doctor'])
def get_invoice(current_user, invoice_id):
    try:
        invoice = (Invoice.query.get(int(invoice_id)) if invoice_id.isdigit()
                   else Invoice.query.filter_by(invoice_id=invoice_id).first())
        if not invoice:
            return jsonify({'success': False, 'message': 'Invoice not found'}), 404

        patient = Patient.query.get(invoice.patient_id)
        if current_user['role'] != 'admin' and (not patient or patient.id != current_user['id']):
            return jsonify({'success': False, 'message': 'Access denied'}), 403

        payment = Payment.query.get(invoice.payment_id) if invoice.payment_id else None
        return jsonify({
            'success': True,
            'invoice': {
                'id': invoice.id,
                'invoice_id': invoice.invoice_id,
                'patient': {'id': patient.id, 'name': patient.username,
                            'email': patient.email} if patient else None,
                'amount': float(invoice.amount),
                'tax': float(invoice.tax) if invoice.tax else 0,
                'discount': float(invoice.discount) if invoice.discount else 0,
                'total_amount': float(invoice.total_amount),
                'status': invoice.status,
                'due_date': invoice.due_date.isoformat() if invoice.due_date else None,
                'paid_at': invoice.paid_at.isoformat() if invoice.paid_at else None,
                'payment': {
                    'id': payment.id,
                    'payment_id': payment.payment_id,
                    'payment_method': payment.payment_method,
                } if payment else None,
                'created_at': invoice.created_at.isoformat() if invoice.created_at else None,
            },
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': 'Error fetching invoice',
                        'error': str(e)}), 500


# ── Refund ────────────────────────────────────────────────────────────────────

@payment_bp.route('/refund/<string:payment_id>', methods=['POST'])
@token_required(['patient', 'admin'])
def process_refund(current_user, payment_id):
    try:
        payment = (Payment.query.get(int(payment_id)) if payment_id.isdigit()
                   else Payment.query.filter_by(payment_id=payment_id).first())
        if not payment:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404

        patient = Patient.query.get(payment.patient_id)
        if current_user['role'] != 'admin' and (not patient or patient.id != current_user['id']):
            return jsonify({'success': False, 'message': 'Access denied'}), 403

        if payment.payment_status != 'completed':
            return jsonify({'success': False,
                            'message': f"Cannot refund payment with status '{payment.payment_status}'"}), 400

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
            'success': True,
            'message': 'Refund processed successfully',
            'refund': {
                'payment_id': payment.payment_id,
                'amount': float(refund_amount),
                'reason': refund_reason,
                'status': 'completed',
                'processed_at': datetime.utcnow().isoformat(),
            },
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error processing refund',
                        'error': str(e)}), 500


# ── Subscriptions ─────────────────────────────────────────────────────────────

@payment_bp.route('/subscription', methods=['POST'])
@token_required(['patient'])
def create_subscription(current_user):
    try:
        data = request.get_json() or {}
        for field in ['plan', 'billing_cycle']:
            if field not in data:
                return jsonify({'success': False,
                                'message': f'Missing required field: {field}'}), 400

        patient = Patient.query.filter_by(id=current_user['id']).first()
        if not patient:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404

        if Subscription.query.filter_by(patient_id=patient.id, status='active').first():
            return jsonify({'success': False,
                            'message': 'Patient already has an active subscription'}), 400

        now = datetime.utcnow()
        days_map = {'weekly': 7, 'monthly': 30, 'quarterly': 90, 'yearly': 365}
        next_billing = now + timedelta(days=days_map.get(data['billing_cycle'], 30))

        sub_id = f"SUB{now.strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"
        subscription = Subscription(
            subscription_id=sub_id,
            patient_id=patient.id,
            plan=data['plan'],
            billing_cycle=data['billing_cycle'],
            amount=data.get('amount', 0),
            status='active',
            start_date=now,
            next_billing_date=next_billing,
            payment_method=data.get('payment_method'),
            created_at=now,
            updated_at=now,
        )
        db.session.add(subscription)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Subscription created successfully',
            'subscription': {
                'id': subscription.id,
                'subscription_id': subscription.subscription_id,
                'plan': subscription.plan,
                'billing_cycle': subscription.billing_cycle,
                'amount': float(subscription.amount) if subscription.amount else None,
                'status': subscription.status,
                'start_date': subscription.start_date.isoformat(),
                'next_billing_date': subscription.next_billing_date.isoformat(),
            },
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error creating subscription',
                        'error': str(e)}), 500


@payment_bp.route('/subscription', methods=['GET'])
@token_required(['patient'])
def get_subscription(current_user):
    try:
        patient = Patient.query.filter_by(id=current_user['id']).first()
        if not patient:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404

        subscription = (
            Subscription.query.filter_by(patient_id=patient.id, status='active').first()
            or Subscription.query.filter_by(patient_id=patient.id)
                         .order_by(Subscription.created_at.desc()).first()
        )
        if not subscription:
            return jsonify({'success': True, 'subscription': None,
                            'message': 'No subscription found'}), 200

        recent_payments = Payment.query.filter_by(patient_id=patient.id)\
            .order_by(Payment.created_at.desc()).limit(5).all()

        return jsonify({
            'success': True,
            'subscription': {
                'id': subscription.id,
                'subscription_id': subscription.subscription_id,
                'plan': subscription.plan,
                'billing_cycle': subscription.billing_cycle,
                'amount': float(subscription.amount) if subscription.amount else None,
                'status': subscription.status,
                'start_date': subscription.start_date.isoformat() if subscription.start_date else None,
                'next_billing_date': subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
                'cancelled_at': subscription.cancelled_at.isoformat() if subscription.cancelled_at else None,
                'payment_method': subscription.payment_method,
                'payment_history': [
                    {'id': p.id, 'payment_id': p.payment_id, 'amount': float(p.amount),
                     'status': p.payment_status,
                     'created_at': p.created_at.isoformat() if p.created_at else None}
                    for p in recent_payments
                ],
            },
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': 'Error fetching subscription',
                        'error': str(e)}), 500


@payment_bp.route('/subscription/cancel', methods=['POST'])
@token_required(['patient'])
def cancel_subscription(current_user):
    try:
        patient = Patient.query.filter_by(id=current_user['id']).first()
        if not patient:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404

        subscription = Subscription.query.filter_by(
            patient_id=patient.id, status='active').first()
        if not subscription:
            return jsonify({'success': False,
                            'message': 'No active subscription found'}), 404

        subscription.status = 'cancelled'
        subscription.cancelled_at = datetime.utcnow()
        subscription.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Subscription cancelled successfully',
            'subscription': {
                'id': subscription.id,
                'status': subscription.status,
                'cancelled_at': subscription.cancelled_at.isoformat(),
            },
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error cancelling subscription',
                        'error': str(e)}), 500


# ── Summary ───────────────────────────────────────────────────────────────────

@payment_bp.route('/summary', methods=['GET'])
@token_required(['patient', 'admin'])
def get_payment_summary(current_user):
    try:
        patient = Patient.query.filter_by(id=current_user['id']).first()
        if not patient:
            return jsonify({'success': False, 'message': 'Patient not found'}), 404

        total_paid = db.session.query(func.sum(Payment.amount)).filter(
            Payment.patient_id == patient.id,
            Payment.payment_status == 'completed'
        ).scalar() or 0

        total_refunded = db.session.query(func.sum(Payment.amount)).filter(
            Payment.patient_id == patient.id,
            Payment.payment_status == 'refunded'
        ).scalar() or 0

        payment_count = Payment.query.filter_by(patient_id=patient.id).count()
        subscription = Subscription.query.filter_by(
            patient_id=patient.id, status='active').first()

        return jsonify({
            'success': True,
            'summary': {
                'total_paid': float(total_paid),
                'total_refunded': float(total_refunded),
                'net_paid': float(total_paid - total_refunded),
                'payment_count': payment_count,
                'has_active_subscription': subscription is not None,
                'current_plan': subscription.plan if subscription else None,
            },
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': 'Error fetching summary',
                        'error': str(e)}), 500


# ── Receipt PDF ───────────────────────────────────────────────────────────────

@payment_bp.route('/receipt/<string:payment_id>/pdf', methods=['GET'])
@token_required(['patient', 'admin'])
def download_receipt_pdf(current_user, payment_id):
    try:
        from flask import send_file
        from backend.services.report_service import generate_payment_receipt_pdf

        payment = (Payment.query.get(int(payment_id)) if payment_id.isdigit()
                   else Payment.query.filter_by(payment_id=payment_id).first())
        if not payment:
            return jsonify({'success': False, 'message': 'Payment not found'}), 404

        patient = Patient.query.get(payment.patient_id)
        if current_user['role'] != 'admin' and (not patient or patient.id != current_user['id']):
            return jsonify({'success': False, 'message': 'Access denied'}), 403

        invoice = Invoice.query.filter_by(payment_id=payment.id).first()
        payment_info = {
            'payment_id': payment.payment_id,
            'invoice_id': invoice.invoice_id if invoice else '—',
            'amount': float(payment.amount),
            'tax': float(payment.tax) if payment.tax else 0,
            'discount': float(payment.discount) if payment.discount else 0,
            'total_amount': float(payment.total_amount),
            'payment_method': payment.payment_method,
            'status': payment.payment_status,
            'notes': payment.notes or 'Healthcare Services',
            'date': payment.created_at.isoformat() if payment.created_at else '',
        }
        patient_info = {
            'name': getattr(patient, 'full_name', None) or (patient.username if patient else '—'),
            'email': patient.email if patient else '—',
        }

        pdf_buf = generate_payment_receipt_pdf(payment_info, patient_info)
        return send_file(pdf_buf, mimetype='application/pdf', as_attachment=True,
                         download_name=f"receipt_{payment.payment_id}.pdf")

    except Exception as e:
        return jsonify({'success': False, 'message': 'Error generating receipt PDF',
                        'error': str(e)}), 500


# ── Chapa Webhook (server-to-server callback) ─────────────────────────────────

@payment_bp.route('/chapa/webhook', methods=['POST'])
def chapa_webhook():
    """
    POST /api/payments/chapa/webhook
    Chapa calls this after a transaction completes.
    Verifies the CHAPA-SIGNATURE header using HMAC-SHA256.
    """
    import hmac
    import hashlib

    webhook_secret = current_app.config.get('CHAPA_WEBHOOK_SECRET', '')
    if webhook_secret:
        signature = request.headers.get('CHAPA-SIGNATURE', '')
        expected = hmac.new(
            webhook_secret.encode(),
            request.data,
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            current_app.logger.warning('Chapa webhook: invalid signature')
            return jsonify({'success': False, 'message': 'Invalid signature'}), 401

    try:
        data = request.get_json(force=True) or {}
        tx_ref = data.get('tx_ref') or data.get('trx_ref')
        status = data.get('status', '')

        if not tx_ref:
            return jsonify({'success': False, 'message': 'tx_ref missing'}), 400

        payment = Payment.query.filter_by(transaction_id=tx_ref).first()
        if not payment:
            # Not our transaction — acknowledge anyway
            return jsonify({'success': True}), 200

        if status == 'success' and payment.payment_status != 'completed':
            payment.payment_status = 'completed'
            payment.payment_date = datetime.utcnow()
            invoice = Invoice.query.filter_by(payment_id=payment.id).first()
            if invoice:
                invoice.status = 'paid'
                invoice.paid_at = datetime.utcnow()
            db.session.commit()
            _send_confirmation(payment.patient_id, payment.total_amount, payment.payment_id)
            current_app.logger.info(f'Chapa webhook: payment {tx_ref} marked completed')

        elif status in ('failed', 'cancelled'):
            payment.payment_status = 'failed'
            db.session.commit()

        return jsonify({'success': True}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Chapa webhook error: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500
