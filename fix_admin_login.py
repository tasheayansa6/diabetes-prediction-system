"""
Fix admin login — reset password and verify it works.
Run: venv\Scripts\python.exe fix_admin_login.py
"""
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

EMAIL    = "admin@system.com"
PASSWORD = "Admin@1234"

conn = sqlite3.connect('database/diabetes.db')
conn.row_factory = sqlite3.Row
cur  = conn.cursor()

# Check if user exists
cur.execute("SELECT id, username, email, role, is_active, password_hash FROM users WHERE email=?", (EMAIL,))
user = cur.fetchone()

if not user:
    print(f"User {EMAIL} not found — creating...")
    # Get or create admin role record
    hashed = generate_password_hash(PASSWORD)
    cur.execute("""
        INSERT INTO users (username, email, password_hash, role, is_active, created_at)
        VALUES (?, ?, ?, 'admin', 1, datetime('now'))
    """, ('admin', EMAIL, hashed))
    user_id = cur.lastrowid
    cur.execute("INSERT OR IGNORE INTO admins (id) VALUES (?)", (user_id,))
    conn.commit()
    print(f"Created admin: {EMAIL} / {PASSWORD}")
else:
    print(f"Found user: id={user['id']} username={user['username']} role={user['role']} active={user['is_active']}")
    
    # Reset password
    hashed = generate_password_hash(PASSWORD)
    cur.execute("UPDATE users SET password_hash=?, is_active=1 WHERE email=?", (hashed, EMAIL))
    conn.commit()
    
    # Verify
    cur.execute("SELECT password_hash FROM users WHERE email=?", (EMAIL,))
    row = cur.fetchone()
    ok = check_password_hash(row['password_hash'], PASSWORD)
    print(f"Password reset. Verification: {'PASS' if ok else 'FAIL'}")

conn.close()
print(f"\nLogin with: {EMAIL} / {PASSWORD}")
