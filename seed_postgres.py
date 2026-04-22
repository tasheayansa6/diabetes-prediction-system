"""
seed_postgres.py — Migrate SQLite data to PostgreSQL on first deploy.
Run once: python seed_postgres.py
Only inserts if tables are empty (safe to run multiple times).
"""
import os, sys, sqlite3
from pathlib import Path

# Must have DATABASE_URL pointing to PostgreSQL
db_url = os.getenv('DATABASE_URL', '')
if not db_url.startswith('postgresql'):
    print('Not a PostgreSQL URL — skipping migration')
    sys.exit(0)

sys.path.insert(0, str(Path(__file__).parent))
from backend import create_app
from backend.extensions import db
from sqlalchemy import text

app = create_app('production')

SQLITE_PATH = Path(__file__).parent / 'instance' / 'diabetes.db'
if not SQLITE_PATH.exists():
    SQLITE_PATH = Path(__file__).parent / 'database' / 'diabetes.db'

if not SQLITE_PATH.exists():
    print(f'SQLite DB not found at {SQLITE_PATH}')
    sys.exit(1)

print(f'Migrating from {SQLITE_PATH} to PostgreSQL...')

# Tables to migrate in dependency order
TABLES = [
    'users', 'patients', 'doctors', 'nurses', 'lab_technicians',
    'pharmacists', 'admins', 'health_records', 'predictions',
    'prescriptions', 'lab_tests', 'appointments', 'payments',
    'invoices', 'notifications', 'audit_logs', 'notes',
    'vital_signs', 'patient_queue', 'medicine_inventory',
    'test_types', 'subscriptions',
]

sqlite_conn = sqlite3.connect(str(SQLITE_PATH))
sqlite_conn.row_factory = sqlite3.Row

with app.app_context():
    db.create_all()
    print('Tables created in PostgreSQL')

    for table in TABLES:
        try:
            # Check if table exists in SQLite
            exists = sqlite_conn.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            ).fetchone()
            if not exists:
                print(f'  SKIP {table} (not in SQLite)')
                continue

            # Check if already has data in PostgreSQL
            pg_count = db.session.execute(
                text(f'SELECT COUNT(*) FROM {table}')
            ).scalar()
            if pg_count > 0:
                print(f'  SKIP {table} (already has {pg_count} rows in PostgreSQL)')
                continue

            # Get rows from SQLite
            rows = sqlite_conn.execute(f'SELECT * FROM {table}').fetchall()
            if not rows:
                print(f'  SKIP {table} (empty in SQLite)')
                continue

            cols = [d[0] for d in sqlite_conn.execute(f'SELECT * FROM {table} LIMIT 0').description]

            # Get PostgreSQL column names to filter out missing ones
            pg_cols_result = db.session.execute(
                text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'")
            ).fetchall()
            pg_cols = {r[0] for r in pg_cols_result}
            valid_cols = [c for c in cols if c in pg_cols]

            if not valid_cols:
                print(f'  SKIP {table} (no matching columns)')
                continue

            inserted = 0
            for row in rows:
                row_dict = {c: row[c] for c in valid_cols if row[c] is not None}
                if not row_dict:
                    continue
                col_str = ', '.join(f'"{c}"' for c in row_dict.keys())
                val_str = ', '.join(f':{c}' for c in row_dict.keys())
                try:
                    db.session.execute(
                        text(f'INSERT INTO {table} ({col_str}) VALUES ({val_str}) ON CONFLICT DO NOTHING'),
                        row_dict
                    )
                    inserted += 1
                except Exception as row_err:
                    db.session.rollback()

            db.session.commit()
            print(f'  OK {table}: {inserted}/{len(rows)} rows inserted')

        except Exception as e:
            db.session.rollback()
            print(f'  ERROR {table}: {e}')

    # Reset sequences for PostgreSQL auto-increment
    for table in TABLES:
        try:
            max_id = db.session.execute(text(f'SELECT MAX(id) FROM {table}')).scalar()
            if max_id:
                db.session.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), {max_id})"
                ))
        except Exception:
            pass
    db.session.commit()
    print('\nSequences reset')

sqlite_conn.close()
print('\nMigration complete!')
