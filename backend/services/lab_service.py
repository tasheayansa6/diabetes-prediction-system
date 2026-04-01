"""
Lab Service - Manages laboratory tests and results
"""

from datetime import datetime

class LabService:
    """
    Service for managing laboratory tests
    Handles test types, test requests, and result entry
    """
    
    def __init__(self):
        self.lab_tests_db = []  # Test requests
        self.test_types_db = self._initialize_test_types()
        self.results_db = []  # Test results
    
    def _initialize_test_types(self):
        """Initialize common diabetes-related lab tests"""
        return [
            {
                'test_id': 'TEST001',
                'name': 'Fasting Blood Glucose',
                'category': 'Blood Sugar',
                'unit': 'mg/dL',
                'normal_range': '70-99',
                'prediabetes_range': '100-125',
                'diabetes_range': '≥126',
                'preparation': 'Fast for 8-12 hours',
                'price': 25.00
            },
            {
                'test_id': 'TEST002',
                'name': 'HbA1c',
                'category': 'Long-term Control',
                'unit': '%',
                'normal_range': '<5.7',
                'prediabetes_range': '5.7-6.4',
                'diabetes_range': '≥6.5',
                'preparation': 'No fasting required',
                'price': 45.00
            },
            {
                'test_id': 'TEST003',
                'name': 'Oral Glucose Tolerance Test',
                'category': 'Diagnostic',
                'unit': 'mg/dL',
                'normal_range': '<140',
                'prediabetes_range': '140-199',
                'diabetes_range': '≥200',
                'preparation': 'Fast for 8-12 hours',
                'price': 60.00
            },
            {
                'test_id': 'TEST004',
                'name': 'Random Blood Glucose',
                'category': 'Blood Sugar',
                'unit': 'mg/dL',
                'normal_range': '<140',
                'prediabetes_range': '140-199',
                'diabetes_range': '≥200',
                'preparation': 'No preparation needed',
                'price': 20.00
            },
            {
                'test_id': 'TEST005',
                'name': 'Insulin Level',
                'category': 'Hormone',
                'unit': 'μU/mL',
                'normal_range': '2-25',
                'preparation': 'Fast for 8 hours',
                'price': 55.00
            }
        ]
    
    def add_test_type(self, test_data):
        """
        Add a new test type (admin/lab technician action)
        
        Args:
            test_data: dict with test details
        
        Returns:
            dict with created test type
        """
        new_test = {
            'test_id': f"TEST{len(self.test_types_db) + 1:03d}",
            'name': test_data.get('name'),
            'category': test_data.get('category'),
            'unit': test_data.get('unit'),
            'normal_range': test_data.get('normal_range'),
            'preparation': test_data.get('preparation'),
            'price': test_data.get('price', 0),
            'created_at': datetime.now().isoformat()
        }
        
        self.test_types_db.append(new_test)
        
        return {
            'success': True,
            'test_type': new_test,
            'message': 'Test type added successfully'
        }
    
    def get_test_types(self, category=None):
        """
        Get all available test types
        
        Args:
            category: optional filter by category
        
        Returns:
            list of test types
        """
        if category:
            results = [t for t in self.test_types_db if t['category'] == category]
        else:
            results = self.test_types_db
        
        return {
            'success': True,
            'test_types': results,
            'count': len(results)
        }
    
    def request_lab_test(self, doctor_id, patient_id, test_id, notes=''):
        """
        Request a lab test for a patient
        
        Args:
            doctor_id: ID of the requesting doctor
            patient_id: ID of the patient
            test_id: ID of the test type
            notes: additional notes
        
        Returns:
            dict with test request
        """
        test_type = next((t for t in self.test_types_db if t['test_id'] == test_id), None)
        
        if not test_type:
            return {'success': False, 'error': 'Test type not found'}
        
        request = {
            'request_id': f"REQ{len(self.lab_tests_db) + 1:04d}",
            'doctor_id': doctor_id,
            'patient_id': patient_id,
            'test_id': test_id,
            'test_name': test_type['name'],
            'request_date': datetime.now().isoformat(),
            'status': 'pending',
            'notes': notes,
            'results': None
        }
        
        self.lab_tests_db.append(request)
        
        return {
            'success': True,
            'request': request,
            'message': 'Lab test requested successfully'
        }
    
    