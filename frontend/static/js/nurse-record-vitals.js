// Nurse Record Vitals Page

function getToken() { return localStorage.getItem('token'); }

function handleLogout() { if(typeof logout==='function') logout(); else { localStorage.clear(); window.location.href='/login'; } }

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
        const res  = await fetch('/api/nurse/patients?limit=500', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();
        if (data.success && data.patients.length) {
            window._allPatients = data.patients;
            _renderPatientOptions(data.patients);
        } else {
            select.innerHTML = '<option value="">No patients found</option>';
        }
    } catch {
        select.innerHTML = '<option value="">Error loading patients</option>';
    }
}

function _renderPatientOptions(patients) {
    const select = document.getElementById('patient_id');
    const current = select.value;
    select.innerHTML = '<option value="">Choose patient...</option>' +
        patients.map(p =>
            `<option value="${p.id}"${p.id == current ? ' selected' : ''}>${p.username} (${p.patient_id || 'ID:' + p.id})</option>`
        ).join('');
}

// When patient is selected, load their latest vitals to pre-fill form
let _existingVitalId = null;  // track if we should PUT (update) or POST (new)

async function onPatientChange() {
    const patientId = document.getElementById('patient_id').value;
    _existingVitalId = null;

    // Clear previous state
    const banner = document.getElementById('missingFieldsBanner');
    if (banner) banner.remove();
    ['pregnancies','diabetes_pedigree','age'].forEach(id => {
        document.getElementById(id)?.classList.remove('border-red-500');
    });

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
            set('skin_thickness',           v.skin_thickness);
            set('pregnancies',              v.pregnancies);
            set('diabetes_pedigree',        v.diabetes_pedigree);
            set('age',                      v.age);

            // Check if ML fields are missing — warn nurse to fill them
            // Use strict null check: undefined means field not in API response (old server)
            // null means field exists in DB but was not filled
            const missing = [];
            if (v.pregnancies       === null) missing.push('Pregnancies');
            if (v.diabetes_pedigree === null) missing.push('Diabetes Pedigree');
            if (v.age               === null) missing.push('Age');

            if (missing.length) {
                _existingVitalId = v.id;  // will UPDATE this record

                // Show persistent banner on the form
                let banner = document.getElementById('missingFieldsBanner');
                if (!banner) {
                    banner = document.createElement('div');
                    banner.id = 'missingFieldsBanner';
                    document.getElementById('vitalsForm').prepend(banner);
                }
                banner.className = 'alert alert-danger mb-4';
                banner.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i>
                    <strong>Missing ML fields from previous visit:</strong> ${missing.join(', ')}.
                    Please fill them below and save — this will <strong>update</strong> the existing record.`;

                // Highlight the missing input fields
                if (v.pregnancies       == null) document.getElementById('pregnancies').classList.add('border-red-500');
                if (v.diabetes_pedigree == null) document.getElementById('diabetes_pedigree').classList.add('border-red-500');
                if (v.age              == null) document.getElementById('age').classList.add('border-red-500');

                showToast(`Missing ML fields: ${missing.join(', ')} — please fill them now.`, 'danger');
            } else {
                // Clear any previous banner
                const banner = document.getElementById('missingFieldsBanner');
                if (banner) banner.remove();
                showToast('Previous vitals pre-filled. Update as needed.', 'warning');
            }
        }
    } catch { /* no previous vitals — that is fine */ }
}

function setCurrentDateTime() {
    document.getElementById('date_time').value = new Date().toISOString().slice(0, 16);
}

// Live BMI calculation
function calcBMI() {
    const h = parseFloat(document.getElementById('height').value);
    const w = parseFloat(document.getElementById('weight').value);
    const bmiInput   = document.getElementById('bmi') || document.getElementById('bmiInput');
    const resultDiv  = document.getElementById('bmiResult');
    const bmiVal     = document.getElementById('bmiValue');
    const bmiCat     = document.getElementById('bmiCategory');
    if (!h || !w || h <= 0) {
        if (bmiInput) bmiInput.readOnly = false;
        if (resultDiv) resultDiv.style.display = 'none';
        return;
    }
    const bmi = w / Math.pow(h / 100, 2);
    let cat = '', color = '';
    if      (bmi < 18.5) { cat = 'Underweight'; color = '#d97706'; }
    else if (bmi < 25)   { cat = 'Normal';       color = '#059669'; }
    else if (bmi < 30)   { cat = 'Overweight';   color = '#d97706'; }
    else                 { cat = 'Obese';         color = '#dc2626'; }
    // Lock BMI field to calculated value — prevents contradictory manual entry
    if (bmiInput) {
        bmiInput.value    = bmi.toFixed(1);
        bmiInput.readOnly = true;
        bmiInput.classList.add('field-autofilled');
        bmiInput.title    = 'Auto-calculated from height & weight';
    }
    if (bmiVal)  { bmiVal.textContent  = bmi.toFixed(1); bmiVal.style.color  = color; }
    if (bmiCat)  { bmiCat.textContent  = cat;            bmiCat.style.color  = color; }
    if (resultDiv) {
        resultDiv.style.display    = '';
        resultDiv.style.background = '#f5f3ff';
        resultDiv.style.borderRadius = '10px';
        resultDiv.style.padding    = '.75rem';
    }
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

    // Validate required ML fields — warn but don't hard block
    const pregVal = document.getElementById('pregnancies').value;
    const dpfVal  = document.getElementById('diabetes_pedigree').value;
    const ageVal  = document.getElementById('age').value;

    const missingML = [];
    if (pregVal === '' || isNaN(parseInt(pregVal)))    missingML.push('Pregnancies');
    if (!dpfVal || isNaN(parseFloat(dpfVal)))          missingML.push('Diabetes Pedigree');
    if (!ageVal || isNaN(parseInt(ageVal)))            missingML.push('Age');

    if (missingML.length) {
        showToast(`Please fill required ML fields: ${missingML.join(', ')}`, 'danger');
        if (missingML.includes('Pregnancies'))       document.getElementById('pregnancies').focus();
        else if (missingML.includes('Diabetes Pedigree')) document.getElementById('diabetes_pedigree').focus();
        else document.getElementById('age').focus();
        return;
    }

    const payload = { patient_id: patientId, notes: document.getElementById('notes').value };

    ['blood_pressure_systolic','blood_pressure_diastolic','heart_rate','respiratory_rate','pain_level']
        .forEach(f => { const v = getOptionalInt(f);   if (v !== undefined) payload[f] = v; });
    ['temperature','oxygen_saturation','height','weight','skin_thickness']
        .forEach(f => { const v = getOptionalFloat(f); if (v !== undefined) payload[f] = v; });

    // Required ML fields — only include if filled
    const pregInt = parseInt(document.getElementById('pregnancies').value);
    const dpfFloat = parseFloat(document.getElementById('diabetes_pedigree').value);
    const ageInt = parseInt(document.getElementById('age').value);
    if (!isNaN(pregInt))   payload.pregnancies       = pregInt;
    if (!isNaN(dpfFloat))  payload.diabetes_pedigree = dpfFloat;
    if (!isNaN(ageInt))    payload.age               = ageInt;

    const btn = event.target.querySelector('[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Saving...';

    try {
        // If existing vital had missing ML fields, UPDATE it instead of creating duplicate
        const method = _existingVitalId ? 'PUT' : 'POST';
        const url    = _existingVitalId
            ? `/api/nurse/vitals/${_existingVitalId}`
            : '/api/nurse/vitals';

        const res  = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            _existingVitalId = null;
            const banner = document.getElementById('missingFieldsBanner');
            if (banner) banner.remove();
            ['pregnancies','diabetes_pedigree','age'].forEach(id => {
                document.getElementById(id)?.classList.remove('border-red-500');
            });
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

    // Load patients, then auto-select from URL ?patient_id= if present
    const urlPatientId = new URLSearchParams(window.location.search).get('patient_id');
    loadPatients().then(function() {
        if (urlPatientId) {
            const select = document.getElementById('patient_id');
            if (select) {
                select.value = urlPatientId;
                if (select.value == urlPatientId) onPatientChange();
            }
        }
    });

    // Patient search filter — live re-render
    const searchInput = document.getElementById('patientSearch');
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const q = this.value.toLowerCase().trim();
            const all = window._allPatients || [];
            const filtered = q
                ? all.filter(p =>
                    (p.username || '').toLowerCase().includes(q) ||
                    (p.patient_id || '').toLowerCase().includes(q) ||
                    String(p.id).includes(q)
                  )
                : all;
            _renderPatientOptions(filtered);
        });
    }

    document.getElementById('patient_id').addEventListener('change', onPatientChange);
    document.getElementById('vitalsForm').addEventListener('submit', handleVitalsSubmit);
});
