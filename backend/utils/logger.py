"""
Logging Configuration for Diabetes Prediction System

This module configures logging for different parts of the application:
- system.log: General application logs
- security.log: Security events (logins, failed attempts, etc.)
- prediction.log: ML prediction events
- api.log: API request logging
- database.log: Database operations
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import traceback


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
    log_level = logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter(log_format, date_format)
    
    def make_handler(filename, level):
        """Create a RotatingFileHandler, fall back to NullHandler if file is locked."""
        try:
            h = RotatingFileHandler(
                os.path.join(logs_dir, filename),
                maxBytes=10485760,
                backupCount=10,
                encoding='utf-8'
            )
            h.setLevel(level)
            h.setFormatter(formatter)
            return h
        except (PermissionError, OSError):
            h = logging.NullHandler()
            h.setLevel(level)
            return h

    system_handler     = make_handler('system.log',     log_level)
    security_handler   = make_handler('security.log',   logging.WARNING)
    prediction_handler = make_handler('prediction.log', log_level)
    api_handler        = make_handler('api.log',        log_level)
    database_handler   = make_handler('database.log',   log_level)
    error_handler      = make_handler('error.log',      logging.ERROR)
    
    # Console handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if os.getenv('FLASK_ENV') == 'development' else logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Configure root logger — console_handler only here, everything propagates up
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    if not root_logger.handlers:  # avoid adding duplicate handlers on reload
        root_logger.addHandler(system_handler)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(error_handler)
    
    # Configure specific loggers — file handlers only, propagate=False to avoid double console output
    loggers = {
        'security': security_handler,
        'prediction': prediction_handler,
        'api': api_handler,
        'database': database_handler
    }
    
    for logger_name, handler in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(log_level)
        if not logger.handlers:
            logger.addHandler(handler)
        logger.propagate = False
    
    # Configure Flask app logger if provided
    if app:
        app.logger.propagate = False
        app.logger.setLevel(log_level)
        if not app.logger.handlers:
            app.logger.addHandler(system_handler)
            app.logger.addHandler(console_handler)
        
        # werkzeug — file only, no extra console handler
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.propagate = False
        if not werkzeug_logger.handlers:
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


def log_prediction(user_id, username=None, input_data=None, result=None, 
                   model_version=None, processing_time_ms=None):
    """
    Log prediction events
    
    Args:
        user_id: User ID making the prediction
        username: Username making the prediction
        input_data: Input data for prediction
        result: Prediction result
        model_version: Version of the model used
        processing_time_ms: Processing time in milliseconds
    """
    logger = logging.getLogger('prediction')
    
    if result is None:
        result = {}
    
    # Build log message
    message_parts = [f"Prediction | User ID: {user_id}"]
    
    if username:
        message_parts.append(f"Username: {username}")
    if result.get('prediction') is not None:
        message_parts.append(f"Result: {result.get('prediction')}")
        message_parts.append(f"Probability: {result.get('probability', 0):.4f}")
        message_parts.append(f"Risk Level: {result.get('risk_level', 'UNKNOWN')}")
    if model_version:
        message_parts.append(f"Model Version: {model_version}")
    if processing_time_ms:
        message_parts.append(f"Processing Time: {processing_time_ms}ms")
    if input_data:
        # Log key features only to avoid huge logs
        key_features = ['glucose', 'bmi', 'age', 'blood_pressure']
        filtered_data = {k: v for k, v in input_data.items() if k in key_features}
        message_parts.append(f"Key Features: {filtered_data}")
    
    message = " | ".join(message_parts)
    logger.info(message)


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


def log_error(error, context=None, user_id=None):
    """
    Log error with full traceback
    
    Args:
        error: Exception object or error message
        context: Additional context about where the error occurred
        user_id: User ID associated with the error
    """
    logger = logging.getLogger('error')
    
    message_parts = []
    
    if context:
        message_parts.append(f"Context: {context}")
    if user_id:
        message_parts.append(f"User ID: {user_id}")
    
    message = " | ".join(message_parts) if message_parts else "Error occurred"
    
    if isinstance(error, Exception):
        logger.error(f"{message}\n{''.join(traceback.format_exception(type(error), error, error.__traceback__))}")
    else:
        logger.error(f"{message} | Error: {error}")


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


# Example usage and test
if __name__ == '__main__':
    # Configure logging
    configure_logging()
    
    print("=" * 60)
    print("Testing Logging Configuration")
    print("=" * 60)
    
    # Test different log types
    logger = get_logger(__name__)
    logger.info("System started successfully")
    
    # Security events
    log_security_event('login', user_id=1, username='admin', ip_address='127.0.0.1', 
                       details='Successful login from web interface')
    log_security_event('failed_login', user_id=None, username='unknown', ip_address='192.168.1.100',
                       details='Invalid password', status='failed', error_message='Wrong password')
    
    # Prediction events
    log_prediction(
        user_id=1,
        username='patient1',
        input_data={'glucose': 140, 'bmi': 28.5, 'age': 45, 'blood_pressure': 120},
        result={'prediction': 1, 'probability': 0.75, 'risk_level': 'HIGH RISK'},
        model_version='v2.0.1',
        processing_time_ms=125
    )
    
    # API requests
    log_api_request('/api/patient/predict', 'POST', user_id=1, username='patient1',
                    status_code=200, duration_ms=145, ip_address='127.0.0.1')
    log_api_request('/api/patient/predict', 'POST', user_id=1, username='patient1',
                    status_code=400, duration_ms=12, ip_address='127.0.0.1')
    
    # Database operations
    log_database_operation('CREATE', 'predictions', record_id=42, user_id=1,
                          details='Prediction result stored', success=True)
    log_database_operation('UPDATE', 'users', record_id=5, user_id=2,
                          details='Updated user profile', success=True)
    
    # System events
    log_system_event('startup', details='Diabetes Prediction System v1.0.0')
    log_system_event('config_change', details='Log level changed to DEBUG', level='warning')
    
    # Error logging
    try:
        result = 10 / 0
    except Exception as e:
        log_error(e, context='Division by zero in test', user_id=1)
    
    print("\n✅ Logging test completed. Check logs/ directory for output files:")
    print("   - logs/system.log (general logs)")
    print("   - logs/security.log (security events)")
    print("   - logs/prediction.log (prediction events)")
    print("   - logs/api.log (API requests)")
    print("   - logs/database.log (database operations)")
    print("   - logs/error.log (error logs)")