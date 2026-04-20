// Payment Success Page
// Handles Chapa return redirect and displays transaction details.
// Does NOT require the user to be logged in to display — Chapa redirects here
// as a plain browser GET, so we show the page first, then verify in the background.

const METHOD_NAMES = {
    credit_card: 'Credit Card', debit_card: 'Debit Card',
    mobile_banking: 'Mobile Banking', bank_transfer: 'Bank Transfer',
    paypal: 'PayPal', cash: 'Cash (Pay at Cashier)',
    insurance: 'Health Insurance', chapa: 'Chapa',
    telebirr: 'TeleBirr', cbe_birr: 'CBE Birr', m_birr: 'M-Birr'
};

// ── User-scoped key helpers (mirrors payment-page.js) ─────────────────────────
// Keys are scoped to user ID so different users on the same browser
// never see each other's payment data.
function _uid() {
    try {
        const u = JSON.parse(localStorage.getItem('user') || '{}');
        // id is a number from the server — convert to string for consistent key
        const id = u.id || u.user_id;
        return id != null ? String(id) : 'anon';
    } catch (_) { return 'anon'; }
}
function txKey()  { return 'lastTransaction_' + _uid(); }
function ctxKey() { return 'chapaPendingContext_' + _uid(); }

// Read transaction for the CURRENT user only.
// Never falls back to legacy unscoped keys — that caused cross-user data leaks.
function readTransaction() {
    try {
        const raw = localStorage.getItem(txKey());
        if (!raw) return {};
        const t = JSON.parse(raw);
        // Extra safety: if the stored record has a userId that doesn't match, discard it
        if (t.userId != null && String(t.userId) !== _uid()) {
            localStorage.removeItem(txKey());
            return {};
        }
        return t;
    } catch (_) { return {}; }
}

function readContext() {
    try {
        const raw = localStorage.getItem(ctxKey());
        if (!raw) return {};
        return JSON.parse(raw);
    } catch (_) { return {}; }
}

// ── Chapa verification ────────────────────────────────────────────────────────
async function verifyChapaIfNeeded() {
    // tx_ref comes from the URL when Chapa redirects back (?tx_ref=...)
    const params = new URLSearchParams(window.location.search);
    let txRef = params.get('tx_ref') || params.get('trx_ref') || params.get('reference');

    // Fallback: read from stored pending context
    if (!txRef) {
        const ctx = readContext();
        if (ctx.tx_ref) txRef = ctx.tx_ref;
    }
    if (!txRef) {
        const t = readTransaction();
        if (t.paymentMethod === 'chapa' && t.status === 'pending' && t.tx_ref) txRef = t.tx_ref;
    }
    if (!txRef) return;

    const token = localStorage.getItem('token');
    if (!token) {
        // No token — mark as pending, user will see the pending state
        // The webhook will update the DB in the background
        const t = readTransaction();
        if (t.tx_ref === txRef) {
            // Already have the transaction stored — just show it
        }
        return;
    }

    try {
        const res = await fetch('/api/payments/chapa/verify?tx_ref=' + encodeURIComponent(txRef), {
            headers: { Authorization: 'Bearer ' + token }
        });
        const data = await res.json().catch(() => ({}));

        const t   = readTransaction();
        const ctx = readContext();

        const merged = {
            ...t,
            id: t.id || data.payment_id || txRef,
            tx_ref: txRef,
            paymentMethod: 'chapa',
            status: data.success ? 'success' : (t.status || 'pending'),
            serviceContext: ctx.serviceContext || t.serviceContext,
            returnTo: ctx.returnTo || t.returnTo,
            userId: _uid(),
        };

        // Write back to scoped key only — never write to legacy unscoped keys
        const merged_str = JSON.stringify(merged);
        localStorage.setItem(txKey(), merged_str);
        // Clean up legacy keys to prevent future cross-user leaks
        localStorage.removeItem('lastTransaction');
        localStorage.removeItem('chapaPendingContext');
        localStorage.removeItem(ctxKey());

        if (merged.serviceContext === 'prediction' ||
            (merged.services || []).some(s => (s.name || '').toLowerCase().includes('prediction'))) {
            localStorage.setItem('predictionPaid_' + _uid(), 'true');
            localStorage.setItem('predictionPaid', 'true');
        }
        if (merged.serviceContext === 'lab') {
            localStorage.setItem('labPaid_' + _uid(), 'true');
            localStorage.setItem('labPaid', 'true');
        }
    } catch (_) {
        /* non-fatal — show whatever we have stored */
    }
}

// ── Display ───────────────────────────────────────────────────────────────────
async function loadTransaction() {
    // Show a loading state immediately
    const statusTitle = document.getElementById('statusTitle');
    if (statusTitle) statusTitle.textContent = 'Confirming Payment...';

    await verifyChapaIfNeeded();

    const t = readTransaction();

    // If we have a tx_ref in the URL but nothing in storage, build a minimal record
    const params = new URLSearchParams(window.location.search);
    const urlTxRef = params.get('tx_ref') || params.get('trx_ref');
    if (!t.id && urlTxRef) {
        t.id = urlTxRef;
        t.tx_ref = urlTxRef;
        t.paymentMethod = 'chapa';
        t.status = 'success';
        t.date = new Date().toLocaleDateString();
    }

    document.getElementById('transactionId').textContent    = t.id || '—';
    document.getElementById('transactionAmount').textContent = t.amount
        ? 'ETB ' + parseFloat(t.amount).toFixed(2) : '—';
    document.getElementById('transactionDate').textContent  = t.date || new Date().toLocaleDateString();
    document.getElementById('paymentMethod').textContent    = METHOD_NAMES[t.paymentMethod] || t.paymentMethod || '—';

    if (t.invoice_id) {
        const invoiceBtn = document.querySelector('a[href*="invoice.html"]');
        if (invoiceBtn) invoiceBtn.href = '/templates/payment/invoice.html?id=' + t.invoice_id;
    }

    const isPending = t.status === 'pending';
    const badge = document.getElementById('paymentStatus');
    if (badge) {
        badge.textContent = isPending ? 'Pending Confirmation' : 'Completed';
        badge.className   = isPending ? 'badge bg-warning text-dark' : 'badge bg-success';
    }

    // Update title/icon for Chapa success
    if (t.paymentMethod === 'chapa' && !isPending) {
        const icon = document.getElementById('statusIcon');
        if (icon) icon.className = 'bi bi-check-circle-fill text-6xl text-green-500 mb-4';
        if (statusTitle) {
            statusTitle.textContent  = 'Payment Successful!';
            statusTitle.className    = 'text-2xl font-bold mb-2 text-green-600';
        }
        const msg = document.getElementById('statusMessage');
        if (msg) msg.textContent = 'Your Chapa payment has been confirmed.';
    }

    if (t.paymentMethod === 'cash') {
        const icon = document.getElementById('statusIcon');
        if (icon) icon.className = 'bi bi-receipt text-6xl text-yellow-500 mb-4';
        if (statusTitle) { statusTitle.textContent = 'Reference Number Generated!'; statusTitle.className = 'text-2xl font-bold mb-2 text-yellow-600'; }
        const msg = document.getElementById('statusMessage');
        if (msg) msg.textContent = 'Please pay at the hospital cashier desk.';
        const ci = document.getElementById('cashInstructions');
        if (ci) ci.style.display = 'block';
        showRefRow(t.referenceNumber);
    }

    if (t.paymentMethod === 'insurance') {
        const icon = document.getElementById('statusIcon');
        if (icon) icon.className = 'bi bi-shield-check text-6xl text-blue-500 mb-4';
        if (statusTitle) { statusTitle.textContent = 'Insurance Claim Submitted!'; statusTitle.className = 'text-2xl font-bold mb-2 text-blue-600'; }
        const msg = document.getElementById('statusMessage');
        if (msg) msg.textContent = 'Your claim is pending approval from your insurance provider.';
        const ii = document.getElementById('insuranceInstructions');
        if (ii) ii.style.display = 'block';
        showRefRow(t.referenceNumber);
    }

    // Show "Continue" button — check if user is logged in first.
    // If logged in as the correct user, go directly to the target page.
    // If not logged in (or different user), go to login with a next= redirect.
    if (t.id) {
        const returnMap = {
            'health_form':  '/templates/patient/health_data_form.html',
            'health-form':  '/templates/patient/health_data_form.html',
            'prediction':   '/templates/patient/health_data_form.html',
        };
        const rawReturn = t.returnTo || '';
        const resolvedReturn = returnMap[rawReturn] || (rawReturn.startsWith('/') ? rawReturn : '');

        const target = resolvedReturn ||
            (t.serviceContext === 'prediction'   ? '/templates/patient/health_data_form.html' :
             t.serviceContext === 'lab'          ? '/templates/patient/lab_results.html?paid=true' :
             t.serviceContext === 'consultation' ? '/templates/patient/appointment.html?paid=true' :
             t.serviceContext === 'medication'   ? '/templates/patient/prescriptions.html?paid=true' :
             '/templates/patient/dashboard.html');

        const continueBtn = document.getElementById('continueBtn');
        const countdownEl = document.getElementById('redirectCountdown');
        if (countdownEl) countdownEl.style.display = 'none';

        if (continueBtn) {
            // Check if a valid token exists for the correct user
            const token = localStorage.getItem('token');
            const storedUser = JSON.parse(localStorage.getItem('user') || '{}');
            let isLoggedIn = false;
            if (token && storedUser.role) {
                try {
                    const payload = JSON.parse(atob(token.split('.')[1]));
                    isLoggedIn = payload.exp && payload.exp * 1000 > Date.now();
                } catch (_) {}
            }

            if (isLoggedIn) {
                // User is logged in — go straight to the target
                continueBtn.href = target;
            } else {
                // Not logged in — go to login, then redirect to target after sign-in
                continueBtn.href = '/login?next=' + encodeURIComponent(target);
                continueBtn.innerHTML = '<i class="bi bi-box-arrow-in-right"></i> Sign In to Continue';
            }
            continueBtn.style.display = 'inline-flex';
        }
    }
}

function showRefRow(ref) {
    const row = document.getElementById('refRow');
    if (row) row.style.cssText = 'display:flex !important';
    const el = document.getElementById('referenceNumber');
    if (el) el.textContent = ref || '—';
}

// ── Init — does NOT call checkAuth so Chapa return always lands here ──────────
document.addEventListener('DOMContentLoaded', function () {
    // Try to show username if logged in, but don't redirect if not
    try {
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        const nameEl = document.getElementById('navUserName');
        if (nameEl && user.username) nameEl.textContent = user.username;
    } catch (_) {}

    loadTransaction();
});
