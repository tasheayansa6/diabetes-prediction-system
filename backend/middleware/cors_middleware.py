from flask_cors import CORS

def setup_cors(app):
  
    
    # Configure CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:5000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
            "max_age": 3600
        }
    })
    
    return app

def setup_cors_manually(app):
    @app.after_request
    def after_request(response):
        response.headers['Access-Control-Allow-Origin']      = '*'
        response.headers['Access-Control-Allow-Headers']     = 'Content-Type,Authorization,X-Requested-With'
        response.headers['Access-Control-Allow-Methods']     = 'GET,PUT,POST,DELETE,OPTIONS,PATCH'
        response.headers['Access-Control-Max-Age']           = '3600'
        return response

    @app.before_request
    def handle_options():
        from flask import request, Response
        if request.method == 'OPTIONS':
            res = Response()
            res.headers['Access-Control-Allow-Origin']  = '*'
            res.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With'
            res.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS,PATCH'
            res.headers['Access-Control-Max-Age']       = '3600'
            return res
    return app
