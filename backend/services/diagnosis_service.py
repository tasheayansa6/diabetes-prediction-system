"""
Diagnosis Service - Manages doctor diagnoses and medical assessments
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class DiagnosisService:
    """
    Diagnosis Service - Handles doctor diagnoses and medical records
    """
    
    def __init__(self, db_session=None):
        """
        Initialize diagnosis service
        
        Args:
            db_session: Optional database session
        """
        self.db_session = db_session
        self.diagnoses = []
    
    def create_diagnosis(self, patient_id: str, doctor_id: str, 
                        diagnosis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new diagnosis for a patient
        
        Args:
            patient_id: Patient identifier
            doctor_id: Doctor identifier
            diagnosis_data: Diagnosis information
        
        Returns:
            Created diagnosis record
        """
        diagnosis = {
            'id': f"DIAG{len(self.diagnoses)+1:06d}",
            'patient_id': patient_id,
            'doctor_id': doctor_id,
            'date': datetime.now().isoformat(),
            'diagnosis': diagnosis_data.get('diagnosis', ''),
            'notes': diagnosis_data.get('notes', ''),
            'recommendations': diagnosis_data.get('recommendations', []),
            'follow_up_date': diagnosis_data.get('follow_up_date'),
            'prescription_id': diagnosis_data.get('prescription_id'),
            'prediction_id': diagnosis_data.get('prediction_id'),
            'status': 'active'
        }
        
        self.diagnoses.append(diagnosis)
        
        if self.db_session:
            self._save_to_database(diagnosis)
        
        return diagnosis
    
    def get_patient_diagnoses(self, patient_id: str) -> List[Dict[str, Any]]:
        """
        Get all diagnoses for a patient
        
        Args:
            patient_id: Patient identifier
        
        Returns:
            List of diagnoses
        """
        return [d for d in self.diagnoses if d['patient_id'] == patient_id]
    
    def get_doctor_diagnoses(self, doctor_id: str, 
                            status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get diagnoses by doctor
        
        Args:
            doctor_id: Doctor identifier
            status: Optional status filter
        
        Returns:
            List of diagnoses
        """
        diagnoses = [d for d in self.diagnoses if d['doctor_id'] == doctor_id]
        
        if status:
            diagnoses = [d for d in diagnoses if d['status'] == status]
        
        return diagnoses
    
    def update_diagnosis(self, diagnosis_id: str, 
                        update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing diagnosis
        
        Args:
            diagnosis_id: Diagnosis identifier
            update_data: Fields to update
        
        Returns:
            Updated diagnosis or None
        """
        for diagnosis in self.diagnoses:
            if diagnosis['id'] == diagnosis_id:
                diagnosis.update(update_data)
                diagnosis['updated_at'] = datetime.now().isoformat()
                
                if self.db_session:
                    self._update_in_database(diagnosis)
                
                return diagnosis
        
        return None
    
    def add_medical_note(self, diagnosis_id: str, note: str, 
                        author_id: str) -> Optional[Dict[str, Any]]:
        """
        Add a medical note to a diagnosis
        
        Args:
            diagnosis_id: Diagnosis identifier
            note: Note text
            author_id: Author identifier
        
        Returns:
            Updated diagnosis
        """
        for diagnosis in self.diagnoses:
            if diagnosis['id'] == diagnosis_id:
                if 'notes_history' not in diagnosis:
                    diagnosis['notes_history'] = []
                
                diagnosis['notes_history'].append({
                    'note': note,
                    'author_id': author_id,
                    'timestamp': datetime.now().isoformat()
                })
                
                diagnosis['notes'] = note  # Latest note
                
                return diagnosis
        
        return None
    
    def link_to_prediction(self, diagnosis_id: str, 
                          prediction_id: str) -> Optional[Dict[str, Any]]:
        """
        Link a diagnosis to a prediction
        
        Args:
            diagnosis_id: Diagnosis identifier
            prediction_id: Prediction identifier
        
        Returns:
            Updated diagnosis
        """
        return self.update_diagnosis(diagnosis_id, {'prediction_id': prediction_id})
    
    def get_diagnosis_statistics(self, doctor_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get diagnosis statistics
        
        Args:
            doctor_id: Optional doctor filter
        
        Returns:
            Statistics dictionary
        """
        diagnoses = self.get_doctor_diagnoses(doctor_id) if doctor_id else self.diagnoses
        
        if not diagnoses:
            return {'error': 'No diagnoses found'}
        
        # Count by diagnosis type
        diagnosis_types = {}
        for d in diagnoses:
            diag = d['diagnosis']
            diagnosis_types[diag] = diagnosis_types.get(diag, 0) + 1
        
        return {
            'total_diagnoses': len(diagnoses),
            'unique_patients': len(set(d['patient_id'] for d in diagnoses)),
            'diagnosis_types': diagnosis_types,
            'recent_diagnoses': sorted(diagnoses, 
                                      key=lambda x: x['date'], 
                                      reverse=True)[:5]
        }
    
    def _save_to_database(self, diagnosis: Dict[str, Any]):
        """Save diagnosis to database"""
        pass
    
    def _update_in_database(self, diagnosis: Dict[str, Any]):
        """Update diagnosis in database"""
        pass