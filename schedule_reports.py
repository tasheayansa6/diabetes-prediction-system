"""
Scheduled report generation — run this via cron/Task Scheduler.

Example cron (weekly on Monday 8am):
    0 8 * * 1 cd /path/to/project && venv/bin/python schedule_reports.py

Example Windows Task Scheduler:
    Program: C:\path\to\venv\Scripts\python.exe
    Arguments: C:\path\to\schedule_reports.py
    Schedule: Weekly, Monday, 8:00 AM
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from backend import create_app
from backend.extensions import db
from datetime import datetime, timedelta
import json

app = create_app(os.getenv('FLASK_ENV', 'production'))

with app.app_context():
    from backend.models.user import User
    from backend.models.prediction import Prediction
    from backend.models.payment import Payment
    from sqlalchemy import text, func

    print(f"[{datetime.utcnow().isoformat()}] Generating scheduled reports...")

    # Weekly summary
    week_ago = datetime.utcnow() - timedelta(days=7)

    stats = {
        'period': f"{week_ago.date()} to {datetime.utcnow().date()}",
        'new_users': User.query.filter(User.created_at >= week_ago).count(),
        'new_predictions': Prediction.query.filter(Prediction.created_at >= week_ago).count(),
        'high_risk_count': Prediction.query.filter(
            Prediction.created_at >= week_ago,
            Prediction.risk_level.in_(['HIGH RISK', 'VERY HIGH RISK'])
        ).count(),
        'total_revenue': db.session.query(func.sum(Payment.total_amount)).filter(
            Payment.created_at >= week_ago,
            Payment.payment_status == 'completed'
        ).scalar() or 0
    }

    # Save to file
    report_path = f"reports/weekly_report_{datetime.utcnow().strftime('%Y%m%d')}.json"
    os.makedirs('reports', exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"  Report saved: {report_path}")
    print(f"  New users: {stats['new_users']}")
    print(f"  New predictions: {stats['new_predictions']}")
    print(f"  High risk: {stats['high_risk_count']}")
    print(f"  Revenue: ETB {stats['total_revenue']}")

    # Email to admins (if configured)
    try:
        from backend.services.notification_service import _send
        admins = User.query.filter_by(role='admin', is_active=True).all()
        for admin in admins:
            html = f"""<div style="font-family:Arial,sans-serif;padding:20px;">
                <h2>Weekly System Report</h2>
                <p>Period: {stats['period']}</p>
                <ul>
                    <li>New Users: {stats['new_users']}</li>
                    <li>New Predictions: {stats['new_predictions']}</li>
                    <li>High Risk Patients: {stats['high_risk_count']}</li>
                    <li>Revenue: ETB {stats['total_revenue']:.2f}</li>
                </ul>
            </div>"""
            _send("Weekly System Report — Diabetes Prediction System", admin.email, html)
    except Exception as e:
        print(f"  Email send skipped: {e}")

    print("Done.")
