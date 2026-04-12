import sqlite3
conn = sqlite3.connect('database/diabetes.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("PRAGMA table_info(test_types)")
cols = [r['name'] for r in cur.fetchall()]
print("Columns:", cols)
cur.execute("SELECT * FROM test_types ORDER BY category, test_name")
for r in cur.fetchall():
    print(f"  {r['category']:20} | {r['test_name']:35} | {r['test_code']:15} | ETB {r['cost']}")
conn.close()
