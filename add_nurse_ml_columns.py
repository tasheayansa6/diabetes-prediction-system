"""
Run this script to add pregnancies, diabetes_pedigree, age columns
to the vital_signs table in both database files.

Usage:
    venv\Scripts\python.exe add_nurse_ml_columns.py
"""
import sqlite3
import os

DB_PATHS = [
    'database/diabetes.db',
    'backend/diabetes.db',
]

COLUMNS = [
    ('pregnancies',       'INTEGER'),
    ('diabetes_pedigree', 'REAL'),
    ('age',               'INTEGER'),
]

NOTIF_COLUMNS = [
    ('link', 'VARCHAR(255)'),
]

for db_path in DB_PATHS:
    if not os.path.exists(db_path):
        print(f'Skipping (not found): {db_path}')
        continue

    print(f'\nProcessing: {db_path}')
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    # vital_signs columns
    cur.execute("PRAGMA table_info(vital_signs)")
    existing = {row[1] for row in cur.fetchall()}

    if existing:
        for col_name, col_type in COLUMNS:
            if col_name in existing:
                print(f'  [vital_signs] Column already exists: {col_name}')
            else:
                cur.execute(f'ALTER TABLE vital_signs ADD COLUMN {col_name} {col_type}')
                print(f'  [vital_signs] Added column: {col_name} {col_type}')
    else:
        print(f'  Table vital_signs not found in {db_path}, skipping.')

    # notifications link column
    cur.execute("PRAGMA table_info(notifications)")
    notif_existing = {row[1] for row in cur.fetchall()}

    if notif_existing:
        for col_name, col_type in NOTIF_COLUMNS:
            if col_name in notif_existing:
                print(f'  [notifications] Column already exists: {col_name}')
            else:
                cur.execute(f'ALTER TABLE notifications ADD COLUMN {col_name} {col_type}')
                print(f'  [notifications] Added column: {col_name} {col_type}')
    else:
        print(f'  Table notifications not found in {db_path}, skipping.')

    conn.commit()
    conn.close()
    print(f'  Done.')

print('\nMigration complete.')
