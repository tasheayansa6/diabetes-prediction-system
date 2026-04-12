from werkzeug.security import check_password_hash
import sqlite3

conn = sqlite3.connect('database/diabetes.db')
cur = conn.cursor()
cur.execute("SELECT username, email, password_hash FROM users WHERE role='admin'")
for row in cur.fetchall():
    ok = check_password_hash(row[2], 'Admin@1234')
    print(f"Email: {row[1]}")
    print(f"Password 'Admin@1234' works: {ok}")
    print()
conn.close()
