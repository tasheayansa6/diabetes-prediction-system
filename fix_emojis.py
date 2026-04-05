"""Remove emojis from notification title strings in backend route files."""
import re, os

files = [
    r'backend\routes\nurse_routes.py',
    r'backend\routes\doctor_routes.py',
    r'backend\routes\pharmacist_routes.py',
    r'backend\routes\lab_routes.py',
    r'backend\routes\patient_routes.py',
    r'backend\routes\auth_routes.py',
]

# Map emoji prefixes to clean titles
replacements = {
    '\U0001f9ea Vitals Recorded':    'Vitals Recorded',
    '\U0001fa7a Vitals Recorded':    'Vitals Recorded',
    '\U0001f489 Vitals Recorded':    'Vitals Recorded',
    '\u2705 Prescription Verified':  'Prescription Verified',
    '\u2705 Medication Dispensed':   'Medication Dispensed',
    '\u274c Prescription Rejected':  'Prescription Rejected',
    '\U0001f48a New Prescription':   'New Prescription',
    '\U0001f52c Lab Result Ready':   'Lab Result Ready',
    '\U0001f4c5 New Appointment Booked': 'New Appointment Booked',
    '\u26a0\ufe0f':                  'HIGH RISK -',
    '\U0001fa7a':                    '',
    '\U0001f489':                    '',
}

def remove_emojis_from_string(s):
    # Remove any non-ASCII characters from title= strings
    def clean_title(m):
        title_content = m.group(1)
        # Remove emoji characters (non-ASCII)
        cleaned = title_content.encode('ascii', 'ignore').decode('ascii').strip()
        # Remove leading/trailing spaces and dashes left by emoji removal
        cleaned = cleaned.strip(' -')
        return f"title='{cleaned}'"
    return re.sub(r"title='([^']*)'", clean_title, s)

for fname in files:
    path = os.path.join(os.path.dirname(__file__), fname)
    if not os.path.exists(path):
        print(f'SKIP (not found): {fname}')
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = remove_emojis_from_string(content)
    if new_content != content:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'FIXED: {fname}')
    else:
        print(f'OK (no changes): {fname}')

print('Done.')
