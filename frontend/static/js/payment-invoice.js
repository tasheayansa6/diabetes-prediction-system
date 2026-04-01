// Invoice Page - GET /api/payments/invoice/<invoice_id>

function authHeaders() {
    return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token') };
}

function esc(str) {
    const d = document.createElement('div');
    d.textContent = str ?? '';
    return d.innerHTML;
}

function fmt(n) {
    return 'ETB ' + parseFloat(n || 0).toFixed(2);
}

function showError(msg) {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('invoiceCard').style.display = 'none';
    document.getElementById('errorMsg').textContent = msg;
    document.getElementById('errorState').style.display = '';
}

function statusBadge(s) {
    const map = { paid: '#22c55e', pending: '#f59e0b', refunded: '#ef4444', cancelled: '#6b7280' };
    const color = map[s] || '#6b7280';
    return `<span style="background:${color};color:#fff;padding:2px 10px;border-radius:12px;font-size:.75rem;">${s || '—'}</span>`;
}

async function loadInvoice() {
    const invoiceId = new URLSearchParams(window.location.search).get('id');

    if (!invoiceId) {
        showError('No invoice ID provided. Please go back and try again.');
        return;
    }

    try {
        const res  = await fetch(`/api/payments/invoice/${invoiceId}`, { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message || 'Invoice not found');

        const inv = data.invoice;

        // Dates
        const createdDate = inv.created_at ? new Date(inv.created_at).toLocaleDateString('en-US', { year:'numeric', month:'long', day:'numeric' }) : '—';
        const dueDate     = inv.due_date   ? new Date(inv.due_date).toLocaleDateString('en-US',   { year:'numeric', month:'long', day:'numeric' }) : createdDate;

        document.getElementById('invoiceId').textContent      = esc(inv.invoice_id);
        document.getElementById('invoiceDate').textContent    = createdDate;
        document.getElementById('invoiceDueDate').textContent = dueDate;
        document.getElementById('invoiceStatus').innerHTML    = statusBadge(inv.status);

        // Patient
        const patient = inv.patient || {};
        document.getElementById('patientName').textContent  = esc(patient.name || patient.username || '—');
        document.getElementById('patientEmail').textContent = esc(patient.email || '—');

        // Payment info
        const payment = inv.payment || {};
        document.getElementById('paymentId').textContent     = esc(payment.payment_id || '—');
        document.getElementById('paymentMethod').textContent = esc(payment.payment_method || '—');
        if (!payment.payment_id) {
            document.getElementById('paymentInfoRow').style.display = 'none';
        }

        // Line items
        const description = payment.payment_method
            ? `Medical Services (${payment.payment_method})`
            : 'Medical Services';

        document.getElementById('invoiceItems').innerHTML = `
            <tr>
                <td>${esc(description)}</td>
                <td class="text-center">1</td>
                <td class="text-right">${fmt(inv.amount)}</td>
                <td class="text-right">${fmt(inv.amount)}</td>
            </tr>`;

        // Totals — use exact values from API, no recalculation
        document.getElementById('subtotal').textContent = fmt(inv.amount);
        document.getElementById('tax').textContent      = fmt(inv.tax);
        document.getElementById('discount').textContent = fmt(inv.discount);
        document.getElementById('total').textContent    = fmt(inv.total_amount);

        // Show card
        document.getElementById('loadingState').style.display = 'none';
        document.getElementById('invoiceCard').style.display  = '';

    } catch (e) {
        showError('Failed to load invoice: ' + e.message);
    }
}

function downloadInvoicePDF() {
    document.querySelectorAll('.no-print').forEach(el => el.style.display = 'none');
    window.print();
    document.querySelectorAll('.no-print').forEach(el => el.style.display = '');
}

document.addEventListener('DOMContentLoaded', function () {
    // Allow patient, admin, doctor to view invoices
    const user = checkAuth(['patient', 'admin', 'doctor']);
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    loadInvoice();
});
