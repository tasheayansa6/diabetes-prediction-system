from flask import request, jsonify
from functools import wraps
from backend.utils.logger import get_logger
import re

logger = get_logger(__name__)

APP_ORIGIN = 'https://diabetes-prediction-system-n7ik.onrender.com'

def strip_html(text):
    """Remove HTML tags and dangerous characters from free-text input."""
    if not text or not isinstance(text, str):
        return text
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'javascript\s*:', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'on\w+\s*=', '', clean, flags=re.IGNORECASE)
    return clean.strip()

def sanitize_free_text_fields(data: dict, fields: list) -> dict:
    if not data:
        return data
    for field in fields:
        if field in data and isinstance(data[field], str):
            data[field] = strip_html(data[field])
    return data

def setup_security_headers(app):
    @app.after_request
    def add_security_headers(response):
        import os
        is_prod = (
            os.getenv('FLASK_ENV', 'development') == 'production'
            or app.config.get('ENV') == 'production'
            or not app.config.get('DEBUG', True)
        )

        # ── HTTPS redirect (fix #1) ───────────────────────────────────────────
        if is_prod and request.headers.get('X-Forwarded-Proto', 'https') == 'http':
            from flask import redirect
            return redirect(request.url.replace('http://', 'https://'), code=301)

        # ── Clickjacking protection ───────────────────────────────────────────
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'

        # ── MIME sniffing protection ──────────────────────────────────────────
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # ── XSS protection (legacy browsers) ─────────────────────────────────
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # ── HSTS — force HTTPS for 1 year ─────────────────────────────────────
        if is_prod:
            response.headers['Strict-Transport-Security'] = \
                'max-age=31536000; includeSubDomains; preload'

        # ── Content Security Policy (fix #3) ─────────────────────────────────
        # Allow same-origin + WebSocket for SocketIO + Chapa payment gateway
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self' https://api.chapa.co wss://diabetes-prediction-system-n7ik.onrender.com ws://localhost:5000; "
            "frame-src https://checkout.chapa.co; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers['Content-Security-Policy'] = csp

        # ── Cache-Control (fixes issues 71-87) ────────────────────────────────
        # HTML pages: never cache (contain auth-sensitive content)
        # Static assets: cache for 1 day
        content_type = response.content_type or ''
        path = request.path
        if 'text/html' in content_type or path.endswith('.html') or \
                path in ('/', '/login', '/register', '/forgot-password',
                         '/reset-password', '/verify-email'):
            response.headers['Cache-Control'] = \
                'no-cache, no-store, must-revalidate, private'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        elif any(path.endswith(ext) for ext in
                 ('.js', '.css', '.png', '.jpg', '.jpeg', '.gif',
                  '.ico', '.woff', '.woff2', '.ttf', '.svg')):
            response.headers['Cache-Control'] = 'public, max-age=86400'

        # ── Referrer policy ───────────────────────────────────────────────────
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # ── Permissions policy ────────────────────────────────────────────────
        response.headers['Permissions-Policy'] = \
            'geolocation=(), microphone=(), camera=()'

        return response

    return app

def sanitize_input(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function
