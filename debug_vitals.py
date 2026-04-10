"""
Debug + fix: check vital_signs and show what patient health form will receive.
Run: python debug_vitals.py
"""
import sqlite3

conn = sqlite3.connect('database/diabetes.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check columns
cur.execute("PRAGMA table_info(vital_signs)")
cols = [r['name'] for r in cur.fetchall()]
print("Columns in vital_signs:", cols)
print()

# Check all records grouped by patient
cur.execute("SELECT DISTINCT patient_id FROM vital_signs")
patients = [r['patient_id'] for r in cur.fetchall()]
print(f"Patients with vitals: {patients}")
print()

for pid in patients:
    cur.execute("SELECT * FROM vital_signs WHERE patient_id=? ORDER BY recorded_at DESC", (pid,))
    rows = cur.fetchall()
    print(f"Patient {pid} — {len(rows)} vital record(s):")
    for row in rows:
        print(f"  ID={row['id']} recorded={row['recorded_at']}")
        print(f"    bp_diastolic={row['blood_pressure_diastolic']} bmi={row['bmi']} skin={row['skin_thickness']}")
        if 'pregnancies' in cols:
            print(f"    pregnancies={row['pregnancies']} pedigree={row['diabetes_pedigree']} age={row['age']}")
    print()

# Check what patient health form would receive
print("=" * 50)
print("What /api/patient/vitals/latest returns per patient:")
for pid in patients:
    cur.execute("SELECT * FROM vital_signs WHERE patient_id=? ORDER BY recorded_at DESC LIMIT 1", (pid,))
    v = cur.fetchone()
    preg = v['pregnancies'] if 'pregnancies' in cols else None
    dpf  = v['diabetes_pedigree'] if 'diabetes_pedigree' in cols else None
    age  = v['age'] if 'age' in cols else None

    # Fallback: check other vitals
    if preg is None or dpf is None or age is None:
        cur.execute("SELECT * FROM vital_signs WHERE patient_id=? AND id!=? ORDER BY recorded_at DESC", (pid, v['id']))
        others = cur.fetchall()
        for ov in others:
            if preg is None and ov['pregnancies'] is not None: preg = ov['pregnancies']
            if dpf  is None and ov['diabetes_pedigree'] is not None: dpf = ov['diabetes_pedigree']
            if age  is None and ov['age'] is not None: age = ov['age']
            if preg and dpf and age: break

    # Fallback: check predictions
    if preg is None or dpf is None or age is None:
        cur.execute("SELECT input_data FROM predictions WHERE patient_id=? ORDER BY created_at DESC LIMIT 1", (pid,))
        pred = cur.fetchone()
        if pred and pred['input_data']:
            import json
            try:
                d = json.loads(pred['input_data'])
                if preg is None: preg = d.get('pregnancies')
                if dpf  is None: dpf  = d.get('diabetes_pedigree')
                if age  is None: age  = d.get('age')
            except: pass

    print(f"  Patient {pid}: bp={v['blood_pressure_diastolic']} bmi={v['bmi']} preg={preg} dpf={dpf} age={age}")
    if preg is None or dpf is None or age is None:
        print(f"    ⚠️  STILL NULL — nurse must record these fields!")
    else:
        print(f"    ✅ All ML fields available")

conn.close()
