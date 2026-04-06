import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, jsonify

# Load .env file FIRST - before anything else
env_path = Path(__file__).parent.parent / '.env'
print(f"Loading .env from: {env_path}")
load_dotenv(dotenv_path=env_path)

from backend.config import config
from backend.extensions import db, migrate, login_manager, bcrypt, mail
from backend.utils.logger import configure_logging
from backend.middleware.error_handler import register_error_handlers
from backend.middleware.request_logger import setup_request_logging
from backend.middleware.security_middleware import setup_security_headers
from backend.middleware.cors_middleware import setup_cors_manually


# IMPORTANT: import models so Flask-Migrate detects them
import backend.models


def create_app(config_name="development"):
    app = Flask(__name__,
                template_folder='../frontend',
                static_folder='../frontend/static')

    # Load configuration
    app.config.from_object(config[config_name])
    
    # Apply static init_app if defined (e.g. WAL mode for SQLite)
    cfg = config[config_name]
    if hasattr(cfg, 'init_app'):
        cfg.init_app(app)
    
    # --- DEBUG DATABASE PATH ---
    # --- END DEBUG ---

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)

    # Configure logging
    configure_logging(app)

    # Setup middleware
    register_error_handlers(app)
    setup_request_logging(app)
    setup_security_headers(app)
    setup_cors_manually(app)

    # Register blueprints
    from backend.routes.auth_routes import auth_bp
    from backend.routes.patient_routes import patient_bp
    from backend.routes.admin_routes import admin_bp
    from backend.routes.doctor_routes import doctor_bp  
    from backend.routes.nurse_routes import nurse_bp
    from backend.routes.lab_routes import lab_bp
    from backend.routes.pharmacist_routes import pharmacist_bp  
    from backend.routes.payment_routes import payment_bp
    
    
    # Auth routes - prefix /api/auth
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    
    # Patient routes - already has /api/patient prefix in blueprint
    app.register_blueprint(patient_bp)
    
    # Admin routes - already has /api/admin prefix in blueprint
    app.register_blueprint(admin_bp)
    
    # Doctor routes - already has /api/doctor prefix in blueprint
    app.register_blueprint(doctor_bp)
    
    # Nurse routes - already has /api/nurse prefix in blueprint
    app.register_blueprint(nurse_bp)
    
    # Lab routes - already has /api/labs prefix in blueprint
    app.register_blueprint(lab_bp)
    
    # Pharmacist routes - already has /api/pharmacy prefix in blueprint
    app.register_blueprint(pharmacist_bp)  
    
    
    app.register_blueprint(payment_bp)

    # Health check route
    @app.route("/health")
    def health_check():
        return jsonify({"status": "healthy"}), 200

    # Public model info route (no auth required)
    @app.route("/api/model/info")
    def model_info():
        import json as _json
        from pathlib import Path
        project_root = Path(app.root_path).parent
        metadata_path = project_root / 'ml_model' / 'saved_models' / 'model_metadata.json'
        registry_path = project_root / 'ml_model' / 'model_registry.json'
        try:
            # Get active model from registry
            if registry_path.exists():
                registry = _json.load(open(registry_path))
                active = next((m for m in registry if m.get('status') == 'active'), registry[-1])
                return jsonify({
                    "success":   True,
                    "accuracy":  active['accuracy'] / 100,
                    "precision": active.get('precision', 0) / 100,
                    "recall":    active.get('recall', 0) / 100,
                    "f1":        active.get('f1Score', 0) / 100,
                    "algorithm": active.get('algorithm', 'Gradient Boosting'),
                    "version":   active.get('version', 'v2.0.0'),
                    "samples":   active.get('trainingSamples', 614),
                    "features":  active.get('features', 8),
                    "date":      active.get('date', '')
                }), 200
            # Fallback to metadata
            metadata = _json.load(open(metadata_path))
            best = max(
                ((k, v) for k, v in metadata.items() if isinstance(v, dict) and 'accuracy' in v),
                key=lambda x: x[1]['accuracy']
            )
            v = best[1]
            return jsonify({
                "success":  True,
                "accuracy": v['accuracy'],
                "precision":v.get('precision', 0),
                "recall":   v.get('recall', 0),
                "f1":       v.get('f1', 0),
                "algorithm":v.get('model_type', 'GradientBoostingClassifier'),
                "samples":  v.get('dataset_size', 614),
                "features": 8
            }), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    return app