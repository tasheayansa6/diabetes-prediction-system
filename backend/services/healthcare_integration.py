"""
HL7/FHIR Healthcare Data Integration

Provides integration with healthcare data standards:
- HL7 v2.x message parsing and generation
- FHIR R4 resource handling
- EHR/EMR system interoperability
- Healthcare data exchange protocols
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import re
import uuid
from flask import current_app

logger = logging.getLogger(__name__)

class HL7MessageType(Enum):
    """HL7 message types"""
    ADT = "ADT"  # Admit/Discharge/Transfer
    ORM = "ORM"  # Order Message
    ORU = "ORU"  # Observation Result
    PID = "PID"  # Patient Identification
    MSH = "MSH"  # Message Header
    OBX = "OBX"  # Observation/Result

class FHIRResourceType(Enum):
    """FHIR resource types"""
    PATIENT = "Patient"
    OBSERVATION = "Observation"
    DIAGNOSTIC_REPORT = "DiagnosticReport"
    SERVICE_REQUEST = "ServiceRequest"
    ENCOUNTER = "Encounter"
    PRACTITIONER = "Practitioner"
    MEDICATION_REQUEST = "MedicationRequest"
    CONDITION = "Condition"

@dataclass
class HL7Message:
    """HL7 message structure"""
    message_type: HL7MessageType
    version: str
    timestamp: datetime
    message_control_id: str
    processing_id: str
    segments: List[Dict[str, Any]]
    
    def to_hl7_string(self) -> str:
        """Convert to HL7 pipe delimited format"""
        lines = []
        
        # MSH segment (Message Header)
        msh = self.segments.get('MSH', {})
        msh_line = f"MSH|^~\\&|{msh.get('sending_application', '')}|{msh.get('sending_facility', '')}|{msh.get('receiving_application', '')}|{msh.get('receiving_facility', '')}|{self.timestamp.strftime('%Y%m%d%H%M%S')}||{self.message_type.value}|{self.message_control_id}|{self.processing_id}|{self.version}"
        lines.append(msh_line)
        
        # Add other segments
        for segment_name, segment_data in self.segments.items():
            if segment_name != 'MSH':
                line = self._format_segment(segment_name, segment_data)
                if line:
                    lines.append(line)
        
        return '\r'.join(lines)
    
    def _format_segment(self, segment_name: str, segment_data: Dict[str, Any]) -> str:
        """Format a segment as HL7 string"""
        if not segment_data:
            return ""
        
        # Handle different segment types
        if segment_name == "PID":
            return self._format_pid_segment(segment_data)
        elif segment_name == "OBX":
            return self._format_obx_segment(segment_data)
        elif segment_name == "ORC":
            return self._format_orc_segment(segment_data)
        else:
            # Generic formatting
            fields = [segment_name]
            for key, value in segment_data.items():
                if value:
                    fields.append(str(value))
            return '|'.join(fields)
    
    def _format_pid_segment(self, pid_data: Dict[str, Any]) -> str:
        """Format PID (Patient Identification) segment"""
        fields = ["PID"]
        fields.append(pid_data.get('set_id', '1'))
        fields.append(pid_data.get('patient_id', ''))
        fields.append(pid_data.get('patient_identifier_list', ''))
        fields.append(pid_data.get('patient_name', ''))
        fields.append(pid_data.get('mother_maiden_name', ''))
        fields.append(pid_data.get('date_of_birth', ''))
        fields.append(pid_data.get('sex', ''))
        fields.append(pid_data.get('patient_address', ''))
        fields.append(pid_data.get('phone_number', ''))
        fields.append(pid_data.get('phone_business', ''))
        fields.append(pid_data.get('language', ''))
        fields.append(pid_data.get('marital_status', ''))
        fields.append(pid_data.get('religion', ''))
        fields.append(pid_data.get('patient_account_number', ''))
        fields.append(pid_data.get('ssn_number', ''))
        fields.append(pid_data.get('drivers_license', ''))
        
        return '|'.join(fields)
    
    def _format_obx_segment(self, obx_data: Dict[str, Any]) -> str:
        """Format OBX (Observation/Result) segment"""
        fields = ["OBX"]
        fields.append(obx_data.get('set_id', '1'))
        fields.append(obx_data.get('value_type', 'ST'))
        fields.append(obx_data.get('observation_identifier', ''))
        fields.append(obx_data.get('observation_sub_id', ''))
        fields.append(obx_data.get('observation_value', ''))
        fields.append(obx_data.get('units', ''))
        fields.append(obx_data.get('reference_range', ''))
        fields.append(obx_data.get('abnormal_flags', ''))
        fields.append(obx_data.get('probability', ''))
        fields.append(obx_data.get('nature_of_abnormal_test', ''))
        fields.append(obx_data.get('observation_result_status', 'F'))
        fields.append(obx_data.get('effective_date_of_reference_range', ''))
        fields.append(obx_data.get('user_defined_access_checks', ''))
        fields.append(obx_data.get('datetime_of_the_observation', ''))
        fields.append(obx_data.get('producer_s_reference', ''))
        fields.append(obx_data.get('responsible_observer', ''))
        fields.append(obx_data.get('analysis_method', ''))
        
        return '|'.join(fields)
    
    def _format_orc_segment(self, orc_data: Dict[str, Any]) -> str:
        """Format ORC (Order Control) segment"""
        fields = ["ORC"]
        fields.append(orc_data.get('order_control', 'NW'))
        fields.append(orc_data.get('placer_order_number', ''))
        fields.append(orc_data.get('filler_order_number', ''))
        fields.append(orc_data.get('placer_group_number', ''))
        fields.append(orc_data.get('order_status', ''))
        fields.append(orc_data.get('response_flag', ''))
        fields.append(orc_data.get('timing_quantity', ''))
        fields.append(orc_data.get('parent', ''))
        fields.append(orc_data.get('date_of_transaction', ''))
        fields.append(orc_data.get('entered_by', ''))
        fields.append(orc_data.get('verified_by', ''))
        fields.append(orc_data.get('ordering_provider', ''))
        fields.append(orc_data.get('entering_organization', ''))
        fields.append(orc_data.get('entering_device', ''))
        
        return '|'.join(fields)

@dataclass
class FHIRResource:
    """FHIR resource structure"""
    resource_type: FHIRResourceType
    id: str
    meta: Dict[str, Any]
    data: Dict[str, Any]
    
    def to_fhir_json(self) -> Dict[str, Any]:
        """Convert to FHIR JSON format"""
        fhir_resource = {
            'resourceType': self.resource_type.value,
            'id': self.id,
            'meta': self.meta
        }
        fhir_resource.update(self.data)
        return fhir_resource
    
    @classmethod
    def from_patient_data(cls, patient_data: Dict[str, Any]) -> 'FHIRResource':
        """Create FHIR Patient resource from patient data"""
        fhir_data = {
            'identifier': [{
                'type': {
                    'coding': [{
                        'system': 'http://terminology.hl7.org/CodeSystem/v2-0203',
                        'code': 'MR',
                        'display': 'Medical Record Number'
                    }]
                },
                'value': patient_data.get('patient_id', '')
            }],
            'name': [{
                'use': 'official',
                'family': patient_data.get('last_name', ''),
                'given': [patient_data.get('first_name', '')]
            }],
            'telecom': [
                {
                    'system': 'phone',
                    'value': patient_data.get('phone', ''),
                    'use': 'home'
                },
                {
                    'system': 'email',
                    'value': patient_data.get('email', ''),
                    'use': 'home'
                }
            ],
            'gender': patient_data.get('gender', 'unknown'),
            'birthDate': patient_data.get('date_of_birth', ''),
            'address': [{
                'use': 'home',
                'line': [patient_data.get('address', '')],
                'city': patient_data.get('city', ''),
                'state': patient_data.get('state', ''),
                'postalCode': patient_data.get('postal_code', ''),
                'country': patient_data.get('country', '')
            }]
        }
        
        return cls(
            resource_type=FHIRResourceType.PATIENT,
            id=str(uuid.uuid4()),
            meta={'versionId': '1', 'lastUpdated': datetime.utcnow().isoformat()},
            data=fhir_data
        )
    
    @classmethod
    def from_observation_data(cls, observation_data: Dict[str, Any]) -> 'FHIRResource':
        """Create FHIR Observation resource from health record data"""
        fhir_data = {
            'status': 'final',
            'category': [{
                'coding': [{
                    'system': 'http://terminology.hl7.org/CodeSystem/observation-category',
                    'code': 'vital-signs',
                    'display': 'Vital Signs'
                }]
            }],
            'code': {
                'coding': [{
                    'system': 'http://loinc.org',
                    'code': observation_data.get('loinc_code', ''),
                    'display': observation_data.get('display_name', '')
                }]
            },
            'subject': {
                'reference': f"Patient/{observation_data.get('patient_id', '')}"
            },
            'effectiveDateTime': observation_data.get('date', ''),
            'valueQuantity': {
                'value': observation_data.get('value', 0),
                'unit': observation_data.get('unit', ''),
                'system': 'http://unitsofmeasure.org',
                'code': observation_data.get('unit_code', '')
            }
        }
        
        return cls(
            resource_type=FHIRResourceType.OBSERVATION,
            id=str(uuid.uuid4()),
            meta={'versionId': '1', 'lastUpdated': datetime.utcnow().isoformat()},
            data=fhir_data
        )

class HL7Parser:
    """HL7 message parser"""
    
    @staticmethod
    def parse_hl7_message(hl7_string: str) -> HL7Message:
        """Parse HL7 message from string"""
        lines = hl7_string.strip().split('\r')
        
        if not lines:
            raise ValueError("Empty HL7 message")
        
        # Parse MSH segment (header)
        msh_line = lines[0]
        msh_fields = msh_line.split('|')
        
        if len(msh_fields) < 9 or msh_fields[0] != 'MSH':
            raise ValueError("Invalid HL7 message header")
        
        # Extract header information
        encoding_chars = msh_fields[1]
        timestamp = datetime.strptime(msh_fields[6], '%Y%m%d%H%M%S')
        message_type = msh_fields[8]
        message_control_id = msh_fields[9] if len(msh_fields) > 9 else ''
        processing_id = msh_fields[10] if len(msh_fields) > 10 else ''
        version = msh_fields[11] if len(msh_fields) > 11 else '2.5'
        
        # Parse segments
        segments = {}
        segments['MSH'] = {
            'sending_application': msh_fields[2],
            'sending_facility': msh_fields[3],
            'receiving_application': msh_fields[4],
            'receiving_facility': msh_fields[5]
        }
        
        # Parse other segments
        for line in lines[1:]:
            if line:
                segment_name = line.split('|')[0]
                segment_data = HL7Parser._parse_segment_line(line)
                segments[segment_name] = segment_data
        
        return HL7Message(
            message_type=HL7MessageType(message_type.split('^')[0]),
            version=version,
            timestamp=timestamp,
            message_control_id=message_control_id,
            processing_id=processing_id,
            segments=segments
        )
    
    @staticmethod
    def _parse_segment_line(line: str) -> Dict[str, Any]:
        """Parse individual HL7 segment line"""
        fields = line.split('|')
        segment_name = fields[0]
        
        segment_data = {}
        
        if segment_name == 'PID':
            segment_data = HL7Parser._parse_pid_segment(fields)
        elif segment_name == 'OBX':
            segment_data = HL7Parser._parse_obx_segment(fields)
        elif segment_name == 'ORC':
            segment_data = HL7Parser._parse_orc_segment(fields)
        else:
            # Generic parsing
            for i, field in enumerate(fields[1:], 1):
                segment_data[f'field_{i}'] = field
        
        return segment_data
    
    @staticmethod
    def _parse_pid_segment(fields: List[str]) -> Dict[str, Any]:
        """Parse PID segment fields"""
        return {
            'set_id': fields[1] if len(fields) > 1 else '',
            'patient_id': fields[2] if len(fields) > 2 else '',
            'patient_identifier_list': fields[3] if len(fields) > 3 else '',
            'patient_name': fields[4] if len(fields) > 4 else '',
            'mother_maiden_name': fields[5] if len(fields) > 5 else '',
            'date_of_birth': fields[6] if len(fields) > 6 else '',
            'sex': fields[7] if len(fields) > 7 else '',
            'patient_address': fields[8] if len(fields) > 8 else '',
            'phone_number': fields[9] if len(fields) > 9 else '',
            'phone_business': fields[10] if len(fields) > 10 else '',
            'language': fields[11] if len(fields) > 11 else '',
            'marital_status': fields[12] if len(fields) > 12 else '',
            'religion': fields[13] if len(fields) > 13 else '',
            'patient_account_number': fields[14] if len(fields) > 14 else '',
            'ssn_number': fields[15] if len(fields) > 15 else '',
            'drivers_license': fields[16] if len(fields) > 16 else ''
        }
    
    @staticmethod
    def _parse_obx_segment(fields: List[str]) -> Dict[str, Any]:
        """Parse OBX segment fields"""
        return {
            'set_id': fields[1] if len(fields) > 1 else '',
            'value_type': fields[2] if len(fields) > 2 else '',
            'observation_identifier': fields[3] if len(fields) > 3 else '',
            'observation_sub_id': fields[4] if len(fields) > 4 else '',
            'observation_value': fields[5] if len(fields) > 5 else '',
            'units': fields[6] if len(fields) > 6 else '',
            'reference_range': fields[7] if len(fields) > 7 else '',
            'abnormal_flags': fields[8] if len(fields) > 8 else '',
            'probability': fields[9] if len(fields) > 9 else '',
            'nature_of_abnormal_test': fields[10] if len(fields) > 10 else '',
            'observation_result_status': fields[11] if len(fields) > 11 else '',
            'effective_date_of_reference_range': fields[12] if len(fields) > 12 else '',
            'user_defined_access_checks': fields[13] if len(fields) > 13 else '',
            'datetime_of_the_observation': fields[14] if len(fields) > 14 else '',
            'producer_s_reference': fields[15] if len(fields) > 15 else '',
            'responsible_observer': fields[16] if len(fields) > 16 else '',
            'analysis_method': fields[17] if len(fields) > 17 else ''
        }
    
    @staticmethod
    def _parse_orc_segment(fields: List[str]) -> Dict[str, Any]:
        """Parse ORC segment fields"""
        return {
            'order_control': fields[1] if len(fields) > 1 else '',
            'placer_order_number': fields[2] if len(fields) > 2 else '',
            'filler_order_number': fields[3] if len(fields) > 3 else '',
            'placer_group_number': fields[4] if len(fields) > 4 else '',
            'order_status': fields[5] if len(fields) > 5 else '',
            'response_flag': fields[6] if len(fields) > 6 else '',
            'timing_quantity': fields[7] if len(fields) > 7 else '',
            'parent': fields[8] if len(fields) > 8 else '',
            'date_of_transaction': fields[9] if len(fields) > 9 else '',
            'entered_by': fields[10] if len(fields) > 10 else '',
            'verified_by': fields[11] if len(fields) > 11 else '',
            'ordering_provider': fields[12] if len(fields) > 12 else '',
            'entering_organization': fields[13] if len(fields) > 13 else '',
            'entering_device': fields[14] if len(fields) > 14 else ''
        }

class FHIRParser:
    """FHIR resource parser"""
    
    @staticmethod
    def parse_fhir_resource(fhir_json: Dict[str, Any]) -> FHIRResource:
        """Parse FHIR resource from JSON"""
        resource_type = FHIRResourceType(fhir_json['resourceType'])
        resource_id = fhir_json.get('id', str(uuid.uuid4()))
        meta = fhir_json.get('meta', {})
        
        # Remove standard fields to get data
        data = fhir_json.copy()
        data.pop('resourceType', None)
        data.pop('id', None)
        data.pop('meta', None)
        
        return FHIRResource(
            resource_type=resource_type,
            id=resource_id,
            meta=meta,
            data=data
        )

class HealthcareIntegrationService:
    """Main healthcare integration service"""
    
    def __init__(self):
        self.hl7_parser = HL7Parser()
        self.fhir_parser = FHIRParser()
        self.supported_message_types = [
            HL7MessageType.ADT,
            HL7MessageType.ORM,
            HL7MessageType.ORU
        ]
        self.supported_resource_types = [
            FHIRResourceType.PATIENT,
            FHIRResourceType.OBSERVATION,
            FHIRResourceType.DIAGNOSTIC_REPORT,
            FHIRResourceType.SERVICE_REQUEST
        ]
    
    def process_incoming_hl7_message(self, hl7_message: str) -> Dict[str, Any]:
        """Process incoming HL7 message"""
        try:
            # Parse HL7 message
            parsed_message = self.hl7_parser.parse_hl7_message(hl7_message)
            
            # Convert to internal format
            internal_data = self._convert_hl7_to_internal(parsed_message)
            
            # Store in database
            result = self._store_hl7_data(parsed_message, internal_data)
            
            return {
                'success': True,
                'message_type': parsed_message.message_type.value,
                'message_control_id': parsed_message.message_control_id,
                'processed_data': internal_data,
                'stored': result
            }
            
        except Exception as e:
            logger.error(f"Failed to process HL7 message: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_incoming_fhir_resource(self, fhir_resource: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming FHIR resource"""
        try:
            # Parse FHIR resource
            parsed_resource = self.fhir_parser.parse_fhir_resource(fhir_resource)
            
            # Convert to internal format
            internal_data = self._convert_fhir_to_internal(parsed_resource)
            
            # Store in database
            result = self._store_fhir_data(parsed_resource, internal_data)
            
            return {
                'success': True,
                'resource_type': parsed_resource.resource_type.value,
                'resource_id': parsed_resource.id,
                'processed_data': internal_data,
                'stored': result
            }
            
        except Exception as e:
            logger.error(f"Failed to process FHIR resource: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def export_patient_as_hl7(self, patient_id: int, message_type: HL7MessageType = HL7MessageType.ADT) -> str:
        """Export patient data as HL7 message"""
        try:
            from backend.models.patient import Patient
            from backend.models.health_record import HealthRecord
            
            # Get patient data
            patient = Patient.query.get(patient_id)
            if not patient:
                raise ValueError(f"Patient {patient_id} not found")
            
            # Get recent health records
            health_records = HealthRecord.query.filter_by(patient_id=patient_id).limit(10).all()
            
            # Create HL7 message
            hl7_message = HL7Message(
                message_type=message_type,
                version='2.5',
                timestamp=datetime.utcnow(),
                message_control_id=str(uuid.uuid4()),
                processing_id='P',
                segments=self._create_hl7_segments_from_patient(patient, health_records)
            )
            
            return hl7_message.to_hl7_string()
            
        except Exception as e:
            logger.error(f"Failed to export patient as HL7: {e}")
            raise
    
    def export_patient_as_fhir(self, patient_id: int, resource_types: List[FHIRResourceType] = None) -> List[Dict[str, Any]]:
        """Export patient data as FHIR resources"""
        try:
            from backend.models.patient import Patient
            from backend.models.health_record import HealthRecord
            
            if resource_types is None:
                resource_types = [FHIRResourceType.PATIENT, FHIRResourceType.OBSERVATION]
            
            # Get patient data
            patient = Patient.query.get(patient_id)
            if not patient:
                raise ValueError(f"Patient {patient_id} not found")
            
            fhir_resources = []
            
            # Export patient resource
            if FHIRResourceType.PATIENT in resource_types:
                patient_data = {
                    'patient_id': patient.patient_id,
                    'first_name': patient.full_name.split()[0] if patient.full_name else '',
                    'last_name': ' '.join(patient.full_name.split()[1:]) if patient.full_name else '',
                    'email': patient.email,
                    'phone': patient.phone,
                    'gender': 'unknown',  # Would need to add to model
                    'date_of_birth': '2000-01-01'  # Would need to add to model
                }
                patient_resource = FHIRResource.from_patient_data(patient_data)
                fhir_resources.append(patient_resource.to_fhir_json())
            
            # Export observations (health records)
            if FHIRResourceType.OBSERVATION in resource_types:
                health_records = HealthRecord.query.filter_by(patient_id=patient_id).all()
                for record in health_records:
                    # Map health record to FHIR Observation
                    observation_data = self._map_health_record_to_observation(record)
                    observation_resource = FHIRResource.from_observation_data(observation_data)
                    fhir_resources.append(observation_resource.to_fhir_json())
            
            return fhir_resources
            
        except Exception as e:
            logger.error(f"Failed to export patient as FHIR: {e}")
            raise
    
    def _convert_hl7_to_internal(self, hl7_message: HL7Message) -> Dict[str, Any]:
        """Convert HL7 message to internal data format"""
        internal_data = {
            'message_type': hl7_message.message_type.value,
            'timestamp': hl7_message.timestamp.isoformat(),
            'message_control_id': hl7_message.message_control_id,
            'patient_data': {},
            'observations': [],
            'orders': []
        }
        
        # Extract patient data from PID segment
        if 'PID' in hl7_message.segments:
            pid_data = hl7_message.segments['PID']
            internal_data['patient_data'] = {
                'patient_id': pid_data.get('patient_id', ''),
                'name': pid_data.get('patient_name', ''),
                'date_of_birth': pid_data.get('date_of_birth', ''),
                'gender': pid_data.get('sex', ''),
                'phone': pid_data.get('phone_number', ''),
                'address': pid_data.get('patient_address', '')
            }
        
        # Extract observations from OBX segments
        for segment_name, segment_data in hl7_message.segments.items():
            if segment_name.startswith('OBX'):
                observation = {
                    'observation_identifier': segment_data.get('observation_identifier', ''),
                    'value': segment_data.get('observation_value', ''),
                    'units': segment_data.get('units', ''),
                    'reference_range': segment_data.get('reference_range', ''),
                    'abnormal_flags': segment_data.get('abnormal_flags', ''),
                    'datetime': segment_data.get('datetime_of_the_observation', '')
                }
                internal_data['observations'].append(observation)
        
        # Extract orders from ORC segments
        for segment_name, segment_data in hl7_message.segments.items():
            if segment_name.startswith('ORC'):
                order = {
                    'order_control': segment_data.get('order_control', ''),
                    'placer_order_number': segment_data.get('placer_order_number', ''),
                    'order_status': segment_data.get('order_status', ''),
                    'ordering_provider': segment_data.get('ordering_provider', '')
                }
                internal_data['orders'].append(order)
        
        return internal_data
    
    def _convert_fhir_to_internal(self, fhir_resource: FHIRResource) -> Dict[str, Any]:
        """Convert FHIR resource to internal data format"""
        internal_data = {
            'resource_type': fhir_resource.resource_type.value,
            'resource_id': fhir_resource.id,
            'last_updated': fhir_resource.meta.get('lastUpdated', ''),
            'data': fhir_resource.data
        }
        
        return internal_data
    
    def _store_hl7_data(self, hl7_message: HL7Message, internal_data: Dict[str, Any]) -> bool:
        """Store HL7 data in database"""
        try:
            # Implementation would depend on specific database schema
            # This is a placeholder for the actual storage logic
            logger.info(f"Storing HL7 message {hl7_message.message_control_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store HL7 data: {e}")
            return False
    
    def _store_fhir_data(self, fhir_resource: FHIRResource, internal_data: Dict[str, Any]) -> bool:
        """Store FHIR data in database"""
        try:
            # Implementation would depend on specific database schema
            # This is a placeholder for the actual storage logic
            logger.info(f"Storing FHIR resource {fhir_resource.id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store FHIR data: {e}")
            return False
    
    def _create_hl7_segments_from_patient(self, patient, health_records) -> Dict[str, Any]:
        """Create HL7 segments from patient data"""
        segments = {}
        
        # PID segment
        segments['PID'] = {
            'set_id': '1',
            'patient_id': patient.patient_id,
            'patient_name': patient.full_name,
            'phone_number': patient.phone,
            'date_of_birth': '20000101',  # Would need to add to model
            'sex': 'U'  # Would need to add to model
        }
        
        # OBX segments for health records
        for i, record in enumerate(health_records):
            segment_name = f'OBX{i+1}'
            segments[segment_name] = {
                'set_id': str(i+1),
                'value_type': 'NM',
                'observation_identifier': 'GLUCOSE',
                'observation_value': str(record.glucose) if record.glucose else '',
                'units': 'mg/dL',
                'datetime_of_the_observation': record.created_at.strftime('%Y%m%d%H%M%S') if record.created_at else ''
            }
        
        return segments
    
    def _map_health_record_to_observation(self, health_record) -> Dict[str, Any]:
        """Map health record to FHIR Observation data"""
        loinc_mapping = {
            'glucose': {'code': '2339-0', 'display': 'Glucose', 'unit': 'mg/dL', 'unit_code': 'mg/dL'},
            'bmi': {'code': '39156-5', 'display': 'Body Mass Index', 'unit': 'kg/m2', 'unit_code': 'kg/m2'},
            'blood_pressure': {'code': '55284-4', 'display': 'Blood Pressure', 'unit': 'mmHg', 'unit_code': 'mmHg'}
        }
        
        # Default to glucose if not found
        observation_data = loinc_mapping.get('glucose', loinc_mapping['glucose'])
        
        return {
            'patient_id': health_record.patient_id,
            'loinc_code': observation_data['code'],
            'display_name': observation_data['display'],
            'value': health_record.glucose or 0,
            'unit': observation_data['unit'],
            'unit_code': observation_data['unit_code'],
            'date': health_record.created_at.strftime('%Y-%m-%d') if health_record.created_at else ''
        }

# Global instance
healthcare_integration = HealthcareIntegrationService()
