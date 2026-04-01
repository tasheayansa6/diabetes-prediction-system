import os
from pathlib import Path

class BaseConfig:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Flask-Mail
    MAIL_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('SMTP_PORT', 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('SMTP_USERNAME')
    MAIL_PASSWORD = os.getenv('SMTP_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('SMTP_USERNAME')
    MAIL_SUPPRESS_SEND = os.getenv('MAIL_SUPPRESS_SEND', 'False').lower() == 'true'
    # Password reset token expiry (seconds)
    RESET_TOKEN_EXPIRY = 3600  # 1 hour
    OTP_EXPIRY = 900           # 15 minutes
    # Chapa Payment Gateway
    CHAPA_SECRET_KEY = os.getenv('CHAPA_SECRET_KEY', '')
    CHAPA_PUBLIC_KEY = os.getenv('CHAPA_PUBLIC_KEY', '')
    CHAPA_BASE_URL = 'https://api.chapa.co/v1'

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'sqlite:///C:/Users/tashe/diabetes-prediction-system/database/diabetes.db'
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'timeout': 30, 'check_same_thread': False},
        'pool_pre_ping': True,
        'pool_size': 1,
        'max_overflow': 0,
    }

    @staticmethod
    def init_app(app):
        pass
    
    # ML Model paths
    PROJECT_ROOT = Path(__file__).parent.parent
    ML_MODEL_PATH = str(PROJECT_ROOT / 'ml_model' / 'saved_models' / 'logistic_regression.pkl')
    SCALER_PATH = str(PROJECT_ROOT / 'ml_model' / 'saved_models' / 'scaler.pkl')

class TestingConfig(BaseConfig):
    """Configuration for testing environment"""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # Use in-memory database for tests
    
    # ML Model paths (can be same as development or mock paths)
    PROJECT_ROOT = Path(__file__).parent.parent
    ML_MODEL_PATH = str(PROJECT_ROOT / 'ml_model' / 'saved_models' / 'logistic_regression.pkl')
    SCALER_PATH = str(PROJECT_ROOT / 'ml_model' / 'saved_models' / 'scaler.pkl')

class ProductionConfig(BaseConfig):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,  # Add this line
    'production': ProductionConfig
}