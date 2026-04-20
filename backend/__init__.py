import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, jsonify, request

# Load .env file FIRST - before anything else
env_path = Path(__file__).parent.parent / '.env'
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

    # Render SQLite bootstrap: ensure tables exist on first boot.
    # This avoids registration/login 500s when /tmp sqlite starts empty.
    if str(app.config.get('SQLALCHEMY_DATABASE_URI', '')).startswith('sqlite:///'):
        try:
            with app.app_context():
                db.create_all()
        except Exception as e:
            app.logger.warning(f"SQLite bootstrap skipped: {e}")

    # Configure logging
    configure_logging(app)

    # Setup middleware
    register_error_handlers(app)
    setup_request_logging(app)
    setup_security_headers(app)
    setup_cors_manually(app)

    # Global free-text sanitization for POST/PUT requests
    from backend.middleware.security_middleware import strip_html
    FREE_TEXT_FIELDS = ['notes', 'remarks', 'description', 'reason', 'instructions',
                        'content', 'message', 'observations', 'clinical_notes']

    @app.before_request
    def sanitize_request_body():
        if request.method in ('POST', 'PUT', 'PATCH') and request.is_json:
            try:
                data = request.get_json(silent=True)
                if data and isinstance(data, dict):
                    for field in FREE_TEXT_FIELDS:
                        if field in data and isinstance(data[field], str):
                            data[field] = strip_html(data[field])
            except Exception:
                pass

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

    # Auto-create default admin on first run if no admin exists
    with app.app_context():
        try:
            from backend.models.user import User
            from backend.utils.role_accounts import create_polymorphic_user
            from werkzeug.security import generate_password_hash, check_password_hash

            default_email    = os.getenv('ADMIN_BOOTSTRAP_EMAIL',    'admin@system.com')
            default_password = os.getenv('ADMIN_BOOTSTRAP_PASSWORD', 'Admin@1234')
            default_username = os.getenv('ADMIN_BOOTSTRAP_USERNAME', 'admin')

            existing = User.query.filter_by(email=default_email).first()
            if not existing:
                data = {'username': default_username, 'email': default_email}
                user = create_polymorphic_user(data, generate_password_hash(default_password), 'admin')
                db.session.add(user)
                db.session.commit()
                print(f"[BOOTSTRAP] Admin created: {default_email} / {default_password}")
            else:
                if not check_password_hash(existing.password_hash, default_password):
                    existing.password_hash = generate_password_hash(default_password)
                    existing.is_active = True
                    db.session.commit()
                    print(f"[BOOTSTRAP] Admin password synced: {default_email}")
        except Exception as e:
            app.logger.warning(f"SQLite bootstrap skipped: {e}")

    # Force ML model reload (fixes startup load failures)
    @app.route("/api/ml/reload", methods=["POST"])
    def reload_ml_model():
        try:
            from backend.services.ml_service import get_ml_service
            ml = get_ml_service(force_reload=True)
            if ml.is_ready():
                return jsonify({"success": True, "message": f"Model reloaded: {type(ml.model).__name__}"}), 200
            else:
                return jsonify({"success": False, "message": "Model reload failed"}), 500
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

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

    # Public model statistics endpoint (dataset size + all registered models)
    @app.route("/api/model/stats")
    def model_stats():
        import json as _json
        from pathlib import Path
        project_root = Path(app.root_path).parent
        metadata_path = project_root / 'ml_model' / 'saved_models' / 'model_metadata.json'
        registry_path = project_root / 'ml_model' / 'model_registry.json'
        try:
            models = []
            active = None
            if registry_path.exists():
                models = _json.load(open(registry_path))
                active = next((m for m in models if m.get('status') == 'active'), None)

            training_samples = None
            test_samples = None
            total_samples = None
            if metadata_path.exists():
                md = _json.load(open(metadata_path))
                training_samples = md.get('training_samples')
                test_samples = md.get('test_samples')
                if training_samples is not None and test_samples is not None:
                    total_samples = training_samples + test_samples

            # Fallback to registry training sample count if metadata is missing
            if total_samples is None and active and active.get('trainingSamples') is not None:
                total_samples = int(active.get('trainingSamples'))

            return jsonify({
                "success": True,
                "active_model": active,
                "models": models,
                "dataset": {
                    "training_samples": training_samples,
                    "test_samples": test_samples,
                    "total_samples": total_samples
                }
            }), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    return app