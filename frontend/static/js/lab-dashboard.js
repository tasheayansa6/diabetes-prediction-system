// Lab Dashboard - uses GET /api/labs/dashboard

function authHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('token')
    };
}

function initCharts(stats, recentActivity) {
    // Results trend chart - use real weekly data if available, else zeros
    const resultsCtx = document.getElementById('resultsChart');
    if (resultsCtx) {
        new Chart(resultsCtx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Tests Completed',
                    data: [0, 0, 0, 0, 0, 0, stats.completed_today || 0],
                    borderColor: '#2A7BE4',
                    backgroundColor: 'rgba(42, 123, 228, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: { y: { beginAtZero: true } }
            }
        });
    }

    // Volume chart - by test category from recent activity
    const volumeCtx = document.getElementById('volumeChart');
    if (volumeCtx) {
        const counts = {};
        (recentActivity || []).forEach(t => {
            const cat = t.test_category || t.test_type || 'Other';
            counts[cat] = (counts[cat] || 0) + 1;
        });
        const labels = Object.keys(counts).length ? Object.keys(counts) : ['No Data'];
        const values = Object.keys(counts).length ? Object.values(counts) : [1];
        const colors = ['#2A7BE4', '#20C997', '#FFC107', '#DC3545', '#6C757D'];

        new Chart(volumeCtx, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{ data: values, backgroundColor: colors.slice(0, labels.length) }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { position: 'bottom' } }
            }
        });
    }
}

function renderPendingList(tests) {
    const el = document.getElementById('pendingList');
    if (!el) return;
    if (!tests.length) {
        el.innerHTML = '<div class="list-item" style="justify-content:center;color:#64748b;">No pending tests</div>';
        return;
    }
    el.innerHTML = tests.slice(0, 8).map(t => {
        const patientName = t.patient?.name || t.patient_name || 'Unknown';
        const patientId   = t.patient?.patient_id || '';
        const priority    = t.priority || 'normal';
        const badgeColor  = priority === 'urgent' ? '#dc2626' : '#d97706';
        const date        = t.created_at ? new Date(t.created_at).toLocaleDateString('en-US',{month:'short',day:'numeric'}) : '';
        const testId      = t.test_id || t.id;
        return `
        <div class="list-item" style="align-items:center;justify-content:space-between;">
            <div style="flex:1;min-width:0;">
                <div style="font-weight:700;font-size:.875rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                    <i class="bi bi-flask-fill" style="color:#2563eb;"></i> ${t.test_name}
                </div>
                <div style="font-size:.75rem;color:#64748b;margin-top:.15rem;display:flex;align-items:center;gap:.4rem;flex-wrap:wrap;">
                    <i class="bi bi-person-fill"></i> ${patientName}
                    ${patientId ? `<span style="background:#1e3a8a;color:#fff;border-radius:6px;padding:.1rem .45rem;font-family:monospace;font-size:.68rem;font-weight:700;">${patientId}</span>` : ''}
                    <span style="color:#94a3b8;">${date}</span>
                    <span style="background:${badgeColor}20;color:${badgeColor};padding:.1rem .5rem;border-radius:99px;font-weight:700;font-size:.68rem;">${priority.toUpperCase()}</span>
                </div>
            </div>
            <a href="/templates/lab/enter_lab_results.html?test_id=${testId}"
               class="btn btn-sm btn-primary" style="margin-left:.75rem;white-space:nowrap;flex-shrink:0;">
               <i class="bi bi-pencil-square"></i> Enter
            </a>
        </div>`;
    }).join('') +
    (tests.length > 8 ? `
        <div class="list-item" style="justify-content:center;padding:.6rem;">
            <a href="/templates/lab/enter_lab_results.html" class="btn btn-sm btn-outline" style="width:100%;justify-content:center;">
                <i class="bi bi-list-check"></i> View All ${tests.length} Pending
            </a>
        </div>` : '');
}

function renderCompletedList(tests) {
    const el = document.getElementById('completedList');
    if (!el) return;
    const completed = tests.filter(t => t.status === 'completed').slice(0, 5);
    if (!completed.length) {
        el.innerHTML = '<div class="list-item" style="justify-content:center;color:#64748b;">No completed tests today</div>';
        return;
    }
    el.innerHTML = completed.map(t => `
        <div class="list-item">
            <div>
                <div class="font-medium text-sm">${t.patient_name || 'Unknown'} — ${t.test_name}</div>
                <div class="text-xs text-muted">${t.created_at ? new Date(t.created_at).toLocaleTimeString() : ''}</div>
            </div>
        </div>
    `).join('');
}

async function loadDashboard() {
    try {
        // Fetch dashboard stats and pending tests in parallel
        const [dashRes, pendingRes] = await Promise.all([
            fetch('/api/labs/dashboard', { headers: authHeaders() }),
            fetch('/api/labs/pending?limit=8', { headers: authHeaders() })
        ]);

        const data        = await dashRes.json();
        const pendingData = await pendingRes.json();

        if (!data.success) throw new Error(data.message);

        const { statistics: stats, recent_activity, technician_info } = data.dashboard;

        // Stat cards
        const _s = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v ?? 0; };
        _s('statPending',   stats.pending_tests);
        _s('statCompleted', stats.completed_today);
        _s('statTotal',     stats.total_processed);
        _s('statUrgent',    stats.urgent_pending);

        // Pending list — from dedicated endpoint (all pending, not just last 10)
        const pendingTests = pendingData.success ? pendingData.pending_tests : [];
        renderPendingList(pendingTests);

        renderCompletedList(recent_activity);
        initCharts(stats, recent_activity);

    } catch (err) {
        console.error('Dashboard load error:', err.message);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('lab_technician');
    if (!user) return;

    const name = user.name || user.username;
    const _t = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
    _t('topUserName', name);
    _t('userName',    name);

    const today = new Date();
    _t('currentDate', today.toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    }));

    loadDashboard();
});
