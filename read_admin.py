import sqlite3
conn = sqlite3.connect('database/diabetes.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, username, email, role, is_active FROM users WHERE role='admin'")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(f"ID:       {r['id']}")
        print(f"Username: {r['username']}")
        print(f"Email:    {r['email']}")
        print(f"Active:   {r['is_active']}")
        print()
else:
    print("No admin users found in database")
conn.close()
