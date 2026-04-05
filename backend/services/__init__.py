"""
Services Package - Business Logic Layer for Diabetes Prediction System
All services are initialized here for easy importing
"""

from .ml_service import MLService
from .prediction_service import PredictionService
from .diagnosis_service import DiagnosisService
from .prescription_service import PrescriptionService
from .lab_service import LabService
from .payment_service import calculate_total, generate_payment_id, generate_invoice_id

class PaymentService:
    def calculate_total(self, *a, **kw): return calculate_total(*a, **kw)
    def generate_payment_id(self): return generate_payment_id()
    def generate_invoice_id(self): return generate_invoice_id()
from .report_service import generate_patient_pdf, generate_payment_receipt_pdf

# Compatibility shim — keeps existing imports working
class ReportService:
    def generate_patient_pdf(self, *a, **kw):
        return generate_patient_pdf(*a, **kw)
    def generate_payment_receipt_pdf(self, *a, **kw):
        return generate_payment_receipt_pdf(*a, **kw)
from .notification_service import (
    send_otp_email, send_password_reset_email,
    send_prediction_notification, send_appointment_reminder, send_prescription_ready
)

# Compatibility shim
class NotificationService:
    pass
from .model_management_service import ModelManagementService

__all__ = [
    'MLService',
    'PredictionService',
    'DiagnosisService',
    'PrescriptionService',
    'LabService',
    'PaymentService',
    'ReportService',
    'NotificationService',
    'ModelManagementService'
]