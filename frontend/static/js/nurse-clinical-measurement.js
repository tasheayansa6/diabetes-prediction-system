// Nurse Clinical Measurement Page

const UNIT_MAP = {
    temperature: '°C', heart_rate: 'bpm', respiratory_rate: 'breaths/min',
    blood_pressure_systolic: 'mmHg', blood_pressure_diastolic: 'mmHg',
    oxygen_saturation: '%', height: 'cm', weight: 'kg', pain_level: '0-10'
};

function getToken() { return localStorage.getItem('token'); }

function showToast(msg, type) {
    type = type || 'success';
    const colors = { success: '#059669', danger: '#dc2626', warning: '#d97706' };
    const t = document.createElement('div');
    t.style.cssText = `background:${colors[type]||colors.success};color:#fff;padding:.85rem 1.25rem;border-radius:12px;font-size:.875rem;font-weight:600;box-shadow:0 8px 24px rgba(0,0,0,.2);min-width:220px;`;
    t.innerHTML = `<i class="bi bi-${type==='success'?'check-circle-fill':type==='warning'?'exclamation-circle-fill':'x-circle-fill'} me-2"></i>${msg}`;
    const c = document.getElementById('toastContainer');
    if (c) c.appendChild(t);
    else document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
}

function handleLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/';
}

async function loadPatients() {
    const select = document.getElementById('patient_id');
    try {
        const res  = await fetch('/api/nurse/patients?limit=200', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();
        if (data.success && data.patients.length) {
            select.innerHTML = '<option value="">Choose patient...</option>' +
                data.patients.map(p =>
                    `<option value="${p.id}">${p.username} (${p.patient_id})</option>`
                ).join('');
        } else {
            select.innerHTML = '<option value="">No patients found</option>';
        }
    } catch {
        select.innerHTML = '<option value="">Error loading patients</option>';
    }
}

function autoFillUnit() {
    const type = document.getElementById('measurement_type').value;
    document.getElementById('unit').value = UNIT_MAP[type] || '';
}

async function handleMeasurementSubmit(event) {
    event.preventDefault();

    const patientId       = parseInt(document.getElementById('patient_id').value);
    const measurementType = document.getElementById('measurement_type').value;
    const value           = parseFloat(document.getElementById('value').value);
    const notes           = document.getElementById('notes').value;

    if (!patientId)       { showToast('Please select a patient.', 'warning'); return; }
    if (!measurementType) { showToast('Please select a measurement type.', 'warning'); return; }
    if (isNaN(value))     { showToast('Please enter a valid value.', 'warning'); return; }

    const payload = { patient_id: patientId, notes, [measurementType]: value };

    const btn = event.target.querySelector('[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Saving...';

    try {
        const res  = await fetch('/api/nurse/vitals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            showToast('Measurement saved successfully!');
            setTimeout(() => window.location.href = '/templates/nurse/dashboard.html', 1200);
        } else {
            showToast(data.message || 'Failed to save measurement', 'danger');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle"></i> Save Measurement';
        }
    } catch {
        showToast('Network error. Please try again.', 'danger');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-circle"></i> Save Measurement';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('nurse');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    const sb = document.getElementById('sidebarName');
    if (sb) sb.textContent = user.name || user.username;

    loadPatients();
    document.getElementById('measurement_type').addEventListener('change', autoFillUnit);
    document.getElementById('clinicalMeasurementForm').addEventListener('submit', handleMeasurementSubmit);
});
