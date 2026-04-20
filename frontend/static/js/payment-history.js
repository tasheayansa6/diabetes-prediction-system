// Payment History - calls GET /api/payments/history + GET /api/payments/summary

function authHeaders() {
    return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token') };
}

let allPayments = [];

async function loadPaymentHistory() {
    const tbody = document.getElementById('paymentHistoryTable');
    try {
        const [histRes, sumRes] = await Promise.all([
            fetch('/api/payments/history?limit=100', { headers: authHeaders() }),
            fetch('/api/payments/summary', { headers: authHeaders() })
        ]);
        if (histRes.status === 401) { logout(); return; }
        const histData = await histRes.json();
        const sumData = await sumRes.json();

        if (!histData.success) throw new Error(histData.message);

        allPayments = histData.payments;

        // Summary cards
        if (sumData.success) {
            const s = sumData.summary;
            document.getElementById('totalSpent').textContent = 'ETB ' + (s.net_paid || 0).toFixed(2);
            document.getElementById('totalTransactions').textContent = s.payment_count || 0;
            document.getElementById('lastPayment').textContent = allPayments.length
                ? new Date(allPayments[0].created_at).toLocaleDateString() : '—';
        }

        renderTable(allPayments);

    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-4">${err.message}</td></tr>`;
    }
}

function renderTable(payments) {
    const tbody = document.getElementById('paymentHistoryTable');
    if (!payments.length) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-5">
            <i class="bi bi-inbox fs-1 text-muted"></i>
            <p class="text-muted mt-2">No payment history found</p></td></tr>`;
        return;
    }

    tbody.innerHTML = payments.map(p => {
        const statusClass = p.status === 'completed' ? 'status-success'
            : p.status === 'refunded' ? 'status-refunded'
            : p.status === 'failed' ? 'status-failed' : 'status-pending';
        const statusLabel = p.status === 'completed' ? 'Completed'
            : p.status === 'refunded' ? 'Refunded'
            : p.status === 'pending' ? 'Pending'
            : p.status === 'failed' ? 'Failed' : p.status;
        const date = p.created_at ? new Date(p.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : '—';

        return `<tr>
            <td><strong>${p.payment_id}</strong></td>
            <td>${date}</td>
            <td>${p.notes || p.payment_type || 'Medical Services'}</td>
            <td><strong>ETB ${parseFloat(p.total_amount).toFixed(2)}</strong></td>
            <td><span class="status-badge ${statusClass}">${statusLabel}</span></td>
            <td>
                ${p.invoice_id
                    ? `<button class="action-btn btn-view" onclick="viewInvoice('${p.invoice_id}')">
                           <i class="bi bi-eye"></i> Invoice
                       </button>`
                    : `<span class="text-muted small">${p.payment_method || '—'}</span>`}
            </td>
        </tr>`;
    }).join('');
}

function applyFilters() {
    const from = document.getElementById('dateFrom').value;
    const to = document.getElementById('dateTo').value;
    const status = document.getElementById('statusFilter').value;

    let filtered = [...allPayments];
    if (from) filtered = filtered.filter(p => p.created_at >= from);
    if (to) filtered = filtered.filter(p => p.created_at <= to + 'T23:59:59');
    if (status) filtered = filtered.filter(p => p.status === status);
    renderTable(filtered);
}

function viewInvoice(invoiceId) {
    window.location.href = '/templates/payment/invoice.html?id=' + invoiceId;
}

function exportHistory() {
    const csv = [
        ['Payment ID', 'Date', 'Description', 'Amount (ETB)', 'Method', 'Status'],
        ...allPayments.map(p => [
            p.payment_id,
            p.created_at ? new Date(p.created_at).toLocaleDateString() : '',
            p.notes || p.payment_type || '',
            parseFloat(p.total_amount).toFixed(2),
            p.payment_method || '',
            p.status
        ])
    ].map(r => r.join(',')).join('\n');

    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = 'payment-history.csv';
    a.click();
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('patient');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    loadPaymentHistory();
});
