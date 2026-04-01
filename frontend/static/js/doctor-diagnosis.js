let currentPatientId = null;

function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }

function riskBadgeClass(risk) {
    if (!risk) return 'badge-gray';
    if (risk.includes('VERY HIGH')) return 'badge-purple';
    if (risk.includes('HIGH'))      return 'badge-red';
    if (risk.includes('MODERATE'))  return 'badge-yellow';
    return 'badge-green';
}

async function loadPatient(patientId) {
    const token   = localStorage.getItem('token');
    const loading = document.getElementById('patientInfoLoading');
    const content = document.getElementById('patientInfoContent');
    const errorDiv = document.getElementById('patientInfoError');

    try {
        const res  = await fetch(`/api/doctor/patients/${patientId}`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        const p = data.patient;
        document.getElementById('patientName').textContent       = p.username;
        document.getElementById('patientEmail').textContent      = p.email;
        document.getElementById('patientId').textContent         = p.patient_id || 'PAT' + p.id;
        document.getElementById('patientRegistered').textContent = p.created_at
            ? new Date(p.created_at).toLocaleDateString() : 'N/A';

        loading.style.display = 'none';
        content.style.display = '';

        loadLatestPrediction(patientId, token);

        const feeNotice = document.getElementById('feeNotice');
        document.getElementById('feeAmount').textContent = 'ETB 500.00';
        document.getElementById('paymentLink').href =
            `/templates/payment/payment_page.html?service=consultation&patient_id=${patientId}`;
        feeNotice.style.display = '';

    } catch (err) {
        loading.style.display = 'none';
        errorDiv.textContent  = 'Error loading patient: ' + err.message;
        errorDiv.style.display = '';
    }
}

async function loadLatestPrediction(patientId, token) {
    try {
        const res  = await fetch(`/api/doctor/patients/${patientId}/predictions?limit=1`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const data = await res.json();
        if (!data.success || !data.predictions.length) return;

        const pred  = data.predictions[0];
        const card  = document.getElementById('predictionCard');
        const riskEl = document.getElementById('predRiskLevel');

        riskEl.textContent = pred.risk_level;
        riskEl.className   = 'badge ' + riskBadgeClass(pred.risk_level);
        document.getElementById('predProbability').textContent =
            pred.probability_percent ? pred.probability_percent.toFixed(1) + '%' : 'N/A';
        document.getElementById('predDate').textContent = pred.created_at
            ? new Date(pred.created_at).toLocaleDateString() : 'N/A';

        card.style.display = '';
    } catch (_) {}
}

async function handleDiagnosisSubmit(event) {
    event.preventDefault();
    if (!currentPatientId) { showAlert('danger', 'No patient selected.'); return; }

    const btn      = document.getElementById('submitBtn');
    const symptoms  = document.getElementById('symptoms').value.trim();
    const diagnosis = document.getElementById('diagnosis').value.trim();
    const treatment = document.getElementById('treatment').value.trim();
    const notes     = document.getElementById('notes').value.trim();

    const content = `SYMPTOMS:\n${symptoms}\n\nDIAGNOSIS:\n${diagnosis}\n\nTREATMENT PLAN:\n${treatment}${notes ? '\n\nADDITIONAL NOTES:\n' + notes : ''}`;

    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Saving...';

    try {
        const res  = await fetch('/api/doctor/notes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token') },
            body: JSON.stringify({
                patient_id:   parseInt(currentPatientId),
                title:        'Diagnosis - ' + new Date().toLocaleDateString(),
                content:      content,
                category:     'diagnosis',
                is_important: true
            })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        showAlert('success', 'Diagnosis saved successfully!');
        event.target.reset();
        setTimeout(() => { window.location.href = '/templates/doctor/patient_list.html'; }, 1500);

    } catch (err) {
        showAlert('danger', 'Error saving diagnosis: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-circle"></i> Save Diagnosis';
    }
}

function showAlert(type, message) {
    const el = document.getElementById('formAlert');
    el.className   = 'alert alert-' + type;
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
    document.getElementById('diagnosisForm').addEventListener('submit', handleDiagnosisSubmit);

    currentPatientId = new URLSearchParams(window.location.search).get('patient_id');
    if (currentPatientId) {
        loadPatient(currentPatientId);
    } else {
        document.getElementById('patientInfoLoading').style.display = 'none';
        document.getElementById('patientInfoError').style.display   = '';
    }
});
