import sqlite3, os
from pathlib import Path

dbs = list(Path('.').rglob('*.db'))
for db in sorted(dbs):
    size = os.path.getsize(db)
    try:
        conn = sqlite3.connect(str(db))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        counts = {}
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM [{t}]")
                counts[t] = cur.fetchone()[0]
            except:
                counts[t] = '?'
        conn.close()
        print(f"\n{'='*60}")
        print(f"DB: {db}  ({size/1024:.0f} KB)")
        print(f"Tables: {len(tables)}")
        for t, c in counts.items():
            print(f"  {t:35} {c} rows")
    except Exception as e:
        print(f"\nDB: {db} -> ERROR: {e}")
