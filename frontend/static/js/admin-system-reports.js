// Admin System Reports - uses /api/admin/reports/summary

const REPORTS_KEY = 'generatedReports';
let _summary = null;

function authHeaders() {
    return { 'Authorization': 'Bearer ' + localStorage.getItem('token') };
}

function showToast(message, type) {
    type = type || 'success';
    const colors = { success: '#22c55e', danger: '#ef4444', warning: '#f59e0b', info: '#06b6d4' };
    const container = document.getElementById('toastContainer');
    const id = 'toast_' + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.style.cssText = 'background:' + (colors[type] || colors.success) + ';color:#fff;padding:.75rem 1.25rem;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.15);font-size:.875rem;min-width:220px;';
    div.textContent = message;
    container.appendChild(div);
    setTimeout(function() { div.remove(); }, 3000);
}

// ===== Load summary from API =====

async function loadSummary() {
    try {
        const res = await fetch('/api/admin/reports/summary', { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        _summary = data.summary;
        renderStatCards(_summary);
    } catch (e) {
        showToast('Failed to load report data: ' + e.message, 'danger');
    }
}

function renderStatCards(s) {
    document.getElementById('statUsers').textContent =
        s.user_activity.total_users + ' users · ' + s.user_activity.new_users_30d + ' new (30d)';
    document.getElementById('statPredictions').textContent =
        s.predictions.total + ' total predictions';
    document.getElementById('statFinancial').textContent =
        s.financial.total_payments + ' payments · ' + s.financial.total_revenue.toLocaleString() + ' ETB';
    document.getElementById('statSecurity').textContent =
        s.security.total_audit_logs + ' logs · ' + s.security.failed_logins + ' failed logins';
}

// ===== Show report detail panel =====

const TYPE_LABELS = {
    user_activity: { label: 'User Activity', badge: 'bg-primary' },
    predictions:   { label: 'Predictions',   badge: 'bg-success' },
    financial:     { label: 'Financial',      badge: 'bg-warning' },
    security:      { label: 'Security',       badge: 'bg-info'    }
};

function showReport(type) {
    if (!_summary) { showToast('Data not loaded yet. Please wait.', 'warning'); return; }
    const card = document.getElementById('reportDetailCard');
    const title = document.getElementById('reportDetailTitle');
    const body = document.getElementById('reportDetailBody');
    const meta = TYPE_LABELS[type];
    title.innerHTML = '<span class="badge ' + meta.badge + ' me-2">' + meta.label + '</span> Live Report';
    body.innerHTML = buildReportHTML(type, _summary);
    card.classList.remove('hidden');
    card.scrollIntoView({ behavior: 'smooth' });
}

function buildReportHTML(type, s) {
    if (type === 'user_activity') {
        return '<div class="grid grid-cols-2 gap-4 p-4">' +
            '<div class="card text-center p-4"><h3 class="text-3xl font-bold">' + s.user_activity.total_users + '</h3><p class="text-gray-500">Total Users</p></div>' +
            '<div class="card text-center p-4"><h3 class="text-3xl font-bold">' + s.user_activity.new_users_30d + '</h3><p class="text-gray-500">New (Last 30 Days)</p></div>' +
            '</div>';
    }
    if (type === 'predictions') {
        const rows = s.predictions.risk_distribution.map(function(r) {
            return '<tr><td>' + r.level + '</td><td><strong>' + r.count + '</strong></td></tr>';
        }).join('');
        return '<div class="p-4"><p class="mb-3"><strong>Total Predictions:</strong> ' + s.predictions.total + '</p>' +
            '<table class="table table-sm table-bordered" style="max-width:320px;">' +
            '<thead><tr><th>Risk Level</th><th>Count</th></tr></thead>' +
            '<tbody>' + (rows || '<tr><td colspan="2" class="text-center text-gray-400">No data</td></tr>') + '</tbody>' +
            '</table></div>';
    }
    if (type === 'financial') {
        return '<div class="grid grid-cols-2 md:grid-cols-4 gap-4 p-4">' +
            '<div class="card text-center p-4"><h3 class="text-3xl font-bold">' + s.financial.total_payments + '</h3><p class="text-gray-500">Total Payments</p></div>' +
            '<div class="card text-center p-4"><h3 class="text-3xl font-bold">' + s.financial.total_revenue.toLocaleString() + '</h3><p class="text-gray-500">Revenue (ETB)</p></div>' +
            '<div class="card text-center p-4"><h3 class="text-3xl font-bold">' + s.financial.lab_tests + '</h3><p class="text-gray-500">Lab Tests</p></div>' +
            '<div class="card text-center p-4"><h3 class="text-3xl font-bold">' + s.financial.prescriptions + '</h3><p class="text-gray-500">Prescriptions</p></div>' +
            '</div>';
    }
    if (type === 'security') {
        const rows = s.security.recent_logs.map(function(l) {
            const badgeCls = l.status === 'failed' ? 'bg-danger' : 'bg-success';
            return '<tr><td>' + esc(l.username) + '</td><td>' + esc(l.role) + '</td><td>' + esc(l.action) + '</td><td>' + esc(l.resource) + '</td>' +
                '<td><span class="badge ' + badgeCls + '">' + esc(l.status) + '</span></td>' +
                '<td>' + esc(l.date) + '</td></tr>';
        }).join('');
        return '<div class="p-4"><p class="mb-3"><strong>Total Audit Logs:</strong> ' + s.security.total_audit_logs +
            ' &nbsp;|&nbsp; <strong>Failed Logins:</strong> <span class="text-danger">' + s.security.failed_logins + '</span></p>' +
            '<div class="table-responsive"><table class="table table-sm table-hover">' +
            '<thead><tr><th>User</th><th>Role</th><th>Action</th><th>Resource</th><th>Status</th><th>Date</th></tr></thead>' +
            '<tbody>' + (rows || '<tr><td colspan="6" class="text-center text-gray-400">No logs found</td></tr>') + '</tbody>' +
            '</table></div></div>';
    }
    return '';
}

function esc(str) {
    const d = document.createElement('div');
    d.textContent = str ?? '';
    return d.innerHTML;
}

// ===== Generated reports history (localStorage) =====

function getReports() {
    return JSON.parse(localStorage.getItem(REPORTS_KEY) || '[]');
}

function saveReports(reports) {
    localStorage.setItem(REPORTS_KEY, JSON.stringify(reports));
}

function renderReportsTable() {
    const reports = getReports();
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const tbody = document.getElementById('reportsTableBody');
    if (!reports.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">No reports generated yet.</td></tr>';
        return;
    }
    tbody.innerHTML = reports.map(function(r, i) {
        const meta = TYPE_LABELS[r.type] || { label: r.type, badge: 'bg-secondary' };
        return '<tr>' +
            '<td>' + esc(r.name) + '</td>' +
            '<td><span class="badge ' + meta.badge + '">' + meta.label + '</span></td>' +
            '<td>' + esc(r.date) + '</td>' +
            '<td>' + esc(user.username || 'Admin') + '</td>' +
            '<td>' +
                '<button class="btn btn-sm btn-info me-1" onclick="showReport(\'' + r.type + '\')">' +
                    '<i class="bi bi-eye"></i> View' +
                '</button>' +
                '<button class="btn btn-sm btn-danger" onclick="deleteReport(' + i + ')">' +
                    '<i class="bi bi-trash"></i>' +
                '</button>' +
            '</td>' +
            '</tr>';
    }).join('');
}

function deleteReport(idx) {
    const reports = getReports();
    reports.splice(idx, 1);
    saveReports(reports);
    renderReportsTable();
}

// ===== Generate report =====

function generateReport(event) {
    event.preventDefault();
    const type = document.getElementById('reportType').value;
    const from = document.getElementById('dateFrom').value;
    const to = document.getElementById('dateTo').value;
    const meta = TYPE_LABELS[type];

    const reports = getReports();
    reports.unshift({
        name: meta.label + ' Report (' + from + ' to ' + to + ')',
        type: type,
        date: new Date().toISOString().split('T')[0]
    });
    saveReports(reports);

    // Close modal
    document.getElementById('generateReportModal').style.display = 'none';
    document.getElementById('generateReportForm').reset();

    renderReportsTable();
    showToast(meta.label + ' report generated!', 'success');

    // Show detail only if summary is loaded
    if (_summary) showReport(type);
}

// ===== Init =====

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('admin');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    loadSummary();
    renderReportsTable();
});
