"""
Integration Tests - Tests for end-to-end workflows across multiple modules
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import json
from datetime import datetime, timedelta
from backend import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.doctor import Doctor
from backend.models.nurse import Nurse
from backend.models.lab_technician import LabTechnician
from backend.models.pharmacist import Pharmacist
from backend.models.admin import Admin
from backend.models.prediction import Prediction
from backend.models.health_record import HealthRecord
from backend.models.prescription import Prescription
from backend.models.lab_test import LabTest
from backend.models.payment import Payment
from backend.models.appointment import Appointment
from backend.models.audit_log import AuditLog
from werkzeug.security import generate_password_hash


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
def test_data(app):
    """Create test data for integration tests"""
    with app.app_context():
        # Create admin
        admin = Admin(
            username='admin_test',
            email='admin@test.com',
            password_hash=generate_password_hash('testpass'),
            role='admin',
            admin_id='ADM001',
            is_active=True
        )
        db.session.add(admin)
        
        # Create doctor
        doctor = Doctor(
            username='dr_test',
            email='doctor@test.com',
            password_hash=generate_password_hash('testpass'),
            role='doctor',
            doctor_id='DOC001',
            specialization='Cardiology'
        )
        db.session.add(doctor)
        
        # Create nurse
        nurse = Nurse(
            username='nurse_test',
            email='nurse@test.com',
            password_hash=generate_password_hash('testpass'),
            role='nurse',
            nurse_id='NUR001'
        )
        db.session.add(nurse)
        
        # Create lab technician
        lab_tech = LabTechnician(
            username='lab_test',
            email='lab@test.com',
            password_hash=generate_password_hash('testpass'),
            role='lab_technician',
            technician_id='LAB001'
        )
        db.session.add(lab_tech)
        
        # Create pharmacist
        pharmacist = Pharmacist(
            username='pharm_test',
            email='pharmacy@test.com',
            password_hash=generate_password_hash('testpass'),
            role='pharmacist',
            pharmacist_id='PHR001'
        )
        db.session.add(pharmacist)
        
        # Create patients
        patient1 = Patient(
            username='patient1',
            email='patient1@test.com',
            password_hash=generate_password_hash('testpass'),
            role='patient',
            patient_id='PAT001',
            blood_group='O+'
        )
        patient2 = Patient(
            username='patient2',
            email='patient2@test.com',
            password_hash=generate_password_hash('testpass'),
            role='patient',
            patient_id='PAT002',
            blood_group='A+'
        )
        db.session.add_all([patient1, patient2])
        
        db.session.commit()
        
        # Return IDs instead of objects to avoid detached instance errors
        return {
            'admin_id': admin.id,
            'admin_email': admin.email,
            'doctor_id': doctor.id,
            'doctor_email': doctor.email,
            'nurse_id': nurse.id,
            'nurse_email': nurse.email,
            'lab_tech_id': lab_tech.id,
            'lab_tech_email': lab_tech.email,
            'pharmacist_id': pharmacist.id,
            'pharmacist_email': pharmacist.email,
            'patient1_id': patient1.id,
            'patient1_email': patient1.email,
            'patient2_id': patient2.id,
            'patient2_email': patient2.email
        }


def get_auth_token(client, email, password, role):
    """Helper to get authentication token"""
    response = client.post('/api/auth/login', json={
        'email': email,
        'password': password,
        'role': role
    })
    if response.status_code == 200:
        return response.json['token']
    return None


# ============ PATIENT WORKFLOW TESTS ============

class TestPatientWorkflow:
    def test_complete_patient_journey(self, client, test_data):
        """Test complete patient journey from registration to prediction"""
        # Step 1: Register patient
        reg_response = client.post('/api/auth/register', json={
            'username': 'new_patient',
            'email': 'new_patient@test.com',
            'password': 'Test1234',
            'role': 'patient'
        })
        assert reg_response.status_code == 201
        token = reg_response.json['token']
        
        # Step 2: Get profile
        profile_response = client.get('/api/patient/profile',
                                       headers={'Authorization': f'Bearer {token}'})
        assert profile_response.status_code == 200
        assert profile_response.json['success'] is True
        
        # Step 3: Submit health record
        health_response = client.post('/api/patient/health-records',
                                       headers={'Authorization': f'Bearer {token}'},
                                       json={
                                           'glucose': 140,
                                           'blood_pressure': 120,
                                           'bmi': 28.5,
                                           'age': 45,
                                           'pregnancies': 2
                                       })
        assert health_response.status_code in [200, 201]
        
        # Step 4: Request prediction
        predict_response = client.post('/api/patient/predict',
                                        headers={'Authorization': f'Bearer {token}'},
                                        json={
                                            'glucose': 140,
                                            'blood_pressure': 120,
                                            'bmi': 28.5,
                                            'age': 45,
                                            'pregnancies': 2
                                        })
        assert predict_response.status_code in [200, 201]
        
        # Step 5: Get predictions history
        predictions_response = client.get('/api/patient/predictions',
                                           headers={'Authorization': f'Bearer {token}'})
        assert predictions_response.status_code == 200
        assert predictions_response.json['success'] is True
    
    def test_patient_appointment_booking(self, client, test_data):
        """Test patient booking an appointment with doctor"""
        # Login as patient
        patient_token = get_auth_token(client, test_data['patient1_email'], 'testpass', 'patient')
        assert patient_token is not None, "Patient login failed"
        
        # Book appointment
        appointment_response = client.post('/api/patient/appointments',
                                            headers={'Authorization': f'Bearer {patient_token}'},
                                            json={
                                                'doctor_id': test_data['doctor_id'],
                                                'appointment_date': (datetime.utcnow() + timedelta(days=7)).strftime('%Y-%m-%d'),
                                                'reason': 'Routine checkup'
                                            })
        assert appointment_response.status_code == 201
        
        # Get appointments
        get_response = client.get('/api/patient/appointments',
                                   headers={'Authorization': f'Bearer {patient_token}'})
        assert get_response.status_code == 200
        assert get_response.json['success'] is True


# ============ DOCTOR WORKFLOW TESTS ============

class TestDoctorWorkflow:
    def test_doctor_prescription_workflow(self, client, test_data):
        """Test doctor creating prescription for patient"""
        # Login as doctor
        doctor_token = get_auth_token(client, test_data['doctor_email'], 'testpass', 'doctor')
        assert doctor_token is not None, "Doctor login failed"
        
        # Login as patient
        patient_token = get_auth_token(client, test_data['patient1_email'], 'testpass', 'patient')
        assert patient_token is not None, "Patient login failed"
        
        # Get patient profile
        profile_response = client.get('/api/patient/profile',
                                       headers={'Authorization': f'Bearer {patient_token}'})
        assert profile_response.status_code == 200
        patient_id = profile_response.json['profile']['id']
        
        # Create prescription
        prescription_response = client.post('/api/doctor/prescriptions',
                                             headers={'Authorization': f'Bearer {doctor_token}'},
                                             json={
                                                 'patient_id': patient_id,
                                                 'medication': 'Metformin',
                                                 'dosage': '500mg',
                                                 'frequency': 'twice daily',
                                                 'duration': '30 days',
                                                 'instructions': 'Take with meals'
                                             })
        assert prescription_response.status_code in [200, 201]
        
        # Get doctor's prescriptions
        get_response = client.get('/api/doctor/prescriptions',
                                    headers={'Authorization': f'Bearer {doctor_token}'})
        assert get_response.status_code == 200
        assert get_response.json['success'] is True
    
    def test_doctor_lab_request_workflow(self, client, test_data):
        """Test doctor requesting lab tests for patient"""
        # Login as doctor
        doctor_token = get_auth_token(client, test_data['doctor_email'], 'testpass', 'doctor')
        assert doctor_token is not None, "Doctor login failed"
        
        # Login as patient
        patient_token = get_auth_token(client, test_data['patient1_email'], 'testpass', 'patient')
        assert patient_token is not None, "Patient login failed"
        
        # Get patient profile
        profile_response = client.get('/api/patient/profile',
                                       headers={'Authorization': f'Bearer {patient_token}'})
        assert profile_response.status_code == 200
        patient_id = profile_response.json['profile']['id']
        
        # Request lab test
        lab_request_response = client.post('/api/doctor/lab-requests',
                                            headers={'Authorization': f'Bearer {doctor_token}'},
                                            json={
                                                'patient_id': patient_id,
                                                'test_name': 'Complete Blood Count',
                                                'test_type': 'hematology',
                                                'priority': 'normal'
                                            })
        assert lab_request_response.status_code in [200, 201]
        
        # Get lab requests
        get_response = client.get('/api/doctor/lab-requests',
                                    headers={'Authorization': f'Bearer {doctor_token}'})
        assert get_response.status_code == 200
        assert get_response.json['success'] is True


# ============ NURSE WORKFLOW TESTS ============

class TestNurseWorkflow:
    def test_nurse_patient_queue_workflow(self, client, test_data):
        """Test nurse managing patient queue"""
        # Login as nurse
        nurse_token = get_auth_token(client, test_data['nurse_email'], 'testpass', 'nurse')
        assert nurse_token is not None, "Nurse login failed"
        
        # Register a new patient via nurse
        queue_response = client.post('/api/nurse/register',
                                      headers={'Authorization': f'Bearer {nurse_token}'},
                                      json={
                                          'username': 'queue_patient',
                                          'email': 'queue@test.com',
                                          'password': 'Test1234',
                                          'role': 'patient'
                                      })
        assert queue_response.status_code == 201
        
        # Get queue
        get_queue_response = client.get('/api/nurse/queue',
                                          headers={'Authorization': f'Bearer {nurse_token}'})
        assert get_queue_response.status_code == 200
        assert get_queue_response.json['success'] is True
    
    def test_nurse_vital_signs_workflow(self, client, test_data):
        """Test nurse recording vital signs for patient - FIXED: Temperature in Celsius"""
        # Login as nurse
        nurse_token = get_auth_token(client, test_data['nurse_email'], 'testpass', 'nurse')
        assert nurse_token is not None, "Nurse login failed"
        
        # Login as patient
        patient_token = get_auth_token(client, test_data['patient1_email'], 'testpass', 'patient')
        assert patient_token is not None, "Patient login failed"
        
        # Get patient profile
        profile_response = client.get('/api/patient/profile',
                                       headers={'Authorization': f'Bearer {patient_token}'})
        assert profile_response.status_code == 200
        patient_id = profile_response.json['profile']['id']
        
        # FIXED: Temperature must be in Celsius (30-45°C range)
        # 37°C = 98.6°F (normal body temperature)
        vitals_response = client.post('/api/nurse/vitals',
                                       headers={'Authorization': f'Bearer {nurse_token}'},
                                       json={
                                           'patient_id': patient_id,
                                           'temperature': 37.0,          # Celsius (normal body temperature)
                                           'heart_rate': 72,
                                           'respiratory_rate': 16,
                                           'blood_pressure_systolic': 120,
                                           'blood_pressure_diastolic': 80,
                                           'oxygen_saturation': 98,
                                           'height': 170,
                                           'weight': 70,
                                           'bmi': 24.2,
                                           'pain_level': 0,
                                           'notes': 'Routine vital signs check'
                                       })
        
        assert vitals_response.status_code == 201
        
        # Get patient vitals
        get_vitals_response = client.get(f'/api/nurse/patients/{patient_id}/vitals',
                                          headers={'Authorization': f'Bearer {nurse_token}'})
        assert get_vitals_response.status_code == 200
        assert get_vitals_response.json['success'] is True


# ============ LAB TECHNICIAN WORKFLOW TESTS ============

class TestLabTechnicianWorkflow:
    def test_lab_test_process_workflow(self, client, test_data):
        """Test lab technician processing lab tests"""
        # Login as doctor
        doctor_token = get_auth_token(client, test_data['doctor_email'], 'testpass', 'doctor')
        assert doctor_token is not None, "Doctor login failed"
        
        # Login as lab technician
        lab_token = get_auth_token(client, test_data['lab_tech_email'], 'testpass', 'lab_technician')
        assert lab_token is not None, "Lab technician login failed"
        
        # Login as patient
        patient_token = get_auth_token(client, test_data['patient1_email'], 'testpass', 'patient')
        assert patient_token is not None, "Patient login failed"
        
        # Get patient profile
        profile_response = client.get('/api/patient/profile',
                                       headers={'Authorization': f'Bearer {patient_token}'})
        assert profile_response.status_code == 200
        patient_id = profile_response.json['profile']['id']
        
        # Doctor requests lab test
        lab_request_response = client.post('/api/doctor/lab-requests',
                                            headers={'Authorization': f'Bearer {doctor_token}'},
                                            json={
                                                'patient_id': patient_id,
                                                'test_name': 'Blood Glucose',
                                                'test_type': 'chemistry',
                                                'priority': 'urgent'
                                            })
        assert lab_request_response.status_code in [200, 201]
        
        # Lab technician gets pending tests
        pending_response = client.get('/api/labs/pending',
                                       headers={'Authorization': f'Bearer {lab_token}'})
        assert pending_response.status_code == 200
        
        # Enter results (need test ID from pending)
        if pending_response.json.get('pending_tests') and len(pending_response.json['pending_tests']) > 0:
            test_id = pending_response.json['pending_tests'][0]['id']
            results_response = client.post('/api/labs/results',
                                            headers={'Authorization': f'Bearer {lab_token}'},
                                            json={
                                                'test_id': test_id,
                                                'results': '120 mg/dL',
                                                'normal_range': '70-100 mg/dL'
                                            })
            assert results_response.status_code == 200
            
            # Validate results
            validate_response = client.put(f'/api/labs/validate/{test_id}',
                                            headers={'Authorization': f'Bearer {lab_token}'},
                                            json={'validation_status': 'verified'})
            assert validate_response.status_code == 200


# ============ PHARMACY WORKFLOW TESTS ============

class TestPharmacyWorkflow:
    def test_prescription_dispensing_workflow(self, client, test_data):
        """Test pharmacist dispensing medication"""
        # Login as doctor
        doctor_token = get_auth_token(client, test_data['doctor_email'], 'testpass', 'doctor')
        assert doctor_token is not None, "Doctor login failed"
        
        # Login as pharmacist
        pharm_token = get_auth_token(client, test_data['pharmacist_email'], 'testpass', 'pharmacist')
        assert pharm_token is not None, "Pharmacist login failed"
        
        # Login as patient
        patient_token = get_auth_token(client, test_data['patient1_email'], 'testpass', 'patient')
        assert patient_token is not None, "Patient login failed"
        
        # Get patient profile
        profile_response = client.get('/api/patient/profile',
                                       headers={'Authorization': f'Bearer {patient_token}'})
        assert profile_response.status_code == 200
        patient_id = profile_response.json['profile']['id']
        
        # Doctor creates prescription
        prescription_response = client.post('/api/doctor/prescriptions',
                                             headers={'Authorization': f'Bearer {doctor_token}'},
                                             json={
                                                 'patient_id': patient_id,
                                                 'medication': 'Metformin',
                                                 'dosage': '500mg',
                                                 'frequency': 'twice daily',
                                                 'duration': '30 days'
                                             })
        assert prescription_response.status_code in [200, 201]
        prescription_id = prescription_response.json['prescription']['id']
        
        # Pharmacist verifies prescription
        verify_response = client.post(f'/api/pharmacy/verify/{prescription_id}',
                                       headers={'Authorization': f'Bearer {pharm_token}'},
                                       json={'notes': 'Prescription verified'})
        assert verify_response.status_code == 200
        
        # Pharmacist dispenses medication
        dispense_response = client.post(f'/api/pharmacy/dispense/{prescription_id}',
                                         headers={'Authorization': f'Bearer {pharm_token}'},
                                         json={'notes': 'Medication dispensed'})
        assert dispense_response.status_code == 200


# ============ ADMIN WORKFLOW TESTS ============

class TestAdminWorkflow:
    def test_admin_user_management_workflow(self, client, test_data):
        """Test admin managing users"""
        # Login as admin
        admin_token = get_auth_token(client, test_data['admin_email'], 'testpass', 'admin')
        assert admin_token is not None, "Admin login failed"
        
        # Create new user
        create_response = client.post('/api/admin/users',
                                       headers={'Authorization': f'Bearer {admin_token}'},
                                       json={
                                           'username': 'new_doctor',
                                           'email': 'newdoctor@test.com',
                                           'password': 'Doctor123',
                                           'role': 'doctor',
                                           'specialization': 'Neurology'
                                       })
        assert create_response.status_code == 201
        
        # Get all users
        users_response = client.get('/api/admin/users',
                                      headers={'Authorization': f'Bearer {admin_token}'})
        assert users_response.status_code == 200
        assert len(users_response.json['users']) >= 6
        
        # Update user
        update_response = client.put('/api/admin/users/1',
                                      headers={'Authorization': f'Bearer {admin_token}'},
                                      json={'username': 'updated_admin'})
        assert update_response.status_code == 200
        
        # Get audit logs
        logs_response = client.get('/api/admin/audit-logs',
                                     headers={'Authorization': f'Bearer {admin_token}'})
        assert logs_response.status_code == 200
        assert logs_response.json['success'] is True
    
    def test_admin_system_monitoring_workflow(self, client, test_data):
        """Test admin monitoring system"""
        # Login as admin
        admin_token = get_auth_token(client, test_data['admin_email'], 'testpass', 'admin')
        assert admin_token is not None, "Admin login failed"
        
        # Get dashboard
        dashboard_response = client.get('/api/admin/dashboard',
                                         headers={'Authorization': f'Bearer {admin_token}'})
        assert dashboard_response.status_code == 200
        assert dashboard_response.json['success'] is True
        
        # Get system stats
        stats_response = client.get('/api/admin/system-stats',
                                     headers={'Authorization': f'Bearer {admin_token}'})
        assert stats_response.status_code == 200
        assert stats_response.json['success'] is True
        
        # Get roles
        roles_response = client.get('/api/admin/roles',
                                     headers={'Authorization': f'Bearer {admin_token}'})
        assert roles_response.status_code == 200
        assert 'roles' in roles_response.json


# ============ PAYMENT WORKFLOW TESTS ============

class TestPaymentWorkflow:
    def test_payment_processing_workflow(self, client, test_data):
        """Test payment processing flow"""
        # Login as patient
        patient_token = get_auth_token(client, test_data['patient1_email'], 'testpass', 'patient')
        assert patient_token is not None, "Patient login failed"
        
        # Process payment
        payment_response = client.post('/api/payments/process',
                                        headers={'Authorization': f'Bearer {patient_token}'},
                                        json={
                                            'amount': 1500.00,
                                            'payment_method': 'online',
                                            'payment_type': 'consultation'
                                        })
        assert payment_response.status_code == 201
        assert payment_response.json['success'] is True
        
        # Get payment history
        history_response = client.get('/api/payments/history',
                                       headers={'Authorization': f'Bearer {patient_token}'})
        assert history_response.status_code == 200
        assert history_response.json['success'] is True
        
        # Get invoice
        invoice_id = payment_response.json['invoice']['invoice_id']
        invoice_response = client.get(f'/api/payments/invoice/{invoice_id}',
                                       headers={'Authorization': f'Bearer {patient_token}'})
        assert invoice_response.status_code == 200


# ============ END-TO-END CROSS-ROLE WORKFLOW ============

class TestCrossRoleWorkflow:
    def test_complete_healthcare_workflow(self, client, test_data):
        """Test complete end-to-end workflow across all roles"""
        
        # ============ STEP 1: REGISTRATION ============
        reg_response = client.post('/api/auth/register', json={
            'username': 'e2e_patient',
            'email': 'e2e_patient@test.com',
            'password': 'Test1234',
            'role': 'patient'
        })
        assert reg_response.status_code == 201
        patient_token = reg_response.json['token']
        
        # Get patient profile
        profile_response = client.get('/api/patient/profile',
                                       headers={'Authorization': f'Bearer {patient_token}'})
        assert profile_response.status_code == 200
        patient_id = profile_response.json['profile']['id']
        
        # ============ STEP 2: PATIENT SUBMITS HEALTH DATA ============
        health_response = client.post('/api/patient/health-records',
                                       headers={'Authorization': f'Bearer {patient_token}'},
                                       json={
                                           'glucose': 145,
                                           'blood_pressure': 125,
                                           'bmi': 29.5,
                                           'age': 48,
                                           'pregnancies': 2
                                       })
        assert health_response.status_code in [200, 201]
        
        # ============ STEP 3: PATIENT GETS PREDICTION ============
        predict_response = client.post('/api/patient/predict',
                                        headers={'Authorization': f'Bearer {patient_token}'},
                                        json={
                                            'glucose': 145,
                                            'blood_pressure': 125,
                                            'bmi': 29.5,
                                            'age': 48,
                                            'pregnancies': 2
                                        })
        assert predict_response.status_code in [200, 201]
        
        # ============ STEP 4: PATIENT BOOKS APPOINTMENT ============
        appointment_response = client.post('/api/patient/appointments',
                                            headers={'Authorization': f'Bearer {patient_token}'},
                                            json={
                                                'doctor_id': test_data['doctor_id'],
                                                'appointment_date': (datetime.utcnow() + timedelta(days=3)).strftime('%Y-%m-%d'),
                                                'reason': 'Diabetes consultation based on prediction'
                                            })
        assert appointment_response.status_code == 201
        
        # ============ STEP 5: DOCTOR CREATES PRESCRIPTION ============
        doctor_token = get_auth_token(client, test_data['doctor_email'], 'testpass', 'doctor')
        assert doctor_token is not None, "Doctor login failed"
        
        prescription_response = client.post('/api/doctor/prescriptions',
                                             headers={'Authorization': f'Bearer {doctor_token}'},
                                             json={
                                                 'patient_id': patient_id,
                                                 'medication': 'Metformin',
                                                 'dosage': '500mg',
                                                 'frequency': 'twice daily',
                                                 'duration': '30 days',
                                                 'instructions': 'Take with meals'
                                             })
        assert prescription_response.status_code in [200, 201]
        prescription_id = prescription_response.json['prescription']['id']
        
        # ============ STEP 6: DOCTOR ORDERS LAB TEST ============
        lab_request_response = client.post('/api/doctor/lab-requests',
                                            headers={'Authorization': f'Bearer {doctor_token}'},
                                            json={
                                                'patient_id': patient_id,
                                                'test_name': 'HbA1c',
                                                'test_type': 'chemistry',
                                                'priority': 'normal'
                                            })
        assert lab_request_response.status_code in [200, 201]
        
        # ============ STEP 7: LAB TECHNICIAN PROCESSES TEST ============
        lab_token = get_auth_token(client, test_data['lab_tech_email'], 'testpass', 'lab_technician')
        assert lab_token is not None, "Lab technician login failed"
        
        # Get pending tests
        pending_response = client.get('/api/labs/pending',
                                       headers={'Authorization': f'Bearer {lab_token}'})
        assert pending_response.status_code == 200
        
        # Enter results if test exists
        if pending_response.json.get('pending_tests') and len(pending_response.json['pending_tests']) > 0:
            test_id = pending_response.json['pending_tests'][0]['id']
            results_response = client.post('/api/labs/results',
                                            headers={'Authorization': f'Bearer {lab_token}'},
                                            json={
                                                'test_id': test_id,
                                                'results': '6.5%',
                                                'normal_range': '4.0-5.6%'
                                            })
            assert results_response.status_code == 200
            
            # Validate results
            validate_response = client.put(f'/api/labs/validate/{test_id}',
                                            headers={'Authorization': f'Bearer {lab_token}'},
                                            json={'validation_status': 'verified'})
            assert validate_response.status_code == 200
        
        # ============ STEP 8: PHARMACIST DISPENSES MEDICATION ============
        pharm_token = get_auth_token(client, test_data['pharmacist_email'], 'testpass', 'pharmacist')
        assert pharm_token is not None, "Pharmacist login failed"
        
        # Verify prescription
        verify_response = client.post(f'/api/pharmacy/verify/{prescription_id}',
                                       headers={'Authorization': f'Bearer {pharm_token}'},
                                       json={'notes': 'Prescription verified'})
        assert verify_response.status_code == 200
        
        # Dispense medication
        dispense_response = client.post(f'/api/pharmacy/dispense/{prescription_id}',
                                         headers={'Authorization': f'Bearer {pharm_token}'},
                                         json={'notes': 'Medication dispensed'})
        assert dispense_response.status_code == 200
        
        # ============ STEP 9: PATIENT MAKES PAYMENT ============
        payment_response = client.post('/api/payments/process',
                                        headers={'Authorization': f'Bearer {patient_token}'},
                                        json={
                                            'amount': 2000.00,
                                            'payment_method': 'online',
                                            'payment_type': 'consultation_and_medication'
                                        })
        assert payment_response.status_code == 201
        
        # ============ STEP 10: VERIFY ALL DATA ============
        dashboard_response = client.get('/api/patient/dashboard',
                                         headers={'Authorization': f'Bearer {patient_token}'})
        assert dashboard_response.status_code == 200
        
        doctor_prescriptions = client.get('/api/doctor/prescriptions',
                                           headers={'Authorization': f'Bearer {doctor_token}'})
        assert doctor_prescriptions.status_code == 200


# ============ RUN INTEGRATION TESTS ============

if __name__ == '__main__':
    pytest.main([__file__, '-v'])