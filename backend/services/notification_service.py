"""
Notification Service - Real email sending via Flask-Mail
"""
from flask import current_app
from flask_mail import Message
from backend.extensions import mail


def _send(subject, recipient, html_body):
    """Send an email. Returns (success, error_message)."""
    try:
        from flask import current_app
        # If suppressed, log what would be sent
        if current_app.config.get('MAIL_SUPPRESS_SEND', True):
            current_app.logger.info(
                f"[EMAIL SUPPRESSED] To: {recipient} | Subject: {subject} "
                f"| Set MAIL_SUPPRESS_SEND=False in .env to send real emails"
            )
            return True, None

        msg = Message(
            subject=subject,
            recipients=[recipient],
            html=html_body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', current_app.config.get('MAIL_USERNAME'))
        )
        mail.send(msg)
        return True, None
    except Exception as e:
        current_app.logger.error(f"Email send failed to {recipient}: {e}")
        return False, str(e)


def _base_template(title, icon, color, content):
    return f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;background:#f8fafc;padding:24px;">
      <div style="background:linear-gradient(135deg,{color});border-radius:16px 16px 0 0;padding:32px 24px;text-align:center;">
        <div style="font-size:2.5rem;">{icon}</div>
        <h1 style="color:#fff;margin:12px 0 0;font-size:1.4rem;">{title}</h1>
      </div>
      <div style="background:#fff;border-radius:0 0 16px 16px;padding:32px 24px;border:1px solid #e2e8f0;border-top:none;">
        {content}
        <hr style="border:none;border-top:1px solid #f1f5f9;margin:24px 0;">
        <p style="color:#94a3b8;font-size:0.75rem;text-align:center;margin:0;">
          Diabetes Prediction System &nbsp;|&nbsp; This is an automated message, please do not reply.
        </p>
      </div>
    </div>
    """


def send_otp_email(recipient_email, recipient_name, otp_code):
    """Send 6-digit OTP for email verification."""
    content = f"""
    <p style="color:#334155;font-size:1rem;">Hi <strong>{recipient_name}</strong>,</p>
    <p style="color:#64748b;">Your email verification code is:</p>
    <div style="text-align:center;margin:24px 0;">
      <span style="font-size:2.5rem;font-weight:800;letter-spacing:0.5rem;color:#1e3a8a;
                   background:#eff6ff;padding:16px 32px;border-radius:12px;display:inline-block;">
        {otp_code}
      </span>
    </div>
    <p style="color:#64748b;font-size:0.875rem;">This code expires in <strong>15 minutes</strong>. Do not share it with anyone.</p>
    """
    html = _base_template("Verify Your Email", "✉️", "#1e3a8a,#2563eb", content)
    return _send("Your Email Verification Code – Diabetes Prediction System", recipient_email, html)


def send_password_reset_email(recipient_email, recipient_name, reset_token, reset_url):
    """Send password reset link."""
    content = f"""
    <p style="color:#334155;font-size:1rem;">Hi <strong>{recipient_name}</strong>,</p>
    <p style="color:#64748b;">We received a request to reset your password. Click the button below:</p>
    <div style="text-align:center;margin:28px 0;">
      <a href="{reset_url}" style="background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff;
         text-decoration:none;padding:14px 32px;border-radius:10px;font-weight:600;font-size:0.95rem;display:inline-block;">
        Reset My Password
      </a>
    </div>
    <p style="color:#64748b;font-size:0.875rem;">Or copy this link: <a href="{reset_url}" style="color:#3b82f6;">{reset_url}</a></p>
    <p style="color:#94a3b8;font-size:0.8rem;">This link expires in <strong>1 hour</strong>. If you didn't request this, ignore this email.</p>
    """
    html = _base_template("Password Reset Request", "🔑", "#3b82f6,#2563eb", content)
    return _send("Reset Your Password – Diabetes Prediction System", recipient_email, html)


def send_prediction_notification(recipient_email, recipient_name, risk_level, probability):
    """Notify patient that their prediction result is ready."""
    color_map = {
        'LOW RISK': '#059669', 'MODERATE RISK': '#d97706',
        'HIGH RISK': '#dc2626', 'VERY HIGH RISK': '#7c3aed'
    }
    badge_color = color_map.get(risk_level, '#64748b')
    content = f"""
    <p style="color:#334155;">Hi <strong>{recipient_name}</strong>,</p>
    <p style="color:#64748b;">Your diabetes risk assessment is complete.</p>
    <div style="background:#f8fafc;border-radius:12px;padding:20px;margin:20px 0;text-align:center;">
      <span style="background:{badge_color};color:#fff;padding:8px 20px;border-radius:99px;font-weight:700;">
        {risk_level}
      </span>
      <p style="color:#334155;font-size:1.5rem;font-weight:800;margin:12px 0 0;">{probability:.1f}% probability</p>
    </div>
    <p style="color:#64748b;font-size:0.875rem;">Log in to your patient portal to view the full report and recommendations.</p>
    """
    html = _base_template("Your Prediction Result is Ready", "🩺", "#1e3a8a,#2563eb", content)
    return _send("Diabetes Risk Assessment Result – Diabetes Prediction System", recipient_email, html)


def send_appointment_reminder(recipient_email, recipient_name, appointment_date, appointment_time, doctor_name):
    """Send appointment reminder email."""
    content = f"""
    <p style="color:#334155;">Hi <strong>{recipient_name}</strong>,</p>
    <p style="color:#64748b;">This is a reminder for your upcoming appointment:</p>
    <div style="background:#eff6ff;border-radius:12px;padding:20px;margin:20px 0;">
      <p style="margin:6px 0;color:#1e3a8a;"><strong>📅 Date:</strong> {appointment_date}</p>
      <p style="margin:6px 0;color:#1e3a8a;"><strong>🕐 Time:</strong> {appointment_time or 'TBD'}</p>
      <p style="margin:6px 0;color:#1e3a8a;"><strong>👨‍⚕️ Doctor:</strong> Dr. {doctor_name}</p>
    </div>
    <p style="color:#64748b;font-size:0.875rem;">Please arrive 15 minutes early. Log in to manage your appointment.</p>
    """
    html = _base_template("Appointment Reminder", "📅", "#059669,#10b981", content)
    return _send("Appointment Reminder – Diabetes Prediction System", recipient_email, html)


def send_prescription_ready(recipient_email, recipient_name, medication, prescription_id):
    """Notify patient that prescription is ready for pickup."""
    content = f"""
    <p style="color:#334155;">Hi <strong>{recipient_name}</strong>,</p>
    <p style="color:#64748b;">Your prescription is approved and ready for pickup.</p>
    <div style="background:#ecfdf5;border-radius:12px;padding:20px;margin:20px 0;">
      <p style="margin:6px 0;color:#065f46;"><strong>💊 Medication:</strong> {medication}</p>
      <p style="margin:6px 0;color:#065f46;"><strong>🆔 Prescription ID:</strong> {prescription_id}</p>
    </div>
    <p style="color:#64748b;font-size:0.875rem;">Visit the pharmacy with your prescription ID to collect your medication.</p>
    """
    html = _base_template("Prescription Ready for Pickup", "💊", "#059669,#10b981", content)
    return _send("Your Prescription is Ready – Diabetes Prediction System", recipient_email, html)


def send_lab_results_ready(recipient_email, recipient_name, test_name, test_id):
    """Notify patient that lab results are available."""
    content = f"""
    <p style="color:#334155;">Hi <strong>{recipient_name}</strong>,</p>
    <p style="color:#64748b;">Your lab test results are now available in your patient portal.</p>
    <div style="background:#eff6ff;border-radius:12px;padding:20px;margin:20px 0;">
      <p style="margin:6px 0;color:#1e3a8a;"><strong>🔬 Test:</strong> {test_name}</p>
      <p style="margin:6px 0;color:#1e3a8a;"><strong>🆔 Test ID:</strong> {test_id}</p>
    </div>
    <p style="color:#64748b;font-size:0.875rem;">Log in to your patient portal to view the full results and recommendations.</p>
    """
    html = _base_template("Lab Results Available", "🔬", "#0891b2,#06b6d4", content)
    return _send("Your Lab Results are Ready – Diabetes Prediction System", recipient_email, html)


def push_notification(user_id, title, message, type='info', category='general', link=''):
    """Save an in-app notification to the database AND emit via WebSocket."""
    try:
        from backend.models.notification import Notification
        from backend.extensions import db, socketio
        notif = Notification(
            user_id=user_id, title=title, message=message,
            type=type, category=category, is_read=False, link=link
        )
        db.session.add(notif)
        db.session.commit()
        # Emit real-time event to the user's private room
        try:
            socketio.emit('notification', {
                'id': notif.id,
                'title': title,
                'message': message,
                'type': type,
                'link': link,
                'is_read': False,
                'created_at': notif.created_at.isoformat() if notif.created_at else None
            }, room=f'user_{user_id}')
        except Exception:
            pass  # WebSocket emit is best-effort
    except Exception as e:
        current_app.logger.error(f"push_notification failed: {e}")


def send_payment_confirmation(recipient_email, recipient_name, amount, payment_id):
    """Notify patient of successful payment."""
    content = f"""
    <p style="color:#334155;">Hi <strong>{recipient_name}</strong>,</p>
    <p style="color:#64748b;">Your payment has been processed successfully.</p>
    <div style="background:#ecfdf5;border-radius:12px;padding:20px;margin:20px 0;">
      <p style="margin:6px 0;color:#065f46;"><strong>💰 Amount:</strong> ETB {amount:.2f}</p>
      <p style="margin:6px 0;color:#065f46;"><strong>🆔 Payment ID:</strong> {payment_id}</p>
    </div>
    <p style="color:#64748b;font-size:0.875rem;">Keep this receipt for your records. Log in to download a PDF receipt.</p>
    """
    html = _base_template("Payment Confirmed", "✅", "#059669,#10b981", content)
    return _send("Payment Confirmation – Diabetes Prediction System", recipient_email, html)


def send_sms(recipient_phone: str, message: str) -> tuple:
    """
    Send SMS notification.
    Requires AFRICASTALKING_API_KEY and AFRICASTALKING_USERNAME in .env
    Or TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER
    Falls back to logging if not configured.
    """
    try:
        from flask import current_app
        import os

        # Try Africa's Talking
        at_key  = os.getenv('AFRICASTALKING_API_KEY', '')
        at_user = os.getenv('AFRICASTALKING_USERNAME', '')
        if at_key and at_user and 'your-' not in at_key:
            import africastalking
            africastalking.initialize(at_user, at_key)
            sms = africastalking.SMS
            response = sms.send(message, [recipient_phone])
            return True, None

        # Try Twilio
        tw_sid  = os.getenv('TWILIO_ACCOUNT_SID', '')
        tw_auth = os.getenv('TWILIO_AUTH_TOKEN', '')
        tw_from = os.getenv('TWILIO_FROM_NUMBER', '')
        if tw_sid and tw_auth and tw_from and 'your-' not in tw_sid:
            from twilio.rest import Client
            client = Client(tw_sid, tw_auth)
            client.messages.create(body=message, from_=tw_from, to=recipient_phone)
            return True, None

        # Fallback: log the SMS
        current_app.logger.info(
            f"[SMS SUPPRESSED] To: {recipient_phone} | Message: {message} "
            f"| Set AFRICASTALKING_API_KEY or TWILIO_ACCOUNT_SID in .env to send real SMS"
        )
        return True, None

    except Exception as e:
        try:
            from flask import current_app
            current_app.logger.error(f"SMS send failed to {recipient_phone}: {e}")
        except Exception:
            pass
        return False, str(e)
