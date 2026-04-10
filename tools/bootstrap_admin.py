"""
Create the first admin account when the database has no admin user.

Set in .env (or environment):
  ADMIN_BOOTSTRAP_EMAIL=owner@example.com
  ADMIN_BOOTSTRAP_PASSWORD=YourStrongPass123
  ADMIN_BOOTSTRAP_USERNAME=owner   (optional; defaults to part before @)

Then run from project root:
  python tools/bootstrap_admin.py

Safe to run multiple times: does nothing if any admin user already exists.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


def main() -> int:
    email = (os.getenv("ADMIN_BOOTSTRAP_EMAIL") or "").strip().lower()
    password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD") or ""
    username = (os.getenv("ADMIN_BOOTSTRAP_USERNAME") or "").strip()
    if not username and email:
        username = email.split("@")[0]
    if not email or not password or not username:
        print(
            "ERROR: Set ADMIN_BOOTSTRAP_EMAIL, ADMIN_BOOTSTRAP_PASSWORD, "
            "and optionally ADMIN_BOOTSTRAP_USERNAME in .env or the environment."
        )
        return 1

    os.environ.setdefault("FLASK_ENV", "development")

    from backend import create_app
    from backend.extensions import db
    from backend.models.user import User
    from backend.routes.auth_routes import validate_password
    from backend.utils.role_accounts import create_polymorphic_user
    from werkzeug.security import generate_password_hash

    ok, msg = validate_password(password)
    if not ok:
        print(f"ERROR: {msg}")
        return 1

    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        if User.query.filter_by(role="admin").first():
            print("SKIP: An admin user already exists. No changes made.")
            return 0

        payload = {"username": username, "email": email, "full_name": username}
        user = create_polymorphic_user(payload, generate_password_hash(password), "admin")
        if not user:
            print("ERROR: Could not create admin user.")
            return 1
        db.session.add(user)
        db.session.commit()
        print(f"OK: Created admin id={user.id} username={user.username!r} email={email!r}")
        print("Next: log in at /login, then disable bootstrap secrets in .env if desired.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
