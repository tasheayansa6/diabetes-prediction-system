import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print(f"📂 Project root added to path: {project_root}")
print(f"📂 Python path: {sys.path[0]}")
print("="*60)
print("Database Configuration Test")
print("="*60)

from backend import create_app
from backend.extensions import db
from sqlalchemy import text

app = create_app('development')

with app.app_context():
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    print(f"\n📂 Database URI: {uri}")
    
    # Extract and check the actual file path
    if uri.startswith('sqlite:///'):
        db_path = uri.replace('sqlite:///', '')
        path = Path(db_path)
        print(f"📁 Database file path: {path.absolute()}")
        print(f"📁 Directory exists: {path.parent.exists()}")
        print(f"📁 Database file exists: {path.exists()}")
    
    try:
        # SQLAlchemy 2.0 syntax
        with db.engine.connect() as conn:
            result = conn.execute(text('SELECT 1')).scalar()
            print(f"\n✅ Database connection successful: {result}")
        
        # Create tables if they don't exist
        db.create_all()
        print("✅ Tables created/verified")
        
        # Check tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"\n📊 Existing tables: {tables}")
        
    except Exception as e:
        print(f"\n❌ Database connection failed: {e}")
        import traceback
        traceback.print_exc()
