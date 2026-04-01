# add your model's MetaData object here
# for 'autogenerate' support
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend import create_app
from backend.extensions import db
from backend.models import *

# This is the critical fix
app = create_app('development')
with app.app_context():
    target_metadata = db.metadata
    # Force Alembic to see all tables
    print(f"🔧 Alembic configured with {len(target_metadata.tables)} tables")