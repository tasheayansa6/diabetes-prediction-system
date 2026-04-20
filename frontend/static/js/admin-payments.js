// Admin Payments & Refunds

let currentPage = 1;
let totalPages = 1;
let selectedPaymentId = null;

function authHeaders() {
    return { 'Authorization': 'Bearer ' + localStorage.getItem('token'), 'Content-Type': 'application/json' };
}

function showToast(msg, type) {
    type = type || 'success';
    const colors = { success: '#22c55e', danger: '#ef4444', warning: '#f59e0b', info: '#06b6d4' };
    const el = document.createElement('div');
    el.style.cssText = 'background:' + (colors[type] || colors.success) + ';color:#fff;padding:.75rem 1.25rem;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.15);font-size:.875rem;min-width:220px;';
    el.textContent = msg;
    document.getElementById('toastContainer').appendChild(el);
    setTimeout(() => el.remove(), 3500);
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

function statusBadge(s) {
    const map = {
        completed: 'badge-green',
        pending:   'badge-yellow',
        refunded:  'badge-red',
        failed:    'badge-red'
    };
    return '<span class="badge ' + (map[s] || 'badge-secondary') + '">' + s + '</span>';
}

function methodIcon(m) {
    const icons = { cash: 'bi-cash', card: 'bi-credit-card', insurance: 'bi-shield-check',
                    bank_transfer: 'bi-bank', chapa: 'bi-phone', mobile: 'bi-phone' };
    return '<i class="bi ' + (icons[m] || 'bi-wallet2') + '"></i> ' + (m || '-');
}

async function loadPayments(page) {
    page = page || 1;
    currentPage = page;

    const search = document.getElementById('searchInput').value.trim();
    const status = document.getElementById('filterStatus').value;
    const method = document.getElementById('filterMethod').value;
    const from   = document.getElementById('filterFrom').value;
    const to     = document.getElementById('filterTo').value;

    const params = new URLSearchParams({ page, per_page: 20 });
    if (search) params.set('search', search);
    if (status) params.set('status', status);
    if (method) params.set('method', method);
    if (from)   params.set('from_date', from);
    if (to)     params.set('to_date', to);

    const tbody = document.getElementById('paymentsTableBody');
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted" style="padding:2rem;">Loading...</td></tr>';

    try {
        const res  = await fetch('/api/admin/payments?' + params, { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        // Update summary cards
        document.getElementById('statRevenue').textContent  = data.summary.total_revenue.toLocaleString();
        document.getElementById('statPending').textContent  = data.summary.pending_count;
        document.getElementById('statRefunded').textContent = data.summary.total_refunded.toLocaleString();
        document.getElementById('statTotal').textContent    = data.pagination.total;

        totalPages = data.pagination.pages || 1;

        if (!data.payments.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted" style="padding:2rem;">No payments found.</td></tr>';
            document.getElementById('paginationBar').style.display = 'none';
            return;
        }

        tbody.innerHTML = data.payments.map(p => `
            <tr>
                <td><span class="font-mono text-xs">${p.payment_id}</span></td>
                <td>
                    <div class="font-medium">${esc(p.patient_name)}</div>
                    <div class="text-xs text-muted">${esc(p.patient_email)}</div>
                </td>
                <td><span class="text-xs">${p.payment_type || '-'}</span></td>
                <td><strong>${p.total_amount.toLocaleString()}</strong></td>
                <td>${methodIcon(p.payment_method)}</td>
                <td>${statusBadge(p.payment_status)}</td>
                <td class="text-xs">${p.created_at ? p.created_at.slice(0,10) : '-'}</td>
                <td>
                    <div class="flex gap-1">
                        ${p.payment_status === 'completed' ? `
                        <button class="btn btn-sm btn-danger" onclick="openRefundModal('${p.payment_id}','${esc(p.patient_name)}',${p.total_amount})" title="Refund">
                            <i class="bi bi-arrow-counterclockwise"></i>
                        </button>` : ''}
                        <button class="btn btn-sm btn-secondary" onclick="openStatusModal('${p.payment_id}','${p.payment_status}')" title="Change Status">
                            <i class="bi bi-pencil"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        // Pagination
        const bar = document.getElementById('paginationBar');
        bar.style.display = 'flex';
        document.getElementById('paginationInfo').textContent =
            `Page ${currentPage} of ${totalPages} (${data.pagination.total} records)`;
        document.getElementById('btnPrev').disabled = currentPage <= 1;
        document.getElementById('btnNext').disabled = currentPage >= totalPages;

    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-danger" style="padding:2rem;">' + e.message + '</td></tr>';
        showToast('Failed to load payments: ' + e.message, 'danger');
    }
}

function changePage(dir) {
    const next = currentPage + dir;
    if (next < 1 || next > totalPages) return;
    loadPayments(next);
}

function clearFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('filterStatus').value = '';
    document.getElementById('filterMethod').value = '';
    document.getElementById('filterFrom').value = '';
    document.getElementById('filterTo').value = '';
    loadPayments(1);
}

// ===== Refund =====

function openRefundModal(paymentId, patientName, amount) {
    selectedPaymentId = paymentId;
    document.getElementById('refundPaymentId').textContent   = paymentId;
    document.getElementById('refundPatientName').textContent = patientName;
    document.getElementById('refundAmount').textContent      = amount.toLocaleString();
    document.getElementById('refundReason').value = '';
    document.getElementById('refundModal').style.display = 'flex';
}

async function confirmRefund() {
    const reason = document.getElementById('refundReason').value.trim();
    if (!reason) { showToast('Please enter a reason for the refund.', 'warning'); return; }
    try {
        const res  = await fetch('/api/admin/payments/' + selectedPaymentId + '/refund', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({ reason })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        showToast('Refund processed successfully!', 'success');
        closeModal('refundModal');
        loadPayments(currentPage);
    } catch (e) {
        showToast('Refund failed: ' + e.message, 'danger');
    }
}

// ===== Status Change =====

function openStatusModal(paymentId, currentStatus) {
    selectedPaymentId = paymentId;
    document.getElementById('statusPaymentId').textContent = paymentId;
    document.getElementById('newStatus').value = currentStatus;
    document.getElementById('statusModal').style.display = 'flex';
}

async function confirmStatusChange() {
    const status = document.getElementById('newStatus').value;
    try {
        const res  = await fetch('/api/admin/payments/' + selectedPaymentId + '/status', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({ status })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        showToast('Status updated to ' + status, 'success');
        closeModal('statusModal');
        loadPayments(currentPage);
    } catch (e) {
        showToast('Update failed: ' + e.message, 'danger');
    }
}

function esc(str) {
    const d = document.createElement('div');
    d.textContent = str ?? '';
    return d.innerHTML;
}

function handleLogout() { if(typeof logout==='function') logout(); else { localStorage.clear(); window.location.href='/login'; } }

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('admin');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    loadPayments(1);

    // Search on Enter
    document.getElementById('searchInput').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') loadPayments(1);
    });
});
