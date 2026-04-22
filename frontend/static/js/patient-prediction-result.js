const API = '/api';
function getToken() { return localStorage.getItem('token'); }

const RISK_CONFIG = {
    'LOW RISK': {
        key: 'low', label: 'LOW RISK', color: '#16a34a', boxKey: 'low',
        icon: 'bi-emoji-smile-fill',
        summary: 'You are not currently at significant risk of diabetes.',
        recommendation: 'Your results look healthy. Maintain regular exercise (30 min/day), a balanced diet low in sugar, and an annual check-up. No immediate medical action is needed.',
        alertHtml: '<div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:14px;padding:1.25rem;display:flex;gap:1rem;align-items:flex-start;">' +
            '<i class="bi bi-emoji-smile-fill" style="color:#16a34a;font-size:1.75rem;flex-shrink:0;"></i>' +
            '<div><div style="font-weight:700;color:#166534;font-size:1rem;margin-bottom:.35rem;">You are not at risk right now</div>' +
            '<div style="color:#15803d;font-size:.875rem;line-height:1.6;">Keep up your healthy habits. No doctor visit is required at this time. Come back for a check-up in 12 months or if you notice any symptoms.</div>' +
            '<div style="margin-top:.85rem;display:flex;gap:.6rem;flex-wrap:wrap;">' +
            '<a href="health_data_form.html" class="btn btn-sm" style="background:#16a34a;color:#fff;border:none;">New Prediction</a>' +
            '<a href="prediction_history.html" class="btn btn-sm btn-outline">View History</a>' +
            '</div></div></div>'
    },
    'MODERATE RISK': {
        key: 'moderate', label: 'MODERATE RISK', color: '#d97706', boxKey: 'moderate',
        icon: 'bi-exclamation-circle-fill',
        summary: 'You have some risk factors. No diabetes yet, but worth monitoring.',
        recommendation: 'Reduce sugar and refined carbohydrate intake, increase physical activity, and maintain a healthy weight. No doctor visit needed now — recheck in 3 months.',
        alertHtml: '<div style="background:#fffbeb;border:1.5px solid #fde68a;border-radius:14px;padding:1.25rem;display:flex;gap:1rem;align-items:flex-start;">' +
            '<i class="bi bi-exclamation-circle-fill" style="color:#d97706;font-size:1.75rem;flex-shrink:0;"></i>' +
            '<div><div style="font-weight:700;color:#92400e;font-size:1rem;margin-bottom:.35rem;">No doctor needed — focus on lifestyle</div>' +
            '<div style="color:#b45309;font-size:.875rem;line-height:1.6;">You do <strong>not</strong> have diabetes. Cut down on sugar, exercise 30 min daily, maintain healthy weight, and recheck in 3 months.</div>' +
            '<div style="margin-top:.85rem;display:flex;gap:.6rem;flex-wrap:wrap;">' +
            '<a href="health_data_form.html" class="btn btn-sm" style="background:#d97706;color:#fff;border:none;">New Prediction in 3 Months</a>' +
            '<a href="prediction_history.html" class="btn btn-sm btn-outline">View History</a>' +
            '</div></div></div>'
    },
    'HIGH RISK': {
        key: 'high', label: 'HIGH RISK', color: '#dc2626', boxKey: 'high',
        icon: 'bi-exclamation-triangle-fill',
        summary: 'You are at high risk. Early action can prevent diabetes.',
        recommendation: 'Please consult your doctor soon. Diet control, weight management, and regular exercise are essential. Further tests such as HbA1c may be ordered by your doctor.',
        alertHtml: '<div style="background:linear-gradient(135deg,#7f1d1d,#991b1b);border-radius:14px;padding:1.25rem;display:flex;gap:1rem;align-items:flex-start;">' +
            '<i class="bi bi-exclamation-triangle-fill" style="color:#fca5a5;font-size:1.75rem;flex-shrink:0;"></i>' +
            '<div><div style="font-weight:700;color:#fff;font-size:1rem;margin-bottom:.35rem;">High Risk — Please See a Doctor Soon</div>' +
            '<div style="color:#fecaca;font-size:.875rem;line-height:1.6;">Your result shows a high diabetes risk. Early intervention significantly reduces your chance of developing diabetes. Please book an appointment with your doctor.</div>' +
            '<div style="margin-top:.85rem;display:flex;gap:.6rem;flex-wrap:wrap;">' +
            '<a href="appointment.html?reason=High+Risk+Diabetes+Review" class="btn btn-sm" style="background:#fff;color:#991b1b;border:none;font-weight:700;">Book Doctor Appointment</a>' +
            '<button onclick="downloadReport()" class="btn btn-sm" style="background:rgba(255,255,255,.15);color:#fecaca;border:1px solid rgba(255,255,255,.3);">Download Report</button>' +
            '</div></div></div>'
    },
    'VERY HIGH RISK': {
        key: 'veryhigh', label: 'VERY HIGH RISK', color: '#7c3aed', boxKey: 'high',
        icon: 'bi-heart-pulse-fill',
        summary: 'Immediate medical attention is strongly recommended.',
        recommendation: 'Please see a doctor immediately. You may require diagnostic tests, medication, or a structured diabetes management program. Do not delay.',
        alertHtml: '<div style="background:linear-gradient(135deg,#4c1d95,#6d28d9);border-radius:14px;padding:1.25rem;display:flex;gap:1rem;align-items:flex-start;">' +
            '<i class="bi bi-heart-pulse-fill" style="color:#ddd6fe;font-size:1.75rem;flex-shrink:0;"></i>' +
            '<div><div style="font-weight:700;color:#fff;font-size:1rem;margin-bottom:.35rem;">Very High Risk — See a Doctor Immediately</div>' +
            '<div style="color:#ddd6fe;font-size:.875rem;line-height:1.6;">Your result indicates a very high diabetes risk. Immediate medical consultation is required. You may need diagnostic tests, medication, or a diabetes management program.</div>' +
            '<div style="margin-top:.85rem;display:flex;gap:.6rem;flex-wrap:wrap;">' +
            '<a href="appointment.html?reason=Very+High+Risk+Diabetes+Urgent" class="btn btn-sm" style="background:#fff;color:#6d28d9;border:none;font-weight:700;">Book Urgent Appointment</a>' +
            '<button onclick="downloadReport()" class="btn btn-sm" style="background:rgba(255,255,255,.15);color:#ddd6fe;border:1px solid rgba(255,255,255,.3);">Download Report</button>' +
            '</div></div></div>'
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
    const iv = setInterval(function() {
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
    const iv = setInterval(function() {
        current = Math.min(current + step, target);
        el.textContent = current + '%';
        if (current >= target) clearInterval(iv);
    }, 20);
}

function moveNeedle(pct) {
    const needle = document.getElementById('riskNeedle');
    if (!needle) return;
    setTimeout(function() { needle.style.left = Math.min(Math.max(pct, 0), 100) + '%'; }, 100);
}

function renderReview(review) {
    const badge   = document.getElementById('reviewStatusBadge');
    const summary = document.getElementById('reviewSummary');
    const meta    = document.getElementById('reviewMeta');
    if (!badge || !summary || !meta) return;

    const st  = (review && review.status) ? String(review.status) : 'pending_review';
    const map = {
        pending_review:  { text: 'Pending Review',              cls: 'pill-moderate' },
        approved:        { text: 'Approved by Doctor',          cls: 'pill-low'      },
        rejected:        { text: 'Rejected - Follow-up Needed', cls: 'pill-high'     },
        needs_followup:  { text: 'Needs Follow-up',             cls: 'pill-high'     }
    };
    const cfg = map[st] || map.pending_review;
    badge.className  = 'risk-pill ' + cfg.cls;
    badge.textContent = cfg.text;
    summary.textContent = (review && review.summary) ? review.summary : 'Awaiting doctor review.';
    if (review && review.doctor_name) {
        const dt = review.reviewed_at ? new Date(review.reviewed_at).toLocaleString() : '';
        meta.textContent = 'Reviewed by Dr. ' + review.doctor_name + (dt ? ' on ' + dt : '');
    } else {
        meta.textContent = '';
    }
}

// ── Main load function ────────────────────────────────────────────────────────
async function loadResult() {
    const user = checkAuth('patient');
    if (!user) return;

    const nameEl = document.getElementById('navUserName');
    if (nameEl) nameEl.textContent = user.name || user.username;
    const sb = document.getElementById('sidebarName');
    if (sb) sb.textContent = user.name || user.username;

    const predId = new URLSearchParams(window.location.search).get('id');
    if (!predId) {
        const main = document.querySelector('.main');
        if (main) main.innerHTML = '<div class="alert alert-warning m-4">No prediction ID found. <a href="/templates/patient/health_data_form.html">Create a new prediction</a>.</div>';
        return;
    }

    try {
        const res = await fetch(API + '/patient/predictions/' + predId, {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        if (res.status === 401) { logout(); return; }

        const data = await res.json();
        if (!data.success) {
            const main = document.querySelector('.main');
            if (main) {
                const msg = res.status === 404
                    ? 'Prediction not found. It may belong to a different account.'
                    : (data.message || 'Could not load prediction.');
                main.innerHTML = `<div class="alert alert-danger m-4">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    <strong>${msg}</strong><br>
                    <a href="/templates/patient/prediction_history.html" class="btn btn-sm btn-outline mt-2">View My Predictions</a>
                    <a href="/templates/patient/health_data_form.html" class="btn btn-sm btn-primary mt-2 ms-2">New Prediction</a>
                </div>`;
            }
            return;
        }

        const p   = data.prediction;
        const cfg = RISK_CONFIG[p.risk_level] || RISK_CONFIG['LOW RISK'];
        const pct = Math.round(p.probability_percent || 0);
        const confidencePct = p.confidence != null
            ? Math.round(p.confidence)
            : Math.round(50 + (Math.max(pct / 100, 1 - pct / 100) - 0.5) * 90);

        // ── Risk label & gauge ────────────────────────────────────────────────
        const labelEl = document.getElementById('riskLabel');
        if (labelEl) { labelEl.textContent = cfg.label; labelEl.style.color = cfg.color; }

        const summaryEl = document.getElementById('riskSummary');
        if (summaryEl) summaryEl.textContent = cfg.summary;

        const card = document.getElementById('riskCard');
        if (card) card.style.borderTop = '4px solid ' + cfg.color;

        moveNeedle(NEEDLE_POS[p.risk_level] || pct);
        animateArc(confidencePct);
        animateCounter('confidencePct', confidencePct);

        // ── 4-level breakdown boxes ───────────────────────────────────────────
        const bd = computeBreakdown(cfg.key, pct);
        ['low', 'moderate', 'high', 'veryhigh'].forEach(function(k) {
            animateCounter('pct-' + k, bd[k] || 0);
            if (k === cfg.key) {
                const box = document.getElementById('box-' + k);
                if (box) box.classList.add('active');
            }
        });

        // ── Health metrics ────────────────────────────────────────────────────
        const inp = p.input_data || {};
        var g  = document.getElementById('glucose');       if (g)  g.textContent  = (inp.glucose        || '--') + ' mg/dL';
        var bp = document.getElementById('bloodPressure'); if (bp) bp.textContent = (inp.blood_pressure || '--') + ' mm Hg';
        var bm = document.getElementById('bmi');           if (bm) bm.textContent = inp.bmi             || '--';
        var ins= document.getElementById('insulin');       if (ins)ins.textContent= (inp.insulin        || '--') + ' uU/mL';
        var ag = document.getElementById('age');           if (ag) ag.textContent = (inp.age            || '--') + ' years';

        // ── Recommendation ────────────────────────────────────────────────────
        const recEl = document.getElementById('recommendation');
        if (recEl) recEl.textContent = cfg.recommendation;

        // ── Doctor review ─────────────────────────────────────────────────────
        renderReview(p.review || null);

        // ── Model badge ───────────────────────────────────────────────────────
        const modelEl = document.getElementById('modelUsed');
        if (modelEl) modelEl.textContent = p.model_version || 'v1.0';

        // ── Action panel ──────────────────────────────────────────────────────
        const actionPanel = document.getElementById('actionPanel');
        if (actionPanel) actionPanel.innerHTML = cfg.alertHtml;

        // ── All-3-models comparison panel ─────────────────────────────────────
        if (p.model_comparison && p.model_comparison.length > 1) {
            var compCard = document.getElementById('modelComparisonCard');
            if (!compCard) {
                compCard = document.createElement('div');
                compCard.id = 'modelComparisonCard';
                compCard.className = 'card mb-4';
                compCard.innerHTML =
                    '<div class="card-header" style="background:linear-gradient(90deg,#1e3a8a,#2563eb);">' +
                    '<h5 style="color:#fff;margin:0;"><i class="bi bi-bar-chart-steps me-2"></i>All 3 Models — Comparison</h5></div>' +
                    '<div class="p-4" id="modelComparisonBody"></div>';
                if (actionPanel) actionPanel.after(compCard);
            }
            var riskColors = {
                'LOW RISK': '#16a34a', 'MODERATE RISK': '#d97706',
                'HIGH RISK': '#dc2626', 'VERY HIGH RISK': '#7c3aed'
            };
            var compBody = document.getElementById('modelComparisonBody');
            if (compBody) {
                compBody.innerHTML =
                    '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;">' +
                    p.model_comparison.map(function(m) {
                        var color  = riskColors[m.risk_level] || '#64748b';
                        var border = m.is_active ? '2px solid #2563eb' : '1px solid #e2e8f0';
                        var bg     = m.is_active ? '#eff6ff' : '#f8fafc';
                        return '<div style="border:' + border + ';background:' + bg + ';border-radius:12px;padding:1rem;text-align:center;">' +
                            (m.is_active ? '<div style="font-size:.65rem;font-weight:700;color:#2563eb;text-transform:uppercase;margin-bottom:.4rem;">Active Model</div>' : '') +
                            '<div style="font-weight:700;font-size:.9rem;color:#1e293b;margin-bottom:.3rem;">' + m.algorithm + '</div>' +
                            '<div style="font-size:.75rem;color:#64748b;margin-bottom:.6rem;">Accuracy: ' + m.accuracy + '%</div>' +
                            '<div style="font-size:1.4rem;font-weight:800;color:' + color + ';">' + (m.probability_percent || 0).toFixed(1) + '%</div>' +
                            '<div style="font-size:.72rem;font-weight:600;color:' + color + ';margin-top:.2rem;">' + m.risk_level + '</div>' +
                            '</div>';
                    }).join('') +
                    '</div>' +
                    '<p style="font-size:.75rem;color:#94a3b8;margin-top:.75rem;text-align:center;">Primary result uses the active model. All models trained on the same dataset.</p>';
            }
        }

        // ── Feature importance chart ──────────────────────────────────────────
        if (p.feature_importance && p.feature_importance.length) {
            var fiCard = document.getElementById('featureImportanceCard');
            if (!fiCard) {
                fiCard = document.createElement('div');
                fiCard.id = 'featureImportanceCard';
                fiCard.className = 'card mb-4';
                fiCard.innerHTML =
                    '<div class="card-header" style="background:linear-gradient(90deg,#1e3a8a,#2563eb);">' +
                    '<h5 style="color:#fff;margin:0;"><i class="bi bi-bar-chart-fill me-2"></i>Why This Result? — Feature Contribution</h5></div>' +
                    '<div class="p-4" id="featureImportance"></div>';
                var dlSection = document.querySelector('.alert.alert-success');
                if (dlSection) dlSection.before(fiCard);
            }
            var fiColors = ['#2563eb','#7c3aed','#059669','#d97706','#dc2626','#0891b2','#6d28d9','#065f46'];
            var fiBody = document.getElementById('featureImportance');
            if (fiBody) {
                fiBody.innerHTML = p.feature_importance.map(function(f, i) {
                    var c = fiColors[i % fiColors.length];
                    return '<div style="margin-bottom:.85rem;">' +
                        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.3rem;">' +
                        '<span style="font-weight:600;color:#1e293b;font-size:.875rem;">' + f.label + '</span>' +
                        '<div style="display:flex;align-items:center;gap:.75rem;">' +
                        '<span style="font-size:.78rem;color:#64748b;">Value: <strong>' + f.value + '</strong></span>' +
                        '<span style="font-weight:700;color:' + c + ';font-size:.875rem;min-width:42px;text-align:right;">' + f.importance + '%</span>' +
                        '</div></div>' +
                        '<div style="background:#f1f5f9;border-radius:99px;height:10px;overflow:hidden;">' +
                        '<div style="width:' + f.importance + '%;height:100%;background:' + c + ';border-radius:99px;transition:width 1s ease;"></div>' +
                        '</div></div>';
                }).join('');
            }
        }

        localStorage.setItem('currentPredictionId', predId);

    } catch (err) {
        console.error('loadResult error:', err);
        var main = document.querySelector('.main');
        if (main) main.innerHTML = '<div class="alert alert-danger m-4"><i class="bi bi-exclamation-triangle me-2"></i>Failed to load prediction result. <a href="/templates/patient/prediction_history.html">View history</a>.</div>';
    }
}

function downloadReport() {
    var predId = new URLSearchParams(window.location.search).get('id');
    window.location.href = '/templates/patient/report_download.html?id=' + (predId || '');
}

document.addEventListener('DOMContentLoaded', loadResult);
