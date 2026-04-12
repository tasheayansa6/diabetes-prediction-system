"""
Test login directly against the running server.
Run: venv\Scripts\python.exe test_login.py
"""
import urllib.request, json

url = 'http://localhost:5000/api/auth/login'
credentials = [
    ('admin@system.com', 'Admin@1234'),
    ('admin@gmail.com', 'Admin@1234'),
]

for email, password in credentials:
    data = json.dumps({'email': email, 'password': password}).encode()
    req = urllib.request.Request(url, data=data,
          headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req) as r:
            resp = json.loads(r.read())
            print(f"OK   {email} -> role={resp.get('user',{}).get('role')}")
    except urllib.error.HTTPError as e:
        resp = json.loads(e.read())
        print(f"FAIL {email} -> {resp.get('message')}")
    except Exception as ex:
        print(f"ERR  {email} -> {ex}")
