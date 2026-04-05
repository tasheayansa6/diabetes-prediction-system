import urllib.request, urllib.error, sys
data = b'{"email":"test@test.com","password":"Test1234"}'
req = urllib.request.Request(
    'http://127.0.0.1:5000/api/auth/login',
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    r = urllib.request.urlopen(req)
    print('200:', r.read().decode()[:400])
except urllib.error.HTTPError as e:
    print('HTTP', e.code, ':', e.read().decode()[:800])
except Exception as e:
    print('ERR:', type(e).__name__, e)
