from flask_cors import CORS
import os

# Only allow the app's own origin + localhost for development
ALLOWED_ORIGINS = [
    'https://diabetes-prediction-system-n7ik.onrender.com',
    'http://localhost:5000',
    'http://127.0.0.1:5000',
]

def setup_cors(app):
    CORS(app, resources={
        r"/api/*": {
            "origins": ALLOWED_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
            "max_age": 3600
        }
    })
    return app

def setup_cors_manually(app):
    @app.after_request
    def after_request(response):
        origin = request_origin()
        # Only set CORS headers on /api/* routes, not on static files or HTML
        from flask import request as _req
        if _req.path.startswith('/api/'):
            if origin in ALLOWED_ORIGINS:
                response.headers['Access-Control-Allow-Origin'] = origin
            else:
                response.headers['Access-Control-Allow-Origin'] = \
                    ALLOWED_ORIGINS[0]  # default to production origin
            response.headers['Access-Control-Allow-Headers'] = \
                'Content-Type,Authorization,X-Requested-With'
            response.headers['Access-Control-Allow-Methods'] = \
                'GET,PUT,POST,DELETE,OPTIONS,PATCH'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '3600'
            response.headers['Vary'] = 'Origin'
        return response

    @app.before_request
    def handle_options():
        from flask import request as _req, Response
        if _req.method == 'OPTIONS' and _req.path.startswith('/api/'):
            origin = request_origin()
            res = Response()
            res.headers['Access-Control-Allow-Origin'] = \
                origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
            res.headers['Access-Control-Allow-Headers'] = \
                'Content-Type,Authorization,X-Requested-With'
            res.headers['Access-Control-Allow-Methods'] = \
                'GET,PUT,POST,DELETE,OPTIONS,PATCH'
            res.headers['Access-Control-Allow-Credentials'] = 'true'
            res.headers['Access-Control-Max-Age'] = '3600'
            res.headers['Vary'] = 'Origin'
            return res
    return app

def request_origin():
    from flask import request as _req
    return _req.headers.get('Origin', '')
