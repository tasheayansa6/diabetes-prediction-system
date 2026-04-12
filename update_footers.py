"""
Replace all simple footer tags with the professional footer across all HTML templates.
Run: venv\Scripts\python.exe update_footers.py
"""
import os, re

NEW_FOOTER = '''<footer class="footer">
  <div class="footer-inner">
    <div class="footer-brand">
      <i class="bi bi-heart-pulse-fill"></i> Diabetes Prediction System
    </div>
    <div class="footer-links">
      <a href="/templates/patient/dashboard.html">Patient Portal</a>
      <a href="/templates/doctor/dashboard.html">Doctor Portal</a>
      <a href="/templates/admin/dashboard.html">Admin</a>
    </div>
  </div>
  <div class="footer-bottom">
    <span>&copy; 2026 Diabetes Prediction System. All rights reserved.</span>
    <div class="footer-badges">
      <span class="footer-badge"><i class="bi bi-shield-check"></i> HIPAA Compliant</span>
      <span class="footer-badge"><i class="bi bi-lock-fill"></i> Secure</span>
      <span class="footer-badge"><i class="bi bi-robot"></i> AI Powered</span>
    </div>
  </div>
</footer>'''

# Pattern matches any simple footer with just a <p> tag
OLD_PATTERN = re.compile(
    r'<footer class="footer"><p>.*?</p></footer>|'
    r'<footer class="footer">\s*<p>.*?</p>\s*</footer>',
    re.DOTALL
)

updated = 0
for root, dirs, files in os.walk('frontend/templates'):
    for fname in files:
        if not fname.endswith('.html'):
            continue
        path = os.path.join(root, fname)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        if OLD_PATTERN.search(content):
            new_content = OLD_PATTERN.sub(NEW_FOOTER, content)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            updated += 1
            print(f"  Updated: {path}")

print(f"\nDone. Updated {updated} templates.")
