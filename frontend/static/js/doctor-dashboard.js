const API = '/api';

function getToken() { return localStorage.getItem('token'); }
function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }
function handleLogout() { if(typeof logout==='function') logout(); else { localStorage.clear(); window.location.href='/login'; } }

async function apiFetch(path) {
    try {
        const res = await fetch(API + path, {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        if (res.status === 401) { handleLogout(); return {}; }
        return res.json();
    } catch {
        return { success: false, message: 'Network error' };
    }
}

// ── Render appointments list ──────────────────────────────────────────────────
function renderAppointments(appointments) {
    const list = document.getElementById('appointmentsList');
    if (!list) return;

    if (!appointments || !appointments.length) {
        list.innerHTML = `<div class="list-item" style="justify-content:center;color:#64748b;padding:1.5rem;">
            <i class="bi bi-calendar-x"></i>&nbsp; No upcoming appointments today
        </div>`;
        return;
    }

    list.innerHTML = appointments.map(a => `
        <div class="list-item">
            <div style="flex:1;min-width:0;">
                <div style="font-weight:700;font-size:0.875rem;color:#0f172a;">${esc(a.patient_name || 'Patient #' + a.patient_id)}</div>
                <div style="font-size:0.78rem;color:#64748b;margin-top:0.15rem;">
                    <i class="bi bi-calendar3"></i> ${esc(a.appointment_date)}
                    ${a.appointment_time ? ' &nbsp;<i class="bi bi-clock"></i> ' + esc(a.appointment_time) : ''}
                    &nbsp;—&nbsp;${esc(a.reason || 'General')}
                </div>
            </div>
            <span class="badge badge-blue">${esc(a.status)}</span>
        </div>`).join('');
}

// ── Render high risk patients — single efficient call ─────────────────────────
async function loadHighRiskPatients() {
    const list = document.getElementById('highRiskList');
    if (!list) return;

    list.innerHTML = `<div class="list-item" style="justify-content:center;color:#64748b;">
        <i class="bi bi-hourglass-split"></i>&nbsp; Loading...
    </div>`;

    try {
        // Get all patients in one call
        const patientsData = await apiFetch('/api/doctor/patients?limit=100');
        if (!patientsData.success || !patientsData.patients?.length) {
            list.innerHTML = `<div class="list-item" style="justify-content:center;color:#64748b;padding:1.5rem;">
                <i class="bi bi-people"></i>&nbsp; No patients registered yet
            </div>`;
            return;
        }

        // Update total patients count with real number
        const totalEl = document.getElementById('totalPatientsCount');
        if (totalEl) totalEl.textContent = patientsData.pagination?.total || patientsData.patients.length;

        // Get nurse predictions view (all predictions) — single call
        const predsData = await apiFetch('/api/nurse/predictions?limit=200');
        if (!predsData.success || !predsData.predictions?.length) {
            list.innerHTML = `<div class="list-item" style="justify-content:center;color:#059669;padding:1.5rem;">
                <i class="bi bi-check-circle-fill"></i>&nbsp; No predictions yet
            </div>`;
            return;
        }

        // Build patient map for quick lookup
        const patientMap = {};
        patientsData.patients.forEach(p => { patientMap[p.id] = p; });

        // Find latest prediction per patient
        const latestByPatient = {};
        predsData.predictions.forEach(pred => {
            const pid = pred.patient?.id;
            if (!pid) return;
            if (!latestByPatient[pid] || pred.created_at > latestByPatient[pid].created_at) {
                latestByPatient[pid] = pred;
            }
        });

        // Filter HIGH / VERY HIGH risk
        const highRisk = Object.entries(latestByPatient)
            .filter(([, pred]) => pred.risk_level && (pred.risk_level === 'HIGH' || pred.risk_level === 'VERY_HIGH'))
            .map(([pid, pred]) => ({
                patient: patientMap[pid] || pred.patient,
                pred
            }))
            .filter(r => r.patient)
            .slice(0, 6);

        if (!highRisk.length) {
            list.innerHTML = `<div class="list-item" style="justify-content:center;color:#059669;padding:1.5rem;">
                <i class="bi bi-check-circle-fill"></i>&nbsp; No high risk patients found
            </div>`;
            return;
        }

        const riskStyle = r => (r === 'VERY_HIGH')
            ? 'background:#fee2e2;color:#991b1b;'
            : 'background:#ffedd5;color:#9a3412;';
        const riskLabel = r => (r === 'VERY_HIGH') ? 'VERY HIGH RISK' : 'HIGH RISK';

        list.innerHTML = highRisk.map(({ patient, pred }) => `
            <div class="list-item">
                <div style="flex:1;min-width:0;">
                    <div style="font-weight:700;font-size:0.875rem;color:#0f172a;">
                        ${esc(patient.username || patient.name || 'Patient')}
                    </div>
                    <div style="font-size:0.75rem;color:#64748b;margin-top:0.1rem;">
                        ${pred.created_at ? new Date(pred.created_at).toLocaleDateString() : '—'}
                        &nbsp;·&nbsp; ${pred.probability_percent ? Math.round(pred.probability_percent) + '%' : ''}
                    </div>
                </div>
                <span style="display:inline-flex;align-items:center;padding:0.25em 0.75em;border-radius:99px;font-size:0.72rem;font-weight:700;${riskStyle(pred.risk_level)}">
                    ${riskLabel(pred.risk_level)}
                </span>
            </div>`).join('');

    } catch (err) {
        list.innerHTML = `<div class="list-item" style="justify-content:center;color:#dc2626;padding:1.5rem;">
            <i class="bi bi-exclamation-circle"></i>&nbsp; Failed to load
        </div>`;
    }
}

// ── Load main dashboard stats ─────────────────────────────────────────────────
async function loadDashboard() {
    const user = checkAuth('doctor');
    if (!user) return;

    const name = user.name || user.username || 'Doctor';
    ['navUserName', 'sidebarDoctorName'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = name;
    });

    document.getElementById('currentDate').textContent = new Date().toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });

    // Load dashboard stats + lab count in parallel
    const [dashData, labData] = await Promise.all([
        apiFetch('/api/doctor/dashboard'),
        apiFetch('/api/doctor/lab-requests/statistics')
    ]);

    if (dashData.success) {
        const stats = dashData.dashboard.statistics;
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val ?? 0; };
        set('todayApptCount',     stats.today_appointments);
        set('upcomingApptBadge',  stats.pending_appointments);
        set('prescriptionsCount', stats.prescriptions_this_month);
        // Don't set totalPatientsCount here — loadHighRiskPatients sets it from real count

        if (dashData.dashboard.doctor_info?.name) {
            ['navUserName', 'sidebarDoctorName'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.textContent = dashData.dashboard.doctor_info.name;
            });
        }
        if (dashData.dashboard.doctor_info?.specialization) {
            const spec = document.getElementById('sidebarDoctorSpec');
            if (spec) spec.textContent = dashData.dashboard.doctor_info.specialization;
        }

        renderAppointments(dashData.dashboard.upcoming_appointments);
    } else {
        const apptList = document.getElementById('appointmentsList');
        if (apptList) apptList.innerHTML = `<div class="list-item" style="justify-content:center;color:#dc2626;padding:1.5rem;">
            <i class="bi bi-exclamation-circle"></i>&nbsp; ${esc(dashData.message || 'Failed to load')}
        </div>`;
    }

    if (labData.success) {
        const el = document.getElementById('labRequestsCount');
        if (el) el.textContent = labData.statistics?.by_status?.pending ?? 0;
    }

    // Load patients + high risk (sets totalPatientsCount)
    loadHighRiskPatients();
}

// ── Charts ────────────────────────────────────────────────────────────────────
function initCharts() {
    const patientCtx = document.getElementById('patientChart');
    if (patientCtx && typeof Chart !== 'undefined') {
        new Chart(patientCtx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Patients Treated',
                    data: [30, 35, 40, 38, 42, 45],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59,130,246,0.08)',
                    tension: 0.4, fill: true, pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: true } },
                scales: { y: { beginAtZero: true } }
            }
        });
    }

    const prescriptionCtx = document.getElementById('prescriptionChart');
    if (prescriptionCtx && typeof Chart !== 'undefined') {
        new Chart(prescriptionCtx, {
            type: 'doughnut',
            data: {
                labels: ['Metformin', 'Insulin', 'Glipizide', 'Others'],
                datasets: [{
                    data: [35, 25, 20, 20],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#94a3b8'],
                    borderWidth: 2, borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { position: 'bottom' } }
            }
        });
    }
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    initCharts();
});

// ── Doctor Availability ───────────────────────────────────────────────────────
async function loadAvailability() {
    try {
        const res  = await fetch('/api/doctor/availability', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();
        if (!data.success) return;
        const a = data.availability;
        const daysEl  = document.getElementById('availDays');
        const hoursEl = document.getElementById('availHours');
        const feeEl   = document.getElementById('consultFee');
        if (daysEl  && a.available_days)   daysEl.value  = a.available_days;
        if (hoursEl && a.available_hours)  hoursEl.value = a.available_hours;
        if (feeEl   && a.consultation_fee) feeEl.value   = a.consultation_fee;
    } catch (_) {}
}

async function saveAvailability() {
    const days  = document.getElementById('availDays')?.value;
    const hours = document.getElementById('availHours')?.value;
    const fee   = parseFloat(document.getElementById('consultFee')?.value) || 0;
    try {
        const res  = await fetch('/api/doctor/availability', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
            body: JSON.stringify({ available_days: days, available_hours: hours, consultation_fee: fee })
        });
        const data = await res.json();
        const msg  = document.getElementById('availSaveMsg');
        if (msg) {
            msg.style.display = data.success ? '' : 'none';
            msg.style.color   = data.success ? '#059669' : '#dc2626';
            msg.innerHTML     = data.success
                ? '<i class="bi bi-check-circle-fill"></i> Saved successfully'
                : '<i class="bi bi-x-circle-fill"></i> ' + (data.message || 'Save failed');
            setTimeout(() => { msg.style.display = 'none'; }, 3000);
        }
    } catch (_) {}
}
