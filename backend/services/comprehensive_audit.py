"""
Comprehensive Audit Trail System

Provides detailed audit logging for HIPAA compliance,
security monitoring, and business intelligence.
"""

import os
import json
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
from flask import request, g, current_app
from backend.extensions import db

logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Audit event types"""
    # Authentication events
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    MFA_ENABLED = "MFA_ENABLED"
    MFA_DISABLED = "MFA_DISABLED"
    MFA_FAILED = "MFA_FAILED"
    
    # Patient data events
    PATIENT_CREATE = "PATIENT_CREATE"
    PATIENT_READ = "PATIENT_READ"
    PATIENT_UPDATE = "PATIENT_UPDATE"
    PATIENT_DELETE = "PATIENT_DELETE"
    
    # Health record events
    HEALTH_RECORD_CREATE = "HEALTH_RECORD_CREATE"
    HEALTH_RECORD_READ = "HEALTH_RECORD_READ"
    HEALTH_RECORD_UPDATE = "HEALTH_RECORD_UPDATE"
    HEALTH_RECORD_DELETE = "HEALTH_RECORD_DELETE"
    
    # Prediction events
    PREDICTION_GENERATE = "PREDICTION_GENERATE"
    PREDICTION_READ = "PREDICTION_READ"
    PREDICTION_UPDATE = "PREDICTION_UPDATE"
    
    # Prescription events
    PRESCRIPTION_CREATE = "PRESCRIPTION_CREATE"
    PRESCRIPTION_READ = "PRESCRIPTION_READ"
    PRESCRIPTION_UPDATE = "PRESCRIPTION_UPDATE"
    PRESCRIPTION_DELETE = "PRESCRIPTION_DELETE"
    PRESCRIPTION_DISPENSE = "PRESCRIPTION_DISPENSE"
    PRESCRIPTION_VERIFY = "PRESCRIPTION_VERIFY"
    
    # Lab test events
    LAB_TEST_CREATE = "LAB_TEST_CREATE"
    LAB_TEST_READ = "LAB_TEST_READ"
    LAB_TEST_UPDATE = "LAB_TEST_UPDATE"
    LAB_TEST_DELETE = "LAB_TEST_DELETE"
    LAB_RESULT_ENTER = "LAB_RESULT_ENTER"
    LAB_RESULT_VALIDATE = "LAB_RESULT_VALIDATE"
    
    # Appointment events
    APPOINTMENT_CREATE = "APPOINTMENT_CREATE"
    APPOINTMENT_READ = "APPOINTMENT_READ"
    APPOINTMENT_UPDATE = "APPOINTMENT_UPDATE"
    APPOINTMENT_DELETE = "APPOINTMENT_DELETE"
    APPOINTMENT_CANCEL = "APPOINTMENT_CANCEL"
    
    # Payment events
    PAYMENT_CREATE = "PAYMENT_CREATE"
    PAYMENT_PROCESS = "PAYMENT_PROCESS"
    PAYMENT_REFUND = "PAYMENT_REFUND"
    
    # System events
    SYSTEM_STARTUP = "SYSTEM_STARTUP"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    BACKUP_CREATE = "BACKUP_CREATE"
    BACKUP_RESTORE = "BACKUP_RESTORE"
    
    # Security events
    SECURITY_BREACH = "SECURITY_BREACH"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    PHI_ACCESS = "PHI_ACCESS"
    DATA_EXPORT = "DATA_EXPORT"
    
    # Admin events
    USER_CREATE = "USER_CREATE"
    USER_UPDATE = "USER_UPDATE"
    USER_DELETE = "USER_DELETE"
    ROLE_CHANGE = "ROLE_CHANGE"

class AuditSeverity(Enum):
    """Audit severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class AuditEvent:
    """Audit event data structure"""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    user_id: Optional[int]
    user_role: Optional[str]
    username: Optional[str]
    timestamp: datetime
    ip_address: str
    user_agent: str
    session_id: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[Union[int, str]]
    action: str
    details: Dict[str, Any]
    phi_fields_accessed: Optional[List[str]] = None
    compliance_check: Optional[Dict[str, Any]] = None
    previous_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditEvent':
        """Create from dictionary"""
        data['event_type'] = AuditEventType(data['event_type'])
        data['severity'] = AuditSeverity(data['severity'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        return cls(**data)

class AuditTrailService:
    """Comprehensive audit trail service"""
    
    def __init__(self):
        self.audit_log_file = os.path.join(
            os.path.dirname(__file__), '..', '..', 'logs', 'comprehensive_audit.log'
        )
        self.security_log_file = os.path.join(
            os.path.dirname(__file__), '..', '..', 'logs', 'security_audit.log'
        )
        self.phi_log_file = os.path.join(
            os.path.dirname(__file__), '..', '..', 'logs', 'phi_access.log'
        )
        self.ensure_log_directories()
        
        # Event severity mapping
        self.severity_mapping = {
            AuditEventType.LOGIN: AuditSeverity.LOW,
            AuditEventType.LOGOUT: AuditSeverity.LOW,
            AuditEventType.LOGIN_FAILED: AuditSeverity.MEDIUM,
            AuditEventType.PASSWORD_CHANGE: AuditSeverity.MEDIUM,
            AuditEventType.MFA_FAILED: AuditSeverity.MEDIUM,
            
            AuditEventType.PATIENT_CREATE: AuditSeverity.MEDIUM,
            AuditEventType.PATIENT_READ: AuditSeverity.MEDIUM,
            AuditEventType.PATIENT_UPDATE: AuditSeverity.HIGH,
            AuditEventType.PATIENT_DELETE: AuditSeverity.CRITICAL,
            
            AuditEventType.HEALTH_RECORD_CREATE: AuditSeverity.MEDIUM,
            AuditEventType.HEALTH_RECORD_READ: AuditSeverity.MEDIUM,
            AuditEventType.HEALTH_RECORD_UPDATE: AuditSeverity.HIGH,
            AuditEventType.HEALTH_RECORD_DELETE: AuditSeverity.CRITICAL,
            
            AuditEventType.PHI_ACCESS: AuditSeverity.HIGH,
            AuditEventType.SECURITY_BREACH: AuditSeverity.CRITICAL,
            AuditEventType.UNAUTHORIZED_ACCESS: AuditSeverity.HIGH,
            AuditEventType.DATA_EXPORT: AuditSeverity.HIGH,
            
            AuditEventType.SYSTEM_STARTUP: AuditSeverity.LOW,
            AuditEventType.SYSTEM_SHUTDOWN: AuditSeverity.MEDIUM,
            AuditEventType.CONFIG_CHANGE: AuditSeverity.HIGH,
        }
    
    def ensure_log_directories(self):
        """Ensure log directories exist"""
        for log_file in [self.audit_log_file, self.security_log_file, self.phi_log_file]:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    def create_audit_event(self, event_type: AuditEventType, 
                          action: str, details: Dict[str, Any] = None,
                          resource_type: str = None, resource_id: Union[int, str] = None,
                          phi_fields_accessed: List[str] = None,
                          previous_values: Dict[str, Any] = None,
                          new_values: Dict[str, Any] = None,
                          success: bool = True, error_message: str = None) -> AuditEvent:
        """Create a comprehensive audit event"""
        
        # Get user information from Flask context
        user_id = getattr(g, 'current_user_id', None)
        user_role = getattr(g, 'current_user_role', None)
        username = getattr(g, 'current_username', None)
        session_id = getattr(g, 'session_id', None)
        
        # Get request information
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', 
                                       request.environ.get('REMOTE_ADDR', 'unknown'))
        user_agent = request.headers.get('User-Agent', 'unknown')
        
        # Generate correlation ID for request tracing
        correlation_id = getattr(g, 'correlation_id', secrets.token_urlsafe(16))
        
        # Determine severity
        severity = self.severity_mapping.get(event_type, AuditSeverity.MEDIUM)
        
        # Compliance check for PHI access
        compliance_check = None
        if phi_fields_accessed:
            compliance_check = self._check_phi_compliance(user_role, action, phi_fields_accessed)
        
        # Create audit event
        event = AuditEvent(
            event_id=f"AUDIT_{secrets.token_urlsafe(16)}",
            event_type=event_type,
            severity=severity,
            user_id=user_id,
            user_role=user_role,
            username=username,
            timestamp=datetime.utcnow(),
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            phi_fields_accessed=phi_fields_accessed,
            compliance_check=compliance_check,
            previous_values=previous_values,
            new_values=new_values,
            success=success,
            error_message=error_message,
            correlation_id=correlation_id
        )
        
        return event
    
    def log_audit_event(self, event: AuditEvent):
        """Log audit event to appropriate logs"""
        try:
            # Log to main audit log
            self._write_to_log_file(self.audit_log_file, event.to_dict())
            
            # Log to security log for security events
            if event.event_type in [AuditEventType.SECURITY_BREACH, 
                                   AuditEventType.UNAUTHORIZED_ACCESS,
                                   AuditEventType.LOGIN_FAILED,
                                   AuditEventType.RATE_LIMIT_EXCEEDED]:
                self._write_to_log_file(self.security_log_file, event.to_dict())
            
            # Log to PHI access log for PHI access
            if event.phi_fields_accessed:
                self._write_to_log_file(self.phi_log_file, event.to_dict())
            
            # Store in database if configured
            if current_app.config.get('AUDIT_TO_DATABASE', False):
                self._store_audit_in_database(event)
                
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    def _write_to_log_file(self, log_file: str, event_data: Dict[str, Any]):
        """Write event to log file"""
        with open(log_file, 'a') as f:
            f.write(json.dumps(event_data) + '\n')
    
    def _store_audit_in_database(self, event: AuditEvent):
        """Store audit event in database"""
        try:
            from backend.models.audit_log import AuditLog
            
            audit_log = AuditLog(
                user_id=event.user_id,
                username=event.username,
                user_role=event.user_role,
                action=event.action,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                details=json.dumps(event.details),
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                success=event.success,
                error_message=event.error_message,
                created_at=event.timestamp
            )
            
            db.session.add(audit_log)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to store audit in database: {e}")
            db.session.rollback()
    
    def _check_phi_compliance(self, user_role: str, action: str, phi_fields: List[str]) -> Dict[str, Any]:
        """Check PHI access compliance"""
        compliance_result = {
            'compliant': True,
            'violations': [],
            'warnings': []
        }
        
        # Role-based access rules
        role_permissions = {
            'patient': ['read'],
            'doctor': ['read', 'write'],
            'nurse': ['read', 'write'],
            'lab_technician': ['read', 'write'],
            'pharmacist': ['read', 'write'],
            'admin': ['read', 'write', 'delete']
        }
        
        if action not in role_permissions.get(user_role, []):
            compliance_result['compliant'] = False
            compliance_result['violations'].append(f"Role {user_role} not authorized for {action} action")
        
        # Minimum necessary principle
        if len(phi_fields) > 5:
            compliance_result['warnings'].append("Access to multiple PHI fields - verify minimum necessary")
        
        return compliance_result
    
    def get_audit_events(self, filters: Dict[str, Any] = None, 
                        limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve audit events with filters"""
        try:
            # For now, read from log file
            events = []
            with open(self.audit_log_file, 'r') as f:
                for line in f:
                    if line.strip():
                        event_data = json.loads(line.strip())
                        events.append(event_data)
            
            # Apply filters
            if filters:
                filtered_events = []
                for event in events:
                    match = True
                    
                    if 'user_id' in filters and event.get('user_id') != filters['user_id']:
                        match = False
                    if 'event_type' in filters and event.get('event_type') != filters['event_type']:
                        match = False
                    if 'severity' in filters and event.get('severity') != filters['severity']:
                        match = False
                    if 'start_date' in filters:
                        start_date = datetime.fromisoformat(filters['start_date'])
                        event_date = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                        if event_date < start_date:
                            match = False
                    if 'end_date' in filters:
                        end_date = datetime.fromisoformat(filters['end_date'])
                        event_date = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                        if event_date > end_date:
                            match = False
                    
                    if match:
                        filtered_events.append(event)
                
                events = filtered_events
            
            # Sort by timestamp (newest first)
            events.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Apply pagination
            return events[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"Failed to retrieve audit events: {e}")
            return []
    
    def generate_audit_report(self, report_type: str = 'summary', 
                            filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate comprehensive audit reports"""
        events = self.get_audit_events(filters, limit=10000)
        
        if report_type == 'summary':
            return self._generate_summary_report(events)
        elif report_type == 'security':
            return self._generate_security_report(events)
        elif report_type == 'phi_access':
            return self._generate_phi_access_report(events)
        elif report_type == 'compliance':
            return self._generate_compliance_report(events)
        else:
            return {'error': 'Unknown report type'}
    
    def _generate_summary_report(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary audit report"""
        summary = {
            'total_events': len(events),
            'event_types': {},
            'severity_distribution': {},
            'user_activity': {},
            'resource_access': {},
            'time_distribution': {},
            'success_rate': 0,
            'report_generated': datetime.utcnow().isoformat()
        }
        
        success_count = 0
        for event in events:
            # Event types
            event_type = event.get('event_type', 'UNKNOWN')
            summary['event_types'][event_type] = summary['event_types'].get(event_type, 0) + 1
            
            # Severity distribution
            severity = event.get('severity', 'MEDIUM')
            summary['severity_distribution'][severity] = summary['severity_distribution'].get(severity, 0) + 1
            
            # User activity
            username = event.get('username', 'UNKNOWN')
            summary['user_activity'][username] = summary['user_activity'].get(username, 0) + 1
            
            # Resource access
            resource_type = event.get('resource_type', 'UNKNOWN')
            summary['resource_access'][resource_type] = summary['resource_access'].get(resource_type, 0) + 1
            
            # Time distribution (by hour)
            timestamp = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            hour = timestamp.hour
            summary['time_distribution'][hour] = summary['time_distribution'].get(hour, 0) + 1
            
            # Success rate
            if event.get('success', True):
                success_count += 1
        
        summary['success_rate'] = (success_count / len(events) * 100) if events else 0
        
        return summary
    
    def _generate_security_report(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate security-focused audit report"""
        security_events = [e for e in events if e.get('event_type') in [
            'LOGIN_FAILED', 'SECURITY_BREACH', 'UNAUTHORIZED_ACCESS', 
            'RATE_LIMIT_EXCEEDED', 'MFA_FAILED'
        ]]
        
        report = {
            'total_security_events': len(security_events),
            'failed_logins': len([e for e in security_events if e['event_type'] == 'LOGIN_FAILED']),
            'unauthorized_access': len([e for e in security_events if e['event_type'] == 'UNAUTHORIZED_ACCESS']),
            'security_breaches': len([e for e in security_events if e['event_type'] == 'SECURITY_BREACH']),
            'mfa_failures': len([e for e in security_events if e['event_type'] == 'MFA_FAILED']),
            'suspicious_ips': {},
            'high_risk_users': {},
            'report_generated': datetime.utcnow().isoformat()
        }
        
        # Analyze suspicious IPs
        ip_counts = {}
        for event in security_events:
            ip = event.get('ip_address', 'unknown')
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
        
        report['suspicious_ips'] = {ip: count for ip, count in ip_counts.items() if count > 5}
        
        # Analyze high-risk users
        user_counts = {}
        for event in security_events:
            username = event.get('username', 'unknown')
            user_counts[username] = user_counts.get(username, 0) + 1
        
        report['high_risk_users'] = {user: count for user, count in user_counts.items() if count > 3}
        
        return report
    
    def _generate_phi_access_report(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate PHI access audit report"""
        phi_events = [e for e in events if e.get('phi_fields_accessed')]
        
        report = {
            'total_phi_access': len(phi_events),
            'phi_fields_accessed': {},
            'user_phi_access': {},
            'role_phi_access': {},
            'compliance_violations': 0,
            'report_generated': datetime.utcnow().isoformat()
        }
        
        for event in phi_events:
            # PHI fields accessed
            phi_fields = event.get('phi_fields_accessed', [])
            for field in phi_fields:
                report['phi_fields_accessed'][field] = report['phi_fields_accessed'].get(field, 0) + 1
            
            # User PHI access
            username = event.get('username', 'unknown')
            report['user_phi_access'][username] = report['user_phi_access'].get(username, 0) + 1
            
            # Role PHI access
            role = event.get('user_role', 'unknown')
            report['role_phi_access'][role] = report['role_phi_access'].get(role, 0) + 1
            
            # Compliance violations
            compliance = event.get('compliance_check', {})
            if not compliance.get('compliant', True):
                report['compliance_violations'] += 1
        
        return report
    
    def _generate_compliance_report(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate compliance-focused audit report"""
        report = {
            'total_events': len(events),
            'hipaa_compliance': {
                'phi_access_events': 0,
                'phi_access_compliant': 0,
                'minimum_necessary_violations': 0,
                'unauthorized_phi_access': 0
            },
            'data_retention': {
                'events_older_than_7_years': 0,
                'events_older_than_6_years': 0
            },
            'audit_trail_integrity': {
                'missing_correlation_ids': 0,
                'missing_user_context': 0,
                'incomplete_events': 0
            },
            'report_generated': datetime.utcnow().isoformat()
        }
        
        seven_years_ago = datetime.utcnow() - timedelta(days=365 * 7)
        six_years_ago = datetime.utcnow() - timedelta(days=365 * 6)
        
        for event in events:
            # HIPAA compliance
            if event.get('phi_fields_accessed'):
                report['hipaa_compliance']['phi_access_events'] += 1
                
                compliance = event.get('compliance_check', {})
                if compliance.get('compliant', True):
                    report['hipaa_compliance']['phi_access_compliant'] += 1
                
                if compliance.get('warnings'):
                    report['hipaa_compliance']['minimum_necessary_violations'] += 1
            
            # Data retention
            event_date = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
            if event_date < seven_years_ago:
                report['data_retention']['events_older_than_7_years'] += 1
            elif event_date < six_years_ago:
                report['data_retention']['events_older_than_6_years'] += 1
            
            # Audit trail integrity
            if not event.get('correlation_id'):
                report['audit_trail_integrity']['missing_correlation_ids'] += 1
            if not event.get('user_id'):
                report['audit_trail_integrity']['missing_user_context'] += 1
            if not event.get('timestamp') or not event.get('event_type'):
                report['audit_trail_integrity']['incomplete_events'] += 1
        
        return report

# Decorator for automatic audit logging
def audit_action(event_type: AuditEventType, action: str, 
                resource_type: str = None, phi_fields: List[str] = None):
    """Decorator for automatic audit logging"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = datetime.utcnow()
            success = True
            error_message = None
            previous_values = None
            new_values = None
            
            try:
                result = f(*args, **kwargs)
                
                # For update operations, capture changes
                if action in ['update', 'modify'] and hasattr(result, 'get'):
                    if 'previous_values' in result:
                        previous_values = result['previous_values']
                    if 'new_values' in result:
                        new_values = result['new_values']
                
                return result
                
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                # Create audit event
                audit_service = AuditTrailService()
                event = audit_service.create_audit_event(
                    event_type=event_type,
                    action=action,
                    resource_type=resource_type,
                    resource_id=kwargs.get('id'),
                    phi_fields_accessed=phi_fields,
                    previous_values=previous_values,
                    new_values=new_values,
                    success=success,
                    error_message=error_message
                )
                audit_service.log_audit_event(event)
        
        return decorated_function
    return decorator

# Global instance
audit_service = AuditTrailService()
