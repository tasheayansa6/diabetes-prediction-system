"""
Payment Service — shared helpers used by payment_routes.py.
All DB persistence is handled in the routes; this module provides
pure utility functions with no side effects.
"""
from datetime import datetime
import uuid

# ── Service prices (ETB) ──────────────────────────────────────────────────────
SERVICE_PRICES = {
    'prediction_service':       45.00,
    'consultation':             50.00,
    'lab_test':                 75.00,
    'lab_test_fasting_glucose': 25.00,
    'lab_test_hba1c':           45.00,
    'lab_test_ogtt':            60.00,
    'lab_test_insulin':         55.00,
    'prescription':             50.00,
    'follow_up':                35.00,
}

TAX_RATE  = 0.08   # 8 %
CURRENCY  = 'ETB'

# Methods that stay "pending" until manually confirmed by staff
PENDING_METHODS = {'cash', 'insurance', 'bank_transfer'}

# Methods that are processed immediately (simulated / gateway-handled)
IMMEDIATE_METHODS = {'credit_card', 'debit_card', 'telebirr', 'cbe_birr',
                     'm_birr', 'chapa', 'paypal'}


# ── ID generators ─────────────────────────────────────────────────────────────
# Use 2-digit year (%y) to keep IDs within VARCHAR(20) on PostgreSQL
# PAY + 12 + 4 = 19 chars, INV + 12 + 4 = 19 chars

def generate_payment_id() -> str:
    return f"PAY{datetime.utcnow().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"


def generate_invoice_id() -> str:
    return f"INV{datetime.utcnow().strftime('%y%m%d%H%M%S')}{uuid.uuid4().hex[:4].upper()}"


def generate_tx_ref() -> str:
    # CHAPA- + 12 + - + 6 = 25 chars — stored in transaction_id VARCHAR(100)
    return f"CHAPA-{datetime.utcnow().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"


# ── Pricing helpers ───────────────────────────────────────────────────────────

def calculate_total(items: list) -> dict:
    """
    Calculate subtotal, tax, and grand total for a list of service items.
    Each item: {'service': str, 'quantity': int}
    """
    breakdown = []
    subtotal = 0.0
    for item in items:
        price = SERVICE_PRICES.get(item.get('service', ''), 0.0)
        qty   = int(item.get('quantity', 1))
        line  = price * qty
        breakdown.append({'service': item.get('service'), 'price': price,
                          'quantity': qty, 'subtotal': line})
        subtotal += line
    tax = round(subtotal * TAX_RATE, 2)
    return {
        'success':     True,
        'subtotal':    round(subtotal, 2),
        'tax':         tax,
        'grand_total': round(subtotal + tax, 2),
        'breakdown':   breakdown,
        'currency':    CURRENCY,
    }


def payment_status_for_method(method: str) -> str:
    """Return the initial payment status for a given payment method."""
    return 'pending' if method in PENDING_METHODS else 'completed'
