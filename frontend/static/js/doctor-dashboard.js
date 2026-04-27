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

// ── Load patients list for dashboard ─────────────────────────────────────────
async function loadPatientsList() {
    const list = document.getElementById('highRiskList');
    if (!list) return;

    list.innerHTML = `<div class="list-item" style="justify-content:center;color:#64748b;">
        <i class="bi bi-hourglass-split"></i>&nbsp; Loading patients...
    </div>`;

    try {
        // Single call — get all patients using doctor API
        const data = await apiFetch('/api/doctor/patients?limit=50');

        if (!data.success) {
            list.innerHTML = `<div class="list-item" style="justify-content:center;color:#dc2626;padding:1.5rem;">
                <i class="bi bi-exclamation-circle"></i>&nbsp; ${esc(data.message || 'Failed to load patients')}
            </div>`;
            return;
        }

        const patients = data.patients || [];
        const total = data.pagination?.total || patients.length;

        // Update total patients count
        const totalEl = document.getElementById('totalPatientsCount');
        if (totalEl) totalEl.textContent = total;

        if (!patients.length) {
            list.innerHTML = `<div class="list-item" style="justify-content:center;color:#64748b;padding:1.5rem;">
                <i class="bi bi-people"></i>&nbsp; No patients registered yet
            </div>`;
            return;
        }

        // Show patient list with link to patient list page
        list.innerHTML = patients.slice(0, 8).map(p => `
            <div class="list-item" style="justify-content:space-between;align-items:center;">
                <div style="flex:1;min-width:0;">
                    <div style="font-weight:700;font-size:0.875rem;color:#0f172a;">${esc(p.username)}</div>
                    <div style="font-size:0.75rem;color:#64748b;margin-top:0.1rem;">
                        <span class="badge badge-blue" style="font-size:.65rem;">${esc(p.patient_id || 'N/A')}</span>
                        &nbsp;${p.created_at ? new Date(p.created_at).toLocaleDateString() : ''}
                    </div>
                </div>
                <div style="display:flex;gap:4px;flex-shrink:0;">
                    <a href="/templates/doctor/diagnosis.html?patient_id=${p.id}"
                       class="btn btn-sm btn-primary" style="padding:.2rem .5rem;font-size:.72rem;" title="Diagnose">
                        <i class="bi bi-clipboard-pulse"></i>
                    </a>
                    <a href="/templates/nurse/record_vitals.html?patient_id=${p.id}"
                       class="btn btn-sm btn-outline" style="padding:.2rem .5rem;font-size:.72rem;color:#059669;border-color:#6ee7b7;" title="Record Vitals">
                        <i class="bi bi-heart-pulse"></i>
                    </a>
                    <a href="/templates/doctor/lab_requests.html?patient_id=${p.id}"
                       class="btn btn-sm btn-outline" style="padding:.2rem .5rem;font-size:.72rem;" title="Lab Test">
                        <i class="bi bi-flask"></i>
                    </a>
                </div>
            </div>`).join('') +
            (total > 8 ? `
            <div class="list-item" style="justify-content:center;padding:.75rem;">
                <a href="/templates/doctor/patient_list.html" class="btn btn-sm btn-outline" style="width:100%;justify-content:center;">
                    <i class="bi bi-people"></i> View All ${total} Patients
                </a>
            </div>` : '');

    } catch (err) {
        list.innerHTML = `<div class="list-item" style="justify-content:center;color:#dc2626;padding:1.5rem;">
            <i class="bi bi-exclamation-circle"></i>&nbsp; Failed to load patients
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

    // Load patient list (sets totalPatientsCount)
    loadPatientsList();
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

// ── Quick Lab Order Modal ─────────────────────────────────────────────────────
async function openQuickLabModal() {
    document.getElementById('quickLabModal').style.display = 'flex';
    document.getElementById('quickLabAlert').style.display = 'none';
    document.getElementById('qlTest').value = '';
    document.getElementById('qlPriority').value = 'normal';
    // Load patients into select
    const sel = document.getElementById('qlPatient');
    sel.innerHTML = '<option value="">Loading...</option>';
    try {
        const data = await apiFetch('/api/doctor/patients?limit=100');
        const patients = data.patients || [];
        sel.innerHTML = '<option value="">Select patient...</option>' +
            patients.map(p => `<option value="${p.id}">${esc(p.username)} (${esc(p.patient_id || 'ID:' + p.id)})</option>`).join('');
    } catch (_) {
        sel.innerHTML = '<option value="">Failed to load patients</option>';
    }
}

function closeQuickLabModal() {
    document.getElementById('quickLabModal').style.display = 'none';
}

async function submitQuickLab() {
    const patientId = document.getElementById('qlPatient').value;
    const testVal   = document.getElementById('qlTest').value;
    const priority  = document.getElementById('qlPriority').value;
    const alertEl   = document.getElementById('quickLabAlert');
    const btn       = document.getElementById('qlSubmitBtn');

    if (!patientId) { alertEl.textContent = 'Please select a patient.'; alertEl.style.display = ''; return; }
    if (!testVal)   { alertEl.textContent = 'Please select a test.';    alertEl.style.display = ''; return; }
    alertEl.style.display = 'none';

    const [testName] = testVal.split('|');
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Ordering...';

    try {
        const res  = await fetch('/api/doctor/lab-requests', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
            body: JSON.stringify({ patient_id: parseInt(patientId), test_name: testName, test_category: 'Diabetes', priority })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        closeQuickLabModal();
        // Refresh lab count
        const labData = await apiFetch('/api/doctor/lab-requests/statistics');
        if (labData.success) {
            const el = document.getElementById('labRequestsCount');
            if (el) el.textContent = labData.statistics?.by_status?.pending ?? 0;
        }
        // Show success toast
        const toast = document.createElement('div');
        toast.style.cssText = 'position:fixed;bottom:1.5rem;right:1.5rem;background:#059669;color:#fff;padding:.75rem 1.25rem;border-radius:10px;font-size:.875rem;font-weight:600;z-index:9999;box-shadow:0 4px 20px rgba(0,0,0,.2);';
        toast.innerHTML = `<i class="bi bi-check-circle-fill"></i> Lab test ordered: ${esc(testName)}`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3500);
    } catch (err) {
        alertEl.textContent = 'Error: ' + err.message;
        alertEl.style.display = '';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-flask"></i> Order Test';
    }
}

// ── Doctor Availability ───────────────────────────────────────────────────────
async function loadAvailability() {
    try {
        const res  = await fetch('/api/doctor/availability', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();
        if (!data.success) return;
        const a = data.availability;
        if (document.getElementById('availDays')  && a.available_days)   document.getElementById('availDays').value  = a.available_days;
        if (document.getElementById('availHours') && a.available_hours)  document.getElementById('availHours').value = a.available_hours;
        if (document.getElementById('consultFee') && a.consultation_fee) document.getElementById('consultFee').value  = a.consultation_fee;
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
            msg.style.display = '';
            msg.style.color   = data.success ? '#059669' : '#dc2626';
            msg.innerHTML     = data.success
                ? '<i class="bi bi-check-circle-fill"></i> Saved successfully'
                : '<i class="bi bi-x-circle-fill"></i> ' + (data.message || 'Save failed');
            setTimeout(() => { msg.style.display = 'none'; }, 3000);
        }
    } catch (_) {}
}
