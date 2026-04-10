"""
Clinical Decision Support System (CDSS)

Provides evidence-based clinical recommendations, drug interaction checking,
allergy alerts, and treatment guidelines for healthcare professionals.
"""

import os
import json
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
from flask import current_app

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Clinical alert severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RecommendationType(Enum):
    """Types of clinical recommendations"""
    MEDICATION = "MEDICATION"
    LIFESTYLE = "LIFESTYLE"
    MONITORING = "MONITORING"
    REFERRAL = "REFERRAL"
    EMERGENCY = "EMERGENCY"
    FOLLOW_UP = "FOLLOW_UP"

@dataclass
class ClinicalAlert:
    """Clinical alert structure"""
    alert_id: str
    patient_id: int
    severity: AlertSeverity
    title: str
    description: str
    recommendation: str
    evidence: List[str]
    timestamp: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[int] = None
    acknowledged_at: Optional[datetime] = None

@dataclass
class DrugInteraction:
    """Drug interaction information"""
    drug1: str
    drug2: str
    severity: AlertSeverity
    interaction_type: str
    description: str
    recommendation: str
    evidence: List[str]

@dataclass
class ClinicalGuideline:
    """Clinical guideline structure"""
    guideline_id: str
    condition: str
    population: str
    recommendations: List[Dict[str, Any]]
    evidence_level: str
    last_updated: datetime
    source: str

class ClinicalGuidelinesEngine:
    """Clinical guidelines and evidence-based recommendations"""
    
    def __init__(self):
        self.guidelines = self._load_guidelines()
        self.evidence_levels = {
            'A': 'Systematic review of RCTs',
            'B': 'Individual RCT or systematic review of cohort studies',
            'C': 'Cohort study or case-control study',
            'D': 'Case series, case report, or expert opinion'
        }
    
    def _load_guidelines(self) -> Dict[str, ClinicalGuideline]:
        """Load clinical guidelines from database or files"""
        guidelines = {}
        
        # Diabetes management guidelines (simplified for example)
        guidelines['diabetes_type2'] = ClinicalGuideline(
            guideline_id='diabetes_type2',
            condition='Type 2 Diabetes',
            population='Adults 18+',
            recommendations=[
                {
                    'hba1c_target': '<7.0%',
                    'frequency': 'Every 3 months',
                    'action': 'Monitor HbA1c levels'
                },
                {
                    'blood_pressure_target': '<130/80 mmHg',
                    'frequency': 'Every visit',
                    'action': 'Monitor blood pressure'
                },
                {
                    'ldl_target': '<100 mg/dL',
                    'frequency': 'Annually',
                    'action': 'Monitor lipid profile'
                },
                {
                    'eye_exam': 'Annual dilated eye exam',
                    'frequency': 'Yearly',
                    'action': 'Refer to ophthalmologist'
                },
                {
                    'foot_exam': 'Comprehensive foot exam',
                    'frequency': 'Every 6 months',
                    'action': 'Check for neuropathy and circulation'
                }
            ],
            evidence_level='A',
            last_updated=datetime(2023, 1, 1),
            source='American Diabetes Association'
        )
        
        guidelines['hypertension'] = ClinicalGuideline(
            guideline_id='hypertension',
            condition='Hypertension',
            population='Adults 18+',
            recommendations=[
                {
                    'bp_target': '<130/80 mmHg',
                    'frequency': 'Every visit',
                    'action': 'Monitor blood pressure'
                },
                {
                    'lifestyle_modification': 'DASH diet, exercise, weight loss',
                    'frequency': 'Ongoing',
                    'action': 'Counsel on lifestyle changes'
                }
            ],
            evidence_level='A',
            last_updated=datetime(2023, 6, 1),
            source='American Heart Association'
        )
        
        return guidelines
    
    def get_recommendations(self, condition: str, patient_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get clinical recommendations for a specific condition"""
        guidelines = self.guidelines.get(condition)
        if not guidelines:
            return []
        
        recommendations = []
        
        for rec in guidelines.recommendations:
            # Check if recommendation is applicable to this patient
            if self._is_recommendation_applicable(rec, patient_data):
                recommendations.append({
                    'recommendation': rec,
                    'guideline': guidelines,
                    'priority': self._calculate_priority(rec, patient_data)
                })
        
        # Sort by priority
        recommendations.sort(key=lambda x: x['priority'], reverse=True)
        
        return recommendations
    
    def _is_recommendation_applicable(self, recommendation: Dict[str, Any], patient_data: Dict[str, Any]) -> bool:
        """Check if recommendation applies to this patient"""
        # Simplified logic - in practice, this would be more complex
        age = patient_data.get('age', 0)
        
        # Age-based applicability
        if age < 18:
            return False
        
        # Condition-specific applicability
        if 'hba1c_target' in recommendation:
            last_hba1c = patient_data.get('last_hba1c', 0)
            if last_hba1c == 0:
                return False
        
        return True
    
    def _calculate_priority(self, recommendation: Dict[str, Any], patient_data: Dict[str, Any]) -> int:
        """Calculate priority score for recommendation"""
        priority = 50  # Base priority
        
        # Increase priority for critical values
        if 'hba1c_target' in recommendation:
            last_hba1c = patient_data.get('last_hba1c', 0)
            if last_hba1c > 9.0:
                priority += 30
            elif last_hba1c > 8.0:
                priority += 20
            elif last_hba1c > 7.0:
                priority += 10
        
        if 'blood_pressure_target' in recommendation:
            last_bp = patient_data.get('last_blood_pressure', {})
            systolic = last_bp.get('systolic', 0)
            diastolic = last_bp.get('diastolic', 0)
            
            if systolic > 160 or diastolic > 100:
                priority += 30
            elif systolic > 140 or diastolic > 90:
                priority += 20
            elif systolic > 130 or diastolic > 80:
                priority += 10
        
        return priority

class DrugInteractionChecker:
    """Drug interaction checking system"""
    
    def __init__(self):
        self.interactions = self._load_drug_interactions()
        self.allergies = self._load_allergy_data()
    
    def _load_drug_interactions(self) -> Dict[str, List[DrugInteraction]]:
        """Load drug interaction database"""
        interactions = {}
        
        # Common diabetes drug interactions
        interactions['metformin'] = [
            DrugInteraction(
                drug1='metformin',
                drug2='iodinated_contrast',
                severity=AlertSeverity.HIGH,
                interaction_type='Contraindication',
                description='Increased risk of lactic acidosis',
                recommendation='Hold metformin before and after procedures with iodinated contrast',
                evidence=['Kidney Disease: Improving Global Outcomes (KDIGO) guidelines']
            ),
            DrugInteraction(
                drug1='metformin',
                drug2='alcohol',
                severity=AlertSeverity.MEDIUM,
                interaction_type='Moderate',
                description='Increased risk of lactic acidosis with chronic alcohol use',
                recommendation='Limit alcohol intake and monitor for signs of lactic acidosis',
                evidence=['FDA prescribing information']
            )
        ]
        
        interactions['insulin'] = [
            DrugInteraction(
                drug1='insulin',
                drug2='beta_blockers',
                severity=AlertSeverity.MEDIUM,
                interaction_type='Moderate',
                description='Beta blockers can mask hypoglycemia symptoms',
                recommendation='Monitor blood glucose closely and educate patient on atypical symptoms',
                evidence=['American Diabetes Association guidelines']
            ),
            DrugInteraction(
                drug1='insulin',
                drug2='corticosteroids',
                severity=AlertSeverity.HIGH,
                interaction_type='Significant',
                description='Corticosteroids increase insulin requirements',
                recommendation='Monitor blood glucose closely and adjust insulin dosage',
                evidence=['Endocrine Society guidelines']
            )
        ]
        
        interactions['sulfonylureas'] = [
            DrugInteraction(
                drug1='sulfonylureas',
                drug2='fluoroquinolones',
                severity=AlertSeverity.HIGH,
                interaction_type='Significant',
                description='Increased risk of hypoglycemia',
                recommendation='Monitor blood glucose closely and consider dose reduction',
                evidence=['FDA drug safety communication']
            )
        ]
        
        return interactions
    
    def _load_allergy_data(self) -> Dict[str, Dict[str, Any]]:
        """Load allergy cross-reactivity data"""
        allergies = {
            'penicillin': {
                'cross_reactive': ['cephalosporins', 'carbapenems'],
                'severity': AlertSeverity.HIGH,
                'recommendation': 'Avoid beta-lactam antibiotics, consider alternative classes'
            },
            'sulfa': {
                'cross_reactive': ['sulfonylureas', 'thiazide diuretics'],
                'severity': AlertSeverity.MEDIUM,
                'recommendation': 'Use with caution and monitor for allergic reactions'
            }
        }
        
        return allergies
    
    def check_interactions(self, medications: List[str]) -> List[DrugInteraction]:
        """Check for drug interactions"""
        found_interactions = []
        
        for i, med1 in enumerate(medications):
            med1_lower = med1.lower()
            
            # Check direct interactions
            if med1_lower in self.interactions:
                for interaction in self.interactions[med1_lower]:
                    if interaction.drug2.lower() in [m.lower() for m in medications]:
                        found_interactions.append(interaction)
            
            # Check reverse interactions
            for j, med2 in enumerate(medications):
                if i != j:
                    med2_lower = med2.lower()
                    if med2_lower in self.interactions:
                        for interaction in self.interactions[med2_lower]:
                            if interaction.drug1.lower() == med1_lower:
                                found_interactions.append(interaction)
        
        return found_interactions
    
    def check_allergies(self, patient_allergies: List[str], medications: List[str]) -> List[Dict[str, Any]]:
        """Check for medication allergies and cross-reactivity"""
        allergy_alerts = []
        
        for allergy in patient_allergies:
            allergy_lower = allergy.lower()
            
            if allergy_lower in self.allergies:
                allergy_data = self.allergies[allergy_lower]
                
                # Check for direct allergy
                for med in medications:
                    if allergy_lower in med.lower():
                        allergy_alerts.append({
                            'type': 'direct_allergy',
                            'allergy': allergy,
                            'medication': med,
                            'severity': allergy_data['severity'],
                            'recommendation': allergy_data['recommendation']
                        })
                
                # Check for cross-reactivity
                for cross_reactive in allergy_data['cross_reactive']:
                    for med in medications:
                        if cross_reactive.lower() in med.lower():
                            allergy_alerts.append({
                                'type': 'cross_reactive',
                                'allergy': allergy,
                                'medication': med,
                                'severity': allergy_data['severity'],
                                'recommendation': allergy_data['recommendation']
                            })
        
        return allergy_alerts

class RiskAssessmentEngine:
    """Risk assessment for various clinical conditions"""
    
    def __init__(self):
        self.risk_calculators = {
            'cardiovascular': self._calculate_cardiovascular_risk,
            'hypoglycemia': self._calculate_hypoglycemia_risk,
            'diabetic_complications': self._calculate_complications_risk
        }
    
    def assess_risk(self, risk_type: str, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess clinical risk"""
        calculator = self.risk_calculators.get(risk_type)
        if not calculator:
            return {'error': f'Unknown risk type: {risk_type}'}
        
        return calculator(patient_data)
    
    def _calculate_cardiovascular_risk(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate cardiovascular risk using simplified ASCVD calculator"""
        age = patient_data.get('age', 0)
        gender = patient_data.get('gender', 'male')
        systolic_bp = patient_data.get('systolic_bp', 120)
        total_cholesterol = patient_data.get('total_cholesterol', 200)
        hdl_cholesterol = patient_data.get('hdl_cholesterol', 50)
        has_diabetes = patient_data.get('has_diabetes', False)
        is_smoker = patient_data.get('is_smoker', False)
        
        # Simplified risk calculation (actual ASCVD is more complex)
        risk_score = 0
        
        # Age factor
        if age >= 75:
            risk_score += 8
        elif age >= 65:
            risk_score += 6
        elif age >= 55:
            risk_score += 4
        elif age >= 45:
            risk_score += 2
        
        # Gender factor
        if gender == 'male':
            risk_score += 2
        
        # Blood pressure factor
        if systolic_bp >= 160:
            risk_score += 3
        elif systolic_bp >= 140:
            risk_score += 2
        elif systolic_bp >= 130:
            risk_score += 1
        
        # Cholesterol factor
        if total_cholesterol >= 240:
            risk_score += 2
        elif total_cholesterol >= 200:
            risk_score += 1
        
        if hdl_cholesterol < 40:
            risk_score += 2
        elif hdl_cholesterol < 50:
            risk_score += 1
        
        # Diabetes factor
        if has_diabetes:
            risk_score += 3
        
        # Smoking factor
        if is_smoker:
            risk_score += 3
        
        # Convert to percentage (simplified)
        risk_percentage = min(risk_score * 2, 30)  # Cap at 30%
        
        risk_level = 'LOW'
        if risk_percentage >= 20:
            risk_level = 'HIGH'
        elif risk_percentage >= 10:
            risk_level = 'MODERATE'
        
        return {
            'risk_score': risk_score,
            'risk_percentage': risk_percentage,
            'risk_level': risk_level,
            'recommendations': self._get_cardiovascular_recommendations(risk_level, risk_percentage)
        }
    
    def _calculate_hypoglycemia_risk(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate hypoglycemia risk"""
        age = patient_data.get('age', 0)
        medications = patient_data.get('medications', [])
        kidney_function = patient_data.get('egfr', 90)  # eGFR in mL/min/1.73m²
        last_glucose = patient_data.get('last_glucose', 100)
        has_hypoglycemia_history = patient_data.get('hypoglycemia_history', False)
        
        risk_score = 0
        
        # Age factor
        if age >= 75:
            risk_score += 3
        elif age >= 65:
            risk_score += 2
        
        # Medication factors
        if 'insulin' in medications:
            risk_score += 3
        if 'sulfonylureas' in medications:
            risk_score += 2
        
        # Kidney function
        if kidney_function < 30:
            risk_score += 3
        elif kidney_function < 60:
            risk_score += 2
        elif kidney_function < 90:
            risk_score += 1
        
        # Recent hypoglycemia
        if has_hypoglycemia_history:
            risk_score += 2
        
        # Current glucose level
        if last_glucose < 70:
            risk_score += 3
        elif last_glucose < 80:
            risk_score += 1
        
        risk_level = 'LOW'
        if risk_score >= 8:
            risk_level = 'HIGH'
        elif risk_score >= 5:
            risk_level = 'MODERATE'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'recommendations': self._get_hypoglycemia_recommendations(risk_level)
        }
    
    def _calculate_complications_risk(self, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate diabetic complications risk"""
        hba1c = patient_data.get('hba1c', 7.0)
        duration = patient_data.get('diabetes_duration', 0)  # years
        blood_pressure = patient_data.get('systolic_bp', 120)
        kidney_function = patient_data.get('egfr', 90)
        
        risk_score = 0
        
        # HbA1c factor
        if hba1c >= 9.0:
            risk_score += 4
        elif hba1c >= 8.0:
            risk_score += 3
        elif hba1c >= 7.5:
            risk_score += 2
        elif hba1c >= 7.0:
            risk_score += 1
        
        # Duration factor
        if duration >= 20:
            risk_score += 4
        elif duration >= 15:
            risk_score += 3
        elif duration >= 10:
            risk_score += 2
        elif duration >= 5:
            risk_score += 1
        
        # Blood pressure factor
        if blood_pressure >= 160:
            risk_score += 3
        elif blood_pressure >= 140:
            risk_score += 2
        elif blood_pressure >= 130:
            risk_score += 1
        
        # Kidney function factor
        if kidney_function < 60:
            risk_score += 3
        elif kidney_function < 90:
            risk_score += 1
        
        risk_level = 'LOW'
        if risk_score >= 10:
            risk_level = 'HIGH'
        elif risk_score >= 6:
            risk_level = 'MODERATE'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'recommendations': self._get_complications_recommendations(risk_level)
        }
    
    def _get_cardiovascular_recommendations(self, risk_level: str, risk_percentage: float) -> List[str]:
        """Get cardiovascular risk recommendations"""
        recommendations = []
        
        if risk_level == 'HIGH':
            recommendations.extend([
                'Consider statin therapy (high-intensity)',
                'Aspirin therapy if not contraindicated',
                'Intensive lifestyle modification',
                'Blood pressure target <130/80 mmHg',
                'Referral to cardiologist'
            ])
        elif risk_level == 'MODERATE':
            recommendations.extend([
                'Consider statin therapy (moderate-intensity)',
                'Lifestyle modification',
                'Blood pressure target <130/80 mmHg'
            ])
        else:
            recommendations.extend([
                'Healthy lifestyle promotion',
                'Regular risk factor monitoring'
            ])
        
        return recommendations
    
    def _get_hypoglycemia_recommendations(self, risk_level: str) -> List[str]:
        """Get hypoglycemia risk recommendations"""
        recommendations = []
        
        if risk_level == 'HIGH':
            recommendations.extend([
                'Consider medication regimen review',
                'Patient education on hypoglycemia symptoms',
                'Frequent glucose monitoring',
                'Adjust medication doses',
                'Consider CGM if available'
            ])
        elif risk_level == 'MODERATE':
            recommendations.extend([
                'Review medication timing and dosing',
                'Educate on hypoglycemia prevention',
                'Regular glucose monitoring'
            ])
        else:
            recommendations.extend([
                'Routine glucose monitoring',
                'Patient education'
            ])
        
        return recommendations
    
    def _get_complications_recommendations(self, risk_level: str) -> List[str]:
        """Get diabetic complications risk recommendations"""
        recommendations = []
        
        if risk_level == 'HIGH':
            recommendations.extend([
                'Intensive glycemic control (HbA1c <7.0%)',
                'Annual comprehensive eye exam',
                'Annual foot exam by podiatrist',
                'Annual kidney function tests',
                'Referral to diabetes specialist'
            ])
        elif risk_level == 'MODERATE':
            recommendations.extend([
                'Target HbA1c 7.0-7.5%',
                'Biannual eye and foot exams',
                'Regular kidney function monitoring'
            ])
        else:
            recommendations.extend([
                'Maintain HbA1c <7.0%',
                'Annual screening for complications'
            ])
        
        return recommendations

class ClinicalDecisionSupportService:
    """Main clinical decision support service"""
    
    def __init__(self):
        self.guidelines_engine = ClinicalGuidelinesEngine()
        self.drug_checker = DrugInteractionChecker()
        self.risk_assessor = RiskAssessmentEngine()
        self.active_alerts = {}
    
    def generate_clinical_recommendations(self, patient_id: int, patient_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive clinical recommendations"""
        recommendations = {
            'patient_id': patient_id,
            'generated_at': datetime.utcnow().isoformat(),
            'guidelines': [],
            'drug_interactions': [],
            'allergy_alerts': [],
            'risk_assessments': [],
            'alerts': [],
            'overall_priority': 'MEDIUM'
        }
        
        # Get guideline-based recommendations
        conditions = patient_data.get('conditions', [])
        for condition in conditions:
            condition_recs = self.guidelines_engine.get_recommendations(condition, patient_data)
            recommendations['guidelines'].extend(condition_recs)
        
        # Check drug interactions
        medications = patient_data.get('medications', [])
        if medications:
            interactions = self.drug_checker.check_interactions(medications)
            recommendations['drug_interactions'] = [
                {
                    'drugs': [interaction.drug1, interaction.drug2],
                    'severity': interaction.severity.value,
                    'description': interaction.description,
                    'recommendation': interaction.recommendation,
                    'evidence': interaction.evidence
                }
                for interaction in interactions
            ]
            
            # Check allergies
            allergies = patient_data.get('allergies', [])
            allergy_alerts = self.drug_checker.check_allergies(allergies, medications)
            recommendations['allergy_alerts'] = allergy_alerts
        
        # Risk assessments
        risk_types = ['cardiovascular', 'hypoglycemia', 'diabetic_complications']
        for risk_type in risk_types:
            risk_assessment = self.risk_assessor.assess_risk(risk_type, patient_data)
            recommendations['risk_assessments'].append({
                'type': risk_type,
                'assessment': risk_assessment
            })
        
        # Generate clinical alerts
        alerts = self._generate_clinical_alerts(patient_id, recommendations)
        recommendations['alerts'] = alerts
        
        # Calculate overall priority
        recommendations['overall_priority'] = self._calculate_overall_priority(recommendations)
        
        return recommendations
    
    def _generate_clinical_alerts(self, patient_id: int, recommendations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate clinical alerts based on recommendations"""
        alerts = []
        
        # High-risk drug interactions
        for interaction in recommendations['drug_interactions']:
            if interaction['severity'] in ['HIGH', 'CRITICAL']:
                alerts.append({
                    'alert_id': f"ALERT_{secrets.token_urlsafe(8)}",
                    'type': 'drug_interaction',
                    'severity': interaction['severity'],
                    'title': f"High-Risk Drug Interaction: {interaction['drugs'][0]} + {interaction['drugs'][1]}",
                    'description': interaction['description'],
                    'recommendation': interaction['recommendation'],
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        # Allergy alerts
        for allergy in recommendations['allergy_alerts']:
            if allergy['severity'] in ['HIGH', 'CRITICAL']:
                alerts.append({
                    'alert_id': f"ALERT_{secrets.token_urlsafe(8)}",
                    'type': 'allergy',
                    'severity': allergy['severity'].value,
                    'title': f"Allergy Alert: {allergy['allergy']} allergy to {allergy['medication']}",
                    'description': f"Patient has documented allergy to {allergy['allergy']} which may cross-react with {allergy['medication']}",
                    'recommendation': allergy['recommendation'],
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        # High-risk assessments
        for assessment in recommendations['risk_assessments']:
            if assessment['assessment'].get('risk_level') == 'HIGH':
                alerts.append({
                    'alert_id': f"ALERT_{secrets.token_urlsafe(8)}",
                    'type': 'risk_assessment',
                    'severity': 'HIGH',
                    'title': f"High {assessment['type'].replace('_', ' ').title()} Risk",
                    'description': f"Patient has high risk for {assessment['type'].replace('_', ' ')}",
                    'recommendation': '; '.join(assessment['assessment'].get('recommendations', [])),
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        return alerts
    
    def _calculate_overall_priority(self, recommendations: Dict[str, Any]) -> str:
        """Calculate overall priority based on all recommendations"""
        priority_score = 0
        
        # Check for critical alerts
        for alert in recommendations['alerts']:
            if alert['severity'] == 'CRITICAL':
                return 'CRITICAL'
            elif alert['severity'] == 'HIGH':
                priority_score += 3
            elif alert['severity'] == 'MEDIUM':
                priority_score += 2
            elif alert['severity'] == 'LOW':
                priority_score += 1
        
        # Check drug interactions
        for interaction in recommendations['drug_interactions']:
            if interaction['severity'] == 'CRITICAL':
                return 'CRITICAL'
            elif interaction['severity'] == 'HIGH':
                priority_score += 3
            elif interaction['severity'] == 'MEDIUM':
                priority_score += 2
            elif interaction['severity'] == 'LOW':
                priority_score += 1
        
        # Check risk assessments
        for assessment in recommendations['risk_assessments']:
            if assessment['assessment'].get('risk_level') == 'HIGH':
                priority_score += 2
            elif assessment['assessment'].get('risk_level') == 'MODERATE':
                priority_score += 1
        
        # Determine overall priority
        if priority_score >= 6:
            return 'HIGH'
        elif priority_score >= 3:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def acknowledge_alert(self, alert_id: str, user_id: int) -> bool:
        """Acknowledge a clinical alert"""
        # In a real implementation, this would update the database
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            self.active_alerts[alert_id].acknowledged_by = user_id
            self.active_alerts[alert_id].acknowledged_at = datetime.utcnow()
            return True
        return False
    
    def get_active_alerts(self, patient_id: int = None) -> List[ClinicalAlert]:
        """Get active clinical alerts"""
        alerts = []
        
        for alert in self.active_alerts.values():
            if not alert.acknowledged:
                if patient_id is None or alert.patient_id == patient_id:
                    alerts.append(alert)
        
        return alerts

# Global instance
cdss_service = ClinicalDecisionSupportService()
