"""Check what lab results exist for patients"""
import sqlite3
conn = sqlite3.connect('database/diabetes.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check all patients
cur.execute("SELECT id, username FROM users WHERE role='patient' LIMIT 10")
patients = cur.fetchall()
print("Patients:")
for p in patients:
    print(f"  id={p['id']} username={p['username']}")

print()
print("Lab tests per patient:")
for p in patients:
    cur.execute("SELECT test_name, status, results, patient_id FROM lab_tests WHERE patient_id=? ORDER BY created_at DESC LIMIT 5", (p['id'],))
    tests = cur.fetchall()
    if tests:
        for t in tests:
            print(f"  patient={p['username']} test={t['test_name']} status={t['status']} results={t['results']}")

print()
# Check the lab_results HTML template path
cur.execute("SELECT COUNT(*) FROM lab_tests WHERE status='completed' AND results IS NOT NULL")
print(f"Total completed lab tests with results: {cur.fetchone()[0]}")

conn.close()
