"""
Remove all admin users except the one matching ADMIN_EMAIL (system owner).

Uses the same DATABASE_URL and ADMIN_EMAIL as the Flask app. Default is dry-run;
pass --apply to perform deletions.

Example:
  set ADMIN_EMAIL=owner@example.com
  python tools/prune_admin_accounts.py
  python tools/prune_admin_accounts.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env from project root if present
try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune admin accounts except ADMIN_EMAIL owner.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Delete non-owner admin rows. Without this flag, only prints what would happen.",
    )
    args = parser.parse_args()

    owner = (os.getenv("ADMIN_EMAIL") or "").strip().lower()
    if not owner:
        print("ERROR: Set ADMIN_EMAIL in the environment (or .env) to the single allowed admin email.")
        return 1

    os.environ.setdefault("FLASK_ENV", "development")

    from backend import create_app
    from backend.extensions import db
    from backend.models.admin import Admin

    app = create_app(os.environ.get("FLASK_ENV", "development"))

    with app.app_context():
        admins = Admin.query.order_by(Admin.id).all()
        to_remove = [a for a in admins if (a.email or "").strip().lower() != owner]
        keep = [a for a in admins if (a.email or "").strip().lower() == owner]

        print(f"ADMIN_EMAIL (owner): {owner}")
        print(f"Admins in database: {len(admins)}")
        print(f"Would keep: {len(keep)}")
        print(f"Would remove: {len(to_remove)}")

        for a in to_remove:
            print(f"  - remove id={a.id} email={a.email!r} username={a.username!r}")

        if not keep and admins:
            print(
                "WARNING: No admin row matches ADMIN_EMAIL. "
                "After --apply, there may be no admin accounts left. "
                "Create one with ALLOW_ADMIN_SIGNUP=true or a DB migration."
            )

        if not to_remove:
            print("Nothing to do.")
            return 0

        if not args.apply:
            print("Dry run only. Re-run with --apply to delete these admin accounts.")
            return 0

        for a in to_remove:
            db.session.delete(a)
        db.session.commit()
        print(f"Deleted {len(to_remove)} admin account(s).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
