"""
One-time fix: update existing vital_signs records that have null
pregnancies/diabetes_pedigree/age by pulling from predictions table.

Run: python fix_vitals_nulls.py
"""
import sqlite3, json

conn = sqlite3.connect('database/diabetes.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Find vitals with null ML fields
cur.execute("""
    SELECT id, patient_id FROM vital_signs
    WHERE pregnancies IS NULL OR diabetes_pedigree IS NULL OR age IS NULL
""")
nulls = cur.fetchall()
print(f"Vitals with null ML fields: {len(nulls)}")

updated = 0
for row in nulls:
    vid = row['id']
    pid = row['patient_id']

    # Try to get from latest prediction
    cur.execute("""
        SELECT input_data FROM predictions
        WHERE patient_id=? AND input_data IS NOT NULL
        ORDER BY created_at DESC LIMIT 1
    """, (pid,))
    pred = cur.fetchone()

    if pred and pred['input_data']:
        try:
            d = json.loads(pred['input_data'])
            preg = d.get('pregnancies')
            dpf  = d.get('diabetes_pedigree')
            age  = d.get('age')

            if preg is not None or dpf is not None or age is not None:
                cur.execute("""
                    UPDATE vital_signs
                    SET pregnancies = COALESCE(pregnancies, ?),
                        diabetes_pedigree = COALESCE(diabetes_pedigree, ?),
                        age = COALESCE(age, ?)
                    WHERE id = ?
                """, (preg, dpf, age, vid))
                updated += 1
                print(f"  Updated vital {vid} (patient {pid}): preg={preg} dpf={dpf} age={age}")
        except Exception as e:
            print(f"  Error for vital {vid}: {e}")
    else:
        print(f"  No prediction found for patient {pid} — nurse must fill manually")

conn.commit()
conn.close()
print(f"\nDone. Updated {updated} records.")
