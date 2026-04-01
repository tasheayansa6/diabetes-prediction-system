"""
Logging Configuration for Diabetes Prediction System

This module configures logging for different parts of the application:
- system.log: General application logs
- security.log: Security events (logins, failed attempts, etc.)
- prediction.log: ML prediction events
- api.log: API request logging
- database.log: Database operations
- error.log: Error logs with tracebacks
"""

import os
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime, timedelta
import traceback
import json
from functools import wraps
import time

# ============================================================================
# Logging Configuration
# ============================================================================

def configure_logging(app=None):
    """
    Configure logging for the application
    
    Args:
        app: Flask application instance (optional)
    
    Returns:
        dict: Dictionary of log handlers
    """
    # Create logs directory if it doesn't exist
    logs_dir = 'logs'
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Configure root logger
    log_level = logging.DEBUG if os.getenv('FLASK_ENV') == 'development' else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(log_format, date_format)
    
    # System log handler (rotating by size)
    system_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'system.log'),
        maxBytes=10485760,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    system_handler.setLevel(log_level)
    system_handler.setFormatter(formatter)
    
    # Security log handler
    security_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'security.log'),
        maxBytes=10485760,
        backupCount=10,
        encoding='utf-8'
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(formatter)
    
    # Prediction log handler (with special format)
    prediction_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'prediction.log'),
        maxBytes=10485760,
        backupCount=10,
        encoding='utf-8'
    )
    prediction_handler.setLevel(log_level)
    
    # Custom formatter for prediction logs (JSON format for easier parsing)
    class PredictionFormatter(logging.Formatter):
        def format(self, record):
            if hasattr(record, 'prediction_data'):
                return json.dumps(record.prediction_data, ensure_ascii=False)
            return super().format(record)
    
    prediction_handler.setFormatter(PredictionFormatter(log_format, date_format))
    
    # API log handler
    api_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'api.log'),
        maxBytes=10485760,
        backupCount=10,
        encoding='utf-8'
    )
    api_handler.setLevel(log_level)
    api_handler.setFormatter(formatter)
    
    # Database log handler
    database_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'database.log'),
        maxBytes=10485760,
        backupCount=10,
        encoding='utf-8'
    )
    database_handler.setLevel(log_level)
    database_handler.setFormatter(formatter)
    
    # Error log handler (for errors only)
    error_handler = RotatingFileHandler(
        os.path.join(logs_dir, 'error.log'),
        maxBytes=10485760,
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # Console handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if os.getenv('FLASK_ENV') == 'development' else logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(system_handler)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(error_handler)
    
    # Configure specific loggers
    loggers = {
        'security': security_handler,
        'prediction': prediction_handler,
        'api': api_handler,
        'database': database_handler
    }
    
    for logger_name, handler in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        logger.addHandler(handler)
        logger.propagate = False  # Don't propagate to root logger to avoid duplication
    
    # Configure Flask app logger if provided
    if app:
        # Add handlers to Flask app logger
        app.logger.addHandler(system_handler)
        app.logger.addHandler(console_handler)
        app.logger.addHandler(error_handler)
        app.logger.setLevel(log_level)
        
        # Also add to Flask's werkzeug logger
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.addHandler(api_handler)
        werkzeug_logger.addHandler(console_handler)
    
    return {
        'system': system_handler,
        'security': security_handler,
        'prediction': prediction_handler,
        'api': api_handler,
        'database': database_handler,
        'error': error_handler,
        'console': console_handler
    }


def get_logger(name):
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# ============================================================================
# Prediction Logging Functions
# ============================================================================

class PredictionLogger:
    """
    Specialized logger for prediction events with structured logging
    """
    
    def __init__(self):
        self.logger = logging.getLogger('prediction')
    
    def log_prediction(self, user_id, username, input_data, result, 
                       model_version=None, processing_time_ms=None,
                       health_record_id=None, prediction_id=None):
        """
        Log a prediction event with structured data
        
        Args:
            user_id: User ID making the prediction
            username: Username making the prediction
            input_data: Input data for prediction
            result: Prediction result dictionary
            model_version: Version of the model used
            processing_time_ms: Processing time in milliseconds
            health_record_id: Associated health record ID
            prediction_id: Associated prediction ID
        """
        # Prepare structured log data
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'prediction',
            'user_id': user_id,
            'username': username,
            'model_version': model_version or 'unknown',
            'processing_time_ms': processing_time_ms,
            'health_record_id': health_record_id,
            'prediction_id': prediction_id,
            'input_features': {
                'glucose': input_data.get('glucose'),
                'bmi': input_data.get('bmi'),
                'age': input_data.get('age'),
                'blood_pressure': input_data.get('blood_pressure'),
                'pregnancies': input_data.get('pregnancies'),
                'insulin': input_data.get('insulin'),
                'skinthickness': input_data.get('skinthickness'),
                'diabetes_pedigree': input_data.get('diabetes_pedigree')
            },
            'prediction_result': {
                'prediction_code': result.get('prediction_code'),
                'prediction_label': 'Diabetic' if result.get('prediction_code') == 1 else 'Non-Diabetic',
                'probability': result.get('probability'),
                'probability_percent': result.get('probability_percent'),
                'risk_level': result.get('risk_level'),
                'risk_color': result.get('risk_color'),
                'interpretation': result.get('interpretation'),
                'recommendation': result.get('recommendation')
            }
        }
        
        # Add extra fields for logging
        extra = {'prediction_data': log_data}
        
        # Log as JSON for easy parsing
        self.logger.info(json.dumps(log_data), extra=extra)
    
    def log_batch_prediction(self, user_id, username, batch_size, 
                              results_summary, processing_time_ms):
        """
        Log batch prediction events
        
        Args:
            user_id: User ID making the batch prediction
            username: Username making the batch prediction
            batch_size: Number of predictions in the batch
            results_summary: Summary of batch results
            processing_time_ms: Total processing time
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'batch_prediction',
            'user_id': user_id,
            'username': username,
            'batch_size': batch_size,
            'processing_time_ms': processing_time_ms,
            'results_summary': results_summary
        }
        
        self.logger.info(json.dumps(log_data))
    
    def log_model_performance(self, model_version, metrics, evaluation_data=None):
        """
        Log model performance metrics
        
        Args:
            model_version: Version of the model
            metrics: Performance metrics (accuracy, precision, recall, etc.)
            evaluation_data: Additional evaluation data
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'model_performance',
            'model_version': model_version,
            'metrics': metrics,
            'evaluation_data': evaluation_data
        }
        
        self.logger.info(json.dumps(log_data))
    
    def log_prediction_error(self, user_id, username, error, input_data=None):
        """
        Log prediction errors
        
        Args:
            user_id: User ID
            username: Username
            error: Error message or exception
            input_data: Input data that caused the error
        """
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'prediction_error',
            'user_id': user_id,
            'username': username,
            'error': str(error),
            'error_type': type(error).__name__,
            'input_data': input_data
        }
        
        self.logger.error(json.dumps(log_data))


# Global prediction logger instance
prediction_logger = PredictionLogger()


def log_prediction(user_id, username=None, input_data=None, result=None, 
                   model_version=None, processing_time_ms=None,
                   health_record_id=None, prediction_id=None):
    """
    Convenience function to log prediction events
    
    Args:
        user_id: User ID making the prediction
        username: Username making the prediction
        input_data: Input data for prediction
        result: Prediction result
        model_version: Version of the model used
        processing_time_ms: Processing time in milliseconds
        health_record_id: Associated health record ID
        prediction_id: Associated prediction ID
    """
    prediction_logger.log_prediction(
        user_id=user_id,
        username=username,
        input_data=input_data or {},
        result=result or {},
        model_version=model_version,
        processing_time_ms=processing_time_ms,
        health_record_id=health_record_id,
        prediction_id=prediction_id
    )


# ============================================================================
# Security Logging Functions
# ============================================================================

def log_security_event(event_type, user_id=None, username=None, ip_address=None, 
                       details=None, status='success', error_message=None):
    """
    Log security-related events
    
    Args:
        event_type: Type of security event (login, logout, failed_login, etc.)
        user_id: User ID involved in the event
        username: Username involved in the event
        ip_address: IP address of the request
        details: Additional details about the event
        status: Status of the event (success, failed, blocked)
        error_message: Error message if status is failed
    """
    logger = logging.getLogger('security')
    
    # Build log message
    timestamp = datetime.utcnow().isoformat()
    message_parts = [f"[{timestamp}] Security Event: {event_type}"]
    
    if user_id:
        message_parts.append(f"User ID: {user_id}")
    if username:
        message_parts.append(f"Username: {username}")
    if ip_address:
        message_parts.append(f"IP: {ip_address}")
    if status:
        message_parts.append(f"Status: {status.upper()}")
    if details:
        message_parts.append(f"Details: {details}")
    if error_message:
        message_parts.append(f"Error: {error_message}")
    
    message = " | ".join(message_parts)
    
    # Log at appropriate level
    if status == 'failed' or status == 'blocked':
        logger.warning(message)
    else:
        logger.info(message)


# ============================================================================
# API Logging Functions
# ============================================================================

def log_api_request(endpoint, method, user_id=None, username=None, 
                    status_code=None, duration_ms=None, ip_address=None):
    """
    Log API requests
    
    Args:
        endpoint: API endpoint
        method: HTTP method
        user_id: User ID making the request
        username: Username making the request
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        ip_address: Client IP address
    """
    logger = logging.getLogger('api')
    
    # Build log message
    message_parts = [f"API Request: {method} {endpoint}"]
    
    if user_id:
        message_parts.append(f"User ID: {user_id}")
    if username:
        message_parts.append(f"Username: {username}")
    if ip_address:
        message_parts.append(f"IP: {ip_address}")
    if status_code:
        message_parts.append(f"Status: {status_code}")
    if duration_ms:
        message_parts.append(f"Duration: {duration_ms}ms")
    
    message = " | ".join(message_parts)
    
    # Log at appropriate level based on status code
    if status_code and status_code >= 500:
        logger.error(message)
    elif status_code and status_code >= 400:
        logger.warning(message)
    else:
        logger.info(message)


def log_api_request_decorator(f):
    """
    Decorator to automatically log API requests
    
    Usage:
        @app.route('/api/endpoint')
        @log_api_request_decorator
        def my_endpoint():
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        start_time = time.time()
        
        try:
            response = f(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            # Get status code
            if isinstance(response, tuple):
                status_code = response[1] if len(response) > 1 else 200
            elif hasattr(response, 'status_code'):
                status_code = response.status_code
            else:
                status_code = 200
            
            # Log the request
            log_api_request(
                endpoint=request.path,
                method=request.method,
                user_id=getattr(request, 'user_id', None),
                username=getattr(request, 'username', None),
                status_code=status_code,
                duration_ms=duration_ms,
                ip_address=request.remote_addr
            )
            
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_api_request(
                endpoint=request.path,
                method=request.method,
                user_id=getattr(request, 'user_id', None),
                username=getattr(request, 'username', None),
                status_code=500,
                duration_ms=duration_ms,
                ip_address=request.remote_addr
            )
            raise
    
    return decorated


# ============================================================================
# Database Logging Functions
# ============================================================================

def log_database_operation(operation, table, record_id=None, user_id=None,
                           details=None, success=True, error=None):
    """
    Log database operations
    
    Args:
        operation: Type of operation (CREATE, READ, UPDATE, DELETE)
        table: Database table name
        record_id: Record ID (if applicable)
        user_id: User performing the operation
        details: Additional details
        success: Whether operation was successful
        error: Error message if operation failed
    """
    logger = logging.getLogger('database')
    
    # Build log message
    status = "SUCCESS" if success else "FAILED"
    message_parts = [f"DB Operation: {operation} on {table}", f"Status: {status}"]
    
    if record_id:
        message_parts.append(f"Record ID: {record_id}")
    if user_id:
        message_parts.append(f"User ID: {user_id}")
    if details:
        message_parts.append(f"Details: {details}")
    if error:
        message_parts.append(f"Error: {error}")
    
    message = " | ".join(message_parts)
    
    if success:
        logger.info(message)
    else:
        logger.error(message, exc_info=True)


# ============================================================================
# Error Logging Functions
# ============================================================================

def log_error(error, context=None, user_id=None, username=None):
    """
    Log error with full traceback
    
    Args:
        error: Exception object or error message
        context: Additional context about where the error occurred
        user_id: User ID associated with the error
        username: Username associated with the error
    """
    logger = logging.getLogger('error')
    
    message_parts = []
    
    if context:
        message_parts.append(f"Context: {context}")
    if user_id:
        message_parts.append(f"User ID: {user_id}")
    if username:
        message_parts.append(f"Username: {username}")
    
    message = " | ".join(message_parts) if message_parts else "Error occurred"
    
    if isinstance(error, Exception):
        logger.error(f"{message}\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}")
    else:
        logger.error(f"{message} | Error: {error}")


# ============================================================================
# System Logging Functions
# ============================================================================

def log_system_event(event_type, details=None, level='info'):
    """
    Log general system events
    
    Args:
        event_type: Type of system event (startup, shutdown, config_change, etc.)
        details: Additional details
        level: Log level (info, warning, error)
    """
    logger = logging.getLogger('system')
    
    message = f"System Event: {event_type}"
    if details:
        message += f" | Details: {details}"
    
    if level == 'error':
        logger.error(message)
    elif level == 'warning':
        logger.warning(message)
    else:
        logger.info(message)


# ============================================================================
# Example Usage and Test
# ============================================================================

if __name__ == '__main__':
    import sys
    
    # Configure logging
    configure_logging()
    
    print("=" * 60)
    print("Testing Logging Configuration")
    print("=" * 60)
    
    # Test different log types
    logger = get_logger(__name__)
    logger.info("System started successfully")
    
    # Test prediction logging
    print("\n📊 Testing Prediction Logging...")
    log_prediction(
        user_id=1,
        username='patient1',
        input_data={
            'glucose': 140,
            'bmi': 28.5,
            'age': 45,
            'blood_pressure': 120,
            'pregnancies': 2
        },
        result={
            'prediction_code': 1,
            'probability': 0.75,
            'probability_percent': 75.0,
            'risk_level': 'HIGH RISK',
            'risk_color': '🔴',
            'interpretation': 'High risk of diabetes detected',
            'recommendation': 'Consult a doctor immediately'
        },
        model_version='v2.0.1',
        processing_time_ms=125,
        health_record_id=42,
        prediction_id=123
    )
    
    # Test security logging
    print("\n🔒 Testing Security Logging...")
    log_security_event('login', user_id=1, username='admin', ip_address='127.0.0.1',
                       details='Successful login from web interface')
    log_security_event('failed_login', username='unknown', ip_address='192.168.1.100',
                       details='Invalid password', status='failed', error_message='Wrong password')
    
    # Test API logging
    print("\n🌐 Testing API Logging...")
    log_api_request('/api/patient/predict', 'POST', user_id=1, username='patient1',
                    status_code=200, duration_ms=145, ip_address='127.0.0.1')
    
    # Test database logging
    print("\n🗄️ Testing Database Logging...")
    log_database_operation('CREATE', 'predictions', record_id=42, user_id=1,
                          details='Prediction result stored', success=True)
    
    # Test error logging
    print("\n⚠️ Testing Error Logging...")
    try:
        result = 10 / 0
    except Exception as e:
        log_error(e, context='Division by zero in test', user_id=1)
    
    # Test batch prediction logging
    print("\n📦 Testing Batch Prediction Logging...")
    prediction_logger.log_batch_prediction(
        user_id=1,
        username='researcher',
        batch_size=100,
        results_summary={
            'high_risk': 25,
            'moderate_risk': 35,
            'low_risk': 40,
            'avg_confidence': 0.82
        },
        processing_time_ms=2345
    )
    
    # Test model performance logging
    print("\n🤖 Testing Model Performance Logging...")
    prediction_logger.log_model_performance(
        model_version='v2.0.1',
        metrics={
            'accuracy': 0.85,
            'precision': 0.82,
            'recall': 0.79,
            'f1_score': 0.80,
            'auc_roc': 0.91
        },
        evaluation_data={'test_samples': 500, 'validation_samples': 200}
    )
    
    print("\n" + "=" * 60)
    print("✅ Logging test completed. Check logs/ directory for output files:")
    print("   - logs/system.log (general logs)")
    print("   - logs/security.log (security events)")
    print("   - logs/prediction.log (prediction events)")
    print("   - logs/api.log (API requests)")
    print("   - logs/database.log (database operations)")
    print("   - logs/error.log (error logs)")
    print("=" * 60)