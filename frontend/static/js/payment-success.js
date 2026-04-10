// Payment Success Page

const METHOD_NAMES = {
    credit_card: 'Credit Card', debit_card: 'Debit Card',
    mobile_banking: 'Mobile Banking', bank_transfer: 'Bank Transfer',
    paypal: 'PayPal', cash: 'Cash (Pay at Cashier)',
    insurance: 'Health Insurance', chapa: 'Chapa',
    telebirr: 'TeleBirr', cbe_birr: 'CBE Birr', m_birr: 'M-Birr'
};

function loadTransaction() {
    const t = JSON.parse(localStorage.getItem('lastTransaction') || '{}');

    document.getElementById('transactionId').textContent = t.id || '—';
    document.getElementById('transactionAmount').textContent = t.amount ? 'ETB ' + parseFloat(t.amount).toFixed(2) : '—';
    document.getElementById('transactionDate').textContent = t.date || new Date().toLocaleDateString();
    document.getElementById('paymentMethod').textContent = METHOD_NAMES[t.paymentMethod] || t.paymentMethod || '—';

    if (t.invoice_id) {
        const invoiceBtn = document.querySelector('a[href*="invoice.html"]');
        if (invoiceBtn) invoiceBtn.href = '/templates/payment/invoice.html?id=' + t.invoice_id;
    }

    const isPending = t.status === 'pending';
    const badge = document.getElementById('paymentStatus');
    badge.textContent = isPending ? 'Pending Confirmation' : 'Completed';
    badge.className = isPending ? 'badge bg-warning text-dark' : 'badge bg-success';

    if (t.paymentMethod === 'cash') {
        document.getElementById('statusIcon').className = 'bi bi-receipt display-1 text-warning mb-4';
        document.getElementById('statusTitle').textContent = 'Reference Number Generated!';
        document.getElementById('statusTitle').className = 'mb-3 text-warning';
        document.getElementById('statusMessage').textContent = 'Please pay at the hospital cashier desk.';
        document.getElementById('cashInstructions').style.display = 'block';
        showRefRow(t.referenceNumber);
    }

    if (t.paymentMethod === 'insurance') {
        document.getElementById('statusIcon').className = 'bi bi-shield-check display-1 text-info mb-4';
        document.getElementById('statusTitle').textContent = 'Insurance Claim Submitted!';
        document.getElementById('statusTitle').className = 'mb-3 text-info';
        document.getElementById('statusMessage').textContent = 'Your claim is pending approval from your insurance provider.';
        document.getElementById('insuranceInstructions').style.display = 'block';
        showRefRow(t.referenceNumber);
    }

    // Auto-continue flow for completed online payments (lab/consultation/medication/prediction).
    if (!isPending) {
        const target = t.returnTo ||
            (t.serviceContext === 'prediction' ? '/templates/patient/health_data_form.html' :
            t.serviceContext === 'lab' ? '/templates/patient/lab_results.html?paid=true' :
            t.serviceContext === 'consultation' ? '/templates/patient/appointment.html?paid=true' :
            t.serviceContext === 'medication' ? '/templates/patient/prescriptions.html?paid=true' : '');

        if (target) {
            setTimeout(() => { window.location.href = target; }, 1200);
        }
    }
}

function showRefRow(ref) {
    const row = document.getElementById('refRow');
    row.style.cssText = 'display:flex !important';
    document.getElementById('referenceNumber').textContent = ref || '—';
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth(['patient', 'doctor']);
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    loadTransaction();
});
