"""
API Documentation with Flasgger (Swagger/OpenAPI)
Provides interactive API documentation for the Diabetes Prediction System.
"""

from flasgger import Swagger, swag_from
from flask import Blueprint, jsonify, request

# Initialize Swagger
def init_swagger(app):
    """Initialize Swagger documentation for the Flask app."""
    
    app.config['SWAGGER'] = {
        'title': 'Diabetes Prediction System API',
        'uiversion': 3,
        'version': '2.0.0',
        'description': '''
            ## Overview
            A comprehensive healthcare platform for diabetes prediction and patient management.
            
            ## Authentication
            Most endpoints require a JWT token in the Authorization header:
            ```
            Authorization: Bearer <your_token>
            ```
            
            ## Base URL
            - Development: http://localhost:5000/api
            - Production: https://your-domain.com/api
        ''',
        'contact': {
            'name': 'Support',
            'email': 'support@diabetes-prediction.com'
        },
        'security': [{
            'BearerAuth': []
        }],
        'specs': [
            {
                'endpoint': 'apispec_1',
                'route': '/apispec_1.json',
                'rule_filter': lambda rule: True,
                'model_filter': lambda tag: True,
            }
        ],
        'static_url_path': '/flasgger_static',
        'swagger_ui': True,
        'specs_route': '/api/docs'
    }
    
    # Security definitions
    app.config['SWAGGER']['security_definitions'] = {
        'BearerAuth': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header',
            'description': 'JWT token obtained from /api/auth/login'
        }
    }
    
    Swagger(app)


# Create a blueprint for API documentation
api_docs_bp = Blueprint('api_docs', __name__, url_prefix='/api/docs')


@api_docs_bp.route('/')
def docs_redirect():
    """Redirect to Swagger UI."""
    return jsonify({
        'message': 'API Documentation',
        'swagger_ui': '/apidocs/',
        'api_spec': '/apispec_1.json',
        'endpoints': {
            'auth': '/api/auth',
            'patient': '/api/patient',
            'doctor': '/api/doctor',
            'nurse': '/api/nurse',
            'lab': '/api/labs',
            'pharmacy': '/api/pharmacy',
            'admin': '/api/admin',
            'payments': '/api/payments'
        }
    })


# Sample endpoint documentation examples
@api_docs_bp.route('/example/predict', methods=['POST'])
@swag_from({
    'tags': ['Prediction'],
    'summary': 'Predict diabetes risk',
    'description': '''
        Analyzes patient health data and returns diabetes risk assessment.
        
        ## Required Features
        - **Glucose**: Blood glucose level (mg/dL)
        - **BMI**: Body Mass Index
        - **Age**: Patient age in years
        - **BloodPressure**: Blood pressure (mm Hg)
        
        ## Optional Features
        - Pregnancies, SkinThickness, Insulin, DiabetesPedigreeFunction
    ''',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['glucose', 'bmi', 'age'],
                'properties': {
                    'glucose': {
                        'type': 'number',
                        'description': 'Blood glucose level in mg/dL',
                        'minimum': 1,
                        'maximum': 600,
                        'example': 120
                    },
                    'bmi': {
                        'type': 'number',
                        'description': 'Body Mass Index',
                        'minimum': 1,
                        'maximum': 100,
                        'example': 25.5
                    },
                    'age': {
                        'type': 'number',
                        'description': 'Patient age in years',
                        'minimum': 1,
                        'maximum': 120,
                        'example': 35
                    },
                    'blood_pressure': {
                        'type': 'number',
                        'description': 'Blood pressure in mm Hg',
                        'minimum': 1,
                        'maximum': 300,
                        'example': 80
                    },
                    'pregnancies': {
                        'type': 'number',
                        'description': 'Number of pregnancies',
                        'minimum': 0,
                        'example': 2
                    }
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Prediction successful',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'prediction': {'type': 'string', 'enum': ['Diabetic', 'Non-Diabetic']},
                    'probability': {'type': 'number', 'description': 'Probability of diabetes (0-1)'},
                    'risk_level': {'type': 'string', 'enum': ['LOW RISK', 'MODERATE RISK', 'HIGH RISK', 'VERY HIGH RISK']},
                    'risk_color': {'type': 'string', 'enum': ['green', 'yellow', 'orange', 'red']},
                    'confidence': {'type': 'number', 'description': 'Model confidence percentage'}
                }
            }
        },
        400: {'description': 'Invalid input'},
        500: {'description': 'Prediction failed'}
    },
    'security': []  # No auth required for prediction
})
def predict_example():
    """Example prediction endpoint documentation."""
    return jsonify({
        'success': True,
        'prediction': 'Non-Diabetic',
        'probability': 0.15,
        'probability_percent': 15.0,
        'risk_level': 'LOW RISK',
        'risk_color': 'green',
        'confidence': 92.5,
        'interpretation': 'Very unlikely to have diabetes',
        'recommendation': 'Regular checkups every 2-3 years'
    })


@api_docs_bp.route('/example/auth/login', methods=['POST'])
@swag_from({
    'tags': ['Authentication'],
    'summary': 'User login',
    'description': 'Authenticate user and return JWT token.',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['email', 'password'],
                'properties': {
                    'email': {
                        'type': 'string',
                        'format': 'email',
                        'description': 'User email address',
                        'example': 'patient@example.com'
                    },
                    'password': {
                        'type': 'string',
                        'format': 'password',
                        'description': 'User password',
                        'example': 'SecurePass123'
                    },
                    'role': {
                        'type': 'string',
                        'enum': ['patient', 'doctor', 'nurse', 'lab_technician', 'pharmacist', 'admin'],
                        'description': 'Optional role validation'
                    }
                }
            }
        }
    ],
    'responses': {
        200: {
            'description': 'Login successful',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'token': {'type': 'string', 'description': 'JWT token for authentication'},
                    'user': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'username': {'type': 'string'},
                            'email': {'type': 'string'},
                            'role': {'type': 'string'},
                            'email_verified': {'type': 'boolean'}
                        }
                    }
                }
            }
        },
        401: {'description': 'Invalid credentials'},
        403: {'description': 'Account deactivated or requires email verification'}
    },
    'security': []
})
def login_example():
    """Example login endpoint documentation."""
    return jsonify({
        'success': True,
        'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        'user': {
            'id': 1,
            'username': 'john_doe',
            'email': 'john@example.com',
            'role': 'patient',
            'email_verified': True
        }
    })


@api_docs_bp.route('/example/patient/health-records', methods=['GET'])
@swag_from({
    'tags': ['Patient'],
    'summary': 'Get patient health records',
    'description': 'Retrieve health records for the authenticated patient.',
    'parameters': [
        {
            'name': 'Authorization',
            'in': 'header',
            'type': 'string',
            'required': True,
            'description': 'JWT token (Bearer <token>)'
        },
        {
            'name': 'limit',
            'in': 'query',
            'type': 'integer',
            'default': 10,
            'description': 'Number of records to return'
        },
        {
            'name': 'offset',
            'in': 'query',
            'type': 'integer',
            'default': 0,
            'description': 'Pagination offset'
        }
    ],
    'responses': {
        200: {
            'description': 'Health records retrieved successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'records': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'integer'},
                                'date': {'type': 'string', 'format': 'date-time'},
                                'weight': {'type': 'number'},
                                'height': {'type': 'number'},
                                'blood_pressure': {'type': 'string'},
                                'notes': {'type': 'string'}
                            }
                        }
                    },
                    'pagination': {
                        'type': 'object',
                        'properties': {
                            'total': {'type': 'integer'},
                            'limit': {'type': 'integer'},
                            'offset': {'type': 'integer'},
                            'has_more': {'type': 'boolean'}
                        }
                    }
                }
            }
        },
        401: {'description': 'Authentication required'},
        404: {'description': 'No records found'}
    }
})
def health_records_example():
    """Example health records endpoint documentation."""
    return jsonify({
        'success': True,
        'records': [
            {
                'id': 1,
                'date': '2026-04-28T10:30:00Z',
                'weight': 70.5,
                'height': 175,
                'blood_pressure': '120/80',
                'notes': 'Normal vitals'
            }
        ],
        'pagination': {
            'total': 1,
            'limit': 10,
            'offset': 0,
            'has_more': False
        }
    })