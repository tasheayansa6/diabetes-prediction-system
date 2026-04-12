"""
Create an admin user directly in the database.
Run: venv\Scripts\python.exe create_admin.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from backend import create_app
from backend.extensions import db
from backend.utils.role_accounts import create_polymorphic_user
from werkzeug.security import generate_password_hash

USERNAME = "admin"
EMAIL    = "admin@system.com"
PASSWORD = "Admin@1234"

app = create_app('development')
with app.app_context():
    from backend.models.user import User
    if User.query.filter_by(email=EMAIL).first():
        print(f"Admin already exists: {EMAIL}")
    else:
        data = {'username': USERNAME, 'email': EMAIL}
        user = create_polymorphic_user(data, generate_password_hash(PASSWORD), 'admin')
        db.session.add(user)
        db.session.commit()
        print(f"Admin created!")
        print(f"  Email:    {EMAIL}")
        print(f"  Password: {PASSWORD}")
