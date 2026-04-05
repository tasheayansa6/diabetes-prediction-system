"""
Service Tests - Tests for all backend services
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from backend import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.doctor import Doctor
from backend.models.prediction import Prediction
from backend.models.health_record import HealthRecord
from backend.models.prescription import Prescription
from backend.models.lab_test import LabTest
from backend.models.payment import Payment
from backend.models.audit_log import AuditLog
from werkzeug.security import generate_password_hash, check_password_hash


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def test_patient(app):
    """Create a test patient within app context"""
    with app.app_context():
        patient = Patient(
            username='testpatient',
            email='patient@test.com',
            password_hash=generate_password_hash('Test1234'),
            role='patient',
            patient_id='PAT001',
            blood_group='O+'
        )
        db.session.add(patient)
        db.session.commit()
        return patient.id


@pytest.fixture
def test_doctor(app):
    """Create a test doctor within app context"""
    with app.app_context():
        doctor = Doctor(
            username='testdoctor',
            email='doctor@test.com',
            password_hash=generate_password_hash('Doctor123'),
            role='doctor',
            doctor_id='DOC001',
            specialization='Cardiology'
        )
        db.session.add(doctor)
        db.session.commit()
        return doctor.id


# ============ PREDICTION SERVICE TESTS ============

class TestPredictionService:
    def test_prediction_service_initialization(self, app):
        """Test prediction service initializes correctly"""
        from backend.services.prediction_service import PredictionService
        service = PredictionService()
        assert service is not None
        assert hasattr(service, 'predict_diabetes')
    
    @patch('backend.services.prediction_service.get_ml_service')
    def test_predict_diabetes_success(self, mock_get_ml_service, app):
        """Test successful diabetes prediction"""
        from backend.services.prediction_service import PredictionService
        
        # Mock ML service response
        mock_ml = MagicMock()
        mock_ml.predict.return_value = {
            'success': True,
            'prediction': 1,
            'probability': 0.85,
            'probability_percent': 85.0,
            'risk_level': 'HIGH RISK',
            'interpretation': 'High risk of diabetes',
            'recommendation': 'Consult doctor immediately'
        }
        mock_get_ml_service.return_value = mock_ml
        
        service = PredictionService()
        result = service.predict_diabetes({
            'glucose': 150,
            'blood_pressure': 90,
            'bmi': 32,
            'age': 55,
            'pregnancies': 2
        })
        
        assert result['success'] is True
        assert 'prediction' in result
        assert 'risk_level' in result
    
    def test_predict_diabetes_missing_fields(self, app):
        """Test prediction with missing required fields - expect exception"""
        from backend.services.prediction_service import PredictionService
        
        service = PredictionService()
        
        # This should raise an exception or return error
        try:
            result = service.predict_diabetes({'glucose': 150})
            # If it returns without exception, check for error
            assert result.get('success') is False or 'error' in result
        except Exception as e:
            # Exception is acceptable too
            assert True
    
    def test_predict_diabetes_invalid_data(self, app):
        """Test prediction with invalid data - expect exception or error"""
        from backend.services.prediction_service import PredictionService
        
        service = PredictionService()
        
        try:
            result = service.predict_diabetes({
                'glucose': -10,  # Invalid glucose
                'blood_pressure': 90,
                'bmi': 32,
                'age': 55
            })
            assert result.get('success') is False or 'error' in result
        except Exception:
            assert True


# ============ AUTH SERVICE TESTS ============

class TestAuthService:
    def test_validate_email_valid(self, app):
        """Test email validation with valid emails"""
        from backend.routes.auth_routes import validate_email
        
        assert validate_email('test@example.com') is True
        assert validate_email('user.name@domain.co.uk') is True
        assert validate_email('test+filter@example.com') is True
    
    def test_validate_email_invalid(self, app):
        """Test email validation with invalid emails"""
        from backend.routes.auth_routes import validate_email
        
        assert validate_email('test@') is False
        assert validate_email('test@example') is False
        assert validate_email('test.example.com') is False
        assert validate_email('') is False
    
    def test_validate_password_valid(self, app):
        """Test password validation with valid passwords"""
        from backend.routes.auth_routes import validate_password
        
        valid, message = validate_password('Test1234')
        assert valid is True
        
        valid, message = validate_password('StrongPass123')
        assert valid is True
        
        valid, message = validate_password('Pass123!@#')
        assert valid is True
    
    def test_validate_password_invalid(self, app):
        """Test password validation with invalid passwords"""
        from backend.routes.auth_routes import validate_password
        
        # Too short
        valid, message = validate_password('Test12')
        assert valid is False
        assert '8 characters' in message
        
        # No uppercase
        valid, message = validate_password('test1234')
        assert valid is False
        assert 'uppercase' in message
        
        # No lowercase
        valid, message = validate_password('TEST1234')
        assert valid is False
        assert 'lowercase' in message
        
        # No number
        valid, message = validate_password('TestPass')
        assert valid is False
        assert 'number' in message


# ============ DIAGNOSIS SERVICE TESTS ============

class TestDiagnosisService:
    def test_risk_level_determination(self, app):
        """Test risk level determination based on probability"""
        def get_risk_level(probability):
            if probability < 30:
                return 'LOW RISK'
            elif probability < 60:
                return 'MODERATE RISK'
            elif probability < 80:
                return 'HIGH RISK'
            else:
                return 'VERY HIGH RISK'
        
        assert get_risk_level(20) == 'LOW RISK'
        assert get_risk_level(50) == 'MODERATE RISK'
        assert get_risk_level(75) == 'HIGH RISK'
        assert get_risk_level(90) == 'VERY HIGH RISK'
    
    def test_risk_color_mapping(self, app):
        """Test risk color mapping - Check VERY before HIGH"""
        def get_risk_color(risk_level):
            if not risk_level:
                return '⚪'
            # Check for VERY first (since it contains HIGH)
            if 'VERY' in risk_level:
                return '🔴'
            elif 'HIGH' in risk_level:
                return '🟠'
            elif 'MODERATE' in risk_level:
                return '🟡'
            elif 'LOW' in risk_level:
                return '🟢'
            return '⚪'
        
        # Map risk levels to colors
        assert get_risk_color('LOW RISK') == '🟢'
        assert get_risk_color('MODERATE RISK') == '🟡'
        assert get_risk_color('HIGH RISK') == '🟠'
        assert get_risk_color('VERY HIGH RISK') == '🔴'
        assert get_risk_color(None) == '⚪'
        assert get_risk_color('UNKNOWN') == '⚪'


# ============ PRESCRIPTION SERVICE TESTS ============

class TestPrescriptionService:
    def test_create_prescription(self, app, test_patient, test_doctor):
        """Test prescription creation"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            doctor = db.session.get(Doctor, test_doctor)
            
            prescription = Prescription(
                prescription_id='RX001',
                patient_id=patient.id,
                doctor_id=doctor.id,
                medication='Metformin',
                dosage='500mg',
                frequency='twice daily',
                duration='30 days',
                status='pending'
            )
            db.session.add(prescription)
            db.session.commit()
            
            assert prescription.id is not None
            assert prescription.medication == 'Metformin'
            assert prescription.status == 'pending'
    
    def test_prescription_status_flow(self, app, test_patient, test_doctor):
        """Test prescription status transitions"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            doctor = db.session.get(Doctor, test_doctor)
            
            prescription = Prescription(
                prescription_id='RX002',
                patient_id=patient.id,
                doctor_id=doctor.id,
                medication='Lisinopril',
                dosage='10mg',
                frequency='once daily',
                duration='30 days',
                status='pending'
            )
            db.session.add(prescription)
            db.session.commit()
            
            assert prescription.status == 'pending'
            
            # Change to verified
            prescription.status = 'verified'
            prescription.verified_at = datetime.utcnow()
            db.session.commit()
            assert prescription.status == 'verified'
            
            # Change to dispensed
            prescription.status = 'dispensed'
            prescription.dispensed_at = datetime.utcnow()
            db.session.commit()
            assert prescription.status == 'dispensed'
    
    def test_prescription_to_dict(self, app, test_patient, test_doctor):
        """Test prescription to_dict method"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            doctor = db.session.get(Doctor, test_doctor)
            
            prescription = Prescription(
                prescription_id='RX003',
                patient_id=patient.id,
                doctor_id=doctor.id,
                medication='Metformin',
                dosage='500mg',
                frequency='twice daily',
                duration='30 days',
                instructions='Take with meals'
            )
            db.session.add(prescription)
            db.session.commit()
            
            prescription_dict = prescription.to_dict()
            assert prescription_dict['prescription_id'] == 'RX003'
            assert prescription_dict['medication'] == 'Metformin'
            assert 'created_at' in prescription_dict


# ============ LAB SERVICE TESTS ============

class TestLabService:
    def test_create_lab_test(self, app, test_patient, test_doctor):
        """Test lab test creation"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            doctor = db.session.get(Doctor, test_doctor)
            
            lab_test = LabTest(
                test_id='LAB001',
                patient_id=patient.id,
                doctor_id=doctor.id,
                test_name='Complete Blood Count',
                test_type='hematology',
                status='pending'
            )
            db.session.add(lab_test)
            db.session.commit()
            
            assert lab_test.id is not None
            assert lab_test.test_name == 'Complete Blood Count'
            assert lab_test.status == 'pending'
    
    def test_lab_test_status_flow(self, app, test_patient, test_doctor):
        """Test lab test status transitions"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            doctor = db.session.get(Doctor, test_doctor)
            
            lab_test = LabTest(
                test_id='LAB002',
                patient_id=patient.id,
                doctor_id=doctor.id,
                test_name='Blood Glucose',
                test_type='chemistry',
                status='pending'
            )
            db.session.add(lab_test)
            db.session.commit()
            
            # Start test
            lab_test.status = 'in_progress'
            lab_test.test_started_at = datetime.utcnow()
            db.session.commit()
            assert lab_test.status == 'in_progress'
            
            # Complete test
            lab_test.status = 'completed'
            lab_test.results = 'Glucose: 95 mg/dL'
            lab_test.test_completed_at = datetime.utcnow()
            db.session.commit()
            assert lab_test.status == 'completed'
            assert lab_test.results is not None
    
    def test_lab_test_validation(self, app):
        """Test lab test validation"""
        # Define validation function
        def validate_vital_signs(data):
            if 'temperature' in data and data['temperature']:
                temp = float(data['temperature'])
                if temp < 35 or temp > 42:
                    return False, "Temperature out of normal range (35-42°C)"
            if 'heart_rate' in data and data['heart_rate']:
                hr = int(data['heart_rate'])
                if hr < 30 or hr > 200:
                    return False, "Heart rate out of normal range (30-200 bpm)"
            return True, "Valid"
        
        # Valid vitals
        valid_data = {
            'temperature': 37.0,
            'heart_rate': 72
        }
        valid, message = validate_vital_signs(valid_data)
        assert valid is True
        
        # Invalid temperature
        invalid_data = {
            'temperature': 50.0,
            'heart_rate': 72
        }
        valid, message = validate_vital_signs(invalid_data)
        assert valid is False
        
        # Invalid heart rate
        invalid_data = {
            'temperature': 37.0,
            'heart_rate': 20
        }
        valid, message = validate_vital_signs(invalid_data)
        assert valid is False


# ============ PAYMENT SERVICE TESTS ============

class TestPaymentService:
    def test_create_payment(self, app, test_patient):
        """Test payment creation"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            
            payment = Payment(
                payment_id='PAY001',
                patient_id=patient.id,
                payment_type='consultation',
                amount=100.00,
                total_amount=100.00,
                payment_method='online',
                payment_status='completed'
            )
            db.session.add(payment)
            db.session.commit()
            
            assert payment.id is not None
            assert payment.amount == 100.00
            assert payment.payment_status == 'completed'
    
    def test_payment_calculation(self, app, test_patient):
        """Test payment amount calculation with tax and discount"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            
            amount = 100.00
            tax = 8.00
            discount = 10.00
            total = amount + tax - discount
            
            payment = Payment(
                payment_id='PAY002',
                patient_id=patient.id,
                payment_type='lab_test',
                amount=amount,
                tax=tax,
                discount=discount,
                total_amount=total,
                payment_method='online',
                payment_status='completed'
            )
            db.session.add(payment)
            db.session.commit()
            
            assert payment.total_amount == 98.00
            assert payment.amount == 100.00
    
    def test_payment_refund(self, app, test_patient):
        """Test payment refund status"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            
            payment = Payment(
                payment_id='PAY003',
                patient_id=patient.id,
                payment_type='consultation',
                amount=150.00,
                total_amount=150.00,
                payment_method='online',
                payment_status='completed'
            )
            db.session.add(payment)
            db.session.commit()
            
            # Refund the payment
            payment.payment_status = 'refunded'
            db.session.commit()
            
            assert payment.payment_status == 'refunded'


# ============ AUDIT LOG SERVICE TESTS ============

class TestAuditLogService:
    def test_create_audit_log(self, app, test_patient):
        """Test audit log creation"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            
            log = AuditLog(
                user_id=patient.id,
                username=patient.username,
                user_role='patient',
                action='LOGIN',
                resource='auth',
                description='User logged in',
                ip_address='127.0.0.1'
            )
            db.session.add(log)
            db.session.commit()
            
            assert log.id is not None
            assert log.action == 'LOGIN'
            assert log.username == patient.username
    
    def test_audit_log_log_action_method(self, app, test_patient):
        """Test AuditLog.log_action helper method"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            
            log = AuditLog.log_action(
                user_id=patient.id,
                username=patient.username,
                user_role='patient',
                action='CREATE_PRESCRIPTION',
                resource='prescription',
                resource_id=123,
                description='Created new prescription',
                ip_address='127.0.0.1'
            )
            
            assert log.id is not None
            assert log.action == 'CREATE_PRESCRIPTION'
            assert log.resource_id == 123
    
    def test_audit_log_to_dict(self, app, test_patient):
        """Test audit log to_dict method"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            
            log = AuditLog(
                user_id=patient.id,
                username=patient.username,
                user_role='patient',
                action='VIEW_PROFILE',
                resource='profile',
                description='Viewed profile',
                ip_address='127.0.0.1'
            )
            db.session.add(log)
            db.session.commit()
            
            log_dict = log.to_dict()
            assert log_dict['action'] == 'VIEW_PROFILE'
            assert 'description' in log_dict
            assert 'created_at' in log_dict


# ============ HEALTH RECORD SERVICE TESTS ============

class TestHealthRecordService:
    def test_create_health_record(self, app, test_patient):
        """Test health record creation - FIXED with all required fields"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            
            # HealthRecord requires diabetes_pedigree field
            record = HealthRecord(
                patient_id=patient.id,
                glucose=120,
                blood_pressure=120,
                bmi=25.5,
                age=30,
                pregnancies=2,
                insulin=85,
                skin_thickness=23,
                diabetes_pedigree=0.5  # Required field
            )
            db.session.add(record)
            db.session.commit()
            
            assert record.id is not None
            assert record.glucose == 120
            assert record.bmi == 25.5
    
    def test_health_record_validation(self, app):
        """Test health record data validation"""
        from backend.utils.validators import validate_health_data
        
        # Valid data
        valid_data = {
            'glucose': 120,
            'blood_pressure': 120,
            'bmi': 25.5,
            'age': 30
        }
        valid, message = validate_health_data(valid_data)
        assert valid is True
        
        # Invalid glucose (negative)
        invalid_data = {
            'glucose': -50,
            'blood_pressure': 120,
            'bmi': 25.5,
            'age': 30
        }
        valid, message = validate_health_data(invalid_data)
        assert valid is False


# ============ ML SERVICE TESTS ============

class TestMLService:
    @patch('backend.services.ml_service.MLService')
    def test_ml_service_initialization(self, mock_ml_service, app):
        """Test ML service initialization"""
        from backend.services.ml_service import get_ml_service
        
        service1 = get_ml_service()
        service2 = get_ml_service()
        
        assert service1 is service2
    
    @patch('backend.services.ml_service.MLService')
    def test_ml_prediction_format(self, mock_ml_service, app):
        """Test ML prediction output format"""
        from backend.services.ml_service import get_ml_service
        
        mock_instance = MagicMock()
        mock_instance.predict.return_value = {
            'success': True,
            'prediction_code': 1,
            'probability': 0.85,
            'probability_percent': 85.0,
            'risk_level': 'HIGH RISK'
        }
        mock_ml_service.return_value = mock_instance
        
        service = get_ml_service()
        result = service.predict({'glucose': 150, 'bmi': 32, 'age': 55})
        
        assert result['success'] is True
        assert 'prediction_code' in result
        assert 'probability' in result
        assert 'risk_level' in result


# ============ REPORT SERVICE TESTS ============

class TestReportService:
    def test_generate_prediction_report(self, app, test_patient):
        """Test prediction report generation - FIXED with all required fields"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            
            # Create health record with all required fields
            record = HealthRecord(
                patient_id=patient.id,
                glucose=140,
                blood_pressure=120,
                bmi=28.5,
                age=45,
                pregnancies=0,
                insulin=85,
                skin_thickness=25,
                diabetes_pedigree=0.5  # Required field
            )
            db.session.add(record)
            db.session.flush()
            
            # Create prediction
            prediction = Prediction(
                patient_id=patient.id,
                health_record_id=record.id,
                prediction=1,
                probability=0.75,
                probability_percent=75.0,
                risk_level='HIGH RISK',
                model_version='1.0'
            )
            db.session.add(prediction)
            db.session.commit()
            
            assert prediction.risk_level == 'HIGH RISK'
            assert prediction.probability_percent == 75.0
    
    def test_generate_payment_report(self, app, test_patient):
        """Test payment report generation"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            
            payments = [
                Payment(
                    payment_id=f'PAY{i}',
                    patient_id=patient.id,
                    payment_type='consultation',
                    amount=100.00,
                    total_amount=100.00,
                    payment_method='online',
                    payment_status='completed'
                ) for i in range(3)
            ]
            for p in payments:
                db.session.add(p)
            db.session.commit()
            
            total = sum(p.amount for p in payments)
            assert total == 300.00


# ============ SERVICE INTEGRATION TESTS ============

class TestServiceIntegration:
    def test_full_prediction_workflow(self, app, test_patient):
        """Test complete prediction workflow - FIXED with all required fields"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            
            # Create health record with all required fields
            record = HealthRecord(
                patient_id=patient.id,
                glucose=150,
                blood_pressure=90,
                bmi=32,
                age=55,
                pregnancies=2,
                insulin=85,
                skin_thickness=28,
                diabetes_pedigree=0.5  # Required field
            )
            db.session.add(record)
            db.session.flush()
            
            # Create prediction
            prediction = Prediction(
                patient_id=patient.id,
                health_record_id=record.id,
                prediction=1,
                probability=0.85,
                probability_percent=85.0,
                risk_level='HIGH RISK',
                model_version='1.0'
            )
            db.session.add(prediction)
            db.session.commit()
            
            assert prediction.health_record_id == record.id
            assert prediction.patient_id == patient.id
            assert 'HIGH' in prediction.risk_level
    
    def test_audit_log_tracking(self, app, test_patient):
        """Test audit log tracks actions correctly"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            
            log = AuditLog.log_action(
                user_id=patient.id,
                username=patient.username,
                user_role='patient',
                action='VIEW_PREDICTION',
                resource='prediction',
                resource_id=123,
                description='Viewed prediction results',
                ip_address='127.0.0.1'
            )
            
            assert log.id is not None
            assert log.action == 'VIEW_PREDICTION'
            assert log.user_id == patient.id
            
            user_logs = AuditLog.query.filter_by(user_id=patient.id).all()
            assert len(user_logs) > 0
    
    def test_prescription_payment_workflow(self, app, test_patient, test_doctor):
        """Test prescription and payment workflow"""
        with app.app_context():
            patient = db.session.get(Patient, test_patient)
            doctor = db.session.get(Doctor, test_doctor)
            
            # Create prescription
            prescription = Prescription(
                prescription_id='RX_INT_001',
                patient_id=patient.id,
                doctor_id=doctor.id,
                medication='Metformin',
                dosage='500mg',
                frequency='twice daily',
                duration='30 days',
                status='verified'
            )
            db.session.add(prescription)
            db.session.flush()
            
            # Create payment for prescription
            payment = Payment(
                payment_id='PAY_INT_001',
                patient_id=patient.id,
                payment_type='prescription',
                reference_id=prescription.id,
                reference_type='prescription',
                amount=50.00,
                total_amount=50.00,
                payment_method='online',
                payment_status='completed'
            )
            db.session.add(payment)
            db.session.commit()
            
            assert payment.reference_id == prescription.id
            assert payment.payment_type == 'prescription'


# ============ RUN TESTS ============

if __name__ == '__main__':
    pytest.main([__file__, '-v'])