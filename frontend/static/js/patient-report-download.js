const API = '/api';

const RISK_CONFIG = {
    'LOW RISK':       { badge: 'bg-success',          label: 'LOW RISK' },
    'MODERATE RISK':  { badge: 'bg-warning text-dark', label: 'MODERATE RISK' },
    'HIGH RISK':      { badge: 'bg-orange text-white', label: 'HIGH RISK' },
    'VERY HIGH RISK': { badge: 'bg-danger',            label: 'VERY HIGH RISK' }
};

function esc(str) {
    const d = document.createElement('div');
    d.textContent = str ?? '—';
    return d.innerHTML;
}

async function loadReport() {
    const user = checkAuth('patient');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;

    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) {
        showError('No prediction ID specified. Please go back and try again.');
        return;
    }

    try {
        const res = await fetch(`${API}/patient/predictions/${id}`, {
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        const p = data.prediction;
        const inp = p.input_data || {};
        const cfg = RISK_CONFIG[p.risk_level] || { badge: 'bg-secondary', label: p.risk_level || 'UNKNOWN' };
        const date = p.created_at ? new Date(p.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : '—';

        document.getElementById('patientName').textContent = user.name || user.username;
        document.getElementById('patientId').textContent = 'PAT' + String(user.id || '').padStart(3, '0');
        document.getElementById('patientAge').textContent = inp.age || '—';
        document.getElementById('reportId').textContent = 'RPT-' + p.id;
        document.getElementById('reportDate').textContent = date;

        const badge = document.getElementById('riskBadge');
        badge.className = 'badge ' + cfg.badge;
        badge.textContent = cfg.label;

        document.getElementById('reportGlucose').textContent = (inp.glucose || '—') + ' mg/dL';
        document.getElementById('reportBloodPressure').textContent = (inp.blood_pressure || '—') + ' mm Hg';
        document.getElementById('reportBmi').textContent = inp.bmi || '—';
        document.getElementById('reportInsulin').textContent = (inp.insulin || '—') + ' mu U/ml';
        document.getElementById('reportSkinThickness').textContent = (inp.skin_thickness || '—') + ' mm';
        document.getElementById('reportDiabetesPedigree').textContent = inp.diabetes_pedigree || '—';
        document.getElementById('reportConfidence').textContent = p.probability_percent != null ? parseFloat(p.probability_percent).toFixed(1) : '—';
        document.getElementById('reportRecommendation').textContent = p.explanation || 'Consult your doctor for personalized advice.';

        // Show full report download button
        const bar = document.getElementById('fullReportBar');
        if (bar) bar.style.display = '';

    } catch (e) {
        showError('Failed to load report: ' + e.message);
    }
}

function showError(msg) {
    document.querySelector('.card-body').innerHTML =
        `<div class="alert alert-danger"><i class="bi bi-exclamation-triangle me-2"></i>${esc(msg)}</div>
         <div class="text-center mt-3">
             <a href="/templates/patient/prediction_history.html" class="btn btn-primary">Back to Predictions</a>
         </div>`;
}

document.addEventListener('DOMContentLoaded', loadReport);
