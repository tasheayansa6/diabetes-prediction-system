"""
Background Job Processing with Celery and Redis

Provides asynchronous task processing for:
- Email notifications
- Report generation
- Data backups
- ML model retraining
- Data cleanup and maintenance
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from celery import Celery
from celery.schedules import crontab
from flask import current_app
import redis
import json
from dataclasses import dataclass
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import pandas as pd
from io import BytesIO
import zipfile

logger = logging.getLogger(__name__)

# Celery configuration
celery_app = Celery('diabetes_prediction_system')

@dataclass
class TaskResult:
    """Task result data structure"""
    task_id: str
    status: str
    result: Any = None
    error: Optional[str] = None
    progress: int = 0
    total_steps: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class BackgroundTaskService:
    """Background task management service"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0)),
            decode_responses=True
        )
        self.task_results = {}
    
    def configure_celery(self, app):
        """Configure Celery with Flask app"""
        celery_app.conf.update(
            broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
            result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
            task_serializer='json',
            accept_content=['json'],
            result_serializer='json',
            timezone='UTC',
            enable_utc=True,
            task_routes={
                'backend.tasks.email_tasks.*': {'queue': 'email'},
                'backend.tasks.report_tasks.*': {'queue': 'reports'},
                'backend.tasks.ml_tasks.*': {'queue': 'ml'},
                'backend.tasks.maintenance_tasks.*': {'queue': 'maintenance'},
            },
            beat_schedule={
                'daily-backup': {
                    'task': 'backend.tasks.maintenance_tasks.daily_backup',
                    'schedule': crontab(hour=2, minute=0),  # 2 AM daily
                },
                'weekly-report': {
                    'task': 'backend.tasks.report_tasks.weekly_system_report',
                    'schedule': crontab(hour=8, minute=0, day_of_week=1),  # Monday 8 AM
                },
                'data-cleanup': {
                    'task': 'backend.tasks.maintenance_tasks.cleanup_old_data',
                    'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Sunday 3 AM
                },
                'ml-model-retraining': {
                    'task': 'backend.tasks.ml_tasks.retrain_models',
                    'schedule': crontab(hour=4, minute=0, day_of_month=1),  # 1st of month 4 AM
                },
                'audit-log-rotation': {
                    'task': 'backend.tasks.maintenance_tasks.rotate_audit_logs',
                    'schedule': crontab(hour=1, minute=0),  # 1 AM daily
                },
            },
            worker_prefetch_multiplier=1,
            task_acks_late=True,
            worker_max_tasks_per_child=1000,
        )
        
        class ContextTask(celery_app.Task):
            """Make celery tasks work with Flask app context."""
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery_app.Task = ContextTask
        return celery_app
    
    def submit_task(self, task_name: str, args: tuple = (), kwargs: dict = None, 
                   queue: str = None) -> str:
        """Submit a background task"""
        kwargs = kwargs or {}
        task = celery_app.send_task(task_name, args=args, kwargs=kwargs, queue=queue)
        
        # Store initial task result
        self.task_results[task.id] = TaskResult(
            task_id=task.id,
            status='PENDING',
            started_at=datetime.utcnow()
        )
        
        logger.info(f"Submitted task {task_name} with ID {task.id}")
        return task.id
    
    def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """Get task status and progress"""
        if task_id in self.task_results:
            return self.task_results[task_id]
        
        # Check Celery result backend
        try:
            result = celery_app.AsyncResult(task_id)
            task_result = TaskResult(
                task_id=task_id,
                status=result.status,
                result=result.result if result.successful() else None,
                error=str(result.info) if result.failed() else None,
                completed_at=datetime.utcnow() if result.ready() else None
            )
            
            self.task_results[task_id] = task_result
            return task_result
            
        except Exception as e:
            logger.error(f"Failed to get task status: {e}")
            return None
    
    def update_task_progress(self, task_id: str, progress: int, total_steps: int = 100):
        """Update task progress"""
        if task_id in self.task_results:
            self.task_results[task_id].progress = progress
            self.task_results[task_id].total_steps = total_steps
            
            # Store in Redis for real-time updates
            progress_data = {
                'progress': progress,
                'total_steps': total_steps,
                'updated_at': datetime.utcnow().isoformat()
            }
            self.redis_client.setex(
                f"task_progress:{task_id}", 
                timedelta(hours=24), 
                json.dumps(progress_data)
            )
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        try:
            celery_app.control.revoke(task_id, terminate=True)
            if task_id in self.task_results:
                self.task_results[task_id].status = 'CANCELLED'
            return True
        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return False

# Email Tasks
@celery_app.task(bind=True)
def send_email_notification(self, recipient_email: str, subject: str, 
                          template_name: str, template_data: Dict[str, Any],
                          attachments: List[str] = None):
    """Send email notification asynchronously"""
    try:
        from flask import render_template
        from backend.config import config
        
        # Update progress
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Preparing email'})
        
        # Get email configuration
        email_config = config['development']
        smtp_server = email_config.MAIL_SERVER
        smtp_port = email_config.MAIL_PORT
        smtp_username = email_config.MAIL_USERNAME
        smtp_password = email_config.MAIL_PASSWORD
        
        self.update_state(state='PROGRESS', meta={'progress': 30, 'status': 'Rendering template'})
        
        # Render email template
        html_body = render_template(f'emails/{template_name}.html', **template_data)
        text_body = render_template(f'emails/{template_name}.txt', **template_data)
        
        self.update_state(state='PROGRESS', meta={'progress': 50, 'status': 'Connecting to SMTP'})
        
        # Create email message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_username
        msg['To'] = recipient_email
        
        # Attach text and HTML parts
        text_part = MIMEText(text_body, 'plain')
        html_part = MIMEText(html_body, 'html')
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Add attachments if provided
        if attachments:
            self.update_state(state='PROGRESS', meta={'progress': 70, 'status': 'Adding attachments'})
            for attachment_path in attachments:
                if os.path.exists(attachment_path):
                    with open(attachment_path, 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {os.path.basename(attachment_path)}'
                        )
                        msg.attach(part)
        
        self.update_state(state='PROGRESS', meta={'progress': 90, 'status': 'Sending email'})
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        self.update_state(state='SUCCESS', meta={'progress': 100, 'status': 'Email sent successfully'})
        return {'success': True, 'message': 'Email sent successfully'}
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(bind=True)
def send_bulk_notifications(self, notification_type: str, recipients: List[str], 
                          message_data: Dict[str, Any]):
    """Send bulk notifications to multiple recipients"""
    try:
        results = []
        total_recipients = len(recipients)
        
        for i, recipient in enumerate(recipients):
            progress = int((i / total_recipients) * 100)
            self.update_state(
                state='PROGRESS', 
                meta={'progress': progress, 'status': f'Sent {i}/{total_recipients}'}
            )
            
            # Send individual notification
            if notification_type == 'email':
                result = send_email_notification(
                    recipient_email=recipient['email'],
                    subject=message_data['subject'],
                    template_name=message_data['template'],
                    template_data=message_data.get('data', {})
                )
                results.append({'recipient': recipient['email'], 'result': result})
            elif notification_type == 'sms':
                # Implement SMS notification logic
                pass
        
        self.update_state(state='SUCCESS', meta={'progress': 100, 'results': results})
        return {'success': True, 'results': results}
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

# Report Generation Tasks
@celery_app.task(bind=True)
def generate_patient_report(self, patient_id: int, report_format: str = 'pdf'):
    """Generate patient report asynchronously"""
    try:
        from backend.services.report_service import ReportService
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Loading patient data'})
        
        report_service = ReportService()
        
        self.update_state(state='PROGRESS', meta={'progress': 30, 'status': 'Generating report content'})
        
        # Generate report
        report_data = report_service.generate_patient_report(patient_id)
        
        self.update_state(state='PROGRESS', meta={'progress': 70, 'status': 'Formatting report'})
        
        # Format based on requested format
        if report_format == 'pdf':
            report_path = report_service.generate_pdf_report(report_data, f"patient_report_{patient_id}.pdf")
        elif report_format == 'csv':
            report_path = report_service.generate_csv_report(report_data, f"patient_report_{patient_id}.csv")
        else:
            report_path = report_service.generate_json_report(report_data, f"patient_report_{patient_id}.json")
        
        self.update_state(state='SUCCESS', meta={'progress': 100, 'report_path': report_path})
        return {'success': True, 'report_path': report_path}
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(bind=True)
def generate_weekly_system_report(self):
    """Generate weekly system analytics report"""
    try:
        from backend.services.comprehensive_audit import audit_service
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Collecting audit data'})
        
        # Get audit data for the past week
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        filters = {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        }
        
        self.update_state(state='PROGRESS', meta={'progress': 30, 'status': 'Generating summary report'})
        
        summary_report = audit_service.generate_audit_report('summary', filters)
        security_report = audit_service.generate_audit_report('security', filters)
        phi_report = audit_service.generate_audit_report('phi_access', filters)
        
        self.update_state(state='PROGRESS', meta={'progress': 60, 'status': 'Compiling final report'})
        
        # Compile final report
        weekly_report = {
            'report_period': f"{start_date.date()} to {end_date.date()}",
            'generated_at': datetime.utcnow().isoformat(),
            'summary': summary_report,
            'security': security_report,
            'phi_access': phi_report
        }
        
        # Save report
        report_path = f"reports/weekly_report_{end_date.strftime('%Y%m%d')}.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(weekly_report, f, indent=2, default=str)
        
        self.update_state(state='SUCCESS', meta={'progress': 100, 'report_path': report_path})
        return {'success': True, 'report_path': report_path}
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

# ML Model Tasks
@celery_app.task(bind=True)
def retrain_models(self, model_type: str = 'all'):
    """Retrain ML models with new data"""
    try:
        from backend.services.ml_service import MLService
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Preparing training data'})
        
        ml_service = MLService()
        
        self.update_state(state='PROGRESS', meta={'progress': 30, 'status': 'Training models'})
        
        # Retrain models
        if model_type == 'all' or model_type == 'gradient_boosting':
            gb_result = ml_service.train_gradient_boosting_model()
        
        if model_type == 'all' or model_type == 'random_forest':
            rf_result = ml_service.train_random_forest_model()
        
        if model_type == 'all' or model_type == 'logistic_regression':
            lr_result = ml_service.train_logistic_regression_model()
        
        self.update_state(state='PROGRESS', meta={'progress': 80, 'status': 'Updating model registry'})
        
        # Update model registry
        ml_service.update_model_registry()
        
        self.update_state(state='SUCCESS', meta={'progress': 100, 'status': 'Model retraining completed'})
        return {'success': True, 'message': 'Models retrained successfully'}
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

# Maintenance Tasks
@celery_app.task(bind=True)
def daily_backup(self):
    """Perform daily database backup"""
    try:
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Starting backup'})
        
        backup_date = datetime.utcnow().strftime('%Y%m%d')
        backup_path = f"backups/diabetes_db_backup_{backup_date}.sql"
        
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        self.update_state(state='PROGRESS', meta={'progress': 30, 'status': 'Creating database dump'})
        
        # Create database backup
        import subprocess
        
        # PostgreSQL backup
        if os.getenv('DATABASE_URL', '').startswith('postgresql'):
            db_url = os.getenv('DATABASE_URL')
            cmd = f"pg_dump {db_url} > {backup_path}"
        else:
            # SQLite backup
            db_path = os.getenv('DATABASE_URL', 'database/diabetes.db').replace('sqlite:///', '')
            cmd = f"cp {db_path} {backup_path}"
        
        subprocess.run(cmd, shell=True, check=True)
        
        self.update_state(state='PROGRESS', meta={'progress': 70, 'status': 'Compressing backup'})
        
        # Compress backup
        zip_path = f"{backup_path}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(backup_path, os.path.basename(backup_path))
        
        # Remove uncompressed backup
        os.remove(backup_path)
        
        self.update_state(state='SUCCESS', meta={'progress': 100, 'backup_path': zip_path})
        return {'success': True, 'backup_path': zip_path}
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(bind=True)
def cleanup_old_data(self):
    """Clean up old data according to retention policies"""
    try:
        from backend.services.hipaa_compliance import hipaa_manager
        
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Analyzing data for cleanup'})
        
        # Clean up old audit logs (older than 6 years)
        six_years_ago = datetime.utcnow() - timedelta(days=365 * 6)
        
        self.update_state(state='PROGRESS', meta={'progress': 30, 'status': 'Cleaning audit logs'})
        
        # Implement audit log cleanup
        # This would typically be done in batches
        
        self.update_state(state='PROGRESS', meta={'progress': 60, 'status': 'Cleaning temporary files'})
        
        # Clean up temporary files
        temp_dir = 'temp'
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                if os.path.isfile(file_path):
                    file_age = datetime.utcnow() - datetime.fromtimestamp(os.path.getctime(file_path))
                    if file_age.days > 7:
                        os.remove(file_path)
        
        self.update_state(state='SUCCESS', meta={'progress': 100, 'status': 'Data cleanup completed'})
        return {'success': True, 'message': 'Data cleanup completed'}
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

@celery_app.task(bind=True)
def rotate_audit_logs(self):
    """Rotate audit log files"""
    try:
        self.update_state(state='PROGRESS', meta={'progress': 10, 'status': 'Starting log rotation'})
        
        log_dir = 'logs'
        rotated_dir = os.path.join(log_dir, 'rotated')
        os.makedirs(rotated_dir, exist_ok=True)
        
        # Rotate audit logs
        audit_logs = ['comprehensive_audit.log', 'security_audit.log', 'phi_access.log']
        
        for log_file in audit_logs:
            log_path = os.path.join(log_dir, log_file)
            if os.path.exists(log_path):
                self.update_state(state='PROGRESS', meta={'progress': 30, 'status': f'Rotating {log_file}'})
                
                # Create rotated filename with date
                timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                rotated_path = os.path.join(rotated_dir, f"{log_file}.{timestamp}")
                
                # Move current log to rotated
                os.rename(log_path, rotated_path)
                
                # Create new empty log file
                with open(log_path, 'w') as f:
                    f.write('')
        
        self.update_state(state='SUCCESS', meta={'progress': 100, 'status': 'Log rotation completed'})
        return {'success': True, 'message': 'Log rotation completed'}
        
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise

# Global instance
background_service = BackgroundTaskService()
