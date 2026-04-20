// Payment Page JS
// Methods: chapa (primary), cash, insurance

const FX_RATES = {
    ETB:1, USD:0.0175, EUR:0.0161, GBP:0.0138,
    AED:0.0643, SAR:0.0656, CNY:0.1268, INR:1.458, CAD:0.0238, AUD:0.0268
};
const CURRENCY_SYMBOLS = { ETB:'ETB', USD:'$', EUR:'€', GBP:'£', AED:'AED', SAR:'SAR', CNY:'¥', INR:'₹', CAD:'CA$', AUD:'A$' };

let selectedServices = [];
let totalAmount = 0;

// ── User-scoped localStorage keys ─────────────────────────────────────────────
// Prefix every key with the logged-in user's ID so different users on the same
// browser never see each other's payment data.
function _uid() {
    try {
        const u = JSON.parse(localStorage.getItem('user') || '{}');
        return u.id || u.user_id || 'anon';
    } catch (_) { return 'anon'; }
}
function txKey()      { return 'lastTransaction_' + _uid(); }
function ctxKey()     { return 'chapaPendingContext_' + _uid(); }
function labKey()     { return 'lab_request_id_' + _uid(); }
function paidKey(k)   { return k + '_' + _uid(); }

function getSelectedCurrency() {
    return document.getElementById('currencySelect')?.value || 'ETB';
}

function formatAmount(etbAmount) {
    const cur = getSelectedCurrency();
    const sym = CURRENCY_SYMBOLS[cur] || cur;
    return sym + ' ' + (etbAmount * (FX_RATES[cur] || 1)).toFixed(2);
}

function changeCurrency() {
    const cur = getSelectedCurrency();
    const rate = FX_RATES[cur] || 1;
    document.getElementById('rateNote').textContent = cur === 'ETB'
        ? 'Prices stored and charged in ETB.'
        : 'Approx. rate: 1 ETB ≈ ' + rate.toFixed(4) + ' ' + cur + '. Charges processed in ETB.';
    document.querySelectorAll('.svc-price').forEach(el => {
        el.textContent = formatAmount(parseFloat(el.dataset.etb));
    });
    updateTotal();
}

function authHeaders() {
    return { 'Content-Type':'application/json', 'Authorization':'Bearer ' + localStorage.getItem('token') };
}

function getServiceContext() {
    const p = new URLSearchParams(window.location.search);
    const from = (p.get('service') || '').toLowerCase();
    if (['prediction','consultation','lab','medication'].includes(from)) return from;
    const names = selectedServices.map(s => (s.name || '').toLowerCase());
    if (names.some(n => n.includes('prediction'))) return 'prediction';
    if (names.some(n => n.includes('consultation'))) return 'consultation';
    if (names.some(n => n.includes('lab'))) return 'lab';
    if (names.some(n => n.includes('medication'))) return 'medication';
    return '';
}

function getReturnTarget() {
    return new URLSearchParams(window.location.search).get('return') || '';
}

function nextPageAfterPayment(serviceContext, returnTo) {
    const map = {
        health_form:   '/templates/patient/health_data_form.html',
        'health-form': '/templates/patient/health_data_form.html',
        prediction:    '/templates/patient/health_data_form.html',
        lab:           '/templates/patient/lab_results.html',
        appointment:   '/templates/patient/appointment.html',
        prescriptions: '/templates/patient/prescriptions.html',
    };
    const resolved = map[returnTo] || (returnTo?.startsWith('/') ? returnTo : null);
    if (resolved) return resolved;
    if (serviceContext === 'prediction') return '/templates/patient/health_data_form.html';
    if (serviceContext === 'lab')        return '/templates/patient/lab_results.html?paid=true';
    if (serviceContext === 'consultation') return '/templates/patient/appointment.html?paid=true';
    if (serviceContext === 'medication') return '/templates/patient/prescriptions.html?paid=true';
    return '/templates/payment/payment_success.html';
}

function updateTotal() {
    selectedServices = [];
    let subtotal = 0;
    document.querySelectorAll('input[type="checkbox"]:checked').forEach(cb => {
        selectedServices.push({ name: cb.dataset.name, price: parseFloat(cb.value) });
        subtotal += parseFloat(cb.value);
    });
    const tax = subtotal * 0.08;
    totalAmount = subtotal + tax;

    document.getElementById('selectedServices').innerHTML = selectedServices.length === 0
        ? '<p class="text-gray-400 text-sm">Select services to see pricing</p>'
        : selectedServices.map(s =>
            '<div class="flex justify-between mb-2 text-sm"><span>' + s.name + '</span><strong>' + formatAmount(s.price) + '</strong></div>'
          ).join('');

    document.getElementById('subtotal').textContent = formatAmount(subtotal);
    document.getElementById('tax').textContent      = formatAmount(tax);
    document.getElementById('total').textContent    = formatAmount(totalAmount);
}

function togglePaymentFields() {
    const method = document.querySelector('input[name="paymentMethod"]:checked')?.value;
    ['chapaFields','cashFields','insuranceFields'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    if (method === 'chapa')     document.getElementById('chapaFields').style.display = 'block';
    if (method === 'cash')      document.getElementById('cashFields').style.display = 'block';
    if (method === 'insurance') document.getElementById('insuranceFields').style.display = 'block';

    const btnText = document.getElementById('submitBtnText');
    if (btnText) {
        btnText.textContent = method === 'chapa'     ? 'Pay with Chapa'
                            : method === 'cash'      ? 'Get Reference Number'
                            : method === 'insurance' ? 'Submit Insurance Claim'
                            : 'Pay Securely';
    }
}

function showAlert(message, type = 'danger') {
    let el = document.getElementById('paymentAlert');
    if (!el) {
        el = document.createElement('div');
        el.id = 'paymentAlert';
        document.getElementById('paymentForm').prepend(el);
    }
    el.innerHTML = '<div class="alert alert-' + type + ' alert-dismissible fade show mb-3">' +
        message + '<button type="button" class="btn-close" onclick="this.parentElement.remove()"></button></div>';
}

async function processPayment(event) {
    event.preventDefault();
    if (selectedServices.length === 0) { showAlert('Please select at least one service.'); return; }

    const method = document.querySelector('input[name="paymentMethod"]:checked')?.value;

    if (method === 'cash') {
        if (!document.getElementById('cashPayerName').value || !document.getElementById('cashPhone').value) {
            showAlert('Please enter your name and phone number.'); return;
        }
    } else if (method === 'insurance') {
        if (!document.getElementById('insuranceProvider').value ||
            !document.getElementById('policyNumber').value ||
            !document.getElementById('insuranceHolderName').value) {
            showAlert('Please fill in all insurance details.'); return;
        }
    } else if (method === 'chapa') {
        await initiateChapaPayment(); return;
    }

    if (!document.getElementById('billingAddress').value) {
        showAlert('Please enter billing address.'); return;
    }

    const btn = document.getElementById('submitBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';

    const subtotal = selectedServices.reduce((s, x) => s + x.price, 0);
    const tax = subtotal * 0.08;
    const serviceContext = getServiceContext();
    const returnTo = getReturnTarget();
    const labRequestId = localStorage.getItem(labKey());

    const payload = {
        amount: subtotal, tax, currency: 'ETB',
        payment_method: method,
        payment_type: serviceContext === 'prediction' ? 'prediction' : 'services',
        notes: selectedServices.map(s => s.name).join(', '),
        billing_address: document.getElementById('billingAddress').value,
        ...(labRequestId && { lab_request_id: labRequestId }),
    };

    if (method === 'cash') {
        payload.payer_name  = document.getElementById('cashPayerName').value;
        payload.payer_phone = document.getElementById('cashPhone').value;
        payload.notes += ' | Cash: ' + payload.payer_name + ' (' + payload.payer_phone + ')';
    } else if (method === 'insurance') {
        payload.insurance_company       = document.getElementById('insuranceProvider').value;
        payload.insurance_claim_number  = document.getElementById('policyNumber').value;
        payload.insurance_holder        = document.getElementById('insuranceHolderName').value;
        payload.notes += ' | Insurance: ' + payload.insurance_company + ' | Policy: ' + payload.insurance_claim_number;
    }

    try {
        const res  = await fetch('/api/payments/process', { method:'POST', headers:authHeaders(), body:JSON.stringify(payload) });
        const data = await res.json();
        if (!data.success) throw new Error(data.message || 'Payment failed');

        localStorage.setItem(txKey(), JSON.stringify({
            id: data.payment.payment_id, invoice_id: data.invoice.invoice_id,
            services: selectedServices, serviceContext, returnTo,
            paymentMethod: method, amount: data.payment.total_amount,
            currency: 'ETB', date: new Date().toISOString().split('T')[0],
            status: data.payment.is_pending ? 'pending' : 'success',
            referenceNumber: data.payment.is_pending ? data.payment.payment_id : null,
            userId: _uid(),
        }));
        // Clean up legacy keys
        localStorage.removeItem('lastTransaction');
        localStorage.removeItem('chapaPendingContext');

        if (data.payment.payment_type === 'prediction' || serviceContext === 'prediction') {
            localStorage.setItem(paidKey('predictionPaid'), 'true');
            // Also write legacy key so health form can read it on return
            localStorage.setItem('predictionPaid', 'true');
        }
        window.location.href = data.payment.is_pending
            ? '/templates/payment/payment_success.html'
            : nextPageAfterPayment(serviceContext, returnTo);

    } catch (err) {
        localStorage.setItem('lastError', JSON.stringify({ code:'PAYMENT_ERROR', message:err.message, date:new Date().toISOString().split('T')[0] }));
        window.location.href = '/templates/payment/payment_failed.html';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-lock"></i> <span id="submitBtnText">Pay Securely</span>';
    }
}

async function initiateChapaPayment() {
    if (selectedServices.length === 0) { showAlert('Please select at least one service.'); return; }

    const btn = document.getElementById('submitBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Connecting to Chapa...';

    const subtotal = selectedServices.reduce((s, x) => s + x.price, 0);
    const tax = subtotal * 0.08;
    const serviceContext = getServiceContext();
    const returnTo = getReturnTarget();
    const labRequestId = localStorage.getItem(labKey());

    try {
        const res = await fetch('/api/payments/chapa/initialize', {
            method: 'POST', headers: authHeaders(),
            body: JSON.stringify({
                amount: subtotal, tax, currency: 'ETB',
                payment_type: serviceContext === 'prediction' ? 'prediction' : 'services',
                notes: selectedServices.map(s => s.name).join(', '),
                billing_address: document.getElementById('billingAddress')?.value || '',
                ...(labRequestId && { lab_request_id: labRequestId }),
            }),
        });
        const data = await res.json();

        if (!data.success) {
            if (data.use_cash) {
                showAlert('Chapa is not available right now. Please use Cash payment.', 'warning');
                document.getElementById('cashPayment').checked = true;
                togglePaymentFields();
            } else {
                showAlert(data.message || 'Chapa initialization failed.');
            }
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-lock"></i> <span id="submitBtnText">Pay with Chapa</span>';
            return;
        }

        // Store transaction data scoped to this user ONLY — no legacy keys
        localStorage.setItem(txKey(), JSON.stringify({
            id: data.payment_id, invoice_id: data.invoice_id, tx_ref: data.tx_ref,
            services: selectedServices, paymentMethod: 'chapa',
            amount: subtotal + tax, currency: 'ETB',
            date: new Date().toISOString().split('T')[0],
            status: 'pending', referenceNumber: data.tx_ref,
            serviceContext, returnTo, userId: _uid(),
        }));
        localStorage.setItem(ctxKey(), JSON.stringify({
            serviceContext, returnTo, tx_ref: data.tx_ref,
            lab_request_id: labRequestId || null,
            userId: _uid(),
        }));

        // Clean up any legacy unscoped keys from previous sessions
        localStorage.removeItem('lastTransaction');
        localStorage.removeItem('chapaPendingContext');

        window.location.href = data.checkout_url;

    } catch (err) {
        showAlert(err.message || 'Could not connect to Chapa. Please try Cash payment.');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-lock"></i> <span id="submitBtnText">Pay with Chapa</span>';
    }
}

function preselectServices() {
    const params = new URLSearchParams(window.location.search);
    const service = params.get('service');
    const map = { prediction:'service1', consultation:'service2', lab:'service3', medication:'service4' };
    if (map[service]) {
        const cb = document.getElementById(map[service]);
        if (cb) { cb.checked = true; }
    }

    const labReqId = params.get('lab_request_id');
    if (labReqId) {
        localStorage.setItem(labKey(), labReqId);
        // Also write legacy key
        localStorage.setItem('lab_request_id', labReqId);
        const labCost = params.get('lab_cost');
        const labName = params.get('lab_name');
        if (labCost && labName) {
            const cb = document.getElementById('service3');
            if (cb) {
                cb.value = labCost;
                cb.dataset.name = labName;
                const priceEl = cb.closest('label')?.querySelector('.svc-price');
                if (priceEl) { priceEl.textContent = 'ETB ' + parseFloat(labCost).toFixed(2); priceEl.dataset.etb = labCost; }
                cb.checked = true;
            }
        }
    }

    updateTotal();

    // Check Chapa status — disable if not configured
    fetch('/api/payments/chapa/status').then(r => r.json()).then(d => {
        if (d.mode === 'disabled') {
            const chapaInput = document.getElementById('chapaPayment');
            const chapaCard  = document.getElementById('chapaMethodCard');
            if (chapaInput) chapaInput.disabled = true;
            if (chapaCard)  {
                chapaCard.style.opacity = '.4';
                chapaCard.title = 'Chapa not configured — use Cash';
            }
            const cashInput = document.getElementById('cashPayment');
            if (cashInput) { cashInput.checked = true; togglePaymentFields(); }
        }
    }).catch(() => {});
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth(['patient', 'doctor']);
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    togglePaymentFields();
    preselectServices();

    // Auto-fill billing address with username as default
    const billingEl = document.getElementById('billingAddress');
    if (billingEl && !billingEl.value) {
        billingEl.value = (user.name || user.username || '') + ', Addis Ababa, Ethiopia';
    }
});
