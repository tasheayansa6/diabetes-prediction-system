"""
Prescription Service - Manages medication prescriptions
"""

from datetime import datetime, timedelta

class PrescriptionService:
    """
    Service for managing medication prescriptions
    Handles prescription creation, approval, and management
    """
    
    def __init__(self):
        self.prescriptions_db = []  # In production, use real database
        self.medications_db = self._initialize_medications()
    
    def _initialize_medications(self):
        """Initialize common diabetes medications"""
        return [
            {
                'id': 'MED001',
                'name': 'Metformin',
                'category': 'Biguanide',
                'dosage_forms': ['500mg', '850mg', '1000mg'],
                'common_dosage': '500mg twice daily',
                'side_effects': ['Nausea', 'Diarrhea', 'Abdominal discomfort']
            },
            {
                'id': 'MED002',
                'name': 'Glipizide',
                'category': 'Sulfonylurea',
                'dosage_forms': ['5mg', '10mg'],
                'common_dosage': '5mg once daily',
                'side_effects': ['Hypoglycemia', 'Weight gain', 'Dizziness']
            },
            {
                'id': 'MED003',
                'name': 'Insulin',
                'category': 'Insulin',
                'dosage_forms': ['U-100'],
                'common_dosage': 'As prescribed by doctor',
                'side_effects': ['Hypoglycemia', 'Injection site reactions']
            },
            {
                'id': 'MED004',
                'name': 'Sitagliptin',
                'category': 'DPP-4 Inhibitor',
                'dosage_forms': ['25mg', '50mg', '100mg'],
                'common_dosage': '100mg once daily',
                'side_effects': ['Headache', 'Upper respiratory infection']
            }
        ]
    
    def create_prescription(self, doctor_id, patient_id, diagnosis_id, prescription_data):
        """
        Create a new prescription
        
        Args:
            doctor_id: ID of the doctor
            patient_id: ID of the patient
            diagnosis_id: ID of the diagnosis
            prescription_data: dict with prescription details
        
        Returns:
            dict with created prescription
        """
        prescription = {
            'prescription_id': f"RX_{len(self.prescriptions_db) + 1}",
            'doctor_id': doctor_id,
            'patient_id': patient_id,
            'diagnosis_id': diagnosis_id,
            'created_date': datetime.now().isoformat(),
            'medications': prescription_data.get('medications', []),
            'instructions': prescription_data.get('instructions', ''),
            'duration_days': prescription_data.get('duration_days', 30),
            'refills': prescription_data.get('refills', 0),
            'status': 'pending_pharmacist',
            'pharmacist_approval': None,
            'notes': prescription_data.get('notes', '')
        }
        
        self.prescriptions_db.append(prescription)
        
        return {
            'success': True,
            'prescription_id': prescription['prescription_id'],
            'prescription': prescription,
            'message': 'Prescription created successfully'
        }
    
    def get_available_medications(self, search_term=None):
        """
        Get list of available medications
        
        Args:
            search_term: optional search term
        
        Returns:
            list of medications
        """
        if search_term:
            search_term = search_term.lower()
            results = [
                m for m in self.medications_db
                if search_term in m['name'].lower() or 
                   search_term in m['category'].lower()
            ]
        else:
            results = self.medications_db
        
        return {
            'success': True,
            'medications': results,
            'count': len(results)
        }
    
    def approve_prescription(self, pharmacist_id, prescription_id, approval_notes=''):
        """
        Approve a prescription (pharmacist action)
        
        Args:
            pharmacist_id: ID of the pharmacist
            prescription_id: ID of the prescription
            approval_notes: optional notes
        
        Returns:
            dict with approval result
        """
        for pres in self.prescriptions_db:
            if pres['prescription_id'] == prescription_id:
                pres['status'] = 'approved'
                pres['pharmacist_approval'] = {
                    'pharmacist_id': pharmacist_id,
                    'date': datetime.now().isoformat(),
                    'notes': approval_notes
                }
                return {
                    'success': True,
                    'prescription': pres,
                    'message': 'Prescription approved'
                }
        
        return {'success': False, 'error': 'Prescription not found'}
    
    def reject_prescription(self, pharmacist_id, prescription_id, reason):
        """
        Reject a prescription (pharmacist action)
        
        Args:
            pharmacist_id: ID of the pharmacist
            prescription_id: ID of the prescription
            reason: rejection reason
        
        Returns:
            dict with rejection result
        """
        for pres in self.prescriptions_db:
            if pres['prescription_id'] == prescription_id:
                pres['status'] = 'rejected'
                pres['pharmacist_approval'] = {
                    'pharmacist_id': pharmacist_id,
                    'date': datetime.now().isoformat(),
                    'reason': reason
                }
                return {
                    'success': True,
                    'prescription': pres,
                    'message': 'Prescription rejected'
                }
        
        return {'success': False, 'error': 'Prescription not found'}
    
    def get_patient_prescriptions(self, patient_id, status=None):
        """
        Get prescriptions for a patient
        
        Args:
            patient_id: ID of the patient
            status: optional filter by status
        
        Returns:
            list of prescriptions
        """
        results = [p for p in self.prescriptions_db if p['patient_id'] == patient_id]
        
        if status:
            results = [p for p in results if p['status'] == status]
        
        return {
            'success': True,
            'prescriptions': results,
            'count': len(results)
        }
    
    def get_pending_approvals(self, pharmacist_id=None):
        """
        Get prescriptions pending pharmacist approval
        
        Returns:
            list of pending prescriptions
        """
        pending = [p for p in self.prescriptions_db if p['status'] == 'pending_pharmacist']
        
        return {
            'success': True,
            'prescriptions': pending,
            'count': len(pending)
        }
    
    def check_medication_interaction(self, medications):
        """
        Check for potential medication interactions
        
        Args:
            medications: list of medication names
        
        Returns:
            dict with interaction check results
        """
        # Simple interaction check (in production, use drug database)
        warnings = []
        
        # Example: Metformin + Insulin interaction
        if 'Metformin' in medications and 'Insulin' in medications:
            warnings.append({
                'medications': ['Metformin', 'Insulin'],
                'severity': 'Moderate',
                'description': 'Increased risk of hypoglycemia. Monitor blood glucose closely.'
            })
        
        return {
            'success': True,
            'has_interactions': len(warnings) > 0,
            'warnings': warnings,
            'safe': len(warnings) == 0
        }