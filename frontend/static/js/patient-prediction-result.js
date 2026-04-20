const API = '/api';
function getToken() { return localStorage.getItem('token'); }

const RISK_CONFIG = {
    'LOW RISK': {
        key: 'low', label: 'LOW RISK', color: '#16a34a', boxKey: 'low',
        icon: 'bi-emoji-smile-fill',
        summary: 'You are not currently at significant risk of diabetes.',
        recommendation: 'Your results look healthy. Maintain regular exercise (30 min/day), a balanced diet low in sugar, and an annual check-up. No immediate medical action is needed.',
        alertHtml: `<div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:14px;padding:1.25rem;display:flex;gap:1rem;align-items:flex-start;">
            <i class="bi bi-emoji-smile-fill" style="color:#16a34a;font-size:1.75rem;flex-shrink:0;"></i>
            <div>
                <div style="font-weight:700;color:#166534;font-size:1rem;margin-bottom:.35rem;">You are not at risk right now</div>
                <div style="color:#15803d;font-size:.875rem;line-height:1.6;">Keep up your healthy habits. No doctor visit is required at this time. Come back for a check-up in 12 months or if you notice any symptoms.</div>
                <div style="margin-top:.85rem;display:flex;gap:.6rem;flex-wrap:wrap;">
                    <a href="health_data_form.html" class="btn btn-sm" style="background:#16a34a;color:#fff;border:none;">New Prediction</a>
                    <a href="prediction_history.html" class="btn btn-sm btn-outline">View History</a>
                </div>
            </div>
        </div>`
    },
    'MODERATE RISK': {
        key: 'moderate', label: 'MODERATE RISK', color: '#d97706', boxKey: 'moderate',
        icon: 'bi-exclamation-circle-fill',
        summary: 'You have some risk factors. No diabetes yet, but worth monitoring.',
        recommendation: 'Reduce sugar and refined carbohydrate intake, increase physical activity, and maintain a healthy weight. No doctor visit needed now — recheck in 3 months.',
        alertHtml: `<div style="background:#fffbeb;border:1.5px solid #fde68a;border-radius:14px;padding:1.25rem;display:flex;gap:1rem;align-items:flex-start;">
            <i class="bi bi-exclamation-circle-fill" style="color:#d97706;font-size:1.75rem;flex-shrink:0;"></i>
            <div>
                <div style="font-weight:700;color:#92400e;font-size:1rem;margin-bottom:.35rem;">No doctor needed — focus on lifestyle</div>
                <div style="color:#b45309;font-size:.875rem;line-height:1.6;">
                    You do <strong>not</strong> have diabetes. Some risk factors are present but manageable on your own:<br>
                    <ul style="margin:.5rem 0 0 1rem;padding:0;">
                        <li>Cut down on sugar and processed foods</li>
                        <li>Walk or exercise at least 30 minutes daily</li>
                        <li>Maintain a healthy weight</li>
                        <li>Recheck your prediction in 3 months</li>
                    </ul>
                </div>
                <div style="margin-top:.85rem;display:flex;gap:.6rem;flex-wrap:wrap;">
                    <a href="health_data_form.html" class="btn btn-sm" style="background:#d97706;color:#fff;border:none;">New Prediction in 3 Months</a>
                    <a href="prediction_history.html" class="btn btn-sm btn-outline">View History</a>
                </div>
            </div>
        </div>`
    },
    'HIGH RISK': {
        key: 'high', label: 'HIGH RISK', color: '#dc2626', boxKey: 'high',
        icon: 'bi-exclamation-triangle-fill',
        summary: 'You are at high risk. Early action can prevent diabetes.',
        recommendation: 'Please consult your doctor soon. Diet control, weight management, and regular exercise are essential. Further tests such as HbA1c may be ordered by your doctor.',
        alertHtml: `<div style="background:linear-gradient(135deg,#7f1d1d,#991b1b);border-radius:14px;padding:1.25rem;display:flex;gap:1rem;align-items:flex-start;animation:pulse-border 2s infinite;">
            <i class="bi bi-exclamation-triangle-fill" style="color:#fca5a5;font-size:1.75rem;flex-shrink:0;"></i>
            <div>
                <div style="font-weight:700;color:#fff;font-size:1rem;margin-bottom:.35rem;">High Risk — Please See a Doctor Soon</div>
                <div style="color:#fecaca;font-size:.875rem;line-height:1.6;">Your result shows a high diabetes risk. Early intervention significantly reduces your chance of developing diabetes. Please book an appointment with your doctor.</div>
                <div style="margin-top:.85rem;display:flex;gap:.6rem;flex-wrap:wrap;">
                    <a href="appointment.html?reason=High+Risk+Diabetes+Review" class="btn btn-sm" style="background:#fff;color:#991b1b;border:none;font-weight:700;">Book Doctor Appointment</a>
                    <button onclick="downloadReport()" class="btn btn-sm" style="background:rgba(255,255,255,.15);color:#fecaca;border:1px solid rgba(255,255,255,.3);">Download Report</button>
                </div>
            </div>
        </div>`
    },
    'VERY HIGH RISK': {
        key: 'veryhigh', label: 'VERY HIGH RISK', color: '#7c3aed', boxKey: 'high',
        icon: 'bi-heart-pulse-fill',
        summary: 'Immediate medical attention is strongly recommended.',
        recommendation: 'Please see a doctor immediately. You may require diagnostic tests, medication, or a structured diabetes management program. Do not delay.',
        alertHtml: `<div style="background:linear-gradient(135deg,#4c1d95,#6d28d9);border-radius:14px;padding:1.25rem;display:flex;gap:1rem;align-items:flex-start;animation:pulse-border 2s infinite;">
            <i class="bi bi-heart-pulse-fill" style="color:#ddd6fe;font-size:1.75rem;flex-shrink:0;"></i>
            <div>
                <div style="font-weight:700;color:#fff;font-size:1rem;margin-bottom:.35rem;">Very High Risk — See a Doctor Immediately</div>
                <div style="color:#ddd6fe;font-size:.875rem;line-height:1.6;">Your result indicates a very high diabetes risk. Immediate medical consultation is required. You may need diagnostic tests, medication, or a diabetes management program.</div>
                <div style="margin-top:.85rem;display:flex;gap:.6rem;flex-wrap:wrap;">
                    <a href="appointment.html?reason=Very+High+Risk+Diabetes+Urgent" class="btn btn-sm" style="background:#fff;color:#6d28d9;border:none;font-weight:700;">Book Urgent Appointment</a>
                    <button onclick="downloadReport()" class="btn btn-sm" style="background:rgba(255,255,255,.15);color:#ddd6fe;border:1px solid rgba(255,255,255,.3);">Download Report</button>
                </div>
            </div>
        </div>`
    }
};

const NEEDLE_POS = { 'LOW RISK': 12, 'MODERATE RISK': 37, 'HIGH RISK': 62, 'VERY HIGH RISK': 88 };

function computeBreakdown(riskKey, pct) {
    const all = ['low', 'moderate', 'high', 'veryhigh'];
    const remainder = 100 - pct;
    const others = all.filter(k => k !== riskKey);
    const weights = { low: 1, moderate: 1.5, high: 2, veryhigh: 2.5 };
    const totalW = others.reduce((s, k) => s + weights[k], 0);
    const bd = {};
    others.forEach(k => { bd[k] = Math.round((weights[k] / totalW) * remainder); });
    bd[riskKey] = pct;
    return bd;
}

function animateArc(targetPct) {
    const circumference = 2 * Math.PI * 50;
    const arc = document.getElementById('confArc');
    if (!arc) return;
    let current = 0;
    const step = targetPct / 60;
    const iv = setInterval(() => {
        current = Math.min(current + step, targetPct);
        arc.setAttribute('stroke-dasharray', (current / 100 * circumference) + ' ' + circumference);
        if (current >= targetPct) clearInterval(iv);
    }, 16);
}

function animateCounter(elId, target) {
    const el = document.getElementById(elId);
    if (!el) return;
    let current = 0;
    const step = Math.max(1, Math.round(target / 40));
    const iv = setInterval(() => {
        current = Math.min(current + step, target);
        el.textContent = current + '%';
        if (current >= target) clearInterval(iv);
    }, 20);
}

function moveNeedle(pct) {
    const needle = document.getElementById('riskNeedle');
    if (!needle) return;
    setTimeout(() => { needle.style.left = Math.min(Math.max(pct, 0), 100) + '%'; }, 100);
}

function renderReview(review) {
    const badge = document.getElementById('reviewStatusBadge');
    const summary = document.getElementById('reviewSummary');
    const meta = document.getElementById('reviewMeta');
    if (!badge || !summary || !meta) return;

    const st = (review && review.status) ? String(review.status) : 'pending_review';
    const map = {
        pending_review: { text: 'Pending Review', cls: 'pill-moderate' },
        approved: { text: 'Approved by Doctor', cls: 'pill-low' },
        rejected: { text: 'Rejected - Follow-up Needed', cls: 'pill-high' },
        needs_followup: { text: 'Needs Follow-up', cls: 'pill-high' }
    };
    const cfg = map[st] || map.pending_review;
    badge.className = 'risk-pill ' + cfg.cls;
    badge.textContent = cfg.text;

    summary.textContent = (review && review.summary) ? review.summary : 'Awaiting doctor review.';
    if (review && review.doctor_name) {
        const dt = review.reviewed_at ? new Date(review.reviewed_at).toLocaleString() : '';
        meta.textContent = `Reviewed by Dr. ${review.doctor_name}${dt ? ' on ' + dt : ''}`;
    } else {
        meta.textContent = '';
    }
}

async function loadResult() {
    const user = checkAuth('patient');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    const sb = document.getElementById('sidebarName');
    if (sb) sb.textContent = user.name || user.username;

    const predId = new URLSearchParams(window.location.search).get('id');
    if (!predId) {
        document.querySelector('.main').innerHTML = '<div class="alert alert-warning m-4">No prediction ID found. <a href="/templates/patient/health_data_form.html">Create a new prediction</a>.</div>';
        return;
    }

    try {
        const res = await fetch(API + '/patient/predictions/' + predId, {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        if (res.status === 401) { logout(); return; }
        const data = await res.json();

    if (!data.success) {
        document.querySelector('.main').innerHTML = '<div class="alert alert-danger m-4">Could not load prediction. <a href="/templates/patient/prediction_history.html">View history</a>.</div>';
        return;
    }

    const p = data.prediction;
    const cfg = RISK_CONFIG[p.risk_level] || RISK_CONFIG['LOW RISK'];
    const pct = Math.round(p.probability_percent || 0);
    const confidencePct = p.confidence != null
        ? Math.round(p.confidence)
        : Math.round(50 + (Math.max(pct / 100, 1 - pct / 100) - 0.5) * 90);

    // Risk label + color
    const labelEl = document.getElementById('riskLabel');
    if (labelEl) { labelEl.textContent = cfg.label; labelEl.style.color = cfg.color; }

    // Summary
    const summaryEl = document.getElementById('riskSummary');
    if (summaryEl) summaryEl.textContent = cfg.summary;

    // Card border color
    const card = document.getElementById('riskCard');
    if (card) card.style.borderTop = '4px solid ' + cfg.color;

    // Needle, arc, counter
    moveNeedle(NEEDLE_POS[p.risk_level] || pct);
    animateArc(confidencePct);
    animateCounter('confidencePct', confidencePct);

    // 4-level breakdown boxes
    const bd = computeBreakdown(cfg.key, pct);
    const keyMap = { low: 'low', moderate: 'moderate', high: 'high', veryhigh: 'veryhigh' };
    ['low','moderate','high','veryhigh'].forEach(k => {
        animateCounter('pct-' + k, bd[k] || 0);
        if (k === cfg.key) {
            const box = document.getElementById('box-' + k);
            if (box) box.classList.add('active');
        }
    });

    // Health metrics
    const inp = p.input_data || {};
    document.getElementById('glucose').textContent       = (inp.glucose        || '--') + ' mg/dL';
    document.getElementById('bloodPressure').textContent = (inp.blood_pressure || '--') + ' mm Hg';
    document.getElementById('bmi').textContent           = inp.bmi             || '--';
    document.getElementById('insulin').textContent       = (inp.insulin        || '--') + ' uU/mL';
    document.getElementById('age').textContent           = (inp.age            || '--') + ' years';

    // Recommendation
    const recEl = document.getElementById('recommendation');
    if (recEl) recEl.textContent = cfg.recommendation;

    // Doctor review status/details
    renderReview(p.review || null);

    // Model used
    const modelEl = document.getElementById('modelUsed');
    if (modelEl) modelEl.textContent = p.model_version || 'v1.0';

    // Context-aware action panel
    const actionPanel = document.getElementById('actionPanel');
    if (actionPanel) actionPanel.innerHTML = cfg.alertHtml;

    // Feature importance chart
    if (p.feature_importance && p.feature_importance.length) {
        let fiCard = document.getElementById('featureImportanceCard');
        if (!fiCard) {
            fiCard = document.createElement('div');
            fiCard.id = 'featureImportanceCard';
            fiCard.className = 'card mb-4';
            fiCard.innerHTML = `
                <div class="card-header" style="background:linear-gradient(90deg,#1e3a8a,#2563eb);">
                    <h5 style="color:#fff;margin:0;"><i class="bi bi-bar-chart-fill me-2"></i>Why This Result? — Feature Contribution</h5>
                </div>
                <div class="p-4" id="featureImportance"></div>`;
            const downloadSection = document.querySelector('.alert.alert-success');
            if (downloadSection) downloadSection.before(fiCard);
        }
        const colors = ['#2563eb','#7c3aed','#059669','#d97706','#dc2626','#0891b2','#6d28d9','#065f46'];
        document.getElementById('featureImportance').innerHTML = p.feature_importance.map((f, i) => `
            <div style="margin-bottom:.85rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.3rem;">
                    <span style="font-weight:600;color:#1e293b;font-size:.875rem;">${f.label}</span>
                    <div style="display:flex;align-items:center;gap:.75rem;">
                        <span style="font-size:.78rem;color:#64748b;">Your value: <strong>${f.value}</strong></span>
                        <span style="font-weight:700;color:${colors[i % colors.length]};font-size:.875rem;min-width:42px;text-align:right;">${f.importance}%</span>
                    </div>
                </div>
                <div style="background:#f1f5f9;border-radius:99px;height:10px;overflow:hidden;">
                    <div style="width:${f.importance}%;height:100%;background:${colors[i % colors.length]};
                                border-radius:99px;transition:width 1s ease;"></div>
                </div>
            </div>`).join('');
    }

    localStorage.setItem('currentPredictionId', predId);
}

function downloadReport() {
    const predId = new URLSearchParams(window.location.search).get('id');
    window.location.href = '/templates/patient/report_download.html?id=' + (predId || '');
}

document.addEventListener('DOMContentLoaded', loadResult);
