// Pharmacist Dashboard Page JavaScript

const API = '/api';

function authHeaders() {
    return { 'Authorization': 'Bearer ' + localStorage.getItem('token') };
}

function updateDate() {
    const el = document.getElementById('currentDate');
    if (el) el.textContent = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

function statusBadge(status) {
    const map = {
        pending: 'badge-yellow', pending_pharmacist: 'badge-yellow',
        verified: 'badge-cyan', dispensed: 'badge-green', rejected: 'badge-red'
    };
    return `<span class="badge ${map[status] || 'badge-gray'}">${status.replace('_',' ')}</span>`;
}

function renderPending(list) {
    const el = document.getElementById('pendingList');
    if (!el) return;
    const pending = list.filter(p => ['pending','pending_pharmacist'].includes(p.status)).slice(0, 5);
    if (!pending.length) { el.innerHTML = '<div class="list-item" style="justify-content:center;color:#64748b;">No pending prescriptions.</div>'; return; }
        el.innerHTML = pending.map(p => `
        <div class="list-item justify-between">
            <div>
                <div class="font-medium text-sm">${p.patient_name} — ${p.medication}</div>
                <div class="text-xs text-muted">Prescribed: ${p.created_at ? p.created_at.split('T')[0] : '—'}</div>
            </div>
            <a href="/templates/pharmacist/prescription_review.html?status=pending" class="btn btn-sm btn-primary">Review</a>
        </div>`).join('');
}

function renderDispensed(list) {
    const el = document.getElementById('dispensedList');
    if (!el) return;
    const dispensed = list.filter(p => p.status === 'dispensed').slice(0, 5);
    if (!dispensed.length) { el.innerHTML = '<div class="list-item" style="justify-content:center;color:#64748b;">No dispensed prescriptions today.</div>'; return; }
    el.innerHTML = dispensed.map(p => `
        <div class="list-item">
            <div>
                <div class="font-medium text-sm">${p.patient_name} — ${p.medication}</div>
                <div class="text-xs text-muted">${statusBadge(p.status)} ${p.created_at ? p.created_at.split('T')[0] : ''}</div>
            </div>
        </div>`).join('');
}

function initCharts(stats) {
    if (typeof Chart === 'undefined') return;
    try {
    const prescriptionCtx = document.getElementById('prescriptionChart');
    if (prescriptionCtx) {
        new Chart(prescriptionCtx, {
            type: 'line',
            data: {
                labels: ['Pending', 'Verified', 'Dispensed Today', 'Total Dispensed'],
                datasets: [{
                    label: 'Prescriptions',
                    data: [
                        stats.pending_prescriptions,
                        stats.verified_prescriptions,
                        stats.dispensed_today,
                        stats.total_dispensed
                    ],
                    borderColor: '#2A7BE4',
                    backgroundColor: 'rgba(42,123,228,0.1)',
                    tension: 0.4
                }]
            },
            options: { responsive: true, maintainAspectRatio: true }
        });
    }

    const activityCtx = document.getElementById('activityChart');
    if (activityCtx) {
        new Chart(activityCtx, {
            type: 'doughnut',
            data: {
                labels: ['Verified', 'Dispensed', 'Pending', 'Low Stock'],
                datasets: [{
                    data: [
                        stats.verified_prescriptions,
                        stats.total_dispensed,
                        stats.pending_prescriptions,
                        stats.low_stock_items
                    ],
                    backgroundColor: ['#17a2b8', '#28a745', '#ffc107', '#dc3545']
                }]
            },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom' } } }
        });
    }
    } catch (_) { /* charts are optional */ }
}

async function loadDashboard() {
    try {
        const res = await fetch(`${API}/pharmacy/dashboard`, { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        const s = data.dashboard.statistics;

        const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        setText('statPending',   s.pending_prescriptions);
        setText('statVerified',  s.verified_prescriptions);
        setText('statDispensed', s.dispensed_today);
        setText('statTotal',     s.total_dispensed);

        renderPending(data.dashboard.recent_activity);
        renderDispensed(data.dashboard.recent_activity);
        initCharts(s);

    } catch (err) {
        console.error('Dashboard load error:', err);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('pharmacist');
    if (!user) return;
    const name = user.name || user.username;
    document.getElementById('navUserName').textContent = name;
    const sb = document.getElementById('sidebarName');
    if (sb) sb.textContent = name;
    updateDate();
    loadDashboard();
});
