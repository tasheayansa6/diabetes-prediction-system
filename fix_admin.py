"""
Quick fix for admin login after deployment.
Run this after deploying the application to create/reset admin access.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from backend import create_app
from backend.extensions import db
from backend.models.user import User
from werkzeug.security import generate_password_hash

def create_admin():
    """Create or reset admin account"""
    app = create_app('development')
    
    with app.app_context():
        # Delete existing admin accounts
        User.query.filter_by(role='admin').delete()
        db.session.commit()
        
        # Create new admin
        admin_data = {
            'username': 'admin',
            'email': 'admin@system.com',
            'full_name': 'System Administrator'
        }
        
        from backend.utils.role_accounts import create_polymorphic_user
        admin_user = create_polymorphic_user(
            admin_data, 
            generate_password_hash('Admin@1234'), 
            'admin'
        )
        
        if admin_user:
            admin_user.is_active = True
            db.session.add(admin_user)
            db.session.commit()
            
            print("✅ Admin account created successfully!")
            print(f"📧 Email: admin@system.com")
            print(f"🔑 Password: Admin@1234")
            print(f"🆔 User ID: {admin_user.id}")
            print(f"🌐 Login at: http://localhost:5000/login")
            return True
        else:
            print("❌ Failed to create admin account")
            return False

if __name__ == '__main__':
    print("🔧 Creating admin account for Diabetes Prediction System...")
    print("=" * 50)
    
    success = create_admin()
    
    if success:
        print("=" * 50)
        print("✅ Ready! You can now login with:")
        print("   Email: admin@system.com")
        print("   Password: Admin@1234")
        print("   URL: http://localhost:5000/login")
    else:
        print("❌ Failed to create admin account")
        sys.exit(1)
