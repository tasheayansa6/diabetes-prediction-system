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

// ── Role-aware dashboard resolver ────────────────────────────────────────────
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

// ── Restore / refresh session after Chapa redirect ───────────────────────────
async function restoreSession() {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
        const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        const payload = JSON.parse(atob(b64 + '='.repeat((4 - b64.length % 4) % 4)));
        const secsLeft = (payload.exp || 0) - Math.floor(Date.now() / 1000);
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        if (secsLeft > 300 && user.id && user.role) return;
    } catch (_) {}

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
    if (!txRef) return null;

    const token = localStorage.getItem('token');
    const endpoint = token
        ? '/api/payments/chapa/verify?tx_ref=' + encodeURIComponent(txRef)
        : '/api/payments/chapa/verify-public?tx_ref=' + encodeURIComponent(txRef);

    try {
        const headers = token ? { Authorization: 'Bearer ' + token } : {};
        const res = await fetch(endpoint, { headers });

        // 401 = token expired — try public endpoint
        if (res.status === 401) {
            const res2 = await fetch('/api/payments/chapa/verify-public?tx_ref=' + encodeURIComponent(txRef));
            if (!res2.ok) return null;
            const data2 = await res2.json();
            return data2.success ? 'success' : 'pending';
        }

        const data = await res.json().catch(() => ({}));
        return data.success ? 'success' : 'pending';
    } catch (_) {
        return null;
    }
}

// ── Main: load and display transaction, then redirect ────────────────────────
async function loadTransaction() {
    const statusTitle = document.getElementById('statusTitle');
    if (statusTitle) statusTitle.textContent = 'Confirming Payment...';

    // Step 1: restore session if lost during Chapa redirect
    await restoreSession();

    // Step 2: get tx_ref from URL
    const params   = new URLSearchParams(window.location.search);
    const urlTxRef = params.get('tx_ref') || params.get('trx_ref') || params.get('reference');

    // Step 3: find stored transaction
    const { t, uid } = findTransaction(urlTxRef);

    // Step 4: verify with Chapa (marks payment completed in DB)
    const txRef = urlTxRef || t.tx_ref;
    if (txRef) {
        const verifyStatus = await verifyChapaIfNeeded(txRef);
        if (verifyStatus === 'success') {
            t.status = 'success';
            if (uid && uid !== 'anon') {
                try { localStorage.setItem(txKey(uid), JSON.stringify({ ...t, status: 'success' })); } catch (_) {}
            }
        }
    }

    // Step 5: if no transaction data at all, build minimal from URL
    if (!t.id && txRef) {
        t.id          = txRef;
        t.tx_ref      = txRef;
        t.paymentMethod = 'chapa';
        t.status      = 'success';
        t.date        = new Date().toLocaleDateString();
    }

    // Step 6: display transaction details
    const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    setText('transactionId',     t.id || '—');
    setText('transactionAmount', t.amount ? 'ETB ' + parseFloat(t.amount).toFixed(2) : '—');
    setText('transactionDate',   t.date  || new Date().toLocaleDateString());
    setText('paymentMethod',     METHOD_NAMES[t.paymentMethod] || t.paymentMethod || '—');

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

    const rawReturn = t.returnTo || '';
    const isPredictionPayment = (
        t.serviceContext === 'prediction' ||
        rawReturn === 'health_form' ||
        rawReturn === 'health-form' ||
        rawReturn === 'prediction'
    );

    const msg = document.getElementById('statusMessage');
    if (msg) {
        msg.textContent = isPending
            ? 'Your payment is being confirmed. This may take a few minutes.'
            : (isPredictionPayment
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

    // ── Pending cash/insurance prediction payment: show "Check & Run" button ──
    // Patient pays cash/insurance → status is 'pending' → admin approves → patient
    // clicks this button → server confirms → prediction runs automatically
    if (isPending && isPredictionPayment) {
        const cdEl = document.getElementById('redirectCountdown');
        if (cdEl) {
            cdEl.style.display = '';
            cdEl.innerHTML =
                '<div style="margin-top:1.25rem;padding:1.25rem;background:#fef9c3;border:1px solid #fde047;border-radius:12px;text-align:center;">' +
                '<p style="margin:0 0 .75rem;font-size:.9rem;color:#854d0e;">' +
                '<strong>⏳ Waiting for admin to confirm your payment.</strong><br>' +
                'After the cashier/admin approves, click the button below.</p>' +
                '<button id="checkPaymentBtn" onclick="checkAndRunPrediction()" ' +
                'style="background:#059669;color:#fff;border:none;border-radius:8px;padding:.65rem 1.75rem;font-weight:700;cursor:pointer;font-size:.9rem;">' +
                '✅ Payment Approved — Run My Prediction</button>' +
                '<p id="checkPaymentMsg" style="margin:.75rem 0 0;font-size:.82rem;color:#64748b;"></p>' +
                '</div>';
        }
        return; // Don't start countdown — wait for manual check
    }

    // Step 7: set up Continue button
    const returnMap = {
        'health_form':  '/templates/patient/health_data_form.html',
        'health-form':  '/templates/patient/health_data_form.html',
        'prediction':   '/templates/patient/health_data_form.html',
    };
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
            window.location.href = isPredictionPayment
                ? '/templates/patient/health_data_form.html'
                : target;
        };
    }

    // Step 8: set predictionPaid flag (all uid variants so health form always finds it)
    if (isPredictionPayment) {
        try {
            const storedUid  = uid || 'anon';
            const sessionUid = _uid();
            localStorage.setItem('predictionPaid_' + storedUid, 'true');
            if (sessionUid && sessionUid !== storedUid) {
                localStorage.setItem('predictionPaid_' + sessionUid, 'true');
            }
            localStorage.setItem('predictionPaid', 'true');
        } catch (_) {}
    }

    // Step 9: auto-redirect
    const cdEl = document.getElementById('redirectCountdown');

    if (isPredictionPayment) {
        // 10-second countdown then go to health form which auto-runs prediction
        let cd = 10;
        if (cdEl) { cdEl.style.display = ''; cdEl.textContent = 'Taking you to your prediction in ' + cd + 's...'; }
        const iv = setInterval(async () => {
            cd--;
            if (cdEl) cdEl.textContent = cd > 0 ? 'Taking you to your prediction in ' + cd + 's...' : 'Loading...';
            if (cd <= 0) {
                clearInterval(iv);
                await restoreSession();
                sessionStorage.setItem('_fromPayment', '1');
                window.location.href = '/templates/patient/health_data_form.html';
            }
        }, 1000);
    } else {
        // 5-second countdown to dashboard for non-prediction payments
        let secs = 5;
        const autoTarget = _dashboardForCurrentUser(target);
        if (cdEl) { cdEl.style.display = ''; cdEl.textContent = 'Redirecting to dashboard in ' + secs + 's...'; }
        const timer = setInterval(async () => {
            secs--;
            if (cdEl) cdEl.textContent = secs > 0 ? 'Redirecting to dashboard in ' + secs + 's...' : 'Redirecting...';
            if (secs <= 0) {
                clearInterval(timer);
                await restoreSession();
                sessionStorage.setItem('_fromPayment', '1');
                window.location.href = autoTarget;
            }
        }, 1000);
    }
}

function showRefRow(ref) {
    const row = document.getElementById('refRow');
    if (row) row.style.cssText = 'display:flex !important';
    const el = document.getElementById('referenceNumber');
    if (el) el.textContent = ref || '—';
}

// ── Check payment status and redirect to prediction ───────────────────────────
// Called when patient clicks "Payment Approved — Run My Prediction" button
async function checkAndRunPrediction() {
    const btn   = document.getElementById('checkPaymentBtn');
    const msgEl = document.getElementById('checkPaymentMsg');
    if (btn)   { btn.disabled = true; btn.textContent = '⏳ Checking...'; }
    if (msgEl) { msgEl.textContent = ''; msgEl.style.color = '#64748b'; }

    const token = localStorage.getItem('token');
    if (!token) {
        if (msgEl) { msgEl.textContent = 'Session expired. Please log in again.'; msgEl.style.color = '#dc2626'; }
        if (btn)   { btn.disabled = false; btn.textContent = '🔄 Check Again'; }
        return;
    }

    try {
        const res  = await fetch('/api/payments/check-prediction-access', {
            headers: { Authorization: 'Bearer ' + token }
        });
        const data = await res.json();

        if (data.has_access) {
            // Payment confirmed by admin — go to health form which auto-runs prediction
            if (msgEl) { msgEl.textContent = '✅ Payment confirmed! Taking you to your prediction...'; msgEl.style.color = '#059669'; }
            if (btn)   { btn.textContent = '✅ Confirmed! Redirecting...'; }

            // Set predictionPaid flag so health form auto-runs
            try {
                const uid = _uid() || 'anon';
                localStorage.setItem('predictionPaid_' + uid, 'true');
                localStorage.setItem('predictionPaid', 'true');
            } catch (_) {}

            await restoreSession();
            sessionStorage.setItem('_fromPayment', '1');
            setTimeout(() => {
                window.location.href = '/templates/patient/health_data_form.html';
            }, 800);

        } else if (data.requires_admin_approval) {
            // Still pending — admin hasn't approved yet
            if (msgEl) {
                msgEl.style.color = '#d97706';
                msgEl.textContent = '⏳ Not yet approved. Ask the cashier/admin to confirm your payment, then click again.';
            }
            if (btn) { btn.disabled = false; btn.textContent = '🔄 Check Again'; }

        } else {
            // No payment found at all
            if (msgEl) {
                msgEl.style.color = '#dc2626';
                msgEl.textContent = '❌ No payment found. Please go back and complete payment.';
            }
            if (btn) { btn.disabled = false; btn.textContent = '🔄 Check Again'; }
        }
    } catch (_) {
        if (msgEl) { msgEl.textContent = 'Network error. Please try again.'; msgEl.style.color = '#dc2626'; }
        if (btn)   { btn.disabled = false; btn.textContent = '🔄 Check Again'; }
    }
}

document.addEventListener('DOMContentLoaded', function () {
    try {
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        const nameEl = document.getElementById('navUserName');
        if (nameEl && (user.name || user.username)) nameEl.textContent = user.name || user.username;
    } catch (_) {}

    loadTransaction();

    // ── Always check server for pending prediction payment ────────────────────
    // This handles the case where patient returns after logout (localStorage gone)
    // If they have a pending prediction payment, show the check button
    const token = localStorage.getItem('token');
    if (token) {
        fetch('/api/payments/check-prediction-access', {
            headers: { Authorization: 'Bearer ' + token }
        }).then(r => r.json()).then(data => {
            if (data.requires_admin_approval) {
                // Show the check button even if localStorage transaction is gone
                const cdEl = document.getElementById('redirectCountdown');
                if (cdEl && !cdEl.innerHTML.includes('checkPaymentBtn')) {
                    cdEl.style.display = '';
                    cdEl.innerHTML =
                        '<div style="margin-top:1.25rem;padding:1.25rem;background:#fef9c3;border:1px solid #fde047;border-radius:12px;text-align:center;">' +
                        '<p style="margin:0 0 .75rem;font-size:.9rem;color:#854d0e;">' +
                        '<strong>⏳ Your payment is awaiting admin confirmation.</strong><br>' +
                        'Once the cashier/admin approves, click the button below.</p>' +
                        '<button id="checkPaymentBtn" onclick="checkAndRunPrediction()" ' +
                        'style="background:#059669;color:#fff;border:none;border-radius:8px;padding:.65rem 1.75rem;font-weight:700;cursor:pointer;font-size:.9rem;">' +
                        '✅ Payment Approved — Run My Prediction</button>' +
                        '<p id="checkPaymentMsg" style="margin:.75rem 0 0;font-size:.82rem;color:#64748b;"></p>' +
                        '</div>';
                }
            }
        }).catch(() => {});
    }
});
