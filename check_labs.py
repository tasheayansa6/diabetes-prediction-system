import sqlite3
from datetime import datetime, timedelta
conn = sqlite3.connect('database/diabetes.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT test_name, status, results, unit, test_completed_at, created_at FROM lab_tests ORDER BY created_at DESC LIMIT 10")
now = datetime.utcnow()
thirty_ago = now - timedelta(days=30)
for r in cur.fetchall():
    ts = r['test_completed_at'] or r['created_at']
    try:
        dt = datetime.fromisoformat(str(ts).replace('Z',''))
        recent = dt > thirty_ago
    except:
        recent = False
    print(f"  {r['test_name']:30} status={r['status']:10} results={str(r['results'])[:20]} recent={recent} ts={ts}")
conn.close()
