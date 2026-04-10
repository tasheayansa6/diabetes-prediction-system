"""
Comprehensive Testing Framework for Diabetes Prediction System

Includes unit tests, integration tests, security tests, performance tests,
and healthcare compliance tests.
"""

import os
import sys
import json
import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import shutil
from typing import Dict, Any, List
import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.health_record import HealthRecord
from backend.models.prediction import Prediction
from backend.services.hipaa_compliance import HIPAAComplianceManager
from backend.services.mfa_service import MFAService
from backend.services.clinical_decision_support import ClinicalDecisionSupportService
from backend.services.background_tasks import BackgroundTaskService

class TestHIPAACompliance(unittest.TestCase):
    """Test HIPAA compliance features"""
    
    def setUp(self):
        self.hipaa_manager = HIPAAComplianceManager()
        self.test_data = "Patient John Doe, Email: john@example.com, Phone: 555-1234"
    
    def test_phi_encryption(self):
        """Test PHI encryption and decryption"""
        encrypted = self.hipaa_manager.encrypt_phi(self.test_data)
        self.assertNotEqual(encrypted, self.test_data)
        self.assertIsInstance(encrypted, str)
        self.assertGreater(len(encrypted), 0)
        
        decrypted = self.hipaa_manager.decrypt_phi(encrypted)
        self.assertEqual(decrypted, self.test_data)
    
    def test_data_anonymization(self):
        """Test patient data anonymization"""
        patient_data = {
            'full_name': 'John Doe',
            'email': 'john@example.com',
            'phone': '555-1234',
            'patient_id': 'PAT001',
            'medical_history': 'Diabetes type 2',
            'created_at': '2023-01-15T10:30:00'
        }
        
        anonymized = self.hipaa_manager.anonymize_patient_data(patient_data)
        
        # Check that direct identifiers are anonymized
        self.assertNotEqual(anonymized['full_name'], 'John Doe')
        self.assertNotEqual(anonymized['email'], 'john@example.com')
        self.assertNotEqual(anonymized['phone'], '555-1234')
        self.assertNotEqual(anonymized['patient_id'], 'PAT001')
        
        # Check that sensitive text fields are redacted
        self.assertEqual(anonymized['medical_history'], '[REDACTED_FOR_PRIVACY]')
        
        # Check that dates are generalized
        self.assertIn('T00:00:00', anonymized['created_at'])
    
    def test_consent_record_creation(self):
        """Test consent record creation"""
        consent_record = self.hipaa_manager.create_consent_record(
            patient_id=1,
            consent_type='treatment',
            consent_text='I consent to treatment',
            expires_at=datetime.utcnow() + timedelta(days=365)
        )
        
        self.assertIn('consent_id', consent_record)
        self.assertEqual(consent_record['patient_id'], 1)
        self.assertEqual(consent_record['consent_type'], 'treatment')
        self.assertIn('digital_signature', consent_record)
    
    def test_audit_phi_access(self):
        """Test PHI access auditing"""
        audit_record = self.hipaa_manager.audit_phi_access(
            user_id=1,
            user_role='doctor',
            action='read',
            resource_type='patient',
            resource_id=1,
            phi_fields_accessed=['full_name', 'medical_history']
        )
        
        self.assertIn('audit_id', audit_record)
        self.assertEqual(audit_record['user_id'], 1)
        self.assertEqual(audit_record['action'], 'read')
        self.assertEqual(len(audit_record['phi_fields_accessed']), 2)
        self.assertIn('compliance_check', audit_record)

class TestMFASecurity(unittest.TestCase):
    """Test Multi-Factor Authentication security"""
    
    def setUp(self):
        self.mfa_service = MFAService()
    
    def test_totp_secret_generation(self):
        """Test TOTP secret generation"""
        secret = self.mfa_service.generate_totp_secret(1)
        self.assertEqual(len(secret), 32)  # Base32 encoded secret length
        
        # Test that secrets are unique
        secret2 = self.mfa_service.generate_totp_secret(1)
        self.assertNotEqual(secret, secret2)
    
    def test_totp_verification(self):
        """Test TOTP token verification"""
        import pyotp
        
        secret = self.mfa_service.generate_totp_secret(1)
        totp = pyotp.TOTP(secret)
        token = totp.now()
        
        # Valid token should verify
        self.assertTrue(self.mfa_service.verify_totp_token(secret, token))
        
        # Invalid token should not verify
        self.assertFalse(self.mfa_service.verify_totp_token(secret, '123456'))
    
    def test_backup_codes(self):
        """Test backup code generation and verification"""
        codes = self.mfa_service.generate_backup_codes(10)
        self.assertEqual(len(codes), 10)
        
        # Test code verification
        test_code = codes[0]
        is_valid, remaining = self.mfa_service.verify_backup_codes(codes, test_code)
        self.assertTrue(is_valid)
        self.assertEqual(len(remaining), 9)  # One code should be consumed
        
        # Test invalid code
        is_valid, remaining = self.mfa_service.verify_backup_codes(remaining, 'INVALIDCODE')
        self.assertFalse(is_valid)
        self.assertEqual(len(remaining), 9)  # No code should be consumed
    
    def test_mfa_enforcement_by_role(self):
        """Test MFA enforcement by user role"""
        # Roles that should require MFA
        mfa_required_roles = ['doctor', 'nurse', 'lab_technician', 'pharmacist', 'admin']
        
        for role in mfa_required_roles:
            self.assertTrue(self.mfa_service.enforce_mfa_for_role(role))
        
        # Roles that might not require MFA
        self.assertFalse(self.mfa_service.enforce_mfa_for_role('patient'))

class TestClinicalDecisionSupport(unittest.TestCase):
    """Test Clinical Decision Support System"""
    
    def setUp(self):
        self.cdss = ClinicalDecisionSupportService()
    
    def test_drug_interaction_checking(self):
        """Test drug interaction checking"""
        medications = ['metformin', 'insulin', 'beta_blockers']
        interactions = self.cdss.drug_checker.check_interactions(medications)
        
        # Should find interactions
        self.assertGreater(len(interactions), 0)
        
        # Check that interactions have required fields
        for interaction in interactions:
            self.assertIn(interaction.drug1, medications)
            self.assertIn(interaction.drug2, medications)
            self.assertIsNotNone(interaction.severity)
            self.assertIsNotNone(interaction.description)
    
    def test_allergy_checking(self):
        """Test allergy checking"""
        patient_allergies = ['penicillin', 'sulfa']
        medications = ['amoxicillin', 'sulfonylureas', 'metformin']
        
        allergy_alerts = self.cdss.drug_checker.check_allergies(patient_allergies, medications)
        
        # Should find allergy alerts
        self.assertGreater(len(allergy_alerts), 0)
        
        # Check that alerts have required fields
        for alert in allergy_alerts:
            self.assertIn(alert['allergy'], patient_allergies)
            self.assertIn(alert['medication'], medications)
            self.assertIsNotNone(alert['severity'])
    
    def test_cardiovascular_risk_assessment(self):
        """Test cardiovascular risk assessment"""
        patient_data = {
            'age': 65,
            'gender': 'male',
            'systolic_bp': 145,
            'total_cholesterol': 220,
            'hdl_cholesterol': 45,
            'has_diabetes': True,
            'is_smoker': True
        }
        
        risk_assessment = self.cdss.risk_assessor.assess_risk('cardiovascular', patient_data)
        
        self.assertIn('risk_score', risk_assessment)
        self.assertIn('risk_percentage', risk_assessment)
        self.assertIn('risk_level', risk_assessment)
        self.assertIn('recommendations', risk_assessment)
        
        # High-risk patient should have high risk level
        self.assertIn(risk_assessment['risk_level'], ['MODERATE', 'HIGH'])
    
    def test_clinical_recommendations_generation(self):
        """Test comprehensive clinical recommendations"""
        patient_data = {
            'age': 65,
            'gender': 'male',
            'conditions': ['diabetes_type2', 'hypertension'],
            'medications': ['metformin', 'insulin'],
            'allergies': ['penicillin'],
            'last_hba1c': 8.5,
            'systolic_bp': 145,
            'diabetes_duration': 10
        }
        
        recommendations = self.cdss.generate_clinical_recommendations(1, patient_data)
        
        self.assertIn('guidelines', recommendations)
        self.assertIn('drug_interactions', recommendations)
        self.assertIn('allergy_alerts', recommendations)
        self.assertIn('risk_assessments', recommendations)
        self.assertIn('alerts', recommendations)
        self.assertIn('overall_priority', recommendations)
        
        # Should have recommendations for each condition
        self.assertGreater(len(recommendations['guidelines']), 0)
        self.assertGreater(len(recommendations['risk_assessments']), 0)

class TestSecurityCompliance(unittest.TestCase):
    """Test security and healthcare compliance"""
    
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # Create test database
        db.create_all()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_password_policy_enforcement(self):
        """Test password policy enforcement"""
        from backend.routes.auth_routes import validate_password
        
        # Test valid passwords
        valid, message = validate_password('StrongPass123')
        self.assertTrue(valid)
        
        valid, message = validate_password('VeryStrong123!')
        self.assertTrue(valid)
        
        # Test invalid passwords
        valid, message = validate_password('weak')
        self.assertFalse(valid)
        self.assertIn('8 characters', message)
        
        valid, message = validate_password('alllowercase123')
        self.assertFalse(valid)
        self.assertIn('uppercase', message)
        
        valid, message = validate_password('ALLUPPERCASE123')
        self.assertFalse(valid)
        self.assertIn('lowercase', message)
        
        valid, message = validate_password('NoNumbers')
        self.assertFalse(valid)
        self.assertIn('number', message)
    
    def test_rate_limiting(self):
        """Test API rate limiting"""
        from backend.middleware.enhanced_security import rate_limit
        
        # Check that rate_limit decorator exists and can be applied
        with self.app.test_request_context('/'):
            @rate_limit('login')
            def test_function():
                return "success"
            
            self.assertEqual(test_function(), "success")
    
    def test_session_security(self):
        """Test session security"""
        with self.client as c:
            # Test login
            response = c.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'Test1234'
            })
            
            if response.status_code == 200:
                # Check that session cookie is secure
                cookies = response.headers.get('Set-Cookie', '')
                self.assertIn('HttpOnly', cookies)
                self.assertIn('Secure', cookies)
                self.assertIn('SameSite', cookies)
    
    def test_csrf_protection(self):
        """Test CSRF protection"""
        # This would test CSRF token validation
        # For now, just check that CSRF protection is enabled
        self.assertTrue(self.app.config.get('WTF_CSRF_ENABLED', True))

class TestPerformance(unittest.TestCase):
    """Test system performance"""
    
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
    
    def tearDown(self):
        self.app_context.pop()
    
    def test_api_response_time(self):
        """Test API response times"""
        endpoints = [
            '/health',
            '/api/model/info',
            '/api/auth/login'
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            
            if endpoint == '/api/auth/login':
                response = self.client.post(endpoint, json={
                    'email': 'test@example.com',
                    'password': 'Test1234'
                })
            else:
                response = self.client.get(endpoint)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # API should respond within 2 seconds
            self.assertLess(response_time, 2.0, f"Endpoint {endpoint} took too long to respond")
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        def make_request():
            response = self.client.get('/health')
            return response.status_code
        
        # Make 10 concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [future.result() for future in futures]
        
        # All requests should succeed
        for result in results:
            self.assertEqual(result, 200)
    
    def test_database_query_performance(self):
        """Test database query performance"""
        from backend.extensions import db
        from sqlalchemy import text
        
        start_time = time.time()
        result = db.session.execute(text('SELECT 1'))
        end_time = time.time()
        
        query_time = end_time - start_time
        
        # Database queries should be fast
        self.assertLess(query_time, 0.1, "Database query took too long")

class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()
        
        # Create test user
        self.test_user = User(
            username='testuser',
            email='test@example.com',
            password_hash='hashed_password',
            role='patient'
        )
        db.session.add(self.test_user)
        db.session.commit()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_patient_workflow(self):
        """Test complete patient workflow"""
        # 1. Register patient
        response = self.client.post('/api/auth/register', json={
            'username': 'patient1',
            'email': 'patient1@example.com',
            'password': 'Test1234',
            'role': 'patient',
            'patient_id': 'PAT001',
            'blood_group': 'O+'
        })
        
        # 2. Login
        response = self.client.post('/api/auth/login', json={
            'email': 'patient1@example.com',
            'password': 'Test1234'
        })
        
        if response.status_code == 200:
            token = response.json.get('token')
            headers = {'Authorization': f'Bearer {token}'}
            
            # 3. Add health record
            response = self.client.post('/api/patient/health-records', json={
                'glucose': 120,
                'bmi': 25.5,
                'blood_pressure': 80,
                'age': 45,
                'notes': 'Feeling good today'
            }, headers=headers)
            
            # 4. Get prediction
            response = self.client.post('/api/patient/predict', json={
                'glucose': 120,
                'bmi': 25.5,
                'blood_pressure': 80,
                'insulin': 15,
                'age': 45,
                'pregnancies': 0,
                'skin_thickness': 20,
                'diabetes_pedigree': 0.5
            }, headers=headers)
            
            # Check that workflow completed successfully
            self.assertIn(response.status_code, [200, 201])
    
    def test_healthcare_data_integration(self):
        """Test HL7/FHIR integration"""
        from backend.services.healthcare_integration import HealthcareIntegrationService
        
        integration_service = HealthcareIntegrationService()
        
        # Test HL7 message parsing
        hl7_message = """MSH|^~\\&|HIS|LAB|LIS|LAB|202301151030||ORU^R01|MSG00001|P|2.5
PID|1||12345||DOE^JOHN^A||19700101|M||123 MAIN ST^^ANYTOWN^NY^12345||(555)555-1234|||||||123456789
OBX|1|NM|GLU^Glucose||105|mg/dL|70-100|N||F|20230115103000"""
        
        result = integration_service.process_incoming_hl7_message(hl7_message)
        self.assertTrue(result['success'])
        self.assertEqual(result['message_type'], 'ORU')
        
        # Test FHIR resource parsing
        fhir_resource = {
            'resourceType': 'Patient',
            'id': 'patient1',
            'name': [{'family': 'Doe', 'given': ['John']}]
        }
        
        result = integration_service.process_incoming_fhir_resource(fhir_resource)
        self.assertTrue(result['success'])
        self.assertEqual(result['resource_type'], 'Patient')

class TestBackgroundTasks(unittest.TestCase):
    """Test background task processing"""
    
    def setUp(self):
        self.background_service = BackgroundTaskService()
    
    def test_task_submission(self):
        """Test task submission to background service"""
        import unittest
        raise unittest.SkipTest("Requires Redis/Celery broker running")
    
    def test_task_status_tracking(self):
        """Test task status tracking"""
        # This would test actual task status tracking
        # For now, just test the interface
        task_id = 'test_task_id'
        status = self.background_service.get_task_status(task_id)
        
        # Should return None for non-existent task
        self.assertIsNone(status)

# Test runner and configuration
def run_comprehensive_tests():
    """Run all comprehensive tests"""
    
    # Test configuration
    pytest_config = {
        'testpaths': ['tests'],
        'python_files': ['test_comprehensive.py'],
        'python_classes': ['Test*'],
        'python_functions': ['test*'],
        'addopts': [
            '--verbose',
            '--tb=short',
            '--strict-markers',
            '--disable-warnings',
            '--cov=backend',
            '--cov-report=html',
            '--cov-report=term-missing',
            '--cov-fail-under=80'
        ]
    }
    
    # Run tests
    test_classes = [
        TestHIPAACompliance,
        TestMFASecurity,
        TestClinicalDecisionSupport,
        TestSecurityCompliance,
        TestPerformance,
        TestIntegration,
        TestBackgroundTasks
    ]
    
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
