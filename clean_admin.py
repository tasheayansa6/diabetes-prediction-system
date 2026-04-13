"""
Clean database and create fresh admin account.
This fixes UNIQUE constraint issues by clearing conflicting entries.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from backend import create_app
from backend.extensions import db
from backend.models.user import User
from werkzeug.security import generate_password_hash

def clean_and_create_admin():
    """Clean database and create fresh admin"""
    app = create_app('development')
    
    with app.app_context():
        try:
            # Delete ALL users to avoid conflicts
            User.query.delete()
            db.session.commit()
            print("🧹 Cleaned existing users from database")
            
            # Reset auto-increment counter
            db.session.execute("DELETE FROM sqlite_sequence WHERE name='users'")
            db.session.commit()
            print("🔄 Reset user ID counter")
            
        except Exception as e:
            print(f"⚠️  Warning during cleanup: {e}")
        
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
    print("🔧 Cleaning database and creating admin account...")
    print("=" * 50)
    
    success = clean_and_create_admin()
    
    if success:
        print("=" * 50)
        print("✅ Ready! You can now login with:")
        print("   Email: admin@system.com")
        print("   Password: Admin@1234")
        print("   URL: http://localhost:5000/login")
    else:
        print("❌ Failed to create admin account")
        sys.exit(1)
