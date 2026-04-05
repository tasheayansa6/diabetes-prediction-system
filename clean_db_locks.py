"""Run this once to clean stale SQLite WAL/SHM lock files before starting the server."""
import os, glob

db_dir = os.path.join(os.path.dirname(__file__), 'database')
for pattern in ['*.db-wal', '*.db-shm']:
    for f in glob.glob(os.path.join(db_dir, pattern)):
        os.remove(f)
        print(f"Removed: {f}")

print("Done. Now start the server with: python run.py")
