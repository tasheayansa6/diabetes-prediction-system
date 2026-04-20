"""
Create admin account for PRODUCTION deployment.
Run ONCE on the production server after first deployment.

Usage:
    python create_production_admin.py

You will be prompted for email and password.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from backend import create_app
from backend.extensions import db
from backend.utils.role_accounts import create_polymorphic_user
from werkzeug.security import generate_password_hash
import getpass

app = create_app(os.getenv('FLASK_ENV', 'production'))

with app.app_context():
    from backend.models.user import User

    print("=" * 60)
    print("CREATE PRODUCTION ADMIN ACCOUNT")
    print("=" * 60)
    print()

    email = input("Admin email: ").strip().lower()
    if not email or '@' not in email:
        print("Invalid email.")
        sys.exit(1)

    # Check if exists
    if User.query.filter_by(email=email).first():
        print(f"User with email {email} already exists.")
        overwrite = input("Reset password? (yes/no): ").strip().lower()
        if overwrite != 'yes':
            sys.exit(0)
        user = User.query.filter_by(email=email).first()
        password = getpass.getpass("New password: ")
        confirm  = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords don't match.")
            sys.exit(1)
        user.password_hash = generate_password_hash(password)
        user.is_active = True
        db.session.commit()
        print(f"\nPassword reset for {email}")
    else:
        username = input("Admin username: ").strip()
        password = getpass.getpass("Password: ")
        confirm  = getpass.getpass("Confirm password: ")

        if password != confirm:
            print("Passwords don't match.")
            sys.exit(1)

        if len(password) < 8:
            print("Password must be at least 8 characters.")
            sys.exit(1)

        data = {'username': username, 'email': email}
        user = create_polymorphic_user(data, generate_password_hash(password), 'admin')
        db.session.add(user)
        db.session.commit()
        print(f"\nAdmin created: {email}")

    print()
    print("=" * 60)
    print("PRODUCTION ADMIN READY")
    print("=" * 60)
    print(f"Email:    {email}")
    print(f"Password: (hidden)")
    print()
    print("IMPORTANT: Store these credentials securely.")
    print("=" * 60)
