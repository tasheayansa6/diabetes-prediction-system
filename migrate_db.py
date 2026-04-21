"""
migrate_db.py — Safe incremental schema migration for diabetes.db
Run: python migrate_db.py
"""
import sqlite3
import sys

DB = 'database/diabetes.db'

def run():
    c = sqlite3.connect(DB)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA foreign_keys=OFF')

    patients_cols = [r[1] for r in c.execute('PRAGMA table_info(patients)').fetchall()]
    pred_cols     = [r[1] for r in c.execute('PRAGMA table_info(predictions)').fetchall()]
    indexes       = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()]

    added = []

    # ── patients: consent + deletion columns ─────────────────────────────────
    for col, defn in [
        ('consent_given',              'INTEGER NOT NULL DEFAULT 0'),
        ('consent_given_at',           'DATETIME'),
        ('data_deletion_requested',    'INTEGER NOT NULL DEFAULT 0'),
        ('data_deletion_requested_at', 'DATETIME'),
    ]:
        if col not in patients_cols:
            c.execute(f'ALTER TABLE patients ADD COLUMN {col} {defn}')
            added.append(f'patients.{col}')

    # ── predictions: ip_address ───────────────────────────────────────────────
    if 'ip_address' not in pred_cols:
        c.execute('ALTER TABLE predictions ADD COLUMN ip_address VARCHAR(50)')
        added.append('predictions.ip_address')

    # ── audit_logs: indexes for fast blacklist + time queries ─────────────────
    if 'ix_audit_logs_action' not in indexes:
        c.execute('CREATE INDEX ix_audit_logs_action ON audit_logs(action)')
        added.append('index:ix_audit_logs_action')

    if 'ix_audit_logs_created_at' not in indexes:
        c.execute('CREATE INDEX ix_audit_logs_created_at ON audit_logs(created_at)')
        added.append('index:ix_audit_logs_created_at')

    c.commit()
    c.execute('PRAGMA foreign_keys=ON')
    c.close()

    if added:
        print('Migration applied:')
        for item in added:
            print(f'  + {item}')
    else:
        print('Already up to date — nothing to migrate.')

    # Verify
    c2 = sqlite3.connect(DB)
    final_patients = [r[1] for r in c2.execute('PRAGMA table_info(patients)').fetchall()]
    final_preds    = [r[1] for r in c2.execute('PRAGMA table_info(predictions)').fetchall()]
    final_idx      = [r[0] for r in c2.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'ix_%'").fetchall()]
    c2.close()

    print('\nFinal state:')
    print(f'  patients cols:    {final_patients}')
    print(f'  predictions cols: {final_preds}')
    print(f'  custom indexes:   {final_idx}')

    required = ['consent_given', 'consent_given_at', 'data_deletion_requested', 'data_deletion_requested_at']
    missing  = [c for c in required if c not in final_patients]
    if missing:
        print(f'\nERROR: Still missing columns: {missing}')
        sys.exit(1)
    else:
        print('\nAll required columns present.')

if __name__ == '__main__':
    run()
