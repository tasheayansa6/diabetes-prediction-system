// Payment Success Page
// Handles Chapa return redirect. Does NOT require auth — Chapa redirects here
// as a plain browser GET so we must work with or without a token.

const METHOD_NAMES = {
    credit_card: 'Credit Card', debit_card: 'Debit Card',
    mobile_banking: 'Mobile Banking', bank_transfer: 'Bank Transfer',
    paypal: 'PayPal', cash: 'Cash (Pay at Cashier)',
    insurance: 'Health Insurance', chapa: 'Chapa',
    telebirr: 'TeleBirr', cbe_birr: 'CBE Birr', m_birr: 'M-Birr'
};

// ── Role-aware dashboard resolver ───────────────────────────────────────────
// Returns the correct dashboard for the currently logged-in user.
// Falls back to `defaultTarget` (e.g. the service-specific page) if role unknown.
function _dashboardForCurrentUser(defaultTarget) {
    try {
        const u = JSON.parse(localStorage.getItem('user') || '{}');
        const map = {
            patient:        '/templates/patient/dashboard.html',
            doctor:         '/templates/doctor/dashboard.html',
            nurse:          '/templates/nurse/dashboard.html',
            lab_technician: '/templates/lab/dashboard.html',
            pharmacist:     '/templates/pharmacist/dashboard.html',
            admin:          '/templates/admin/dashboard.html',
        };
        return map[u.role] || defaultTarget || '/templates/patient/dashboard.html';
    } catch (_) {
        return defaultTarget || '/templates/patient/dashboard.html';
    }
}

// ── User ID helper ────────────────────────────────────────────────────────────
// Try to get user ID from localStorage. If missing (session lost during Chapa
// redirect), fall back to scanning all lastTransaction_* keys.
function _uid() {
    try {
        const u = JSON.parse(localStorage.getItem('user') || '{}');
        const id = u.id || u.user_id;
        if (id != null) return String(id);
    } catch (_) {}
    return null;
}

function txKey(uid)  { return 'lastTransaction_' + uid; }
function ctxKey(uid) { return 'chapaPendingContext_' + uid; }

// Find the stored transaction even if uid is unknown (session lost during Chapa)
function findTransaction(txRef) {
    const uid = _uid();

    // Try known uid first
    if (uid) {
        try {
            const raw = localStorage.getItem(txKey(uid));
            if (raw) {
                const t = JSON.parse(raw);
                if (!txRef || t.tx_ref === txRef || t.id === txRef) return { t, uid };
            }
        } catch (_) {}
    }

    // Scan all keys — handles case where session was lost during Chapa redirect
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('lastTransaction_')) {
            try {
                const t = JSON.parse(localStorage.getItem(key));
                if (t && (!txRef || t.tx_ref === txRef || t.id === txRef)) {
                    const scannedUid = key.replace('lastTransaction_', '');
                    return { t, uid: scannedUid };
                }
            } catch (_) {}
        }
    }
    return { t: {}, uid: uid || 'anon' };
}

// ── Restore / refresh session after Chapa redirect ──────────────────────────
// Always attempts a token refresh so an expired token gets renewed before
// navigating to the dashboard. Without this, checkAuth on the next page
// sees an expired token and redirects to login.
async function restoreSession() {
    const token = localStorage.getItem('token');
    if (!token) return;

    // Check if token is expired (or close to it — within 5 min)
    try {
        const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        const payload = JSON.parse(atob(b64 + '='.repeat((4 - b64.length % 4) % 4)));
        const secsLeft = (payload.exp || 0) - Math.floor(Date.now() / 1000);
        // Token still has plenty of time and user object is intact — skip refresh
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        if (secsLeft > 300 && user.id && user.role) return;
    } catch (_) {}

    // Refresh token
    try {
        const res = await fetch('/api/auth/refresh', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token }
        });
        if (!res.ok) return;
        const data = await res.json();
        if (data.success && data.token) {
            localStorage.setItem('token', data.token);
            if (data.user) {
                const stored = JSON.parse(localStorage.getItem('user') || '{}');
                const merged = Object.assign({}, stored);
                Object.keys(data.user).forEach(k => { if (data.user[k] != null) merged[k] = data.user[k]; });
                localStorage.setItem('user', JSON.stringify(merged));
            }
        }
    } catch (_) {}
}

// ── Chapa verification ────────────────────────────────────────────────────────
async function verifyChapaIfNeeded(txRef) {
    if (!txRef) return;

    const token = localStorage.getItem('token');
    const endpoint = token
        ? '/api/payments/chapa/verify?tx_ref=' + encodeURIComponent(txRef)
        : '/api/payments/chapa/verify-public?tx_ref=' + encodeURIComponent(txRef);

    try {
        const headers = token ? { Authorization: 'Bearer ' + token } : {};
        const res  = await fetch(endpoint, { headers });

        // 401 = token expired during Chapa flow — try public endpoint
        if (res.status === 401) {
            const res2 = await fetch(
                '/api/payments/chapa/verify-public?tx_ref=' + encodeURIComponent(txRef)
            );
            if (!res2.ok) return;
            const data2 = await res2.json();
            return data2.success ? 'success' : 'pending';
        }

        const data = await res.json().catch(() => ({}));
        return data.success ? 'success' : 'pending';
    } catch (_) {
        return null;
    }
}

// ── Run prediction directly from payment success page ────────────────────────
// Called when Chapa payment is verified and serviceContext === 'prediction'.
// Uses the pendingHealthData stored before the payment redirect.
async function runPredictionAfterPayment(uid) {
    const statusTitle = document.getElementById('statusTitle');
    const msg         = document.getElementById('statusMessage');
    const countdownEl = document.getElementById('redirectCountdown');

    // Read pending health data stored by the health form before redirecting to payment
    let body = null;
    try {
        const scoped = localStorage.getItem('pendingHealthData_' + uid);
        if (scoped) body = JSON.parse(scoped);
    } catch (_) {}
    if (!body) {
        try {
            const legacy = localStorage.getItem('pendingHealthData');
            if (legacy) body = JSON.parse(legacy);
        } catch (_) {}
    }

    if (!body) {
        // No pending data — fall back to health form
        if (msg) msg.textContent = 'Redirecting to health form...';
        if (countdownEl) countdownEl.textContent = '';
        await new Promise(r => setTimeout(r, 800));
        window.location.href = '/templates/patient/health_data_form.html';
        return;
    }

    if (statusTitle) statusTitle.textContent = 'Running Your Prediction...';
    if (msg)         msg.textContent = 'Payment confirmed! Analysing your health data now...';
    if (countdownEl) countdownEl.textContent = '⏳ Please wait — this takes a few seconds...';

    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/templates/patient/health_data_form.html';
        return;
    }

    try {
        const res  = await fetch('/api/patient/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            body: JSON.stringify(body)
        });
        const data = await res.json();

        if (data.success && data.prediction && data.prediction.id) {
            // Consume payment token
            fetch('/api/payments/consume-prediction-payment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token }
            }).catch(() => {});

            // Clean up pending data
            try { localStorage.removeItem('pendingHealthData_' + uid); } catch (_) {}
            try { localStorage.removeItem('pendingHealthData'); } catch (_) {}
            try { localStorage.removeItem('predictionPaid_' + uid); } catch (_) {}
            try { localStorage.removeItem('predictionPaid'); } catch (_) {}

            if (countdownEl) countdownEl.textContent = '✅ Prediction complete! Redirecting to your result...';
            await new Promise(r => setTimeout(r, 800));
            window.location.href = '/templates/patient/prediction_result.html?id=' + data.prediction.id;
        } else if (res.status === 402 || data.requires_payment) {
            // Payment not yet confirmed in DB — go to health form which will retry
            if (msg) msg.textContent = 'Payment processing... redirecting to health form.';
            await new Promise(r => setTimeout(r, 1000));
            window.location.href = '/templates/patient/health_data_form.html';
        } else {
            // Other error — go to health form with error context
            if (msg) msg.textContent = (data.message || 'Prediction failed') + ' — redirecting to health form.';
            await new Promise(r => setTimeout(r, 1500));
            window.location.href = '/templates/patient/health_data_form.html';
        }
    } catch (err) {
        if (msg) msg.textContent = 'Network error — redirecting to health form.';
        await new Promise(r => setTimeout(r, 1200));
        window.location.href = '/templates/patient/health_data_form.html';
    }
}
async function loadTransaction() {
    const statusTitle = document.getElementById('statusTitle');
    if (statusTitle) statusTitle.textContent = 'Confirming Payment...';

    // Step 1: restore session if lost during Chapa redirect
    await restoreSession();

    // Step 2: get tx_ref from URL
    const params = new URLSearchParams(window.location.search);
    const urlTxRef = params.get('tx_ref') || params.get('trx_ref') || params.get('reference');

    // Step 3: find stored transaction (works even if uid changed)
    const { t, uid } = findTransaction(urlTxRef);

    // Step 4: verify with Chapa if we have a tx_ref
    const txRef = urlTxRef || t.tx_ref;
    if (txRef) {
        const verifyStatus = await verifyChapaIfNeeded(txRef);
        if (verifyStatus === 'success') {
            t.status = 'success';
            // Write back with correct uid
            if (uid && uid !== 'anon') {
                localStorage.setItem(txKey(uid), JSON.stringify({ ...t, status: 'success' }));
            }
        }
    }

    // Step 5: if still no transaction data, build minimal from URL
    if (!t.id && txRef) {
        t.id = txRef;
        t.tx_ref = txRef;
        t.paymentMethod = 'chapa';
        t.status = 'success';
        t.date = new Date().toLocaleDateString();
    }

    // Step 6: display
    document.getElementById('transactionId').textContent     = t.id || '—';
    document.getElementById('transactionAmount').textContent = t.amount
        ? 'ETB ' + parseFloat(t.amount).toFixed(2) : '—';
    document.getElementById('transactionDate').textContent   = t.date || new Date().toLocaleDateString();
    document.getElementById('paymentMethod').textContent     = METHOD_NAMES[t.paymentMethod] || t.paymentMethod || '—';

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

    if (statusTitle) {
        statusTitle.textContent = isPending ? 'Payment Pending' : 'Payment Successful!';
        statusTitle.className   = 'text-2xl font-bold mb-2 ' + (isPending ? 'text-yellow-600' : 'text-green-600');
    }
    const msg = document.getElementById('statusMessage');
    if (msg) {
        msg.textContent = isPending
            ? 'Your payment is being confirmed. This may take a few minutes.'
            : (t.serviceContext === 'prediction' || (t.returnTo || '').includes('health')
                ? 'Payment confirmed! Taking you to your prediction now...'
                : 'Your payment has been confirmed.');
    }

    if (t.paymentMethod === 'cash') {
        const ci = document.getElementById('cashInstructions');
        if (ci) ci.style.display = 'block';
        showRefRow(t.referenceNumber);
    }
    if (t.paymentMethod === 'insurance') {
        const ii = document.getElementById('insuranceInstructions');
        if (ii) ii.style.display = 'block';
        showRefRow(t.referenceNumber);
    }

    // Step 7: set up Continue button and auto-redirect
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
    if (continueBtn) {
        continueBtn.href = target;
        continueBtn.style.display = 'inline-flex';
        continueBtn.onclick = async function(e) {
            e.preventDefault();
            await restoreSession();
            sessionStorage.setItem('_fromPayment', '1');
            window.location.href = target;
        };
    }

    // ── Set predictionPaid flag for pending cash/insurance payments ──────────
    // Cash/insurance payments are pending in DB but the patient has paid.
    // Set the flag so the health form can auto-run the prediction on return.
    const isPredictionPayment = (t.serviceContext === 'prediction' ||
        rawReturn === 'health_form' || rawReturn === 'health-form' || rawReturn === 'prediction');

    if (isPredictionPayment) {
        try {
            const storedUid = uid || 'anon';
            localStorage.setItem('predictionPaid_' + storedUid, 'true');
            localStorage.setItem('predictionPaid', 'true');
        } catch (_) {}
    }

    // ── For prediction payments: run prediction directly, skip health form ───
    if (isPredictionPayment && t.status === 'success') {
        // 10-second countdown so the user can see the payment confirmation
        const cdEl = document.getElementById('redirectCountdown');
        let cd = 10;
        if (cdEl) {
            cdEl.style.display = '';
            cdEl.textContent = 'Running your prediction in ' + cd + 's...';
        }
        await new Promise(resolve => {
            const iv = setInterval(() => {
                cd--;
                if (cdEl) {
                    cdEl.textContent = cd > 0
                        ? 'Running your prediction in ' + cd + 's...'
                        : 'Starting prediction...';
                }
                if (cd <= 0) { clearInterval(iv); resolve(); }
            }, 1000);
        });
        await runPredictionAfterPayment(uid || 'anon');
        return; // runPredictionAfterPayment handles all further navigation
    }

    // Auto-redirect after 3s for prediction, 5s for others
    const countdownEl = document.getElementById('redirectCountdown');
    let secs = isPredictionPayment ? 3 : 5;
    const autoTarget = target !== '/templates/patient/dashboard.html' ? target : _dashboardForCurrentUser(target);
    const redirectLabel = isPredictionPayment ? 'running your prediction' : 'dashboard';

    if (countdownEl) {
        countdownEl.style.display = '';
        countdownEl.textContent = isPredictionPayment
            ? 'Running your prediction in ' + secs + 's...'
            : 'Auto-redirecting to ' + redirectLabel + ' in ' + secs + 's...';
    }
    const timer = setInterval(async () => {
        secs--;
        if (countdownEl) {
            countdownEl.textContent = secs > 0
                ? (isPredictionPayment
                    ? 'Running your prediction in ' + secs + 's...'
                    : 'Auto-redirecting to ' + redirectLabel + ' in ' + secs + 's...')
                : 'Redirecting...';
        }
        if (secs <= 0) {
            clearInterval(timer);
            await restoreSession();
            sessionStorage.setItem('_fromPayment', '1');
            window.location.href = autoTarget;
        }
    }, 1000);
}

function showRefRow(ref) {
    const row = document.getElementById('refRow');
    if (row) row.style.cssText = 'display:flex !important';
    const el = document.getElementById('referenceNumber');
    if (el) el.textContent = ref || '—';
}

document.addEventListener('DOMContentLoaded', function () {
    // Show username if available
    try {
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        const nameEl = document.getElementById('navUserName');
        if (nameEl && (user.name || user.username)) {
            nameEl.textContent = user.name || user.username;
        }
    } catch (_) {}

    loadTransaction();
});
