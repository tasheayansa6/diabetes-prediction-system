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
    el.innerHTML = tests.slice(0, 5).map(t => `
        <div class="list-item justify-between">
            <div>
                <div class="font-medium text-sm">${t.patient_name || 'Unknown'} — ${t.test_name}</div>
                <div class="text-xs text-muted">${t.created_at ? new Date(t.created_at).toLocaleDateString() : ''}</div>
            </div>
            <a href="/templates/lab/enter_lab_results.html" class="btn btn-sm btn-primary">Process</a>
        </div>
    `).join('');
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
        const res = await fetch('/api/labs/dashboard', { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        const { statistics: stats, recent_activity, technician_info } = data.dashboard;

        // Stat cards
        document.getElementById('statPending').textContent = stats.pending_tests ?? 0;
        document.getElementById('statCompleted').textContent = stats.completed_today ?? 0;
        document.getElementById('statTotal').textContent = stats.total_processed ?? 0;
        document.getElementById('statUrgent').textContent = stats.urgent_pending ?? 0;

        renderPendingList(recent_activity.filter(t => t.status === 'pending'));
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
    document.getElementById('topUserName').textContent = name;
    document.getElementById('userName').textContent = name;

    const today = new Date();
    document.getElementById('currentDate').textContent = today.toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });

    loadDashboard();
});
