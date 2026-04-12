"""
Resets all admin passwords to: Admin@1234
"""
import sqlite3
from werkzeug.security import generate_password_hash

NEW_PASSWORD = "Admin@1234"
hashed = generate_password_hash(NEW_PASSWORD)

conn = sqlite3.connect('database/diabetes.db')
cur  = conn.cursor()
cur.execute("UPDATE users SET password_hash=? WHERE role='admin'", (hashed,))
conn.commit()

cur.execute("SELECT username, email FROM users WHERE role='admin'")
for row in cur.fetchall():
    print(f"  {row[0]} / {row[1]}  ->  password: {NEW_PASSWORD}")

conn.close()
print("\nDone. All admin passwords reset.")
