from flask import jsonify
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from backend.utils.logger import get_logger

logger = get_logger(__name__)

def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        logger.warning(f"Bad Request: {error}")
        return jsonify({
            'error': 'Bad Request',
            'message': str(error)
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        logger.warning(f"Unauthorized: {error}")
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        logger.warning(f"Forbidden: {error}")
        return jsonify({
            'error': 'Forbidden',
            'message': 'Insufficient permissions'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        logger.warning(f"Not Found: {error}")
        return jsonify({
            'error': 'Not Found',
            'message': 'Resource not found'
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        logger.warning(f"Method Not Allowed: {error}")
        return jsonify({
            'error': 'Method Not Allowed',
            'message': 'The method is not allowed for the requested URL'
        }), 405
    
    @app.errorhandler(500)
    def internal_server_error(error):
        logger.error(f"Internal Server Error: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500
    
    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(error):
        logger.error(f"Database Error: {error}")
        return jsonify({
            'error': 'Database Error',
            'message': 'A database error occurred'
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        logger.warning(f"HTTP Exception: {error}")
        return jsonify({
            'error': error.name,
            'message': error.description
        }), error.code
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        logger.error(f"Unhandled Exception: {error}", exc_info=True)
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500
