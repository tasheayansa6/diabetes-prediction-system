const API = '/api';
function getToken() { return localStorage.getItem('token'); }

const RISK_CONFIG = {
    'NON-DIABETIC': {
        key: 'non_diabetic', label: 'NON-DIABETIC', color: '#16a34a', boxKey: 'low',
        icon: 'bi-emoji-smile-fill',
        summary: 'Your results are within the normal range. No diabetes detected.',
        recommendation: 'Maintain a healthy lifestyle — balanced diet, regular exercise (30 min/day), and routine checkups every 1–2 years.',
        alertHtml: '<div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:14px;padding:1.25rem;display:flex;gap:1rem;align-items:flex-start;">' +
            '<i class="bi bi-emoji-smile-fill" style="color:#16a34a;font-size:1.75rem;flex-shrink:0;"></i>' +
            '<div><div style="font-weight:700;color:#166534;font-size:1rem;margin-bottom:.35rem;">✅ Non-Diabetic — You are in the healthy range</div>' +
            '<div style="color:#15803d;font-size:.875rem;line-height:1.6;">Your glucose and health indicators are normal. Keep up your healthy habits. No immediate medical action is needed. Return for a checkup in 12 months.</div>' +
            '<div style="margin-top:.85rem;display:flex;gap:.6rem;flex-wrap:wrap;">' +
            '<a href="/templates/patient/health_data_form.html" class="btn btn-sm" style="background:#16a34a;color:#fff;border:none;">New Prediction</a>' +
            '<a href="/templates/patient/prediction_history.html" class="btn btn-sm btn-outline">View History</a>' +
            '</div></div></div>'
    },
    'PRE-DIABETIC': {
        key: 'pre_diabetic', label: 'PRE-DIABETIC', color: '#d97706', boxKey: 'moderate',
        icon: 'bi-exclamation-circle-fill',
        summary: 'Your glucose is in the pre-diabetic range (100–125 mg/dL). You are at risk of developing Type 2 diabetes.',
        recommendation: 'Lifestyle changes now can prevent or delay diabetes. Reduce sugar intake, increase physical activity, and consult your doctor. HbA1c test recommended.',
        alertHtml: '<div style="background:#fffbeb;border:1.5px solid #fde68a;border-radius:14px;padding:1.25rem;display:flex;gap:1rem;align-items:flex-start;">' +
            '<i class="bi bi-exclamation-circle-fill" style="color:#d97706;font-size:1.75rem;flex-shrink:0;"></i>' +
            '<div><div style="font-weight:700;color:#92400e;font-size:1rem;margin-bottom:.35rem;">⚠️ Pre-Diabetic — Action needed to prevent diabetes</div>' +
            '<div style="color:#b45309;font-size:.875rem;line-height:1.6;">Your glucose is elevated but not yet diabetic. With lifestyle changes you can reverse this. Cut sugar, exercise 30 min daily, lose 5–7% body weight if overweight. See your doctor for an HbA1c test.</div>' +
            '<div style="margin-top:.85rem;display:flex;gap:.6rem;flex-wrap:wrap;">' +
            '<a href="/templates/patient/appointment.html?reason=Pre-Diabetic+Review" class="btn btn-sm" style="background:#d97706;color:#fff;border:none;font-weight:700;">Book Doctor Appointment</a>' +
            '<a href="/templates/patient/prediction_history.html" class="btn btn-sm btn-outline">View History</a>' +
            '</div></div></div>'
    },
    'DIABETIC': {
        key: 'diabetic', label: 'DIABETIC', color: '#dc2626', boxKey: 'high',
        icon: 'bi-heart-pulse-fill',
        summary: 'Your results indicate diabetes. Immediate medical attention is required.',
        recommendation: 'Please see a doctor immediately. Confirmatory HbA1c and fasting glucose tests are needed. Begin a diabetes management plan.',
        alertHtml: '<div style="background:linear-gradient(135deg,#7f1d1d,#991b1b);border-radius:14px;padding:1.25rem;display:flex;gap:1rem;align-items:flex-start;animation:pulse-border 2s infinite;">' +
            '<i class="bi bi-heart-pulse-fill" style="color:#fca5a5;font-size:1.75rem;flex-shrink:0;"></i>' +
            '<div><div style="font-weight:700;color:#fff;font-size:1rem;margin-bottom:.35rem;">🔴 Diabetic — See a Doctor Immediately</div>' +
            '<div style="color:#fecaca;font-size:.875rem;line-height:1.6;">Your result indicates diabetes. Immediate medical consultation is required. You need confirmatory tests (HbA1c, fasting glucose) and a diabetes management plan. Do not delay.</div>' +
            '<div style="margin-top:.85rem;display:flex;gap:.6rem;flex-wrap:wrap;">' +
            '<a href="/templates/patient/appointment.html?reason=Diabetic+Urgent+Review" class="btn btn-sm" style="background:#fff;color:#991b1b;border:none;font-weight:700;">Book Urgent Appointment</a>' +
            '<button onclick="downloadReport()" class="btn btn-sm" style="background:rgba(255,255,255,.15);color:#fecaca;border:1px solid rgba(255,255,255,.3);">Download Report</button>' +
            '</div></div></div>'
    }
};

const NEEDLE_POS = { 'NON-DIABETIC': 12, 'PRE-DIABETIC': 50, 'DIABETIC': 88 };

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
        if (main) main.innerHTML = '<div class="alert alert-warning m-4"><i class="bi bi-exclamation-circle me-2"></i><strong>No prediction ID found.</strong><br><a href="/templates/patient/prediction_history.html" class="btn btn-sm btn-outline mt-2">View My Predictions</a><a href="/templates/patient/health_data_form.html" class="btn btn-sm btn-primary mt-2 ms-2">New Prediction</a></div>';
        return;
    }

    try {
        const res = await fetch(API + '/patient/predictions/' + predId, {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        if (res.status === 401) { window.location.href = '/login?reason=session_expired'; return; }

        let data;
        try { data = await res.json(); }
        catch (jsonErr) {
            throw new Error('Server returned invalid response (status ' + res.status + '). Check Render logs.');
        }
        if (!data.success) {
            const main = document.querySelector('.main');
            if (main) {
                const msg = res.status === 403
                    ? 'This prediction belongs to a different account.'
                    : res.status === 404
                    ? 'Prediction not found. It may have been deleted.'
                    : (data.message || 'Could not load prediction.');
                main.innerHTML = `<div class="alert alert-danger m-4" style="max-width:600px;margin:2rem auto!important;">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>
                    <strong>${msg}</strong><br>
                    <small style="color:#991b1b;display:block;margin-top:.5rem;word-break:break-all;">${data.message || ''}</small>
                    <div style="margin-top:1rem;display:flex;gap:.5rem;flex-wrap:wrap;">
                    <a href="/templates/patient/prediction_history.html" class="btn btn-sm btn-outline">View My Predictions</a>
                    <a href="/templates/patient/health_data_form.html" class="btn btn-sm btn-primary">New Prediction</a>
                    </div>
                </div>`;
            }
            return;
        }

        const p   = data.prediction;
        const cfg = RISK_CONFIG[p.risk_level] || RISK_CONFIG['NON-DIABETIC'];
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

        moveNeedle(NEEDLE_POS[p.risk_level] || 50);
        animateArc(confidencePct);
        animateCounter('confidencePct', confidencePct);

        // ── 3-class breakdown boxes ───────────────────────────────────────────
        const probs = {
            non_diabetic: Math.round(p.prob_non_diabetic || 0),
            pre_diabetic: Math.round(p.prob_pre_diabetic || 0),
            diabetic:     Math.round(p.prob_diabetic     || pct)
        };
        ['non_diabetic', 'pre_diabetic', 'diabetic'].forEach(function(k) {
            const pctEl = document.getElementById('pct-' + k);
            if (pctEl) animateCounter('pct-' + k, probs[k] || 0);
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

        // ── Model badge — shows active model version ──────────────────────────
        const modelEl = document.getElementById('modelUsed');
        if (modelEl) modelEl.textContent = p.model_version || 'v1.0';

        // ── Action panel ──────────────────────────────────────────────────────
        const actionPanel = document.getElementById('actionPanel');
        if (actionPanel) actionPanel.innerHTML = cfg.alertHtml;

        // ── All-3-models comparison panel — REMOVED ──────────────────────────
        // Model comparison is admin-only. Patients only see the active model result.
        // Admin can switch the active model from /templates/admin/manage_models.html

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

        // ── Right panel: prescriptions + dosage taken ─────────────────────────
        loadRightPanel();

    } catch (err) {
        console.error('loadResult error:', err);
        var main = document.querySelector('.main');
        if (main) main.innerHTML = '<div class="alert alert-danger m-4">'
            + '<i class="bi bi-exclamation-triangle-fill me-2"></i>'
            + '<strong>Could not load prediction result.</strong><br>'
            + '<span style="font-size:.85rem;color:#991b1b;">' + (err.message || 'Unknown error') + '</span><br><br>'
            + '<a href="/templates/patient/prediction_history.html" class="btn btn-sm btn-outline mt-2">'
            + '<i class="bi bi-clock-history"></i> View My Predictions</a>'
            + '<a href="/templates/patient/health_data_form.html" class="btn btn-sm btn-primary mt-2 ms-2">'
            + '<i class="bi bi-plus-circle"></i> New Prediction</a></div>';
    }
}

// ── Right panel: prescriptions + dosage taken ─────────────────────────────
async function loadRightPanel() {
    await Promise.all([loadPrescriptions(), loadMedicationTaken()]);
}

async function loadPrescriptions() {
    const panel = document.getElementById('prescriptionPanel');
    if (!panel) return;
    try {
        const res  = await fetch(API + '/patient/prescriptions?limit=20', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        if (res.status === 401) { window.location.href = '/login?reason=session_expired'; return; }
        const data = await res.json();
        const rxs  = (data.prescriptions || []).filter(function(r) {
            return ['active','pending','verified','dispensed'].includes(r.status);
        });
        if (!rxs.length) {
            panel.innerHTML = '<div style="padding:1rem;text-align:center;color:#94a3b8;font-size:.82rem;"><i class="bi bi-capsule" style="display:block;font-size:1.3rem;margin-bottom:.3rem;"></i>No active prescriptions</div>';
            return;
        }
        var statusColor = { active:'#059669', pending:'#d97706', verified:'#2563eb', dispensed:'#7c3aed' };
        panel.innerHTML = rxs.map(function(r) {
            var sc  = statusColor[r.status] || '#64748b';
            var med = (r.medication || '—').replace(/</g,'&lt;').replace(/>/g,'&gt;');
            var dos = (r.dosage    || '—').replace(/</g,'&lt;').replace(/>/g,'&gt;');
            var frq = (r.frequency || '—').replace(/</g,'&lt;').replace(/>/g,'&gt;');
            var dur = (r.duration  || '—').replace(/</g,'&lt;').replace(/>/g,'&gt;');
            var doc = (r.doctor_name || '—').replace(/</g,'&lt;').replace(/>/g,'&gt;');
            var ins = r.instructions ? ('<div style="font-size:.72rem;color:#94a3b8;margin-top:.2rem;"><i class="bi bi-info-circle"></i> ' + r.instructions.replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</div>') : '';
            var st  = (r.status || '').toUpperCase().replace(/</g,'&lt;');
            return '<div style="padding:.85rem 1rem;border-bottom:1px solid #f1f5f9;">' +
                '<div style="display:flex;justify-content:space-between;align-items:flex-start;">' +
                '<div style="flex:1;">' +
                '<div style="font-weight:700;font-size:.875rem;color:#0f172a;">' + med + '</div>' +
                '<div style="font-size:.75rem;color:#64748b;margin-top:.2rem;">' +
                '<i class="bi bi-droplet-half"></i> ' + dos +
                ' &nbsp;|&nbsp; <i class="bi bi-clock"></i> ' + frq +
                ' &nbsp;|&nbsp; <i class="bi bi-calendar3"></i> ' + dur +
                '</div>' + ins +
                '<div style="font-size:.7rem;color:#94a3b8;margin-top:.15rem;">By Dr. ' + doc + '</div>' +
                '</div>' +
                '<span style="background:' + sc + '20;color:' + sc + ';border-radius:99px;padding:.15em .6em;font-size:.68rem;font-weight:700;flex-shrink:0;margin-left:.5rem;">' + st + '</span>' +
                '</div></div>';
        }).join('');
    } catch (err) {
        console.error('loadPrescriptions error:', err);
        panel.innerHTML = '<div style="padding:1rem;color:#dc2626;font-size:.82rem;"><i class="bi bi-exclamation-circle"></i> Failed to load prescriptions: ' + (err.message || '') + '</div>';
    }
}

async function loadMedicationTaken() {
    const panel = document.getElementById('medicationTakenPanel');
    if (!panel) return;
    try {
        const res  = await fetch(API + '/patient/prescriptions?limit=20', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        if (res.status === 401) { window.location.href = '/login?reason=session_expired'; return; }
        const data = await res.json();
        const rxs  = (data.prescriptions || []).filter(function(r) {
            return ['active','pending','verified','dispensed'].includes(r.status);
        });
        if (!rxs.length) {
            panel.innerHTML = '<div style="padding:1rem;text-align:center;color:#94a3b8;font-size:.82rem;">No active medications</div>';
            return;
        }
        // Fetch adherence for each prescription
        var adherenceList = await Promise.all(rxs.map(async function(r) {
            try {
                var ar = await fetch(API + '/patient/prescriptions/' + r.id + '/adherence', {
                    headers: { 'Authorization': 'Bearer ' + getToken() }
                });
                var ad = await ar.json();
                return { rx: r, today: ad.today_taken || false, days: ad.days_taken || 0 };
            } catch (_) {
                return { rx: r, today: false, days: 0 };
            }
        }));

        panel.innerHTML = adherenceList.map(function(item) {
            var r    = item.rx;
            var today = item.today;
            var days  = item.days;
            var med  = (r.medication || '—').replace(/</g,'&lt;').replace(/>/g,'&gt;');
            var dos  = (r.dosage || '').replace(/</g,'&lt;').replace(/>/g,'&gt;');
            var dayStr = days + ' day' + (days !== 1 ? 's' : '') + ' taken';
            var actionBtn = today
                ? '<span style="background:#dcfce7;color:#166534;border-radius:99px;padding:.2em .75em;font-size:.72rem;font-weight:700;"><i class="bi bi-check-circle-fill"></i> Taken Today</span>'
                : '<button onclick="markTaken(' + r.id + ', this)" style="background:#7c3aed;color:#fff;border:none;border-radius:8px;padding:.3rem .75rem;font-size:.75rem;font-weight:600;cursor:pointer;"><i class="bi bi-check2"></i> Mark Taken</button>';
            return '<div style="padding:.85rem 1rem;border-bottom:1px solid #f1f5f9;display:flex;align-items:center;gap:.75rem;">' +
                '<div style="flex:1;">' +
                '<div style="font-weight:600;font-size:.85rem;color:#0f172a;">' + med + '</div>' +
                '<div style="font-size:.72rem;color:#64748b;">' + dos + ' &nbsp;|&nbsp; ' + dayStr + '</div>' +
                '</div>' + actionBtn + '</div>';
        }).join('');
    } catch (err) {
        console.error('loadMedicationTaken error:', err);
        panel.innerHTML = '<div style="padding:1rem;color:#dc2626;font-size:.82rem;"><i class="bi bi-exclamation-circle"></i> Failed to load</div>';
    }
}

async function markTaken(prescriptionId, btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i>';
    try {
        const res  = await fetch(API + '/patient/prescriptions/' + prescriptionId + '/taken', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();
        if (data.success) {
            // Replace button with taken badge
            btn.outerHTML = '<span style="background:#dcfce7;color:#166534;border-radius:99px;padding:.2em .75em;font-size:.72rem;font-weight:700;"><i class="bi bi-check-circle-fill"></i> Taken Today</span>';
        } else {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check2"></i> Mark Taken';
        }
    } catch (_) {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check2"></i> Mark Taken';
    }
}

function downloadReport() {
    var predId = new URLSearchParams(window.location.search).get('id');
    window.location.href = '/templates/patient/report_download.html?id=' + (predId || '');
}

document.addEventListener('DOMContentLoaded', loadResult);
