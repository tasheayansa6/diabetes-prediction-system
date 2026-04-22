import os
from pathlib import Path
import sqlite3 as _sqlite3


def _make_sqlite_wal_connection():
    """Create a SQLite connection with WAL mode enabled.
    WAL allows concurrent reads + one writer, preventing 'database is locked' errors
    under Gunicorn multi-worker deployments."""
    db_path = os.getenv('DATABASE_URL', '').replace('sqlite:///', '') or \
        str(Path(__file__).parent.parent / 'database' / 'diabetes.db')
    conn = _sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=-64000')  # 64MB cache
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

class BaseConfig:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    REMEMBER_COOKIE_HTTPONLY = True
    PREFERRED_URL_SCHEME = os.getenv('PREFERRED_URL_SCHEME', 'https')
    # JWT expiry: 24h in dev, override with JWT_EXPIRY_SECONDS env var
    JWT_EXPIRY_SECONDS = int(os.getenv('JWT_EXPIRY_SECONDS', '86400'))
    # Never expose internal error details to clients
    EXPOSE_ERRORS = os.getenv('FLASK_ENV', 'development') == 'development'
    # Flask-Mail
    MAIL_SERVER = os.getenv('SMTP_SERVER', os.getenv('MAIL_SERVER', 'smtp.gmail.com'))
    MAIL_PORT = int(os.getenv('SMTP_PORT', os.getenv('MAIL_PORT', 587)))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv('SMTP_USERNAME', os.getenv('MAIL_USERNAME'))
    MAIL_PASSWORD = os.getenv('SMTP_PASSWORD', os.getenv('MAIL_PASSWORD'))
    MAIL_DEFAULT_SENDER = os.getenv('SMTP_USERNAME', os.getenv('MAIL_USERNAME'))
    MAIL_SUPPRESS_SEND = os.getenv('MAIL_SUPPRESS_SEND', 'True').lower() == 'true'
    # Password reset token expiry (seconds)
    RESET_TOKEN_EXPIRY = 3600  # 1 hour
    OTP_EXPIRY = 900           # 15 minutes
    # Chapa Payment Gateway
    CHAPA_SECRET_KEY = os.getenv('CHAPA_SECRET_KEY', '')
    CHAPA_PUBLIC_KEY = os.getenv('CHAPA_PUBLIC_KEY', '')
    CHAPA_WEBHOOK_SECRET = os.getenv('CHAPA_WEBHOOK_SECRET', '')
    CHAPA_BASE_URL = os.getenv('CHAPA_BASE_URL', 'https://api.chapa.co/v1')
    CHAPA_CALLBACK_URL = os.getenv('CHAPA_CALLBACK_URL', 'http://localhost:5000/api/payments/chapa/verify')
    CHAPA_RETURN_URL = os.getenv('CHAPA_RETURN_URL', 'http://localhost:5000/templates/payment/payment_success.html')
    # Security hardening: public signup must not create admin accounts by default.
    ALLOW_ADMIN_SIGNUP = os.getenv('ALLOW_ADMIN_SIGNUP', 'False').lower() == 'true'
    # Optional hard lock: only this email can login as admin.
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', '').strip().lower()

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    _db_path = Path(__file__).parent.parent / 'database' / 'diabetes.db'
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f'sqlite:///{_db_path.as_posix()}'
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'timeout': 30, 'check_same_thread': False},
        'pool_pre_ping': True,
        'pool_size': 1,
        'max_overflow': 0,
        'creator': _make_sqlite_wal_connection,
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
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'max_overflow': 10,
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'pool_timeout': 30,
    }
    # Session timeout: 30 minutes of inactivity
    PERMANENT_SESSION_LIFETIME = 1800
    JWT_EXPIRY_SECONDS = int(os.getenv('JWT_EXPIRY_SECONDS', '1800'))
    PROPAGATE_EXCEPTIONS = False
    EXPOSE_ERRORS = False

    # PostgreSQL specific settings
    POSTGRES_SSL_MODE = os.getenv('POSTGRES_SSL_MODE', 'require')
    POSTGRES_SSL_CERT = os.getenv('POSTGRES_SSL_CERT')
    POSTGRES_SSL_KEY = os.getenv('POSTGRES_SSL_KEY')
    POSTGRES_SSL_CA = os.getenv('POSTGRES_SSL_CA')

    @staticmethod
    def init_app(app):
        # Enforce secure defaults in production.
        app.config['SESSION_COOKIE_SECURE'] = True
        secret = app.config.get('SECRET_KEY') or ''
        if secret in ['', 'dev-secret-key', 'your-secret-key-change-this-in-production']:
            raise RuntimeError('Unsafe SECRET_KEY for production. Set a strong SECRET_KEY in environment.')

        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI') or ''
        if not db_uri:
            raise RuntimeError('DATABASE_URL is required in production.')

        # HTTPS redirect enforcement
        from flask import request as _req, redirect
        @app.before_request
        def _enforce_https():
            if not _req.is_secure and _req.headers.get('X-Forwarded-Proto', 'http') != 'https':
                if _req.url.startswith('http://'):
                    return redirect(_req.url.replace('http://', 'https://', 1), code=301)

        # If using sqlite in production-like environments (e.g. Render free tier),
        # normalize to an absolute writable path and apply sqlite-safe engine options.
        if db_uri.startswith('sqlite:///'):
            sqlite_path = db_uri.replace('sqlite:///', '', 1)
            db_file = Path(sqlite_path) if Path(sqlite_path).is_absolute() else (Path(app.root_path).parent / sqlite_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_file.as_posix()}"
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'connect_args': {'check_same_thread': False, 'timeout': 30},
                'pool_pre_ping': True,
                'creator': _make_sqlite_wal_connection,
            }
class PostgreSQLConfig(BaseConfig):
    """PostgreSQL-specific configuration for production"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'POSTGRES_URL',
        'postgresql://username:password@localhost:5432/diabetes_db'
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'max_overflow': 30,
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_timeout': 30,
        'connect_args': {
            'sslmode': os.getenv('POSTGRES_SSL_MODE', 'require'),
            'sslcert': os.getenv('POSTGRES_SSL_CERT'),
            'sslkey': os.getenv('POSTGRES_SSL_KEY'),
            'sslrootcert': os.getenv('POSTGRES_SSL_CA'),
            'application_name': 'diabetes_prediction_system',
            'connect_timeout': 30,
        }
    }
    
    # Connection pooling settings
    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '20'))
    DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '30'))
    DB_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))
    DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))
    
    # Performance settings
    DB_STATEMENT_TIMEOUT = int(os.getenv('DB_STATEMENT_TIMEOUT', '30000'))  # 30 seconds
    DB_IDLE_IN_TRANSACTION_TIMEOUT = int(os.getenv('DB_IDLE_IN_TRANSACTION_TIMEOUT', '60000'))  # 1 minute

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'postgresql': PostgreSQLConfig
}