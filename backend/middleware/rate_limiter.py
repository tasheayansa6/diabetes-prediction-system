from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta
from collections import defaultdict
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# In-memory storage for rate limiting (use Redis in production)
request_counts = defaultdict(list)

def rate_limit(max_requests=100, window_seconds=60):
    """
    Rate limiting middleware
    
    Args:
        max_requests: Maximum number of requests allowed
        window_seconds: Time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier (IP address or user ID)
            client_id = request.remote_addr
            
            # Get current time
            now = datetime.now()
            
            # Clean old requests outside the window
            cutoff_time = now - timedelta(seconds=window_seconds)
            request_counts[client_id] = [
                req_time for req_time in request_counts[client_id]
                if req_time > cutoff_time
            ]
            
            # Check if limit exceeded
            if len(request_counts[client_id]) >= max_requests:
                logger.warning(f"Rate limit exceeded for {client_id}")
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {max_requests} requests per {window_seconds} seconds'
                }), 429
            
            # Add current request
            request_counts[client_id].append(now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def setup_rate_limiting(app):
    """
    Setup global rate limiting for the application.
    Uses per-user rate limiting when a token is present,
    falls back to per-IP for unauthenticated requests.
    """

    @app.before_request
    def check_rate_limit():
        # Skip rate limiting for health check and static files
        if request.path == '/health' or request.path.startswith('/static/'):
            return None

        # Use user_id from JWT as identifier when available (more accurate than IP)
        client_id = request.remote_addr  # default: IP
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            try:
                import jwt as _jwt
                payload = _jwt.decode(
                    auth[7:],
                    app.config['SECRET_KEY'],
                    algorithms=['HS256'],
                    options={'verify_exp': False}   # just read the user_id, don't re-validate
                )
                uid = payload.get('user_id')
                if uid:
                    client_id = 'user_' + str(uid)
            except Exception:
                pass

        now = datetime.now()

        # Global rate limit: 5000 requests per hour per user/IP
        cutoff_time = now - timedelta(hours=1)
        request_counts[client_id] = [
            req_time for req_time in request_counts[client_id]
            if req_time > cutoff_time
        ]

        if len(request_counts[client_id]) >= 5000:
            logger.warning(f"Global rate limit exceeded for {client_id}")
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.'
            }), 429

        request_counts[client_id].append(now)
        return None
