"""
Fix old notifications that have NULL link by matching them to their lab tests.
Run: python fix_notification_links.py
"""
import sqlite3, json

conn = sqlite3.connect('database/diabetes.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Fix lab_order notifications with null link
cur.execute("""
    SELECT n.id, n.message, n.created_at
    FROM notifications n
    WHERE n.type = 'lab_order' AND (n.link IS NULL OR n.link = '')
""")
notifs = cur.fetchall()
print(f"lab_order notifications with no link: {len(notifs)}")

fixed = 0
for n in notifs:
    # Try to find the lab test by matching creation time (within 5 seconds)
    cur.execute("""
        SELECT test_id FROM lab_tests
        WHERE ABS(strftime('%s', created_at) - strftime('%s', ?)) < 10
        ORDER BY ABS(strftime('%s', created_at) - strftime('%s', ?)) ASC
        LIMIT 1
    """, (n['created_at'], n['created_at']))
    row = cur.fetchone()
    if row:
        link = f"/templates/lab/enter_lab_results.html?test_id={row['test_id']}"
        cur.execute("UPDATE notifications SET link=? WHERE id=?", (link, n['id']))
        print(f"  Fixed notif {n['id']} → {link}")
        fixed += 1
    else:
        # Just point to enter results page
        cur.execute("UPDATE notifications SET link='/templates/lab/enter_lab_results.html' WHERE id=?", (n['id'],))
        print(f"  Notif {n['id']} — no matching test found, set generic link")

# Fix lab_result notifications for patients with null link
cur.execute("""
    SELECT n.id, n.user_id, n.message, n.created_at
    FROM notifications n
    WHERE n.type = 'lab_result' AND (n.link IS NULL OR n.link = '')
""")
lab_result_notifs = cur.fetchall()
print(f"\nlab_result notifications with no link: {len(lab_result_notifs)}")

for n in lab_result_notifs:
    # Check if user is a patient or doctor
    cur.execute("SELECT role FROM users WHERE id=?", (n['user_id'],))
    user = cur.fetchone()
    if user:
        if user['role'] == 'patient':
            cur.execute("UPDATE notifications SET link='/templates/patient/lab_results.html' WHERE id=?", (n['id'],))
        elif user['role'] == 'doctor':
            cur.execute("UPDATE notifications SET link='/templates/doctor/lab_requests.html' WHERE id=?", (n['id'],))
        print(f"  Fixed notif {n['id']} for {user['role']}")
        fixed += 1

conn.commit()
conn.close()
print(f"\nTotal fixed: {fixed}")
