"""
Payment Service - Utility helpers for payment processing.
All persistence is handled via SQLAlchemy models in payment_routes.py.
"""

from datetime import datetime
import uuid

# Service prices in ETB
SERVICE_PRICES = {
    'consultation': 50.00,
    'lab_test_fasting_glucose': 25.00,
    'lab_test_hba1c': 45.00,
    'lab_test_ogtt': 60.00,
    'lab_test_insulin': 55.00,
    'prediction_service': 45.00,
    'prescription': 50.00,
    'follow_up': 35.00,
}

TAX_RATE = 0.08  # 8%
CURRENCY = 'ETB'


def calculate_total(items):
    """
    Calculate subtotal, tax, and grand total for a list of service items.
    Each item: {'service': str, 'quantity': int}
    Returns dict with subtotal, tax, grand_total, breakdown.
    """
    breakdown = []
    subtotal = 0.0
    for item in items:
        price = SERVICE_PRICES.get(item.get('service', ''), 0.0)
        qty = int(item.get('quantity', 1))
        line_total = price * qty
        breakdown.append({
            'service': item.get('service'),
            'price': price,
            'quantity': qty,
            'subtotal': line_total
        })
        subtotal += line_total
    tax = round(subtotal * TAX_RATE, 2)
    return {
        'success': True,
        'subtotal': round(subtotal, 2),
        'tax': tax,
        'grand_total': round(subtotal + tax, 2),
        'breakdown': breakdown,
        'currency': CURRENCY,
    }


def generate_payment_id():
    return f"PAY{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"


def generate_invoice_id():
    return f"INV{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"


def generate_tx_ref():
    return f"CHAPA-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
