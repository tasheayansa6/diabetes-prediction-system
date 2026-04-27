import os
from flask import send_from_directory, send_file
from backend import create_app
from backend.extensions import socketio

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists(os.path.join(PROJECT_ROOT, 'backend')):
    raise RuntimeError("Backend package directory not found relative to run.py")

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
