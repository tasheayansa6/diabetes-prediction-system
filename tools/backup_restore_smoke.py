from __future__ import annotations

from datetime import datetime
from pathlib import Path
import os
import shutil
import sqlite3
import sys


def _sqlite_path_from_uri(uri: str) -> Path | None:
    if not uri:
        return None
    if uri.startswith("sqlite:///"):
        raw = uri.replace("sqlite:///", "", 1)
        return Path(raw).resolve()
    return None


def main() -> int:
    uri = os.getenv("DATABASE_URL", "sqlite:///database/diabetes.db")
    db_path = _sqlite_path_from_uri(uri)
    if not db_path:
        print("SKIP: backup smoke test currently supports sqlite DATABASE_URL only.")
        return 0

    if not db_path.exists():
        print(f"SKIP: sqlite DB not found at {db_path}.")
        return 0

    backup_dir = Path("backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    backup_path = backup_dir / f"smoke_backup_{stamp}.db"
    restore_path = backup_dir / f"smoke_restore_{stamp}.db"

    shutil.copy2(db_path, backup_path)
    shutil.copy2(backup_path, restore_path)

    try:
        with sqlite3.connect(str(restore_path)) as conn:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
    except Exception as exc:
        print(f"ERROR: restore connectivity check failed: {exc}")
        return 1

    if not tables:
        print("ERROR: restore database has no tables.")
        return 1

    print(f"OK: backup/restore smoke passed. tables={len(tables)} backup={backup_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

