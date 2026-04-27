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

// When patient is selected, auto-fill ALL fields from profile + previous vitals
let _existingVitalId = null;

async function onPatientChange() {
    const patientId = document.getElementById('patient_id').value;
    _existingVitalId = null;

    // Clear banners and highlights
    const banner = document.getElementById('missingFieldsBanner');
    if (banner) banner.remove();
    ['pregnancies','diabetes_pedigree','age'].forEach(id => {
        document.getElementById(id)?.classList.remove('border-red-500');
    });

    if (!patientId) {
        document.getElementById('patientInfo').style.display = 'none';
        return;
    }

    await autoFillFromProfile(patientId);
}

// Auto-fill ALL form fields from patient profile + previous vitals
async function autoFillFromProfile(patientId) {
    try {
        const res  = await fetch(`/api/nurse/patient-profile/${patientId}`, {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();
        if (!data.success) return;

        const p = data.patient;
        const v = data.vitals || {};

        // ── Show patient info card ──────────────────────────────────────────
        const infoDiv   = document.getElementById('patientInfo');
        const nameEl    = document.getElementById('selectedPatientName');
        const uidEl     = document.getElementById('selectedPatientUniqueId');
        const emailEl   = document.getElementById('selectedPatientEmail');
        const metaEl    = document.getElementById('selectedPatientMeta');
        const prevTag   = document.getElementById('prevVitalsTag');
        const newTag    = document.getElementById('newPatientTag');

        if (nameEl)  nameEl.textContent  = p.username;
        if (uidEl)   uidEl.textContent   = p.patient_id;
        if (emailEl) emailEl.textContent = p.email;
        if (metaEl)  metaEl.innerHTML =
            `Registered: <strong>${p.created_at ? new Date(p.created_at).toLocaleDateString('en-US',{year:'numeric',month:'short',day:'numeric'}) : 'N/A'}</strong>` +
            (p.blood_group ? ` &nbsp;|&nbsp; Blood Group: <strong>${p.blood_group}</strong>` : '') +
            (p.allergies   ? ` &nbsp;|&nbsp; <span style="color:#dc2626;">Allergies: ${p.allergies}</span>` : '');

        if (prevTag) prevTag.style.display = data.has_previous_vitals ? '' : 'none';
        if (newTag)  newTag.style.display  = data.has_previous_vitals ? 'none' : '';
        if (infoDiv) infoDiv.style.display = '';
        // Scroll info card into view
        if (infoDiv) infoDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        // ── Auto-select gender from profile ─────────────────────────────────────────
        const gender = p.gender || (data.has_previous_vitals && v.pregnancies === 0 ? 'male' : null);
        if (gender === 'male') {
            const maleRadio = document.getElementById('genderMale');
            if (maleRadio) { maleRadio.checked = true; onGenderChange(); }
        } else if (gender === 'female') {
            const femaleRadio = document.getElementById('genderFemale');
            if (femaleRadio) { femaleRadio.checked = true; onGenderChange(); }
        }

        // ── Auto-fill vitals fields ─────────────────────────────────────────
        const set = (id, val) => {
            const el = document.getElementById(id);
            if (el && val != null && val !== '') {
                el.value = val;
                el.classList.add('field-autofilled');
            }
        };

        if (data.has_previous_vitals) {
            // Fill from previous vitals record
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
            // Recalculate BMI if height+weight filled
            if (v.height && v.weight) calcBMI();
            if (v.blood_pressure_diastolic) updateBPStatus();
            showToast('Previous vitals auto-filled. Review and update if needed.', 'warning');
        } else {
            showToast(`New patient ${p.username} (${p.patient_id}) — please fill vitals.`, 'success');
        }

        // Check missing ML fields and highlight
        const missing = [];
        if (!document.getElementById('pregnancies').value)       missing.push('Pregnancies');
        if (!document.getElementById('diabetes_pedigree').value) missing.push('Diabetes Pedigree');
        if (!document.getElementById('age').value)               missing.push('Age');
        if (!document.getElementById('blood_pressure_diastolic').value) missing.push('Diastolic BP');

        if (missing.length) {
            missing.forEach(name => {
                const idMap = {
                    'Pregnancies': 'pregnancies',
                    'Diabetes Pedigree': 'diabetes_pedigree',
                    'Age': 'age',
                    'Diastolic BP': 'blood_pressure_diastolic'
                };
                document.getElementById(idMap[name])?.classList.add('border-red-500');
            });
        }

    } catch (e) {
        console.warn('autoFillFromProfile error:', e);
    }
}

// Gender change handler — lock pregnancies to 0 for male
function onGenderChange() {
    const isMale = document.getElementById('genderMale')?.checked;
    const pregEl = document.getElementById('pregnancies');
    const hintEl = document.getElementById('pregnanciesHint');
    const noteEl = document.getElementById('pregnanciesNote');
    const maleLabel   = document.getElementById('genderMaleLabel');
    const femaleLabel = document.getElementById('genderFemaleLabel');

    if (isMale) {
        pregEl.value    = '0';
        pregEl.readOnly = true;
        pregEl.disabled = true;
        pregEl.style.background = '#f1f5f9';
        pregEl.style.color      = '#94a3b8';
        pregEl.style.cursor     = 'not-allowed';
        pregEl.classList.add('field-autofilled');
        if (hintEl) hintEl.textContent = '(locked to 0 — male patient)';
        if (noteEl) { noteEl.textContent = 'Male patient — pregnancies locked to 0.'; noteEl.style.color = '#2563eb'; }
        if (maleLabel)   maleLabel.style.cssText   += ';border-color:#2563eb;background:#eff6ff;color:#1e40af;';
        if (femaleLabel) femaleLabel.style.cssText  += ';border-color:#e2e8f0;background:#fff;color:#475569;';
    } else {
        pregEl.readOnly = false;
        pregEl.disabled = false;
        pregEl.style.background = '';
        pregEl.style.color      = '';
        pregEl.style.cursor     = '';
        pregEl.classList.remove('field-autofilled');
        if (pregEl.value === '0') pregEl.value = '';
        if (hintEl) hintEl.textContent = '(enter number of pregnancies)';
        if (noteEl) { noteEl.textContent = 'Number of times pregnant.'; noteEl.style.color = '#90a4ae'; }
        if (femaleLabel) femaleLabel.style.cssText += ';border-color:#db2777;background:#fdf2f8;color:#9d174d;';
        if (maleLabel)   maleLabel.style.cssText   += ';border-color:#e2e8f0;background:#fff;color:#475569;';
    }
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

    // Save gender to patient record
    const gender = document.querySelector('input[name="gender"]:checked')?.value || null;
    if (gender) payload.gender = gender;

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
