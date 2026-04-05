"""
Debug script - run this while server is running to check notifications
Usage: python debug_notifications.py
"""
import sys
sys.path.insert(0, '.')

from backend import create_app
app = create_app('development')

with app.app_context():
    from backend.extensions import db
    from sqlalchemy import text

    print("=" * 60)
    print("1. ALL USERS IN DB:")
    print("=" * 60)
    rows = db.session.execute(text('SELECT id, username, email, role FROM users ORDER BY role')).fetchall()
    for r in rows:
        print(f"  ID={r[0]}  username={r[1]}  email={r[2]}  role={r[3]}")

    print()
    print("=" * 60)
    print("2. ALL NOTIFICATIONS IN DB:")
    print("=" * 60)
    rows = db.session.execute(text(
        'SELECT id, user_id, title, type, is_read, created_at FROM notifications ORDER BY created_at DESC LIMIT 20'
    )).fetchall()
    if not rows:
        print("  *** NO NOTIFICATIONS FOUND IN DB ***")
        print("  This means the nurse vitals save is NOT creating notifications.")
    for r in rows:
        print(f"  ID={r[0]}  user_id={r[1]}  title={r[2]}  type={r[3]}  read={r[4]}  at={r[5]}")

    print()
    print("=" * 60)
    print("3. NOTIFICATIONS TABLE EXISTS?")
    print("=" * 60)
    try:
        count = db.session.execute(text('SELECT COUNT(*) FROM notifications')).scalar()
        print(f"  YES — {count} total notifications")
    except Exception as e:
        print(f"  ERROR: {e}")
        print("  The notifications table may not exist! Run: flask db upgrade")

    print()
    print("=" * 60)
    print("4. VITAL SIGNS IN DB:")
    print("=" * 60)
    rows = db.session.execute(text(
        'SELECT id, patient_id, nurse_id, blood_pressure_diastolic, bmi, recorded_at FROM vital_signs ORDER BY recorded_at DESC LIMIT 5'
    )).fetchall()
    if not rows:
        print("  *** NO VITALS FOUND IN DB ***")
    for r in rows:
        print(f"  ID={r[0]}  patient={r[1]}  nurse={r[2]}  BP={r[3]}  BMI={r[4]}  at={r[5]}")

    print()
    print("=" * 60)
    print("5. DOCTORS IN DB (who should receive notifications):")
    print("=" * 60)
    rows = db.session.execute(text(
        "SELECT id, username, email, is_active FROM users WHERE role='doctor'"
    )).fetchall()
    if not rows:
        print("  *** NO DOCTORS FOUND — notifications have nobody to send to! ***")
    for r in rows:
        print(f"  ID={r[0]}  username={r[1]}  email={r[2]}  active={r[3]}")
