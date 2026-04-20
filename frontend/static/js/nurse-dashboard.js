// Nurse Dashboard

function getToken() { return localStorage.getItem('token'); }

function handleLogout() { if(typeof logout==='function') logout(); else { localStorage.clear(); window.location.href='/login'; } }

function esc(str) {
    const d = document.createElement('div');
    d.textContent = str ?? '';
    return d.innerHTML;
}

function updateDate() {
    document.getElementById('currentDate').textContent =
        new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

function initCharts(stats) {
    // Activity chart — use real stats
    const activityCtx = document.getElementById('activityChart');
    if (activityCtx && typeof Chart !== 'undefined') {
        new Chart(activityCtx, {
            type: 'bar',
            data: {
                labels: ['Patients Seen', 'Appointments', 'Waiting', 'Urgent', 'Emergency'],
                datasets: [{
                    label: 'Today',
                    data: [
                        stats.patients_seen_today || 0,
                        stats.today_appointments  || 0,
                        stats.patients_in_queue   || 0,
                        stats.urgent_cases        || 0,
                        stats.emergency_cases     || 0
                    ],
                    backgroundColor: ['#3b82f6','#f59e0b','#ef4444','#f97316','#dc2626'],
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
            }
        });
    }

    // Vitals chart — priority breakdown
    const vitalsCtx = document.getElementById('vitalsChart');
    if (vitalsCtx && typeof Chart !== 'undefined') {
        new Chart(vitalsCtx, {
            type: 'doughnut',
            data: {
                labels: ['Normal', 'Urgent', 'Emergency'],
                datasets: [{
                    data: [
                        Math.max(0, (stats.patients_in_queue || 0) - (stats.urgent_cases || 0) - (stats.emergency_cases || 0)),
                        stats.urgent_cases    || 0,
                        stats.emergency_cases || 0
                    ],
                    backgroundColor: ['#22c55e', '#f59e0b', '#ef4444']
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                plugins: { legend: { position: 'bottom' } }
            }
        });
    }
}

function renderRecentActivity(activity) {
    const measureList = document.getElementById('recentMeasurementsList');
    const vitalsList  = document.getElementById('recentVitalsList');

    if (!activity || !activity.length) {
        const empty = '<div class="list-item" style="justify-content:center;color:#64748b;font-size:.85rem;">No recent activity</div>';
        measureList.innerHTML = empty;
        vitalsList.innerHTML  = empty;
        return;
    }

    const rows = activity.slice(0, 5).map(v => {
        const name = esc(v.patient ? v.patient.name : 'Unknown');
        const pid  = esc(v.patient ? v.patient.patient_id : '');
        const time = v.recorded_at
            ? new Date(v.recorded_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
            : '';
        return `<div class="list-item justify-between">
            <div>
                <div class="font-medium text-sm">${name}</div>
                <div class="text-xs text-muted">${esc(time)}</div>
            </div>
            <span class="badge badge-blue">${pid}</span>
        </div>`;
    }).join('');

    measureList.innerHTML = rows;
    vitalsList.innerHTML  = rows;
}

async function loadDashboard() {
    try {
        const res  = await fetch('/api/nurse/dashboard', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        const stats = data.dashboard.statistics;
        document.getElementById('statPatientsSeen').textContent = stats.patients_seen_today ?? 0;
        document.getElementById('statAppointments').textContent = stats.today_appointments  ?? 0;
        document.getElementById('statWaiting').textContent      = stats.patients_in_queue   ?? 0;
        document.getElementById('statTotal').textContent        = stats.total_patients       ?? 0;

        initCharts(stats);
        renderRecentActivity(data.dashboard.recent_activity);

    } catch (e) {
        const err = `<div class="list-item" style="justify-content:center;color:#ef4444;font-size:.85rem;">Failed to load: ${esc(e.message)}</div>`;
        document.getElementById('recentMeasurementsList').innerHTML = err;
        document.getElementById('recentVitalsList').innerHTML = err;
        // Still init charts with zeros so page doesn't break
        initCharts({});
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('nurse');
    if (!user) return;

    document.getElementById('navUserName').textContent = user.name || user.username;
    const sb = document.getElementById('sidebarName');
    if (sb) sb.textContent = user.name || user.username;

    updateDate();
    loadDashboard();
});
