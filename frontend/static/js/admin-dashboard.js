const token = () => localStorage.getItem('token');

// ── Auth & Logout ─────────────────────────────────────────────────────────────
function handleLogout() { if(typeof logout==='function') logout(); else { localStorage.clear(); window.location.href='/login'; } }

// ── Check admin auth ──────────────────────────────────────────────────────────
function checkAdminAuth() {
    const t = token();
    if (!t) { window.location.href = '/login'; return false; }
    try {
        const payload = JSON.parse(atob(t.split('.')[1]));
        if (payload.role !== 'admin') { window.location.href = '/login'; return false; }
        document.getElementById('navUserName').textContent = payload.username || 'Administrator';
        return true;
    } catch (_) {
        window.location.href = '/login';
        return false;
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function set(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

function showToast(message, type = 'danger') {
    const id = 'toast-' + Date.now();
    const bg = type === 'success' ? 'bg-success' : 'bg-danger';
    const c = document.getElementById('toastContainer');
    if (!c) return;
    c.insertAdjacentHTML('beforeend', `
        <div id="${id}" class="toast show mb-2" role="alert">
            <div class="toast-header ${bg} text-white">
                <strong class="me-auto">${type === 'success' ? 'Success' : 'Error'}</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">${message}</div>
        </div>
    `);
    setTimeout(() => document.getElementById(id)?.remove(), 5000);
}

// ── Load dashboard from GET /api/admin/dashboard ──────────────────────────────
async function loadDashboard() {
    try {
        const res = await fetch('/api/admin/dashboard', {
            headers: { 'Authorization': `Bearer ${token()}` }
        });

        if (res.status === 401) { handleLogout(); return; }

        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        const { statistics, role_distribution, recent_users, today_activity } = data.dashboard;

        set('totalUsersStat',      statistics.total_users       ?? 0);
        set('totalPatientsStat',   statistics.total_patients    ?? 0);
        set('totalPredictionsStat',statistics.total_predictions ?? 0);
        set('averageRiskStat',     (statistics.average_risk_percentage ?? 0).toFixed(1) + '%');
        set('totalDoctorsStat',    statistics.total_doctors     ?? 0);
        set('todayRegistrations',  today_activity?.new_registrations ?? 0);
        set('todayPredictions',    today_activity?.predictions       ?? 0);
        set('totalPaymentsStat',     statistics.total_payments     ?? '—');
        set('totalAppointmentsStat', statistics.total_appointments ?? '—');

        const dbEl = document.getElementById('dbStatus');
        if (dbEl) dbEl.textContent = 'Online';

        loadRiskStats(role_distribution);
        drawRoleChart(role_distribution);
        renderRecentUsers(recent_users);
        renderActivity(recent_users);

    } catch (err) {
        showToast('Failed to load dashboard: ' + err.message);
    }
}

// ── Load risk distribution ────────────────────────────────────────────────────
async function loadRiskStats(roleDistribution) {
    try {
        const res = await fetch('/api/admin/statistics', {
            headers: { 'Authorization': `Bearer ${token()}` }
        });
        const data = await res.json();
        if (!data.success) return;

        const rd = data.statistics.risk_distribution;
        set('riskLow',      rd['LOW RISK']       ?? 0);
        set('riskModerate', rd['MODERATE RISK']  ?? 0);
        set('riskHigh',     rd['HIGH RISK']      ?? 0);
        set('riskVeryHigh', rd['VERY HIGH RISK'] ?? 0);
        set('highRiskStat', (rd['HIGH RISK'] ?? 0) + (rd['VERY HIGH RISK'] ?? 0));
        drawRiskChart(rd);
    } catch (_) {}
}

// ── Role Distribution Doughnut Chart ─────────────────────────────────────────
function drawRoleChart(roleDistribution) {
    const ctx = document.getElementById('systemUsageChart');
    if (!ctx || !roleDistribution?.length) return;

    const roleLabels = {
        patient: 'Patients', doctor: 'Doctors', nurse: 'Nurses',
        lab_technician: 'Lab Techs', pharmacist: 'Pharmacists', admin: 'Admins'
    };
    const roleColors = {
        patient: '#38bdf8', doctor: '#22c55e', nurse: '#facc15',
        lab_technician: '#a78bfa', pharmacist: '#f472b6', admin: '#f43f5e'
    };

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: roleDistribution.map(r => roleLabels[r.role] || r.role),
            datasets: [{
                data: roleDistribution.map(r => r.count),
                backgroundColor: roleDistribution.map(r => roleColors[r.role] || '#64748b'),
                borderWidth: 2,
                borderColor: '#1e293b'
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#94a3b8', padding: 16, font: { size: 12 } } },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            return ` ${ctx.label}: ${ctx.raw} (${((ctx.raw/total)*100).toFixed(1)}%)`;
                        }
                    }
                }
            }
        }
    });
}

// ── ML Risk Distribution Bar Chart ───────────────────────────────────────────
function drawRiskChart(rd) {
    const ctx = document.getElementById('riskTrendChart');
    if (!ctx) return;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Low Risk', 'Moderate Risk', 'High Risk', 'Very High Risk'],
            datasets: [{
                label: 'Patients',
                data: [
                    rd['LOW RISK']       ?? 0,
                    rd['MODERATE RISK']  ?? 0,
                    rd['HIGH RISK']      ?? 0,
                    rd['VERY HIGH RISK'] ?? 0
                ],
                backgroundColor: ['#22c55e', '#facc15', '#f97316', '#f43f5e'],
                borderRadius: 6,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#94a3b8' }, grid: { color: '#1e293b' } },
                y: { beginAtZero: true, ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: '#334155' } }
            }
        }
    });
}

// ── Recent Users Table ────────────────────────────────────────────────────────
function renderRecentUsers(users) {
    const tbody = document.getElementById('recentUsersTable');
    const badge = document.getElementById('userCountBadge');
    if (!tbody || !users?.length) {
        if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted" style="padding:1.5rem;">No users yet</td></tr>';
        return;
    }

    if (badge) badge.textContent = users.length + ' users';

    const roleClass = {
        patient: 'role-patient', doctor: 'role-doctor', nurse: 'role-nurse',
        lab_technician: 'role-lab', pharmacist: 'role-pharmacist', admin: 'role-admin'
    };
    const roleLabel = {
        patient: 'Patient', doctor: 'Doctor', nurse: 'Nurse',
        lab_technician: 'Lab Tech', pharmacist: 'Pharmacist', admin: 'Admin'
    };

    tbody.innerHTML = users.map((u, i) => `
        <tr>
            <td class="text-muted" style="font-size:.8rem;">${i + 1}</td>
            <td><strong style="color:#e2e8f0;">${u.username}</strong></td>
            <td style="color:#94a3b8;">${u.email}</td>
            <td><span class="badge ${roleClass[u.role] || 'badge-gray'}">${roleLabel[u.role] || u.role}</span></td>
            <td style="color:#64748b;font-size:.82rem;">${u.created_at ? new Date(u.created_at).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}) : 'N/A'}</td>
            <td><span class="${u.is_active !== false ? 'status-active' : 'status-inactive'}">
                <i class="bi bi-${u.is_active !== false ? 'check-circle-fill' : 'x-circle-fill'}"></i>
                ${u.is_active !== false ? 'Active' : 'Inactive'}
            </span></td>
        </tr>
    `).join('');
}

// ── Recent Activity Panel ─────────────────────────────────────────────────────
function renderActivity(users) {
    const container = document.getElementById('recentActivity');
    if (!container) return;

    if (!users?.length) {
        container.innerHTML = '<p class="text-muted" style="padding:1rem;">No recent activity</p>';
        return;
    }

    const roleIcon = {
        patient: 'bi-person-heart', doctor: 'bi-heart-pulse', nurse: 'bi-bandaid',
        lab_technician: 'bi-eyedropper', pharmacist: 'bi-capsule', admin: 'bi-shield-check'
    };

    container.innerHTML = `<ul class="activity-list">
        ${users.slice(0, 6).map(u => `
            <li class="activity-item">
                <div class="activity-icon"><i class="bi ${roleIcon[u.role] || 'bi-person-plus-fill'}"></i></div>
                <div class="activity-details">
                    <strong>${u.username}</strong> registered as <em>${u.role}</em>
                    <span class="activity-time"><i class="bi bi-clock"></i> ${u.created_at ? new Date(u.created_at).toLocaleString() : ''}</span>
                </div>
            </li>
        `).join('')}
    </ul>`;
}

// ── Check DB health ───────────────────────────────────────────────────────────
async function checkDbHealth() {
    try {
        const res = await fetch('/api/admin/system/health');
        const data = await res.json();
        const el = document.getElementById('dbStatus');
        if (el) {
            el.textContent = data.status === 'healthy' ? 'Online' : 'Error';
            el.className = data.status === 'healthy' ? 'status-active' : 'status-inactive';
        }
    } catch (_) {
        const el = document.getElementById('dbStatus');
        if (el) { el.textContent = 'Offline'; el.className = 'status-inactive'; }
    }
}

// ── Load active model info ────────────────────────────────────────────────────
async function loadActiveModel() {
    try {
        const statsRes = await fetch('/api/model/stats');
        const stats = await statsRes.json();

        const nameEl   = document.getElementById('activeModelName');
        const subEl    = document.getElementById('activeModelSub');
        const mlNameEl = document.getElementById('mlModelName');
        const mlStatus = document.getElementById('mlStatus');

        if (stats && stats.success && stats.active_model) {
            const active = stats.active_model;
            const ds = stats.dataset || {};
            const total = ds.total_samples != null ? ds.total_samples : 'N/A';
            const tr = ds.training_samples != null ? ds.training_samples : 'N/A';
            const te = ds.test_samples != null ? ds.test_samples : 'N/A';
            const algo = active.algorithm || 'Unknown';
            const version = active.version || 'N/A';
            const acc = active.accuracy != null ? `${active.accuracy}%` : 'N/A';

            if (nameEl) nameEl.textContent = algo;
            if (subEl) subEl.innerHTML = `${version} &nbsp;&middot;&nbsp; Accuracy: <strong>${acc}</strong><br>Dataset: <strong>${total}</strong> (train ${tr} / test ${te})`;
            if (mlNameEl) mlNameEl.textContent = `${algo} (${version})`;
            if (mlStatus) {
                mlStatus.textContent = active.status === 'fallback_active' ? 'Fallback Active' : 'Active';
                mlStatus.className   = active.status === 'fallback_active' ? 'badge badge-red' : 'badge badge-green';
            }
            return;
        }

        const res = await fetch('/api/admin/models', { headers: { 'Authorization': `Bearer ${token()}` } });
        const data = await res.json();
        if (!data.success) return;
        const active = data.models.find(m => m.status === 'active') || data.models[0];
        if (!active) return;
        if (nameEl) nameEl.textContent = active.algorithm;
        if (subEl)  subEl.innerHTML = `${active.version} &nbsp;&middot;&nbsp; Accuracy: <strong>${active.accuracy}%</strong>`;
        if (mlNameEl) mlNameEl.textContent = active.algorithm + ' (' + active.version + ')';
    } catch (_) {}
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    if (!checkAdminAuth()) return;

    document.getElementById('currentDate').textContent =
        new Date().toLocaleDateString('en-US', { weekday:'long', year:'numeric', month:'long', day:'numeric' });

    checkDbHealth();
    loadDashboard();
    loadActiveModel();
});

// ── System Health Monitor (single definition) ─────────────────────────────────
async function loadSystemHealth() {
    try {
        const res  = await fetch('/api/admin/system/health', {
            headers: { 'Authorization': 'Bearer ' + token() }
        });
        const data = await res.json();
        if (!data.success) return;

        const dbStatus = document.getElementById('dbStatus');
        const dbDot    = document.getElementById('dbDot');
        if (dbStatus) {
            const sizeMb = data.database?.size_mb || 0;
            dbStatus.textContent = `Connected · ${sizeMb} MB`;
            dbStatus.className   = sizeMb > 500 ? 'badge badge-yellow' : 'badge badge-green';
        }
        if (dbDot) dbDot.className = 'status-dot online';

        if (data.alerts && data.alerts.length) {
            const alertsEl = document.getElementById('healthAlerts');
            if (alertsEl) {
                alertsEl.innerHTML = data.alerts.map(a =>
                    `<div style="background:#7f1d1d;color:#fca5a5;padding:.5rem .85rem;border-radius:8px;font-size:.78rem;margin-bottom:.4rem;">
                        <i class="bi bi-exclamation-triangle-fill me-1"></i>${a.message}
                    </div>`
                ).join('');
                alertsEl.style.display = '';
            }
        }
    } catch (_) {}
}
