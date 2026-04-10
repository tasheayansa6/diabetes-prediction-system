"""
Debug the predict 500 error.
Run: python debug_predict.py
"""
import sqlite3

conn = sqlite3.connect('database/diabetes.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check health_records columns
cur.execute("PRAGMA table_info(health_records)")
cols = [r['name'] for r in cur.fetchall()]
print("health_records columns:", cols)
print()

# Check predictions columns
cur.execute("PRAGMA table_info(predictions)")
cols2 = [r['name'] for r in cur.fetchall()]
print("predictions columns:", cols2)
print()

# Check notifications columns
cur.execute("PRAGMA table_info(notifications)")
cols3 = [r['name'] for r in cur.fetchall()]
print("notifications columns:", cols3)
print()

# Try a test insert to health_records to see what fails
print("Testing health_records insert...")
try:
    cur.execute("""
        INSERT INTO health_records 
        (patient_id, pregnancies, glucose, blood_pressure, skin_thickness, insulin, bmi, diabetes_pedigree, age, created_at)
        VALUES (1, 0, 120.0, 80.0, 0.0, 0.0, 25.0, 0.5, 30, datetime('now'))
    """)
    conn.rollback()
    print("  health_records insert: OK")
except Exception as e:
    print(f"  health_records insert FAILED: {e}")

# Try a test insert to predictions
print("Testing predictions insert...")
try:
    cur.execute("""
        INSERT INTO predictions 
        (patient_id, prediction, probability, probability_percent, risk_level, model_version, explanation, input_data, created_at)
        VALUES (1, 0, 0.3, 30.0, 'LOW RISK', 'v2.1.0', 'test', '{}', datetime('now'))
    """)
    conn.rollback()
    print("  predictions insert: OK")
except Exception as e:
    print(f"  predictions insert FAILED: {e}")

conn.close()
