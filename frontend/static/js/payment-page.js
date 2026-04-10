// Payment Page - calls POST /api/payments/process

let selectedServices = [];
let totalAmount = 0;

const FX_RATES = {
    ETB: 1, USD: 0.0175, EUR: 0.0161, GBP: 0.0138,
    AED: 0.0643, SAR: 0.0656, CNY: 0.1268, INR: 1.458, CAD: 0.0238, AUD: 0.0268
};
const CURRENCY_SYMBOLS = {
    ETB: 'ETB', USD: '$', EUR: '\u20ac', GBP: '\u00a3',
    AED: 'AED', SAR: 'SAR', CNY: '\u00a5', INR: '\u20b9', CAD: 'CA$', AUD: 'A$'
};

function getSelectedCurrency() {
    return document.getElementById('currencySelect')?.value || 'ETB';
}

function formatAmount(etbAmount) {
    const cur = getSelectedCurrency();
    const converted = etbAmount * (FX_RATES[cur] || 1);
    return (CURRENCY_SYMBOLS[cur] || cur) + ' ' + converted.toFixed(2);
}

function changeCurrency() {
    const cur = getSelectedCurrency();
    const rate = FX_RATES[cur] || 1;
    const note = document.getElementById('rateNote');
    note.textContent = cur === 'ETB'
        ? 'Prices stored and charged in ETB.'
        : `Approx. rate: 1 ETB \u2248 ${rate.toFixed(4)} ${cur}. Charges processed in ETB.`;
    document.querySelectorAll('.svc-price').forEach(el => {
        el.textContent = formatAmount(parseFloat(el.dataset.etb));
    });
    updateTotal();
}

function authHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('token')
    };
}

function getServiceContext() {
    const params = new URLSearchParams(window.location.search);
    const fromQuery = (params.get('service') || '').toLowerCase();
    if (['prediction', 'consultation', 'lab', 'medication'].includes(fromQuery)) return fromQuery;

    const names = selectedServices.map(s => (s.name || '').toLowerCase());
    if (names.some(n => n.includes('prediction'))) return 'prediction';
    if (names.some(n => n.includes('consultation'))) return 'consultation';
    if (names.some(n => n.includes('lab'))) return 'lab';
    if (names.some(n => n.includes('medication'))) return 'medication';
    return '';
}

function getReturnTarget() {
    const params = new URLSearchParams(window.location.search);
    return params.get('return') || '';
}

function nextPageAfterCompletedPayment(serviceContext, returnTo) {
    if (returnTo) return returnTo;
    if (serviceContext === 'prediction') return '/templates/patient/health_data_form.html';
    if (serviceContext === 'lab') return '/templates/patient/lab_results.html?paid=true';
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

    const div = document.getElementById('selectedServices');
    div.innerHTML = selectedServices.length === 0
        ? '<p class="text-muted small">Select services to see pricing</p>'
        : selectedServices.map(s =>
            `<div class="d-flex justify-content-between mb-2"><span>${s.name}</span><strong>${formatAmount(s.price)}</strong></div>`
          ).join('');

    document.getElementById('subtotal').textContent = formatAmount(subtotal);
    document.getElementById('tax').textContent = formatAmount(tax);
    document.getElementById('total').textContent = formatAmount(totalAmount);
}

function togglePaymentFields() {
    const method = document.querySelector('input[name="paymentMethod"]:checked').value;
    ['cardFields','mobileBankingFields','bankFields','paypalFields','cashFields','insuranceFields','chapaFields']
        .forEach(id => document.getElementById(id).style.display = 'none');

    const map = {
        credit_card: 'cardFields', debit_card: 'cardFields',
        telebirr: 'mobileBankingFields', cbe_birr: 'mobileBankingFields', m_birr: 'mobileBankingFields',
        bank_transfer: 'bankFields',
        paypal: 'paypalFields', cash: 'cashFields', insurance: 'insuranceFields',
        chapa: 'chapaFields'
    };
    if (map[method]) document.getElementById(map[method]).style.display = 'block';

    // Auto-select provider in dropdown
    const providerMap = { telebirr: 'telebirr', cbe_birr: 'cbe_birr', m_birr: 'm_birr' };
    if (providerMap[method]) {
        const sel = document.getElementById('mobileProvider');
        if (sel) sel.value = providerMap[method];
    }

    const btnText = document.getElementById('submitBtnText');
    btnText.textContent = method === 'paypal' ? 'Continue to PayPal'
        : method === 'chapa' ? 'Pay with Chapa'
        : method === 'cash' ? 'Get Reference Number'
        : method === 'insurance' ? 'Submit Insurance Claim'
        : 'Pay Securely';
}

function showAlert(message, type = 'danger') {
    let el = document.getElementById('paymentAlert');
    if (!el) {
        el = document.createElement('div');
        el.id = 'paymentAlert';
        document.getElementById('paymentForm').prepend(el);
    }
    el.innerHTML = `<div class="alert alert-${type} alert-dismissible fade show">
        ${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>`;
}

async function processPayment(event) {
    event.preventDefault();

    if (selectedServices.length === 0) {
        showAlert('Please select at least one service.');
        return;
    }

    const method = document.querySelector('input[name="paymentMethod"]:checked').value;

    // Validate per method
    if (['credit_card','debit_card'].includes(method)) {
        if (!document.getElementById('cardName').value || !document.getElementById('cardNumber').value
            || !document.getElementById('expiryDate').value || !document.getElementById('cvv').value) {
            showAlert('Please fill in all card details.'); return;
        }
    } else if (['telebirr','cbe_birr','m_birr'].includes(method)) {
        if (!document.getElementById('mobileNumber').value || !document.getElementById('mobileProvider').value) {
            showAlert('Please enter mobile number and select provider.'); return;
        }
    } else if (method === 'bank_transfer') {
        if (!document.getElementById('bankName').value || !document.getElementById('accountNumber').value
            || !document.getElementById('accountHolderName').value) {
            showAlert('Please select bank, enter account number and account holder name.'); return;
        }
    } else if (method === 'paypal') {
        if (!document.getElementById('paypalEmail').value) {
            showAlert('Please enter your PayPal email address.'); return;
        }
        showPaypalRedirect(); return;
    } else if (method === 'cash') {
        if (!document.getElementById('cashPayerName').value || !document.getElementById('cashPhone').value) {
            showAlert('Please enter your name and phone number.'); return;
        }
    } else if (method === 'insurance') {
        if (!document.getElementById('insuranceProvider').value || !document.getElementById('policyNumber').value
            || !document.getElementById('insuranceHolderName').value) {
            showAlert('Please fill in all insurance details.'); return;
        }
    } else if (method === 'chapa') {
        await initiateChapaPayment();
        return;
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
    const isPrediction = serviceContext === 'prediction';
    const labRequestId = localStorage.getItem('lab_request_id');

    const payload = {
        amount: subtotal,
        tax: tax,
        currency: 'ETB',
        payment_method: method,
        payment_type: isPrediction ? 'prediction' : 'services',
        notes: selectedServices.map(s => s.name).join(', '),
        billing_address: document.getElementById('billingAddress').value,
        ...(labRequestId && { lab_request_id: labRequestId })
    };

    // Attach method-specific fields
    if (['credit_card', 'debit_card'].includes(method)) {
        payload.card_holder = document.getElementById('cardName').value;
        payload.card_last4 = document.getElementById('cardNumber').value.replace(/\s/g,'').slice(-4);
        payload.card_expiry = document.getElementById('expiryDate').value;
        payload.notes += ` | Card: **** ${payload.card_last4}`;
    } else if (['telebirr', 'cbe_birr', 'm_birr'].includes(method)) {
        payload.mobile_number = document.getElementById('mobileNumber').value;
        payload.mobile_provider = document.getElementById('mobileProvider').value;
        payload.notes += ` | Mobile: ${payload.mobile_number} (${payload.mobile_provider})`;
    } else if (method === 'bank_transfer') {
        payload.bank_name = document.getElementById('bankName').value;
        payload.account_number = document.getElementById('accountNumber').value;
        payload.account_holder = document.getElementById('accountHolderName').value;
        payload.notes += ` | Bank: ${payload.bank_name} | Acct: ${payload.account_number}`;
    } else if (method === 'cash') {
        payload.payer_name = document.getElementById('cashPayerName').value;
        payload.payer_phone = document.getElementById('cashPhone').value;
        payload.notes += ` | Cash payer: ${payload.payer_name} (${payload.payer_phone})`;
    } else if (method === 'insurance') {
        payload.insurance_company = document.getElementById('insuranceProvider').value;
        payload.insurance_claim_number = document.getElementById('policyNumber').value;
        payload.insurance_holder = document.getElementById('insuranceHolderName').value;
        payload.notes += ` | Insurance: ${payload.insurance_company} | Policy: ${payload.insurance_claim_number}`;
    }

    try {
        const res = await fetch('/api/payments/process', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message || 'Payment failed');

        localStorage.setItem('lastTransaction', JSON.stringify({
            id: data.payment.payment_id,
            invoice_id: data.invoice.invoice_id,
            services: selectedServices,
            serviceContext,
            returnTo,
            paymentMethod: method,
            amount: data.payment.total_amount,
            currency: 'ETB',
            date: new Date().toISOString().split('T')[0],
            status: data.payment.is_pending ? 'pending' : 'success',
            referenceNumber: data.payment.is_pending ? data.payment.payment_id : null
        }));

        const isPredictionPayment = data.payment.payment_type === 'prediction' || serviceContext === 'prediction';
        if (isPredictionPayment) {
            localStorage.setItem('predictionPaid', 'true');
            window.location.href = nextPageAfterCompletedPayment(serviceContext, returnTo);
        } else if (!data.payment.is_pending) {
            window.location.href = nextPageAfterCompletedPayment(serviceContext, returnTo);
        } else {
            window.location.href = '/templates/payment/payment_success.html';
        }

    } catch (err) {
        localStorage.setItem('lastError', JSON.stringify({
            code: 'PAYMENT_ERROR',
            message: err.message,
            date: new Date().toISOString().split('T')[0]
        }));
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
    const isPrediction = serviceContext === 'prediction'
        || selectedServices.some(s => (s.name || '').toLowerCase().includes('prediction'));
    const labRequestId = localStorage.getItem('lab_request_id');

    try {
        const res = await fetch('/api/payments/chapa/initialize', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({
                amount: subtotal,
                tax: tax,
                currency: 'ETB',
                payment_type: isPrediction ? 'prediction' : 'services',
                notes: selectedServices.map(s => s.name).join(', '),
                billing_address: document.getElementById('billingAddress').value,
                ...(labRequestId && { lab_request_id: labRequestId })
            })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message || 'Chapa initialization failed');

        const pendingTx = {
            id: data.payment_id,
            invoice_id: data.invoice_id,
            tx_ref: data.tx_ref,
            services: selectedServices,
            paymentMethod: 'chapa',
            amount: subtotal + tax,
            currency: 'ETB',
            date: new Date().toISOString().split('T')[0],
            status: 'pending',
            referenceNumber: data.tx_ref,
            serviceContext,
            returnTo
        };
        localStorage.setItem('lastTransaction', JSON.stringify(pendingTx));
        localStorage.setItem('chapaPendingContext', JSON.stringify({
            serviceContext,
            returnTo,
            tx_ref: data.tx_ref,
            lab_request_id: labRequestId || null
        }));

        // Redirect to Chapa checkout
        window.location.href = data.checkout_url;

    } catch (err) {
        showAlert(err.message || 'Could not connect to Chapa. Please try another method.');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-lock"></i> <span id="submitBtnText">Pay with Chapa</span>';
    }
}

function showPaypalRedirect() {
    const overlay = document.createElement('div');
    overlay.id = 'paypalOverlay';
    overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center;';
    overlay.innerHTML = `
        <div style="background:#fff;border-radius:16px;padding:2.5rem;max-width:420px;width:90%;text-align:center;">
            <svg xmlns="http://www.w3.org/2000/svg" width="60" height="60" viewBox="0 0 24 24" fill="#003087" style="margin-bottom:1rem;"><path d="M7.076 21.337H2.47a.641.641 0 0 1-.633-.74L4.944.901C5.026.382 5.474 0 5.998 0h7.46c2.57 0 4.578.543 5.69 1.81 1.01 1.15 1.304 2.42 1.012 4.287-.023.143-.047.288-.077.437-.983 5.05-4.349 6.797-8.647 6.797h-2.19c-.524 0-.968.382-1.05.9l-1.12 7.106zm14.146-14.42a3.35 3.35 0 0 0-.607-.541c-.013.076-.026.175-.041.254-.93 4.778-4.005 7.201-9.138 7.201h-2.19a.563.563 0 0 0-.556.479l-1.187 7.527h-.506l-.24 1.516a.56.56 0 0 0 .554.647h3.882c.46 0 .85-.334.922-.788.06-.26.76-4.852.816-5.09a.932.932 0 0 1 .923-.788h.58c3.76 0 6.705-1.528 7.565-5.946.36-1.847.174-3.388-.777-4.471z"/></svg>
            <h4 style="color:#003087;font-weight:700;">Redirecting to PayPal</h4>
            <p style="color:#555;margin:0.75rem 0;">Completing payment of <strong>ETB ${totalAmount.toFixed(2)}</strong></p>
            <div style="margin:1.5rem 0;">
                <div style="width:100%;height:6px;background:#e9ecef;border-radius:3px;overflow:hidden;">
                    <div id="paypalProgress" style="height:100%;width:0%;background:linear-gradient(90deg,#003087,#009cde);border-radius:3px;transition:width 0.1s linear;"></div>
                </div>
                <p style="color:#888;font-size:0.85rem;margin-top:0.5rem;" id="paypalCountdown">Redirecting in 3 seconds...</p>
            </div>
            <button onclick="cancelPaypal()" style="background:none;border:1px solid #ccc;padding:0.4rem 1.2rem;border-radius:6px;color:#666;cursor:pointer;">Cancel</button>
        </div>`;
    document.body.appendChild(overlay);

    let elapsed = 0;
    window._paypalInterval = setInterval(async () => {
        elapsed += 100;
        const pct = Math.min((elapsed / 3000) * 100, 100);
        document.getElementById('paypalProgress').style.width = pct + '%';
        const rem = Math.ceil((3000 - elapsed) / 1000);
        if (rem > 0) document.getElementById('paypalCountdown').textContent = `Redirecting in ${rem} second${rem > 1 ? 's' : ''}...`;
        if (elapsed >= 3000) {
            clearInterval(window._paypalInterval);
            // Simulate PayPal approval — call real API
            document.getElementById('paypalCountdown').textContent = 'Approving payment...';
            const subtotal = selectedServices.reduce((s, x) => s + x.price, 0);
            try {
                const res = await fetch('/api/payments/process', {
                    method: 'POST',
                    headers: authHeaders(),
                    body: JSON.stringify({
                        amount: subtotal, tax: subtotal * 0.08, currency: 'ETB',
                        payment_method: 'paypal',
                        payment_type: selectedServices.some(s => s.name.toLowerCase().includes('prediction')) ? 'prediction' : 'services',
                        notes: selectedServices.map(s => s.name).join(', '),
                        paypal_email: document.getElementById('paypalEmail').value,
                        ...(localStorage.getItem('lab_request_id') && { lab_request_id: localStorage.getItem('lab_request_id') })
                    })
                });
                const data = await res.json();
                if (!data.success) throw new Error(data.message);
                const serviceContext = getServiceContext();
                const returnTo = getReturnTarget();
                localStorage.setItem('lastTransaction', JSON.stringify({
                    id: data.payment.payment_id, invoice_id: data.invoice.invoice_id,
                    services: selectedServices, paymentMethod: 'paypal',
                    serviceContext, returnTo,
                    amount: data.payment.total_amount, currency: 'ETB',
                    date: new Date().toISOString().split('T')[0],
                    status: data.payment.is_pending ? 'pending' : 'success',
                    referenceNumber: data.payment.is_pending ? data.payment.payment_id : null
                }));
                const isPredictionPayment = data.payment.payment_type === 'prediction' || serviceContext === 'prediction';
                if (isPredictionPayment) {
                    localStorage.setItem('predictionPaid', 'true');
                    window.location.href = nextPageAfterCompletedPayment(serviceContext, returnTo);
                } else if (!data.payment.is_pending) {
                    window.location.href = nextPageAfterCompletedPayment(serviceContext, returnTo);
                } else {
                    window.location.href = '/templates/payment/payment_success.html';
                }
            } catch (err) {
                localStorage.setItem('lastError', JSON.stringify({ code: 'PAYPAL_ERROR', message: err.message, date: new Date().toISOString().split('T')[0] }));
                window.location.href = '/templates/payment/payment_failed.html';
            }
        }
    }, 100);
}

function cancelPaypal() {
    clearInterval(window._paypalInterval);
    document.getElementById('paypalOverlay')?.remove();
}

function preselectServices() {
    const params = new URLSearchParams(window.location.search);
    const service = params.get('service');
    const returnTo = params.get('return');

    // Save return destination if provided
    // return destination is handled directly in payment success logic

    const map = { prediction: 'service1', consultation: 'service2', lab: 'service3', medication: 'service4' };
    if (map[service]) {
        const cb = document.getElementById(map[service]);
        if (cb) { cb.checked = true; updateTotal(); }
    }
    // Store lab_request_id for reference
    const labReqId = params.get('lab_request_id');
    if (labReqId) localStorage.setItem('lab_request_id', labReqId);
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth(['patient', 'doctor']);
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;

    const cardNumberInput = document.getElementById('cardNumber');
    if (cardNumberInput) {
        cardNumberInput.addEventListener('input', e => {
            e.target.value = (e.target.value.replace(/\s/g, '').match(/.{1,4}/g) || []).join(' ');
        });
    }
    const expiryInput = document.getElementById('expiryDate');
    if (expiryInput) {
        expiryInput.addEventListener('input', e => {
            let v = e.target.value.replace(/\D/g, '');
            if (v.length >= 2) v = v.slice(0, 2) + '/' + v.slice(2, 4);
            e.target.value = v;
        });
    }
    const cvvInput = document.getElementById('cvv');
    if (cvvInput) cvvInput.addEventListener('input', e => { e.target.value = e.target.value.replace(/\D/g, ''); });

    togglePaymentFields();
    preselectServices();
});
