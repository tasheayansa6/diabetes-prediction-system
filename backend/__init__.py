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


def _repair_sqlite_polymorphic_user_integrity(app):
    """
    Keep users + role tables consistent for SQLite deployments.

    Some maintenance scripts can delete rows from `users` without deleting
    corresponding joined-table inheritance rows (doctors, nurses, ...), which
    later causes UNIQUE collisions when new users reuse those ids.
    """
    role_tables = [
        'patients',
        'doctors',
        'nurses',
        'lab_technicians',
        'pharmacists',
        'admins',
    ]

    try:
        from sqlalchemy import text

        # 1) Remove role rows that no longer have a parent user.
        for table in role_tables:
            db.session.execute(text(
                f"DELETE FROM {table} "
                "WHERE id NOT IN (SELECT id FROM users)"
            ))

        # 2) Ensure next users.id is above every role-table id.
        max_ids = []
        for table in ['users', *role_tables]:
            row = db.session.execute(text(f"SELECT COALESCE(MAX(id), 0) AS max_id FROM {table}")).fetchone()
            max_ids.append(int(row.max_id if row and row.max_id is not None else 0))

        target_seq = max(max_ids) if max_ids else 0
        if target_seq > 0:
            updated = db.session.execute(
                text("UPDATE sqlite_sequence SET seq = :seq WHERE name = 'users'"),
                {'seq': target_seq}
            )
            if getattr(updated, 'rowcount', 0) == 0:
                db.session.execute(
                    text("INSERT INTO sqlite_sequence(name, seq) VALUES ('users', :seq)"),
                    {'seq': target_seq}
                )

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.warning(f"SQLite user-role integrity repair skipped: {e}")


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

    # Create all tables (works for both SQLite and PostgreSQL)
    try:
        with app.app_context():
            db.create_all()
            # PostgreSQL: widen VARCHAR columns that were too small
            # (db.create_all does NOT alter existing columns)
            db_uri = str(app.config.get('SQLALCHEMY_DATABASE_URI', ''))
            if db_uri.startswith('postgresql'):
                try:
                    from sqlalchemy import text as _text
                    with db.engine.connect() as conn:
                        # Widen all _id VARCHAR columns that may be too small
                        alter_stmts = [
                            "ALTER TABLE lab_tests ALTER COLUMN test_id TYPE VARCHAR(50)",
                            "ALTER TABLE notes ALTER COLUMN note_id TYPE VARCHAR(50)",
                            "ALTER TABLE prescriptions ALTER COLUMN prescription_id TYPE VARCHAR(50)",
                            "ALTER TABLE payments ALTER COLUMN payment_id TYPE VARCHAR(50)",
                            "ALTER TABLE payments ALTER COLUMN transaction_id TYPE VARCHAR(100)",
                            "ALTER TABLE invoices ALTER COLUMN invoice_id TYPE VARCHAR(50)",
                            "ALTER TABLE appointments ALTER COLUMN appointment_id TYPE VARCHAR(50)",
                            "ALTER TABLE vital_signs ALTER COLUMN vital_id TYPE VARCHAR(50)",
                            "ALTER TABLE patient_queue ALTER COLUMN queue_id TYPE VARCHAR(50)",
                            "ALTER TABLE subscriptions ALTER COLUMN subscription_id TYPE VARCHAR(50)",
                            "ALTER TABLE patients ALTER COLUMN patient_id TYPE VARCHAR(50)",
                            "ALTER TABLE doctors ALTER COLUMN doctor_id TYPE VARCHAR(50)",
                            "ALTER TABLE nurses ALTER COLUMN nurse_id TYPE VARCHAR(50)",
                            "ALTER TABLE lab_technicians ALTER COLUMN technician_id TYPE VARCHAR(50)",
                            "ALTER TABLE pharmacists ALTER COLUMN pharmacist_id TYPE VARCHAR(50)",
                            "ALTER TABLE admins ALTER COLUMN admin_id TYPE VARCHAR(50)",
                        ]
                        for stmt in alter_stmts:
                            try:
                                conn.execute(_text(stmt))
                            except Exception:
                                pass  # column may already be wide enough
                        conn.commit()
                        app.logger.info('PostgreSQL column widening applied')
                except Exception as pg_err:
                    app.logger.warning(f'PostgreSQL column widening skipped: {pg_err}')
    except Exception as e:
        app.logger.warning(f"db.create_all() skipped: {e}")

    # SQLite-only bootstrap: schema migrations and data fixes
    db_uri = str(app.config.get('SQLALCHEMY_DATABASE_URI', ''))
    if db_uri.startswith('sqlite:///'):
        try:
            with app.app_context():
                _repair_sqlite_polymorphic_user_integrity(app)
                # Clean orphaned lab tests
                try:
                    from sqlalchemy import text as _text
                    deleted = db.session.execute(_text(
                        "DELETE FROM lab_tests WHERE patient_id NOT IN (SELECT id FROM patients)"
                    )).rowcount
                    if deleted:
                        db.session.commit()
                        app.logger.info(f"Cleaned {deleted} orphaned lab tests on startup")
                except Exception:
                    db.session.rollback()

                # Add missing columns (safe ALTER TABLE)
                try:
                    from sqlalchemy import text as _text, inspect as _inspect
                    inspector = _inspect(db.engine)
                    patient_cols = [c['name'] for c in inspector.get_columns('patients')]
                    pred_cols    = [c['name'] for c in inspector.get_columns('predictions')]
                    idx_names    = [i['name'] for i in inspector.get_indexes('audit_logs')]
                    with db.engine.connect() as conn:
                        for col, defn in [
                            ('consent_given',              'INTEGER NOT NULL DEFAULT 0'),
                            ('consent_given_at',           'DATETIME'),
                            ('data_deletion_requested',    'INTEGER NOT NULL DEFAULT 0'),
                            ('data_deletion_requested_at', 'DATETIME'),
                        ]:
                            if col not in patient_cols:
                                conn.execute(_text(f'ALTER TABLE patients ADD COLUMN {col} {defn}'))
                        if 'ip_address' not in pred_cols:
                            conn.execute(_text('ALTER TABLE predictions ADD COLUMN ip_address VARCHAR(50)'))
                        if 'model_used' not in pred_cols:
                            conn.execute(_text('ALTER TABLE predictions ADD COLUMN model_used VARCHAR(50)'))
                        if 'ix_audit_logs_action' not in idx_names:
                            conn.execute(_text('CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action)'))
                        if 'ix_audit_logs_created_at' not in idx_names:
                            conn.execute(_text('CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at)'))
                        conn.execute(_text(
                            "UPDATE patients SET consent_given=1, consent_given_at=datetime('now') "
                            "WHERE consent_given=0 OR consent_given IS NULL"
                        ))
                        conn.commit()
                except Exception as _me:
                    app.logger.warning(f'Schema migration skipped: {_me}')
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

    # Health check route — real check, not just a static response
    @app.route("/health")
    def health_check():
        status = {"status": "healthy", "checks": {}}
        http_code = 200
        # DB check
        try:
            db.session.execute(text("SELECT 1"))
            status["checks"]["database"] = "ok"
        except Exception as e:
            status["checks"]["database"] = f"error: {type(e).__name__}"
            status["status"] = "degraded"
            http_code = 503
        # ML model check
        try:
            from backend.services.ml_service import get_ml_service
            ml = get_ml_service()
            status["checks"]["ml_model"] = "ok" if ml.is_ready() else "not_loaded"
            if not ml.is_ready():
                status["status"] = "degraded"
                http_code = 503
        except Exception as e:
            status["checks"]["ml_model"] = f"error: {type(e).__name__}"
            status["status"] = "degraded"
            http_code = 503
        return jsonify(status), http_code

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

    # Secure ML model reload — admin auth required
    @app.route("/api/ml/reload", methods=["POST"])
    def reload_ml_model():
        # Require admin token
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            try:
                import jwt as _jwt
                payload = _jwt.decode(auth[7:], app.config['SECRET_KEY'], algorithms=['HS256'])
                if payload.get('role') != 'admin':
                    return jsonify({"success": False, "message": "Admin access required"}), 403
            except Exception:
                return jsonify({"success": False, "message": "Invalid token"}), 401
        else:
            return jsonify({"success": False, "message": "Token required"}), 401
        try:
            from backend.services.ml_service import get_ml_service
            ml = get_ml_service(force_reload=True)
            if ml.is_ready():
                return jsonify({"success": True, "message": f"Model reloaded: {type(ml.model).__name__}"}), 200
            else:
                return jsonify({"success": False, "message": "Model reload failed"}), 500
        except Exception as e:
            return jsonify({"success": False, "message": "Reload error"}), 500

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