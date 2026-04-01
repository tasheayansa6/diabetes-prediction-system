from flask import request, g
from functools import wraps
import time
from backend.utils.logger import get_logger, log_api_request

logger = get_logger(__name__)

def log_request(f):
    """
    Middleware to log incoming requests
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Start timer
        g.start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
        
        # Execute the route function
        response = f(*args, **kwargs)
        
        # Calculate duration
        duration = time.time() - g.start_time
        
        # Log response
        status_code = response[1] if isinstance(response, tuple) else 200
        logger.info(f"Response: {request.method} {request.path} - Status: {status_code} - Duration: {duration:.3f}s")
        
        return response
    return decorated_function

def setup_request_logging(app):
    """
    Setup request logging for all routes
    
    Args:
        app: Flask application instance
    """
    
    @app.before_request
    def before_request():
        g.start_time = time.time()
        logger.info(f"Incoming Request: {request.method} {request.path} from {request.remote_addr}")
    
    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            logger.info(
                f"Request Completed: {request.method} {request.path} - "
                f"Status: {response.status_code} - Duration: {duration:.3f}s"
            )
        return response
    
    @app.teardown_request
    def teardown_request(exception=None):
        if exception:
            logger.error(f"Request failed with exception: {exception}", exc_info=True)
