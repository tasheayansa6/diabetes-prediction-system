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

async function loadWaitingPatients() {
    try {
        const res  = await fetch('/api/nurse/queue?status=waiting&limit=20', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();
        const list  = document.getElementById('waitingPatientsList');
        const badge = document.getElementById('waitingBadge');
        if (!list) return;
        const queue = (data.success && data.queue) ? data.queue : [];

        // Detect newly registered patients (in queue for < 5 min) and show popup
        const now = Date.now();
        queue.forEach(function(q) {
            if (!q.check_in_time) return;
            const age = (now - new Date(q.check_in_time).getTime()) / 1000;
            if (age < 300) { // registered within last 5 minutes
                const name = q.patient ? q.patient.name : 'New Patient';
                const pid  = q.patient ? q.patient.patient_id : '';
                const key  = 'notified_' + (q.patient ? q.patient.id : q.id);
                if (!sessionStorage.getItem(key)) {
                    sessionStorage.setItem(key, '1');
                    showNewPatientPopup(name, pid, q.patient ? q.patient.id : '');
                }
            }
        });

        if (badge) badge.textContent = queue.length;
        if (!queue.length) {
            list.innerHTML = '<div class="list-item" style="justify-content:center;color:#64748b;font-size:.85rem;">No patients waiting</div>';
            return;
        }
        list.innerHTML = queue.map(function(q) {
            const name = esc(q.patient ? q.patient.name : 'Patient #' + q.id);
            const pid  = esc(q.patient ? q.patient.patient_id : '');
            const wait = esc(q.waiting_time || '');
            const pri  = q.priority_label || 'Normal';
            const priColor = pri === 'Emergency' ? '#dc2626' : pri === 'Urgent' ? '#f59e0b' : '#22c55e';
            const patId = q.patient ? q.patient.id : '';
            return `<div class="list-item" style="padding:.85rem 1rem;border-bottom:1px solid #f1f5f9;">
                <div style="flex:1;min-width:0;">
                    <div style="font-weight:700;font-size:.9rem;color:#0f172a;">${name}</div>
                    <div style="display:flex;align-items:center;gap:.4rem;margin-top:.25rem;flex-wrap:wrap;">
                        <span style="background:#1e3a8a;color:#fff;border-radius:6px;padding:.1rem .5rem;font-weight:700;font-family:monospace;font-size:.78rem;">${pid}</span>
                        <span style="font-size:.72rem;color:#64748b;">Waiting: ${wait}</span>
                        <span style="background:${priColor}20;color:${priColor};padding:.1rem .45rem;border-radius:99px;font-size:.68rem;font-weight:700;">${pri}</span>
                    </div>
                </div>
                <a href="/templates/nurse/record_vitals.html?patient_id=${patId}"
                   class="btn btn-sm btn-primary" style="padding:.3rem .75rem;font-size:.78rem;flex-shrink:0;">
                    <i class="bi bi-heart-pulse"></i> Record Vitals
                </a>
            </div>`;
        }).join('');
    } catch (e) {
        const list = document.getElementById('waitingPatientsList');
        if (list) list.innerHTML = '<div class="list-item" style="color:#ef4444;font-size:.85rem;">Failed to load queue</div>';
    }
}

function showNewPatientPopup(name, patientId, dbId) {
    // Remove any existing popup
    const existing = document.getElementById('newPatientPopup');
    if (existing) existing.remove();

    const popup = document.createElement('div');
    popup.id = 'newPatientPopup';
    popup.style.cssText = [
        'position:fixed', 'top:1.25rem', 'right:1.25rem', 'z-index:9999',
        'background:linear-gradient(135deg,#059669,#10b981)',
        'color:#fff', 'border-radius:16px', 'padding:1.1rem 1.4rem',
        'box-shadow:0 8px 32px rgba(5,150,105,.4)',
        'min-width:300px', 'max-width:380px',
        'animation:slideIn .3s ease'
    ].join(';');
    popup.innerHTML =
        '<div style="display:flex;align-items:flex-start;gap:.85rem;">' +
        '<div style="width:42px;height:42px;border-radius:50%;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;flex-shrink:0;">' +
        '<i class="bi bi-person-plus-fill" style="font-size:1.3rem;"></i></div>' +
        '<div style="flex:1;">' +
        '<div style="font-weight:800;font-size:.95rem;margin-bottom:.3rem;">New Patient Registered!</div>' +
        `<div style="font-weight:700;font-size:1rem;">${esc(name)}</div>` +
        `<div style="background:rgba(255,255,255,.25);border-radius:6px;padding:.2rem .6rem;font-family:monospace;font-weight:700;font-size:.85rem;display:inline-block;margin:.3rem 0;">${esc(patientId)}</div>` +
        '<div style="font-size:.78rem;opacity:.9;margin-top:.2rem;">Waiting for vitals recording</div>' +
        '</div>' +
        `<a href="/templates/nurse/record_vitals.html?patient_id=${dbId}" ` +
        'style="background:#fff;color:#059669;border:none;border-radius:10px;padding:.4rem .85rem;font-size:.8rem;font-weight:700;cursor:pointer;text-decoration:none;flex-shrink:0;margin-left:.5rem;align-self:center;">' +
        '<i class="bi bi-heart-pulse"></i> Record</a>' +
        '</div>' +
        '<button onclick="document.getElementById(\"newPatientPopup\").remove()" ' +
        'style="position:absolute;top:.6rem;right:.75rem;background:none;border:none;color:rgba(255,255,255,.7);font-size:1.2rem;cursor:pointer;line-height:1;">&times;</button>';
    popup.style.position = 'fixed';
    document.body.appendChild(popup);
    // Auto-dismiss after 12 seconds
    setTimeout(function() { if (popup.parentNode) popup.remove(); }, 12000);
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
        loadWaitingPatients();

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
    setInterval(loadWaitingPatients, 30000);

    // Real-time: reload waiting list when a WebSocket notification arrives
    if (typeof _connectSocket === 'function') {
        _connectSocket();
    }
    // Also poll every 15s for new patients
    setInterval(loadWaitingPatients, 15000);
});
