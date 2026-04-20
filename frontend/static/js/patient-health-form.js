const API = '/api';

function getToken() { return localStorage.getItem('token'); }
function authHeaders() {
    return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() };
}

// ── User-scoped localStorage helpers ─────────────────────────────────────────
function _uid() {
    try {
        const u = JSON.parse(localStorage.getItem('user') || '{}');
        const id = u.id || u.user_id;
        return id != null ? String(id) : 'anon';
    } catch (_) { return 'anon'; }
}
function _paidKey()    { return 'predictionPaid_' + _uid(); }
function _pendingKey() { return 'pendingHealthData_' + _uid(); }

// Read predictionPaid — check scoped key first, then legacy
function isPredictionPaid() {
    return localStorage.getItem(_paidKey()) === 'true' ||
           localStorage.getItem('predictionPaid') === 'true';
}
// Clear predictionPaid from both scoped and legacy keys
function clearPredictionPaid() {
    localStorage.removeItem(_paidKey());
    localStorage.removeItem('predictionPaid');
}
// Read pending health data — scoped first, then legacy
function _getPendingData() {
    const scoped = localStorage.getItem(_pendingKey());
    if (scoped) { try { return JSON.parse(scoped); } catch (_) {} }
    const legacy = localStorage.getItem('pendingHealthData');
    if (legacy) { try { return JSON.parse(legacy); } catch (_) {} }
    return null;
}
// Clear pending health data from both keys
function _clearPendingData() {
    localStorage.removeItem(_pendingKey());
    localStorage.removeItem('pendingHealthData');
}

// Robustly parse a lab result value — handles plain numbers, JSON objects, and strings
function parseLabValue(raw) {
    if (raw == null) return NaN;
    if (typeof raw === 'number') return raw;
    if (typeof raw === 'object') {
        const v = raw.value ?? raw.result ?? raw.glucose ?? raw.insulin ?? Object.values(raw)[0];
        return parseFloat(v);
    }
    // Try JSON string first
    try {
        const obj = JSON.parse(raw);
        if (typeof obj === 'number') return obj;
        const v = obj.value ?? obj.result ?? obj.glucose ?? obj.insulin ?? Object.values(obj)[0];
        return parseFloat(v);
    } catch { /* not JSON */ }
    // Plain numeric string
    return parseFloat(raw);
}

const Steps = { nurseVitals: false, labResults: false };
let labPollingTimer = null;

// ── Validation ────────────────────────────────────────────────────────────────
function validateForm(body) {
    const rules = [
        [body.pregnancies,       0,     17,  'Pregnancies must be 0–17 (enter 0 if male)'],
        [body.glucose,           1,    300,  'Glucose must be 1–300 mg/dL'],
        [body.blood_pressure,    1,    200,  'Blood pressure must be 1–200 mm Hg'],
        [body.skin_thickness,    0,     99,  'Skin thickness must be 0–99 mm'],
        [body.insulin,           0,    846,  'Insulin must be 0–846 μU/mL'],
        [body.bmi,               1,     80,  'BMI must be 1–80'],
        [body.diabetes_pedigree, 0.001,  3,  'Diabetes pedigree must be 0.001–3.0'],
        [body.age,               1,    120,  'Age must be 1–120']
    ];
    for (const [val, min, max, msg] of rules) {
        if (isNaN(val) || val < min || val > max) return msg;
    }
    return null;
}

function collectFormData() {
    return {
        pregnancies:       parseInt(document.getElementById('pregnancies').value)        || 0,
        glucose:           parseFloat(document.getElementById('glucose').value),
        blood_pressure:    parseFloat(document.getElementById('bloodPressure').value),
        skin_thickness:    parseFloat(document.getElementById('skinThickness').value)    || 0,
        insulin:           parseFloat(document.getElementById('insulin').value)          || 0,
        bmi:               parseFloat(document.getElementById('bmi').value),
        diabetes_pedigree: parseFloat(document.getElementById('diabetesPedigree').value) || 0.5,
        age:               parseInt(document.getElementById('age').value)
    };
}

function updateLiveRiskHint() {
    const hint = document.getElementById('liveRiskHint');
    if (!hint) return;

    const glucose = parseFloat(document.getElementById('glucose')?.value);
    const bmi = parseFloat(document.getElementById('bmi')?.value);
    const age = parseFloat(document.getElementById('age')?.value);
    const bp = parseFloat(document.getElementById('bloodPressure')?.value);
    const dpf = parseFloat(document.getElementById('diabetesPedigree')?.value);
    const insulin = parseFloat(document.getElementById('insulin')?.value);

    const reasons = [];
    let score = 0;

    if (!isNaN(glucose)) {
        if (glucose >= 200) { score += 3; reasons.push(`very high glucose (${glucose} mg/dL)`); }
        else if (glucose >= 140) { score += 2; reasons.push(`high glucose (${glucose} mg/dL)`); }
        else if (glucose >= 126) { score += 1; reasons.push(`elevated fasting glucose (${glucose} mg/dL)`); }
    }
    if (!isNaN(bmi)) {
        if (bmi >= 35) { score += 2; reasons.push(`obesity class II+ (BMI ${bmi.toFixed(1)})`); }
        else if (bmi >= 30) { score += 1; reasons.push(`obesity (BMI ${bmi.toFixed(1)})`); }
        else if (bmi >= 25) { score += 0.5; reasons.push(`overweight (BMI ${bmi.toFixed(1)})`); }
    }
    if (!isNaN(age) && age >= 45) { score += 1; reasons.push(`age ${age}`); }
    if (!isNaN(bp) && bp >= 90) { score += 1; reasons.push(`high diastolic BP (${bp} mmHg)`); }
    if (!isNaN(dpf) && dpf > 0.8) { score += 1; reasons.push(`strong family-history score (${dpf})`); }
    if (!isNaN(insulin) && insulin > 200) { score += 0.5; reasons.push(`high insulin (${insulin})`); }

    // If key fields aren't entered yet, keep hint hidden.
    if (isNaN(glucose) || isNaN(bmi) || isNaN(age)) {
        hint.style.display = 'none';
        return;
    }

    let level = 'Low';
    let cls = 'alert-success';
    if (score >= 4) { level = 'High'; cls = 'alert-danger'; }
    else if (score >= 2) { level = 'Moderate'; cls = 'alert-warning'; }

    const why = reasons.length ? reasons.join(', ') : 'values are currently within lower-risk ranges';
    hint.className = `alert ${cls} mt-3`;
    hint.innerHTML =
        `<i class="bi bi-activity me-2"></i>` +
        `<strong>Live Risk Hint (pre-check): ${level}</strong><br>` +
        `<span style="font-size:.85rem;">Based on your current entries: ${why}. ` +
        `Final risk comes from the ML model after submission.</span>`;
    hint.style.display = 'block';
}

// ── Alert helpers ─────────────────────────────────────────────────────────────
function showAlert(msg, type) {
    type = type || 'danger';
    const el = document.getElementById('formAlert');
    if (!el) return;
    el.innerHTML = msg;
    el.className = 'alert alert-' + type + ' mb-4';
    el.style.display = 'block';
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}
function hideAlert() {
    const el = document.getElementById('formAlert');
    if (el) el.style.display = 'none';
}

// ── Processing overlay ────────────────────────────────────────────────────────
function showOverlay() { document.getElementById('processingOverlay')?.classList.add('show'); }
function hideOverlay() { document.getElementById('processingOverlay')?.classList.remove('show'); }
function setStep(n) {
    for (let i = 1; i <= 4; i++) {
        const el = document.getElementById('ps' + i);
        if (!el) continue;
        const icon = el.querySelector('i');
        if (i < n)  { el.className = 'proc-step done';   if (icon) icon.className = 'bi bi-check-circle-fill'; }
        if (i === n){ el.className = 'proc-step active';  if (icon) icon.className = 'bi bi-arrow-repeat'; }
        if (i > n)  { el.className = 'proc-step';         if (icon) icon.className = 'bi bi-circle'; }
    }
}
function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

// ── Step UI updater ───────────────────────────────────────────────────────────
function updateStepUI(stepId, status, detail) {
    const el    = document.getElementById(stepId);
    const icon  = document.getElementById(stepId + 'Icon');
    const badge = document.getElementById(stepId + 'Badge');
    const detEl = document.getElementById(stepId + 'Detail');
    if (!el) return;

    const cfg = {
        checking: { cls: 'step-checking', iconCls: 'bi bi-arrow-repeat spin-icon', badge: 'Checking...',  badgeCls: 'badge-checking' },
        done:     { cls: 'step-done',     iconCls: 'bi bi-check-circle-fill',       badge: 'Done ✅',      badgeCls: 'badge-done'     },
        missing:  { cls: 'step-missing',  iconCls: 'bi bi-x-circle-fill',           badge: 'Not Done ❌',  badgeCls: 'badge-missing'  },
        expired:  { cls: 'step-missing',  iconCls: 'bi bi-clock-history',           badge: 'Expired ⏰',   badgeCls: 'badge-missing'  }
    }[status] || {};

    el.className = 'step-row ' + (cfg.cls || '');
    if (icon)  icon.className = cfg.iconCls || '';
    if (badge) { badge.textContent = cfg.badge || ''; badge.className = 'step-badge ' + (cfg.badgeCls || ''); }
    if (detEl && detail) { detEl.textContent = detail; detEl.style.display = 'block'; }
}

// ── Step 1: Nurse vitals — fetched from DB via API ────────────────────────────
async function checkNurseVitals() {
    updateStepUI('step1', 'checking');
    try {
        const res  = await fetch(API + '/patient/vitals/latest', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();

        if (!data.success || !data.vitals) {
            updateStepUI('step1', 'missing');
            Steps.nurseVitals = false;
            return false;
        }

        const v = data.vitals;

        const filled = [];

        if (v.blood_pressure_diastolic != null) {
            const el = document.getElementById('bloodPressure');
            if (el) { el.value = v.blood_pressure_diastolic; el.readOnly = true; el.classList.add('field-autofilled'); }
            const badge = document.getElementById('bpBadge');
            if (badge) badge.style.display = 'inline';
            const hint = document.getElementById('bpHint');
            if (hint) {
                if (v.bp_source === 'previous_record')
                    hint.innerHTML = '&#128203; From your last visit record. Verify with nurse if changed.';
                else if (v.bp_source === 'default')
                    hint.innerHTML = '&#9432; Using normal estimate (72 mmHg). Ask nurse to measure your BP.';
                else
                    hint.innerHTML = '&#129706; Auto-filled from nurse vitals. Diastolic BP. Normal: 60&ndash;80 mm Hg.';
            }
            filled.push('Diastolic BP: ' + v.blood_pressure_diastolic + ' mmHg');
        }
        if (v.bmi != null) {
            const el = document.getElementById('bmi');
            if (el) { el.value = v.bmi; el.readOnly = true; el.classList.add('field-autofilled'); }
            const badge = document.getElementById('bmiBadge');
            if (badge) badge.style.display = 'inline';
            filled.push('BMI: ' + v.bmi);
        } else if (v.height && v.weight) {
            // Calculate BMI client-side from height + weight
            const h = v.height / 100;
            const calcBmi = Math.round((v.weight / (h * h)) * 100) / 100;
            const el = document.getElementById('bmi');
            if (el) { el.value = calcBmi; el.readOnly = true; el.classList.add('field-autofilled'); }
            const badge = document.getElementById('bmiBadge');
            if (badge) badge.style.display = 'inline';
            filled.push('BMI: ' + calcBmi + ' (calculated)');
        }
        if (v.skin_thickness != null) {
            const el = document.getElementById('skinThickness');
            if (el) { el.value = v.skin_thickness; el.readOnly = true; el.classList.add('field-autofilled'); }
            const badge = document.getElementById('skinBadge');
            if (badge) badge.style.display = 'inline';
            filled.push('Skin Thickness: ' + v.skin_thickness + ' mm');
        } else {
            // Default to 0 when nurse didn't measure — standard ML model default
            const el = document.getElementById('skinThickness');
            if (el) { el.value = '0'; el.readOnly = true; el.classList.add('field-autofilled'); }
            const badge = document.getElementById('skinBadge');
            if (badge) badge.style.display = 'inline';
            filled.push('Skin Thickness: 0 mm (not measured)');
        }

        // Auto-fill ML fields recorded by nurse
        if (v.pregnancies != null) {
            const el = document.getElementById('pregnancies');
            if (el) { el.value = v.pregnancies; el.readOnly = true; el.classList.add('field-autofilled'); }
            const badge = document.getElementById('pregnanciesBadge');
            if (badge) badge.style.display = 'inline';
            const hint = document.getElementById('pregnanciesHint');
            if (hint) hint.innerHTML = '🩺 Auto-filled from nurse record.';
            filled.push('Pregnancies: ' + v.pregnancies);
        }
        if (v.diabetes_pedigree != null) {
            const el = document.getElementById('diabetesPedigree');
            if (el) { el.value = v.diabetes_pedigree; el.readOnly = true; el.classList.add('field-autofilled'); }
            const badge = document.getElementById('pedigreeBadge');
            if (badge) badge.style.display = 'inline';
            const hint = document.getElementById('pedigreeHint');
            if (hint) hint.innerHTML = '🩺 Auto-filled from nurse record.';
            filled.push('Pedigree: ' + v.diabetes_pedigree);
        }
        if (v.age != null) {
            const el = document.getElementById('age');
            if (el) { el.value = v.age; el.readOnly = true; el.classList.add('field-autofilled'); }
            const badge = document.getElementById('ageBadge');
            if (badge) badge.style.display = 'inline';
            const hint = document.getElementById('ageHint');
            if (hint) hint.innerHTML = '🩺 Auto-filled from nurse record.';
            filled.push('Age: ' + v.age);
        }

        // Auto-fill glucose from previous health record if no lab result yet
        if (v.glucose != null) {
            const el = document.getElementById('glucose');
            if (el && !el.readOnly) {
                el.value = v.glucose;
                el.readOnly = true;
                el.classList.add('field-autofilled');
            }
            const badge = document.getElementById('glucoseBadge');
            if (badge) { badge.style.display = 'inline'; badge.textContent = '📋 From Record'; }
            const hint = document.getElementById('glucoseHint');
            if (hint) hint.innerHTML = '📋 Auto-filled from your last health record. Normal fasting: 70–99 mg/dL.';
            filled.push('Glucose: ' + v.glucose + ' mg/dL');
        }

        // Auto-fill insulin from previous health record if no lab result yet
        if (v.insulin != null) {
            const el = document.getElementById('insulin');
            if (el && !el.readOnly) {
                el.value = v.insulin;
                el.readOnly = true;
                el.classList.add('field-autofilled');
            }
        }

        // Unlock form if at least one vital field was filled
        const hasBMI  = document.getElementById('bmi')?.readOnly;
        const hasBP   = v.blood_pressure_diastolic != null;
        const hasAge  = v.age != null;

        if (!hasBMI && !hasBP && !hasAge) {
            updateStepUI('step1', 'missing', 'Nurse recorded vitals but key fields (BP, BMI, Age) are all missing.');
            Steps.nurseVitals = false;
            return false;
        }

        updateStepUI('step1', 'done', '\uD83E\uDE7A Auto-filled from DB: ' + (filled.length ? filled.join(' | ') : 'vitals recorded'));
        Steps.nurseVitals = true;
        return true;

    } catch {
        updateStepUI('step1', 'missing');
        Steps.nurseVitals = false;
        return false;
    }
}

// ── Step 2: Lab results — fetched from DB via API ─────────────────────────────
async function checkLabResults() {
    updateStepUI('step2', 'checking');
    try {
        const res  = await fetch(API + '/patient/lab-results?limit=100', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();

        if (!data.success || !data.lab_results || data.lab_results.length === 0) {
            updateStepUI('step2', 'missing');
            Steps.labResults = false;
            return false;
        }

        const thirtyDaysAgo = Date.now() - (90 * 24 * 3600000); // 90 days window
        const isDone = r => {
            const s = (r.status || '').toLowerCase();
            // Accept completed, validated, or any non-pending status with results
            return (s === 'completed' || s === 'validated' || (s !== 'pending' && s !== 'cancelled')) && r.results;
        };
        const getResultTime = r => {
            const ts = r.test_completed_at || r.created_at;
            if (!ts) return Date.now(); // if no timestamp, assume recent
            try {
                const t = new Date(ts).getTime();
                return Number.isFinite(t) ? t : Date.now();
            } catch { return Date.now(); }
        };
        const isRecent = r => getResultTime(r) > thirtyDaysAgo;
        const normalize = s => String(s || '').toLowerCase();

        const isGlucoseLike = r => {
            const name = normalize(r.test_name);
            const unit = normalize(r.unit || '');
            const range = normalize(r.normal_range || '');
            return (
                name.includes('glucose') ||
                name.includes('blood sugar') ||
                name.includes('fasting') ||
                name.includes('fbs') ||
                name.includes('hba1c') ||
                name.includes('sugar') ||
                name.includes('ogtt') ||
                name.includes('postprandial') ||
                name.includes('random blood') ||
                unit.includes('mg/dl') ||
                range.includes('mg/dl')
            );
        };
        const isInsulinLike = r => {
            const name = normalize(r.test_name);
            return name.includes('insulin');
        };

        const completedRecent = data.lab_results
            .filter(r => isDone(r) && isRecent(r))
            .sort((a, b) => getResultTime(b) - getResultTime(a));

        const glucoseTest = completedRecent.find(isGlucoseLike);
        const insulinTest = completedRecent.find(isInsulinLike);

        if (!glucoseTest) {
            updateStepUI('step2', 'missing', 'No recent glucose lab result found. Enter glucose manually below.');
            const insulinEl = document.getElementById('insulin');
            if (insulinEl && !insulinEl.readOnly) {
                insulinEl.value = '0';
                insulinEl.readOnly = true;
                insulinEl.classList.add('field-autofilled');
                const hint = document.getElementById('insulinHint');
                if (hint) hint.innerHTML = '<span style="color:#64748b;">&#9432; No insulin lab test on record. Value set to <strong>0</strong> — this is the standard default used by the ML model when insulin is not measured.</span>';
            }
            Steps.labResults = false;
            return false;
        }

        const filled = [];

        const glucoseVal = parseLabValue(glucoseTest.results);
        if (!isNaN(glucoseVal) && glucoseVal > 0) {
            const el = document.getElementById('glucose');
            if (el) { el.value = glucoseVal; el.readOnly = true; el.classList.add('field-autofilled'); }
            const badge = document.getElementById('glucoseBadge');
            if (badge) badge.style.display = 'inline';
            const hint = document.getElementById('glucoseHint');
            if (hint) hint.innerHTML = `🔬 Auto-filled from lab: <strong>${glucoseTest.test_name}</strong>. Normal fasting: 70–99 mg/dL.`;
            filled.push('Glucose: ' + glucoseVal + ' mg/dL');
        } else {
            // parseLabValue failed — try raw string
            const raw = String(glucoseTest.results || '').trim();
            const fallback = parseFloat(raw);
            if (!isNaN(fallback) && fallback > 0) {
                const el = document.getElementById('glucose');
                if (el) { el.value = fallback; el.readOnly = true; el.classList.add('field-autofilled'); }
                const badge = document.getElementById('glucoseBadge');
                if (badge) badge.style.display = 'inline';
                filled.push('Glucose: ' + fallback + ' mg/dL');
            }
        }
        if (insulinTest) {
            const insulinVal = parseLabValue(insulinTest.results);
            if (!isNaN(insulinVal)) {
                const el = document.getElementById('insulin');
                if (el) { el.value = insulinVal; el.readOnly = true; el.classList.add('field-autofilled'); }
                const badge = document.getElementById('insulinBadge');
                if (badge) badge.style.display = 'inline';
                filled.push('Insulin: ' + insulinVal + ' μU/mL');
            }
        } else {
            const el = document.getElementById('insulin');
            if (el && !el.readOnly) {
                el.value = '0';
                el.readOnly = true;
                el.classList.add('field-autofilled');
                const hint = document.getElementById('insulinHint');
                if (hint) hint.innerHTML = '<span style="color:#64748b;">&#9432; No insulin lab test on record. Value set to <strong>0</strong> — this is the standard default used by the ML model when insulin is not measured.</span>';
            }
        }

        updateStepUI('step2', 'done', '🔬 Auto-filled from DB: ' + filled.join(' | '));
        Steps.labResults = true;
        return true;

    } catch {
        updateStepUI('step2', 'missing');
        Steps.labResults = false;
        return false;
    }
}

async function refreshLabResultsIfNeeded() {
    // Skip background polling when tab is hidden.
    if (document.hidden) return;
    await checkLabResults();
    evaluateFormAccess();
}

// ── Step 3: Last prediction data — auto-fill all fields not yet filled ───────
async function checkLastPredictionData() {
    try {
        const res  = await fetch(API + '/patient/health-data/last', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();
        if (!data.success || !data.data) return;

        const d = data.data;
        const filled = [];

        // Helper: fill a field only if it's not already auto-filled
        const fill = (id, val, label, makeReadOnly) => {
            if (val == null) return;
            const el = document.getElementById(id);
            if (!el || el.readOnly) return; // already filled by vitals/lab
            el.value = val;
            if (makeReadOnly) {
                el.readOnly = true;
                el.classList.add('field-autofilled');
            }
            filled.push(label + ': ' + val);
        };

        fill('age',              d.age,               'Age',         true);
        fill('pregnancies',      d.pregnancies,        'Pregnancies', true);
        fill('diabetesPedigree', d.diabetes_pedigree,  'Pedigree',    true);

        // Fill glucose from last prediction if not already filled from lab/vitals
        if (d.glucose != null) {
            const el = document.getElementById('glucose');
            if (el && !el.readOnly && !el.value) {
                el.value = d.glucose;
                el.readOnly = true;
                el.classList.add('field-autofilled');
                const badge = document.getElementById('glucoseBadge');
                if (badge) { badge.style.display = 'inline'; badge.textContent = '📋 From Last Visit'; }
                const hint = document.getElementById('glucoseHint');
                if (hint) hint.innerHTML = '📋 Auto-filled from your last prediction. Normal fasting: 70–99 mg/dL.';
                filled.push('Glucose: ' + d.glucose + ' mg/dL');
            }
        }

        // Fill blood pressure if not already filled
        if (d.blood_pressure != null) {
            const el = document.getElementById('bloodPressure');
            if (el && !el.readOnly && !el.value) {
                el.value = d.blood_pressure;
                el.readOnly = true;
                el.classList.add('field-autofilled');
                const hint = document.getElementById('bpHint');
                if (hint) hint.innerHTML = '📋 Auto-filled from your last prediction.';
                filled.push('BP: ' + d.blood_pressure);
            }
        }

        // Fill BMI if not already filled
        if (d.bmi != null) {
            const el = document.getElementById('bmi');
            if (el && !el.readOnly && !el.value) {
                el.value = d.bmi;
                el.readOnly = true;
                el.classList.add('field-autofilled');
                filled.push('BMI: ' + d.bmi);
            }
        }

        // Fill insulin if not already filled
        if (d.insulin != null) {
            const el = document.getElementById('insulin');
            if (el && !el.readOnly && !el.value) {
                el.value = d.insulin;
                el.readOnly = true;
                el.classList.add('field-autofilled');
                filled.push('Insulin: ' + d.insulin);
            }
        }

        if (filled.length) {
            const banner = document.getElementById('autofillBanner');
            const text   = document.getElementById('autofillText');
            if (banner && text) {
                if (!text.textContent) {
                    text.textContent = 'Auto-filled from last visit: ' + filled.join(', ') + '.';
                    banner.style.cssText = 'display:block;background:#f0fdf4;border:1px solid #86efac;color:#166534;padding:.75rem 1rem;border-radius:10px;margin-bottom:1rem;';
                } else {
                    text.textContent += ' | From last visit: ' + filled.join(', ') + '.';
                }
            }
        }
    } catch (_) { /* no previous prediction — that is fine */ }
}

// ── Autofill banner ───────────────────────────────────────────────────────────
function showAutofillBanner() {
    const banner     = document.getElementById('autofillBanner');
    const bannerText = document.getElementById('autofillText');
    if (!banner || !bannerText) return;
    const autofilled = [];
    if (document.getElementById('bloodPressure')?.readOnly)  autofilled.push('Diastolic BP 🩺');
    if (document.getElementById('bmi')?.readOnly)            autofilled.push('BMI 🩺');
    if (document.getElementById('skinThickness')?.readOnly)  autofilled.push('Skin Thickness 🩺');
    if (document.getElementById('pregnancies')?.readOnly)    autofilled.push('Pregnancies 🩺');
    if (document.getElementById('diabetesPedigree')?.readOnly) autofilled.push('Pedigree 🩺');
    if (document.getElementById('age')?.readOnly)            autofilled.push('Age 🩺');
    if (document.getElementById('glucose')?.readOnly)        autofilled.push('Glucose 🔬');
    if (document.getElementById('insulin')?.readOnly)        autofilled.push('Insulin 🔬');
    if (autofilled.length) {
        bannerText.textContent = 'Auto-filled from database: ' + autofilled.join(', ') + '. Please verify before submitting.';
        banner.style.cssText = 'display:block;background:#f0fdf4;border:1px solid #86efac;color:#166534;padding:.75rem 1rem;border-radius:10px;margin-bottom:1rem;';
    }
}

// ── Evaluate form access ──────────────────────────────────────────────────────
function evaluateFormAccess() {
    const formSection = document.getElementById('formSection');
    const blockedMsg  = document.getElementById('blockedMessage');
    const submitBtn   = document.getElementById('submitBtn');

    showAutofillBanner();

    if (Steps.nurseVitals && Steps.labResults) {
        if (formSection) formSection.style.display = 'block';
        if (blockedMsg)  blockedMsg.style.display  = 'none';
        if (submitBtn)   submitBtn.disabled = false;

    } else if (Steps.nurseVitals && !Steps.labResults) {
        if (formSection) formSection.style.display = 'block';
        if (blockedMsg)  blockedMsg.style.display  = 'none';
        if (submitBtn)   submitBtn.disabled = false;
        // Only show manual entry hint if glucose is truly empty and not auto-filled
        const glucoseEl = document.getElementById('glucose');
        if (glucoseEl && !glucoseEl.readOnly && !glucoseEl.value) {
            const hint = document.getElementById('glucoseHint');
            if (hint) hint.innerHTML = '✍️ No recent lab result found. Enter your latest fasting glucose reading manually.';
        }
        const insulinEl = document.getElementById('insulin');
        if (insulinEl && !insulinEl.readOnly) {
            insulinEl.value = '0';
            insulinEl.placeholder = '0 (no lab test — leave as 0)';
            const hint = document.getElementById('insulinHint');
            if (hint) hint.innerHTML = '<span style="color:#64748b;">&#9432; No insulin lab test on record. Value set to <strong>0</strong> — this is the standard default used by the ML model when insulin is not measured.</span>';
        }
    } else {
        // No nurse vitals at all — still show form, all fields editable
        if (formSection) formSection.style.display = 'block';
        if (blockedMsg)  blockedMsg.style.display  = 'none';
        if (submitBtn)   submitBtn.disabled = false;
        // Default insulin to 0 if not already filled
        const insulinEl = document.getElementById('insulin');
        if (insulinEl && !insulinEl.readOnly) {
            insulinEl.value = '0';
            insulinEl.readOnly = true;
            insulinEl.classList.add('field-autofilled');
        }
        // Only show manual glucose hint if glucose is truly empty (not filled from last prediction)
        const glucoseEl = document.getElementById('glucose');
        const glucoseHint = document.getElementById('glucoseHint');
        if (glucoseHint && glucoseEl && !glucoseEl.readOnly && !glucoseEl.value) {
            glucoseHint.innerHTML = '✍️ Enter your latest fasting glucose reading (mg/dL).';
        }
    }
    updateLiveRiskHint();
}

// ── Payment redirect — uses localStorage (persists across page navigations) ───
function goToPayment(body) {
    // Store form data scoped to this user so it survives the payment page redirect
    localStorage.setItem(_pendingKey(), JSON.stringify(body));
    // Also write legacy key for backward compat with payment-page.js
    localStorage.setItem('pendingHealthData', JSON.stringify(body));
    window.location.href = '/templates/payment/payment_page.html?service=prediction&return=health_form';
}

// ── Restore pending form data after returning from payment ────────────────────
function restorePendingData() {
    return _getPendingData();
}

function applyRestoredData(d) {
    const set = (id, val) => {
        const el = document.getElementById(id);
        if (el && !el.readOnly && val !== undefined && val !== null) el.value = val;
    };
    set('pregnancies',      d.pregnancies);
    set('diabetesPedigree', d.diabetes_pedigree);
    set('age',              d.age);
    // Only restore glucose/insulin/bp/bmi if NOT already auto-filled from DB
    if (!document.getElementById('glucose')?.readOnly)       set('glucose',       d.glucose);
    if (!document.getElementById('bloodPressure')?.readOnly) set('bloodPressure', d.blood_pressure);
    if (!document.getElementById('insulin')?.readOnly)       set('insulin',       d.insulin);
    if (!document.getElementById('bmi')?.readOnly)           set('bmi',           d.bmi);
    updateLiveRiskHint();
}

// ── Run ML prediction ─────────────────────────────────────────────────────────
async function runPrediction(body) {
    showOverlay();
    try {
        setStep(1); await delay(400);
        setStep(2);

        const res  = await fetch(API + '/patient/predict', {
            method: 'POST', headers: authHeaders(), body: JSON.stringify(body)
        });
        const data = await res.json();

        if (!data.success) {
            hideOverlay();
            // Payment required — redirect to payment page
            if (res.status === 402 || data.requires_payment) {
                goToPayment(body);
                return;
            }
            showAlert(data.message || 'Prediction failed. Please try again.');
            resetBtn();
            return;
        }

        setStep(3); await delay(400);
        setStep(4); await delay(400);

        // Consume payment token (fire-and-forget)
        fetch(API + '/payments/consume-prediction-payment', {
            method: 'POST', headers: authHeaders()
        }).catch(() => {});

        // Clean up localStorage — both scoped and legacy keys
        _clearPendingData();
        clearPredictionPaid();

        window.location.href = '/templates/patient/prediction_result.html?id=' + data.prediction.id;

    } catch {
        hideOverlay();
        showAlert('Network error. Please check your connection and try again.');
        resetBtn();
    }
}

function resetBtn() {
    const btn = document.getElementById('submitBtn');
    if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-calculator"></i> Get Prediction'; }
}

function clearForm() {
    ['pregnancies', 'skinThickness', 'diabetesPedigree', 'age'].forEach(id => {
        const el = document.getElementById(id);
        if (el && !el.readOnly) el.value = id === 'diabetesPedigree' ? '0.500' : id === 'pregnancies' ? '0' : '';
    });
    ['glucose', 'bloodPressure', 'insulin', 'bmi'].forEach(id => {
        const el = document.getElementById(id);
        if (el && !el.readOnly) el.value = '';
    });
    hideAlert();
}

// ── Main submit handler ───────────────────────────────────────────────────────
async function handleSubmit(e) {
    e.preventDefault();
    hideAlert();

    if (!Steps.nurseVitals) {
        // Warn but don't block — nurse may not have recorded yet, patient can still fill manually
        const bmi = parseFloat(document.getElementById('bmi')?.value);
        const bp  = parseFloat(document.getElementById('bloodPressure')?.value);
        if (isNaN(bmi) || isNaN(bp)) {
            showAlert(
                '<i class="bi bi-exclamation-triangle-fill me-2"></i>' +
                '<strong>BMI and Blood Pressure are required.</strong> Please visit the nurse station or enter values manually.',
                'warning'
            );
            return;
        }
    }

    const body = collectFormData();
    const err  = validateForm(body);
    if (err) { showAlert(err); return; }

    const btn = document.getElementById('submitBtn');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Checking...'; }

    try {
        // Check payment status from server
        const chk    = await fetch(API + '/payments/check-prediction-access', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const access = await chk.json();

        if (access.has_access) {
            resetBtn();
            await runPrediction(body);
        } else {
            // Save form data to localStorage, redirect to payment
            goToPayment(body);
        }
    } catch {
        // If payment check fails, still redirect to payment to be safe
        goToPayment(body);
    }
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async function () {
    const user = checkAuth('patient');
    if (!user) return;

    const nameEl = document.getElementById('navUserName');
    if (nameEl) nameEl.textContent = user.name || user.username;
    const sidebarName = document.getElementById('sidebarName');
    if (sidebarName) sidebarName.textContent = user.name || user.username;

    const form = document.getElementById('healthDataForm');
    if (form) form.addEventListener('submit', handleSubmit);
    ['glucose', 'bloodPressure', 'bmi', 'age', 'diabetesPedigree', 'insulin'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', updateLiveRiskHint);
    });

    // Step 1: Fetch nurse vitals from DB
    await checkNurseVitals();
    // Step 2: Fetch lab results from DB
    await checkLabResults();
    // Step 3: Auto-fill Age, Pregnancies, Pedigree from last prediction
    await checkLastPredictionData();
    // Show/hide form based on results
    evaluateFormAccess();

    // Keep checking for newly entered lab results so patient does not need to refresh.
    labPollingTimer = setInterval(refreshLabResultsIfNeeded, 20000);
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden) refreshLabResultsIfNeeded();
    });

    // Check if returning from payment page
    const paid    = isPredictionPaid();
    const pending = restorePendingData();

    if (pending) {
        // Restore manually-entered fields (pregnancies, age, pedigree)
        applyRestoredData(pending);
    }

    if (paid && pending) {
        clearPredictionPaid();
        _clearPendingData();
        const body = collectFormData();
        const err  = validateForm(body);
        if (!err) {
            showAlert('Payment confirmed! Running your prediction now...', 'success');
            await delay(800);
            hideAlert();
            await runPrediction(body);
        }
    }
    updateLiveRiskHint();
});
