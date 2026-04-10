const token = () => localStorage.getItem('token');

function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }

async function loadPatients(preselectedId) {
    const select = document.getElementById('patient_id');
    try {
        const res  = await fetch('/api/doctor/patients?limit=100', {
            headers: { 'Authorization': 'Bearer ' + token() }
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        select.innerHTML = '<option value="">Choose patient...</option>';
        data.patients.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = `${p.username} (${p.patient_id || 'ID:' + p.id})`;
            if (String(p.id) === String(preselectedId)) opt.selected = true;
            select.appendChild(opt);
        });

        if (preselectedId) onPatientChange(preselectedId);
    } catch (err) {
        select.innerHTML = `<option value="">Error loading patients: ${err.message}</option>`;
    }
}

async function onPatientChange(patientId) {
    const panel        = document.getElementById('patientPanel');
    const predPanel    = document.getElementById('predictionPanel');
    const paymentNotice = document.getElementById('paymentNotice');

    if (!patientId) {
        panel.innerHTML = '<p class="text-muted text-sm">Select a patient to see their info.</p>';
        predPanel.style.display   = 'none';
        paymentNotice.style.display = 'none';
        const blockMsg = document.getElementById('prescribeBlockMsg');
        if (blockMsg) blockMsg.style.display = 'none';
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) submitBtn.disabled = true;
        const form = document.getElementById('prescriptionForm');
        if (form) form.style.opacity = '1';
        return;
    }

    panel.innerHTML = '<div class="text-center py-2 text-muted"><i class="bi bi-hourglass-split"></i> Loading...</div>';

    try {
        const res  = await fetch(`/api/doctor/patients/${patientId}`, {
            headers: { 'Authorization': 'Bearer ' + token() }
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        const p = data.patient;
        panel.innerHTML = `
            <div class="space-y-1 text-sm" style="padding:.5rem;">
                <div><strong>Name:</strong> ${esc(p.username)}</div>
                <div><strong>Email:</strong> ${esc(p.email)}</div>
                <div><strong>Patient ID:</strong> ${esc(p.patient_id || 'PAT' + p.id)}</div>
                <div><strong>Registered:</strong> ${p.created_at ? new Date(p.created_at).toLocaleDateString() : 'N/A'}</div>
            </div>`;

        document.getElementById('paymentLink').href =
            `/templates/payment/payment_page.html?service=medication&patient_id=${patientId}`;
        paymentNotice.style.display = '';

        loadPrediction(patientId);

    } catch (err) {
        panel.innerHTML = `<p class="text-sm" style="color:#dc2626;">${esc(err.message)}</p>`;
    }
}

async function loadPrediction(patientId) {
    const panel = document.getElementById('predictionPanel');
    const body  = document.getElementById('predictionBody');
    const form  = document.getElementById('prescriptionForm');
    const submitBtn = document.getElementById('submitBtn');
    const blockMsg  = document.getElementById('prescribeBlockMsg');

    const fmt = (v, suffix = '') => (v === null || v === undefined || v === '' ? 'N/A' : `${v}${suffix}`);
    const toDate = (v) => v ? new Date(v).toLocaleString() : 'N/A';
    const showPanel = () => {
        panel.classList.remove('hidden');
        panel.style.display = '';
    };

    try {
        const res  = await fetch(`/api/doctor/patients/${patientId}/predictions?limit=1`, {
            headers: { 'Authorization': 'Bearer ' + token() }
        });
        const data = await res.json();

        if (!data.success || !data.predictions.length) {
            panel.classList.add('hidden');
            panel.style.display = 'none';
            // No prediction — block prescription
            if (blockMsg) {
                blockMsg.style.display = '';
                blockMsg.innerHTML = `<div style="background:#fff7ed;border:1.5px solid #fed7aa;border-radius:12px;padding:1.25rem;">
                    <strong style="color:#c2410c;"><i class="bi bi-x-circle-fill"></i> Cannot Prescribe</strong>
                    <p style="color:#9a3412;font-size:.875rem;margin:.5rem 0 0;">This patient has no ML prediction on record. A prediction must be completed before a prescription can be issued.</p>
                </div>`;
            }
            if (submitBtn) submitBtn.disabled = true;
            return;
        }

        const pred = data.predictions[0];
        const risk = (pred.risk_level || '').toUpperCase();
        const isHighRisk = risk.includes('HIGH');
        const badgeColor = risk.includes('LOW') ? '#16a34a' : risk.includes('MODERATE') ? '#d97706' : '#dc2626';

        // Pull full prediction details so doctor sees full patient values before prescribing/tests.
        let detail = null;
        try {
            const dRes = await fetch(`/api/doctor/predictions/${pred.id}`, {
                headers: { 'Authorization': 'Bearer ' + token() }
            });
            const dData = await dRes.json();
            if (dData.success) detail = dData.prediction;
        } catch (_) {}

        const input = detail?.input_data || {};
        const hr = detail?.health_record || {};
        const glucose = input.glucose ?? input.Glucose ?? hr.glucose;
        const insulin = input.insulin ?? input.Insulin;
        const bmi = input.bmi ?? input.BMI ?? hr.bmi;
        const bp = input.blood_pressure ?? input.BloodPressure ?? hr.blood_pressure;
        const age = input.age ?? input.Age ?? hr.age;
        const pregnancies = input.pregnancies ?? input.Pregnancies ?? hr.pregnancies;
        const dpf = input.diabetes_pedigree_function ?? input.DiabetesPedigreeFunction;

        body.innerHTML = `
            <div class="space-y-1 text-sm" style="padding:.5rem;">
                <div><strong>Risk Level:</strong> <span style="background:${badgeColor};color:#fff;padding:2px 10px;border-radius:99px;font-size:.75rem;font-weight:700;">${esc(pred.risk_level)}</span></div>
                <div><strong>Probability:</strong> ${fmt(pred.probability_percent, '%')}</div>
                <div><strong>Prediction:</strong> ${esc(detail?.prediction_result || (isHighRisk ? 'Diabetic (likely)' : 'Non-Diabetic / Lower risk'))}</div>
                ${isHighRisk ? `
                <div style="background:#fef2f2;border:1px solid #fecaca;color:#991b1b;border-radius:8px;padding:.5rem .75rem;margin:.35rem 0;">
                    <i class="bi bi-exclamation-triangle-fill"></i> HIGH RISK ALERT: Review labs/vitals before prescription.
                </div>` : ''}
                <div class="mt-2" style="border-top:1px solid #e5e7eb;padding-top:.5rem;">
                    <div class="font-semibold mb-1">Patient Values Used</div>
                    <div>Glucose: <strong>${fmt(glucose)}</strong></div>
                    <div>Insulin: <strong>${fmt(insulin)}</strong></div>
                    <div>BMI: <strong>${fmt(bmi)}</strong></div>
                    <div>Blood Pressure: <strong>${fmt(bp)}</strong></div>
                    <div>Age: <strong>${fmt(age)}</strong></div>
                    <div>Pregnancies: <strong>${fmt(pregnancies)}</strong></div>
                    <div>DPF: <strong>${fmt(dpf)}</strong></div>
                </div>
                <div class="text-xs text-muted mt-1">Date: ${toDate(pred.created_at)}</div>
            </div>`;
        showPanel();

        // Block prescription for Low and Moderate risk
        if (!isHighRisk) {
            if (blockMsg) {
                blockMsg.style.display = '';
                blockMsg.innerHTML = `<div style="background:#fff7ed;border:1.5px solid #fed7aa;border-radius:12px;padding:1.25rem;">
                    <strong style="color:#c2410c;"><i class="bi bi-x-circle-fill"></i> Prescription Not Required</strong>
                    <p style="color:#9a3412;font-size:.875rem;margin:.5rem 0 0;">
                        This patient has a <strong>${esc(pred.risk_level)}</strong> result (${pred.probability_percent?.toFixed(1)}%).
                        Prescriptions are only issued for <strong>High Risk</strong> or <strong>Very High Risk</strong> patients.
                        Advise lifestyle changes only.
                    </p>
                </div>`;
            }
            if (submitBtn) submitBtn.disabled = true;
            if (form) form.style.opacity = '0.4';
        } else {
            if (blockMsg) blockMsg.style.display = 'none';
            if (submitBtn) submitBtn.disabled = false;
            if (form) form.style.opacity = '1';
        }

    } catch (_) {
        panel.classList.add('hidden');
        panel.style.display = 'none';
    }
}

async function handleSubmit(event) {
    event.preventDefault();

    const patientId = document.getElementById('patient_id').value;
    if (!patientId) { showAlert('danger', 'Please select a patient.'); return; }

    const btn = document.getElementById('submitBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Saving...';

    try {
        const res  = await fetch('/api/doctor/prescriptions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token() },
            body: JSON.stringify({
                patient_id:   parseInt(patientId),
                medication:   document.getElementById('medication').value.trim(),
                dosage:       document.getElementById('dosage').value.trim(),
                frequency:    document.getElementById('frequency').value,
                duration:     document.getElementById('duration').value,
                instructions: document.getElementById('instructions').value.trim(),
                notes:        document.getElementById('notes').value.trim()
            })
        });

        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        showAlert('success', `Prescription created! ID: ${data.prescription.prescription_id}`);
        event.target.reset();
        document.getElementById('patientPanel').innerHTML = '<p class="text-muted text-sm">Select a patient to see their info.</p>';
        document.getElementById('predictionPanel').style.display  = 'none';
        document.getElementById('paymentNotice').style.display    = 'none';

        setTimeout(() => { window.location.href = '/templates/doctor/patient_list.html'; }, 2000);

    } catch (err) {
        showAlert('danger', 'Error: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-circle"></i> Create Prescription';
    }
}

function showAlert(type, message) {
    const el = document.getElementById('formAlert');
    el.className = 'alert alert-' + type;
    el.textContent = message;
    el.style.display = '';
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function handleLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/';
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('doctor');
    if (!user) return;

    document.getElementById('navUserName').textContent = user.name || user.username;
    const sb = document.getElementById('sidebarDoctorName');
    if (sb) sb.textContent = user.name || user.username;

    const preselectedId = new URLSearchParams(window.location.search).get('patient_id');
    loadPatients(preselectedId);

    document.getElementById('patient_id').addEventListener('change', e => onPatientChange(e.target.value));
    document.getElementById('prescriptionForm').addEventListener('submit', handleSubmit);
});
