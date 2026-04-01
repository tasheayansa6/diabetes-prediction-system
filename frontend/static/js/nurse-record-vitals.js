// Nurse Record Vitals Page

function getToken() { return localStorage.getItem('token'); }

function handleLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/';
}

function showToast(msg, type) {
    type = type || 'success';
    const colors = { success: '#059669', danger: '#dc2626', warning: '#d97706' };
    const t = document.createElement('div');
    t.style.cssText = `position:fixed;top:1.5rem;right:1.5rem;z-index:9999;background:${colors[type]||colors.success};color:#fff;padding:.85rem 1.25rem;border-radius:12px;font-size:.875rem;font-weight:600;box-shadow:0 8px 24px rgba(0,0,0,.2);display:flex;align-items:center;gap:.5rem;min-width:220px;`;
    t.innerHTML = `<i class="bi bi-${type==='success'?'check-circle-fill':type==='warning'?'exclamation-circle-fill':'x-circle-fill'}"></i> ${msg}`;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
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

// When patient is selected, load their latest vitals to pre-fill form
async function onPatientChange() {
    const patientId = document.getElementById('patient_id').value;
    if (!patientId) return;

    try {
        const res  = await fetch(`/api/nurse/patients/${patientId}/vitals?limit=1`, {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();
        if (data.success && data.vitals && data.vitals.length) {
            const v = data.vitals[0];
            const set = (id, val) => { if (val != null) document.getElementById(id).value = val; };
            set('blood_pressure_systolic',  v.blood_pressure_systolic);
            set('blood_pressure_diastolic', v.blood_pressure_diastolic);
            set('heart_rate',               v.heart_rate);
            set('temperature',              v.temperature);
            set('respiratory_rate',         v.respiratory_rate);
            set('oxygen_saturation',        v.oxygen_saturation);
            set('height',                   v.height);
            set('weight',                   v.weight);
            showToast('Previous vitals pre-filled. Update as needed.', 'warning');
        }
    } catch { /* no previous vitals — that's fine */ }
}

function setCurrentDateTime() {
    document.getElementById('date_time').value = new Date().toISOString().slice(0, 16);
}

// Live BMI calculation
function calcBMI() {
    const h = parseFloat(document.getElementById('height').value);
    const w = parseFloat(document.getElementById('weight').value);
    const resultDiv  = document.getElementById('bmiResult');
    const bmiVal     = document.getElementById('bmiValue');
    const bmiCat     = document.getElementById('bmiCategory');
    if (!h || !w || h <= 0) { resultDiv.style.display = 'none'; return; }
    const bmi = w / Math.pow(h / 100, 2);
    let cat = '', color = '';
    if      (bmi < 18.5) { cat = 'Underweight'; color = '#d97706'; }
    else if (bmi < 25)   { cat = 'Normal';       color = '#059669'; }
    else if (bmi < 30)   { cat = 'Overweight';   color = '#d97706'; }
    else                 { cat = 'Obese';         color = '#dc2626'; }
    bmiVal.textContent  = bmi.toFixed(1);
    bmiVal.style.color  = color;
    bmiCat.textContent  = cat;
    bmiCat.style.color  = color;
    resultDiv.style.display = '';
    resultDiv.style.background = '#f5f3ff';
    resultDiv.style.borderRadius = '10px';
    resultDiv.style.padding = '.75rem';
}

// BP status indicator
function updateBPStatus() {
    const d = parseInt(document.getElementById('blood_pressure_diastolic').value);
    const el = document.getElementById('bpStatus');
    if (!d) { el.style.display = 'none'; return; }
    let msg = '', cls = 'alert-info';
    if      (d < 60)  { msg = 'Low diastolic BP — monitor closely';  cls = 'alert-warning'; }
    else if (d <= 80) { msg = 'Normal diastolic BP (' + d + ' mmHg)'; cls = 'alert-success'; }
    else if (d <= 90) { msg = 'Elevated diastolic BP — note for doctor'; cls = 'alert-warning'; }
    else              { msg = 'High diastolic BP — alert doctor';      cls = 'alert-danger'; }
    el.className   = 'alert ' + cls + ' text-sm';
    el.textContent = msg;
    el.style.display = '';
}

function getOptionalInt(id) {
    const el = document.getElementById(id);
    if (!el) return undefined;
    const val = el.value;
    return val !== '' ? parseInt(val) : undefined;
}

function getOptionalFloat(id) {
    const el = document.getElementById(id);
    if (!el) return undefined;
    const val = el.value;
    return val !== '' ? parseFloat(val) : undefined;
}

async function handleVitalsSubmit(event) {
    event.preventDefault();

    const patientId = parseInt(document.getElementById('patient_id').value);
    if (!patientId) { showToast('Please select a patient.', 'warning'); return; }

    const diasVal = document.getElementById('blood_pressure_diastolic').value;
    if (!diasVal || isNaN(parseInt(diasVal))) {
        showToast('Diastolic Blood Pressure is required for ML prediction.', 'danger');
        document.getElementById('blood_pressure_diastolic').focus();
        return;
    }

    const payload = { patient_id: patientId, notes: document.getElementById('notes').value };

    ['blood_pressure_systolic','blood_pressure_diastolic','heart_rate','respiratory_rate','pain_level']
        .forEach(f => { const v = getOptionalInt(f);   if (v !== undefined) payload[f] = v; });
    ['temperature','oxygen_saturation','height','weight']
        .forEach(f => { const v = getOptionalFloat(f); if (v !== undefined) payload[f] = v; });
    // skin_thickness is NOT sent to backend (no DB column)

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
            showToast('Vitals saved successfully!');
            setTimeout(() => window.location.href = '/templates/nurse/dashboard.html', 1200);
        } else {
            showToast(data.message || 'Failed to save vitals', 'danger');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle"></i> Save Vitals';
        }
    } catch {
        showToast('Network error. Please try again.', 'danger');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-circle"></i> Save Vitals';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('nurse');
    if (!user) return;

    document.getElementById('navUserName').textContent = user.name || user.username;
    const sb = document.getElementById('sidebarName');
    if (sb) sb.textContent = user.name || user.username;

    setCurrentDateTime();
    loadPatients();

    // Patient search filter
    const searchInput = document.getElementById('patientSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const q = this.value.toLowerCase();
            const select = document.getElementById('patient_id');
            Array.from(select.options).forEach(opt => {
                opt.style.display = (!q || opt.text.toLowerCase().includes(q)) ? '' : 'none';
            });
        });
    }

    document.getElementById('patient_id').addEventListener('change', onPatientChange);
    document.getElementById('vitalsForm').addEventListener('submit', handleVitalsSubmit);
});
