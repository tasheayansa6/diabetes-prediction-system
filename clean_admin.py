"""
Create admin account using the correct environment config.
Runs during Render build: uses FLASK_ENV env var (defaults to production on Render).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def clean_and_create_admin():
    # Use the same config that the server will use at runtime
    config_name = os.getenv('FLASK_ENV', 'production')
    print(f"Using config: {config_name}")

    from backend import create_app
    from backend.extensions import db
    from backend.models.user import User
    from werkzeug.security import generate_password_hash

    app = create_app(config_name)

    with app.app_context():
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        print(f"DB URI: {db_uri}")

        # Read credentials from env (set in render.yaml / Render dashboard)
        admin_email    = os.getenv('ADMIN_BOOTSTRAP_EMAIL',    'admin@system.com')
        admin_password = os.getenv('ADMIN_BOOTSTRAP_PASSWORD', 'Admin@1234')
        admin_username = os.getenv('ADMIN_BOOTSTRAP_USERNAME', 'admin')

        existing = User.query.filter_by(email=admin_email).first()
        if existing:
            # Always sync password so deploy always resets to known credentials
            existing.password_hash = generate_password_hash(admin_password)
            existing.is_active = True
            db.session.commit()
            print(f"Admin password synced: {admin_email}")
            return True

        from backend.utils.role_accounts import create_polymorphic_user
        admin_user = create_polymorphic_user(
            {'username': admin_username, 'email': admin_email},
            generate_password_hash(admin_password),
            'admin'
        )
        if admin_user:
            admin_user.is_active = True
            db.session.add(admin_user)
            db.session.commit()
            print(f"Admin created: {admin_email} / {admin_password}")
            return True

        print("Failed to create admin")
        return False


if __name__ == '__main__':
    success = clean_and_create_admin()
    if not success:
        sys.exit(1)
