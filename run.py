import os
import socket
from flask import send_from_directory, send_file
from backend import create_app
from backend.extensions import socketio

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(os.path.join(PROJECT_ROOT, 'backend')):
    raise RuntimeError("Backend package directory not found relative to run.py")

# ── Kill any non-Python process blocking port 5000 ───────────────────────────
def _free_port_5000():
    """Kill any process (e.g. Node.js) blocking port 5000 before Flask starts."""
    try:
        import subprocess, sys
        port = 5000
        if sys.platform == 'win32':
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.strip().split()
                    pid = int(parts[-1])
                    # Only kill non-Python processes
                    proc_result = subprocess.run(
                        ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'],
                        capture_output=True, text=True, timeout=5
                    )
                    if 'python' not in proc_result.stdout.lower():
                        subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                                       capture_output=True, timeout=5)
                        print(f'[run.py] Killed non-Python process {pid} blocking port {port}')
    except Exception as e:
        print(f'[run.py] Port check warning: {e}')

_free_port_5000()

config_name = os.getenv('FLASK_ENV', 'development')
app = create_app(config_name)

FRONTEND_DIR = os.path.join(PROJECT_ROOT, 'frontend')

def send_html(path):
    return send_file(os.path.join(FRONTEND_DIR, path))

@app.route('/')
@app.route('/index.html')
def index():
    return send_html('index.html')

@app.route('/login')
@app.route('/login.html')
def login():
    return send_html('login.html')

@app.route('/register')
@app.route('/register.html')
def register_page():
    return send_html('register.html')

@app.route('/forgot-password')
@app.route('/forgot-password.html')
def forgot_password():
    return send_html('forgot-password.html')

@app.route('/reset-password')
@app.route('/reset-password.html')
def reset_password():
    return send_html('reset-password.html')

@app.route('/verify-email')
@app.route('/verify-email.html')
def verify_email():
    return send_html('verify-email.html')

@app.route('/404.html')
def not_found_page():
    return send_html('404.html')

@app.route('/templates/<path:filename>')
def serve_template(filename):
    return send_file(os.path.join(FRONTEND_DIR, 'templates', filename))

@app.route('/static/<path:filename>')
def serve_static(filename):
    from flask import make_response
    resp = make_response(send_from_directory(os.path.join(FRONTEND_DIR, 'static'), filename))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(FRONTEND_DIR, 'favicon.ico')

if __name__ == '__main__':
    print("=" * 60)
    print("   Starting Diabetes Prediction System")
    print("=" * 60)
    print(f"Environment: {config_name}")
    print(f"Debug Mode: {app.config.get('DEBUG', False)}")
    print(f"Database: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')}")
    print("=" * 60)
    print("\n Server starting with WebSocket support...")
    print(" Access the API at: http://localhost:5000")
    print("Health check: http://localhost:5000/health")
    print("Press CTRL+C to quit\n")
    socketio.run(
        app,
        debug=app.config.get('DEBUG', False),
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        use_reloader=False
    )
