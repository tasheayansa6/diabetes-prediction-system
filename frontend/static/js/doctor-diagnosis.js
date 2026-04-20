let currentPatientId = null;
let wizardStep = 1;
let latestPrediction = null;
let latestPredictionId = null;

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
        if (content) {
            content.classList.remove('hidden');
            content.style.display = '';
        }

        loadLatestPrediction(patientId, token);

        const feeNotice = document.getElementById('feeNotice');
        document.getElementById('feeAmount').textContent = 'ETB 500.00';
        document.getElementById('paymentLink').href =
            `/templates/payment/payment_page.html?service=consultation&patient_id=${patientId}`;
        if (feeNotice) feeNotice.style.display = '';

    } catch (err) {
        loading.style.display = 'none';
        errorDiv.textContent  = 'Error loading patient: ' + err.message;
        errorDiv.classList.remove('hidden');
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
        latestPredictionId = pred.id;
        const card  = document.getElementById('predictionCard');
        const riskEl = document.getElementById('predRiskLevel');

        riskEl.textContent = pred.risk_level;
        riskEl.className   = 'badge ' + riskBadgeClass(pred.risk_level);
        document.getElementById('predProbability').textContent =
            pred.probability_percent ? pred.probability_percent.toFixed(1) + '%' : 'N/A';
        document.getElementById('predDate').textContent = pred.created_at
            ? new Date(pred.created_at).toLocaleDateString() : 'N/A';

        if (card) {
            card.classList.remove('hidden');
            card.style.display = '';
        }

        // Load full prediction details for clinical autofill suggestions.
        const detailRes = await fetch(`/api/doctor/predictions/${pred.id}`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const detailData = await detailRes.json();
        if (detailData.success && detailData.prediction) {
            latestPrediction = detailData.prediction;
            enablePredictionAssist();
        }
    } catch (_) {}
}

function showReviewAlert(type, message) {
    const el = document.getElementById('reviewAlert');
    if (!el) return;
    el.className = 'alert alert-' + type;
    el.textContent = message;
    el.classList.remove('hidden');
}

async function savePredictionReview() {
    if (!latestPredictionId) {
        showReviewAlert('warning', 'No prediction selected for review.');
        return;
    }
    const statusEl = document.getElementById('reviewStatus');
    const summaryEl = document.getElementById('reviewSummaryInput');
    const btn = document.getElementById('saveReviewBtn');
    const status = statusEl ? statusEl.value : '';
    const summary = summaryEl ? summaryEl.value.trim() : '';
    if (!summary) {
        showReviewAlert('warning', 'Review summary is required.');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Saving...';
    try {
    const payload = { status, summary };
    const res = await fetch(`/api/doctor/predictions/${latestPredictionId}/review`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('token')
            },
            body: JSON.stringify(payload)
        });
        let data = null;
        try { data = await res.json(); } catch (_) {}

        // Fallback route for environments where review endpoint isn't active yet.
        if (res.status === 404 && latestPrediction && latestPrediction.patient && latestPrediction.patient.id) {
            const noteRes = await fetch('/api/doctor/notes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + localStorage.getItem('token')
                },
                body: JSON.stringify({
                    patient_id: latestPrediction.patient.id,
                    title: `Prediction Review #${latestPredictionId}`,
                    content: `status:${status}\nsummary:${summary}`,
                    category: 'prediction_review',
                    is_important: status === 'rejected' || status === 'needs_followup'
                })
            });
            let noteData = null;
            try { noteData = await noteRes.json(); } catch (_) {}
            if (!noteRes.ok || !noteData || !noteData.success) {
                throw new Error((noteData && noteData.message) || 'Failed to save review fallback note');
            }
            showReviewAlert('success', 'Prediction review saved successfully (fallback mode).');
            return;
        }

        if (!res.ok || !data || !data.success) throw new Error((data && data.message) || 'Failed to save review');
        showReviewAlert('success', 'Prediction review saved successfully.');
    } catch (err) {
        showReviewAlert('danger', 'Error saving review: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-shield-check"></i> Save Review';
    }
}

function setWizardStep(step) {
    wizardStep = Math.max(1, Math.min(4, step));
    for (let i = 1; i <= 4; i++) {
        const panel = document.getElementById('step' + i + 'Panel');
        const pill = document.getElementById('wizS' + i);
        if (panel) panel.classList.toggle('active', i === wizardStep);
        if (pill) {
            pill.classList.remove('active', 'done');
            if (i < wizardStep) pill.classList.add('done');
            if (i === wizardStep) pill.classList.add('active');
        }
    }

    const prevBtn = document.getElementById('prevStepBtn');
    const nextBtn = document.getElementById('nextStepBtn');
    const submitBtn = document.getElementById('submitBtn');
    if (prevBtn) prevBtn.classList.toggle('hidden', wizardStep === 1);
    if (nextBtn) nextBtn.classList.toggle('hidden', wizardStep === 4);
    if (submitBtn) submitBtn.classList.toggle('hidden', wizardStep !== 4);
}

function canAdvance(step) {
    if (step === 1) return document.getElementById('symptoms').value.trim().length > 0;
    if (step === 2) return document.getElementById('diagnosis').value.trim().length > 0;
    if (step === 3) return document.getElementById('treatment').value.trim().length > 0;
    return true;
}

function nextStep() {
    if (!canAdvance(wizardStep)) {
        showAlert('warning', 'Please complete this section before continuing.');
        return;
    }
    setWizardStep(wizardStep + 1);
}

function previousStep() {
    setWizardStep(wizardStep - 1);
}

function clinicalRiskText(risk) {
    if (!risk) return 'unknown metabolic risk';
    if (risk.includes('VERY HIGH')) return 'very high diabetes risk';
    if (risk.includes('HIGH')) return 'high diabetes risk';
    if (risk.includes('MODERATE')) return 'moderate diabetes risk';
    return 'low diabetes risk';
}

function enablePredictionAssist() {
    const assist = document.getElementById('predictionAssist');
    const actions = document.getElementById('predictionAssistActions');
    if (assist) assist.classList.remove('hidden');
    if (actions) actions.classList.remove('hidden');
}

function buildSymptomsSuggestion() {
    if (!latestPrediction) return '';
    const risk = clinicalRiskText(latestPrediction.risk_level || '');
    const input = latestPrediction.input_data || {};
    const glucose = input.glucose != null ? `${input.glucose} mg/dL` : 'N/A';
    const bmi = input.bmi != null ? String(input.bmi) : 'N/A';
    return [
        `Reported for review after ML screening.`,
        `Clinical context: ${risk}.`,
        `Key values from prediction intake: Glucose ${glucose}, BMI ${bmi}.`,
        `Please confirm current symptoms with patient interview and exam findings.`
    ].join('\n');
}

function buildDiagnosisSuggestion() {
    if (!latestPrediction) return '';
    const risk = latestPrediction.risk_level || 'UNKNOWN';
    const prob = latestPrediction.probability_percent != null ? `${Number(latestPrediction.probability_percent).toFixed(1)}%` : 'N/A';
    return [
        `ML-assisted risk stratification: ${risk} (${prob}).`,
        `Provisional diagnosis: Dysglycemia risk requiring clinical correlation.`,
        `Recommend confirmatory assessment (HbA1c / fasting plasma glucose / OGTT as appropriate).`
    ].join('\n');
}

function buildTreatmentSuggestion() {
    if (!latestPrediction) return '';
    const risk = latestPrediction.risk_level || '';
    const highRisk = risk.includes('HIGH');
    const plan = [
        '1) Lifestyle counseling: nutrition, physical activity, and weight targets.',
        '2) Order/Review confirmatory lab tests and document baseline vitals.',
        '3) Schedule follow-up visit for trend review and treatment adjustment.'
    ];
    if (highRisk) {
        plan.unshift('0) Prioritize early follow-up due to elevated risk category.');
    }
    return plan.join('\n');
}

function applySuggestion(targetId, textBuilder) {
    const el = document.getElementById(targetId);
    if (!el) return;
    if (el.value.trim()) return;
    const val = textBuilder();
    if (val) el.value = val;
}

async function handleDiagnosisSubmit(event) {
    event.preventDefault();
    if (!currentPatientId) { showAlert('danger', 'No patient selected.'); return; }
    if (!canAdvance(1) || !canAdvance(2) || !canAdvance(3)) {
        showAlert('warning', 'Please complete Symptoms, Diagnosis, and Treatment first.');
        return;
    }

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

function handleLogout() { if(typeof logout==='function') logout(); else { localStorage.clear(); window.location.href='/login'; } }

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('doctor');
    if (!user) return;

    document.getElementById('navUserName').textContent = user.name || user.username;
    const sidebarName = document.getElementById('sidebarDoctorName');
    if (sidebarName) sidebarName.textContent = user.name || user.username;
    document.getElementById('diagnosisForm').addEventListener('submit', handleDiagnosisSubmit);
    document.getElementById('nextStepBtn').addEventListener('click', nextStep);
    document.getElementById('prevStepBtn').addEventListener('click', previousStep);

    const fillSymptomsBtn = document.getElementById('fillSymptomsBtn');
    const fillDiagnosisBtn = document.getElementById('fillDiagnosisBtn');
    const fillTreatmentBtn = document.getElementById('fillTreatmentBtn');
    if (fillSymptomsBtn) fillSymptomsBtn.addEventListener('click', () => applySuggestion('symptoms', buildSymptomsSuggestion));
    if (fillDiagnosisBtn) fillDiagnosisBtn.addEventListener('click', () => applySuggestion('diagnosis', buildDiagnosisSuggestion));
    if (fillTreatmentBtn) fillTreatmentBtn.addEventListener('click', () => applySuggestion('treatment', buildTreatmentSuggestion));
    const saveReviewBtn = document.getElementById('saveReviewBtn');
    if (saveReviewBtn) saveReviewBtn.addEventListener('click', savePredictionReview);
    setWizardStep(1);

    currentPatientId = new URLSearchParams(window.location.search).get('patient_id');
    if (currentPatientId) {
        loadPatient(currentPatientId);
    } else {
        document.getElementById('patientInfoLoading').style.display = 'none';
        const errEl = document.getElementById('patientInfoError');
        if (errEl) {
            errEl.classList.remove('hidden');
            errEl.style.display = '';
        }
    }
});
