const API = '/api';

function getToken() { return localStorage.getItem('token'); }
function authHeaders() {
    return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() };
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
        }

        // Unlock form if at least one vital field was filled
        const hasBMI = document.getElementById('bmi')?.readOnly;
        const hasBP  = v.blood_pressure_diastolic != null;

        if (!hasBMI && !hasBP) {
            updateStepUI('step1', 'missing', 'Nurse recorded vitals but BP and BMI are both missing.');
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
    updateStepUI('step4', 'checking');
    try {
        const res  = await fetch(API + '/patient/lab-results?limit=20', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();

        if (!data.success || !data.lab_results || data.lab_results.length === 0) {
            updateStepUI('step4', 'missing');
            Steps.labResults = false;
            return false;
        }

        const thirtyDaysAgo = Date.now() - (30 * 24 * 3600000);
        const isDone = r => ['completed', 'validated'].includes(r.status) && r.results;

        const glucoseTest = data.lab_results.find(r =>
            isDone(r) &&
            new Date(r.created_at).getTime() > thirtyDaysAgo &&
            (r.test_name.toLowerCase().includes('glucose') ||
             r.test_name.toLowerCase().includes('blood sugar') ||
             r.test_name.toLowerCase().includes('fasting') ||
             r.test_name.toLowerCase().includes('hba1c') ||
             r.test_name.toLowerCase().includes('sugar'))
        );
        const insulinTest = data.lab_results.find(r =>
            isDone(r) &&
            new Date(r.created_at).getTime() > thirtyDaysAgo &&
            r.test_name.toLowerCase().includes('insulin')
        );

        if (!glucoseTest) {
            updateStepUI('step4', 'missing', 'No recent glucose lab result found. Enter glucose manually below.');
            // Default insulin to 0 since no lab test exists
            const insulinEl = document.getElementById('insulin');
            if (insulinEl && !insulinEl.readOnly) insulinEl.value = '0';
            Steps.labResults = false;
            return false;
        }

        const filled = [];

        const glucoseVal = parseLabValue(glucoseTest.results);
        if (!isNaN(glucoseVal)) {
            const el = document.getElementById('glucose');
            if (el) { el.value = glucoseVal; el.readOnly = true; el.classList.add('field-autofilled'); }
            const badge = document.getElementById('glucoseBadge');
            if (badge) badge.style.display = 'inline';
            filled.push('Glucose: ' + glucoseVal + ' mg/dL');
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
        }

        updateStepUI('step4', 'done', '🔬 Auto-filled from DB: ' + filled.join(' | '));
        Steps.labResults = true;
        return true;

    } catch {
        updateStepUI('step4', 'missing');
        Steps.labResults = false;
        return false;
    }
}

// ── Step 3: Last prediction data — auto-fill Age, Pregnancies, Pedigree ─────
async function checkLastPredictionData() {
    try {
        const res  = await fetch(API + '/patient/health-data/last', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();
        if (!data.success || !data.data) return;

        const d = data.data;
        const filled = [];

        if (d.age != null) {
            const el = document.getElementById('age');
            if (el && !el.readOnly) { el.value = d.age; filled.push('Age: ' + d.age); }
        }
        if (d.pregnancies != null) {
            const el = document.getElementById('pregnancies');
            if (el && !el.readOnly) { el.value = d.pregnancies; filled.push('Pregnancies: ' + d.pregnancies); }
        }
        if (d.diabetes_pedigree != null) {
            const el = document.getElementById('diabetesPedigree');
            if (el && !el.readOnly) { el.value = d.diabetes_pedigree; filled.push('Pedigree: ' + d.diabetes_pedigree); }
        }

        if (filled.length) {
            const banner = document.getElementById('autofillBanner');
            const text   = document.getElementById('autofillText');
            if (banner && text) {
                text.textContent += ' | From last visit: ' + filled.join(', ') + '.';
            }
        }
    } catch { /* no previous prediction — that is fine */ }
}

// ── Autofill banner ───────────────────────────────────────────────────────────
function showAutofillBanner() {
    const banner     = document.getElementById('autofillBanner');
    const bannerText = document.getElementById('autofillText');
    if (!banner || !bannerText) return;
    const autofilled = [];
    if (document.getElementById('bloodPressure')?.readOnly) autofilled.push('Diastolic BP (from nurse) 🩺');
    if (document.getElementById('bmi')?.readOnly)           autofilled.push('BMI 🩺');
    if (document.getElementById('skinThickness')?.readOnly) autofilled.push('Skin Thickness 🩺');
    if (document.getElementById('glucose')?.readOnly)       autofilled.push('Glucose 🔬');
    if (document.getElementById('insulin')?.readOnly)       autofilled.push('Insulin 🔬');
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
        // Glucose and insulin remain editable — patient fills manually
        const glucoseEl  = document.getElementById('glucose');
        const insulinEl  = document.getElementById('insulin');
        if (glucoseEl && !glucoseEl.readOnly) {
            const hint = document.getElementById('glucoseHint');
            if (hint) hint.innerHTML = '✍️ No recent lab result found. Enter your latest fasting glucose reading manually.';
        }
    } else {
        // No nurse vitals at all — still show form, all fields editable
        if (formSection) formSection.style.display = 'block';
        if (blockedMsg)  blockedMsg.style.display  = 'none';
        if (submitBtn)   submitBtn.disabled = false;
        // Default insulin to 0
        const insulinEl = document.getElementById('insulin');
        if (insulinEl && !insulinEl.readOnly) insulinEl.value = '0';
        const glucoseHint = document.getElementById('glucoseHint');
        if (glucoseHint) glucoseHint.innerHTML = '✍️ Enter your latest fasting glucose reading manually.';
    }
}

// ── Payment redirect — uses localStorage (persists across page navigations) ───
function goToPayment(body) {
    // Store form data in localStorage so it survives the payment page redirect
    localStorage.setItem('pendingHealthData', JSON.stringify(body));
    window.location.href = '/templates/payment/payment_page.html?service=prediction&return=health_form';
}

// ── Restore pending form data after returning from payment ────────────────────
function restorePendingData() {
    const saved = localStorage.getItem('pendingHealthData');
    if (!saved) return null;
    try {
        return JSON.parse(saved);
    } catch { return null; }
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

        // Clean up localStorage
        localStorage.removeItem('pendingHealthData');
        localStorage.removeItem('predictionPaid');

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
        showAlert(
            '<i class="bi bi-exclamation-triangle-fill me-2"></i>' +
            '<strong>Nurse check-up required first.</strong> Please visit the nurse station to have your vitals recorded.',
            'danger'
        );
        return;
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
        resetBtn();
        showAlert('Could not verify payment status. Please try again.');
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

    // Step 1: Fetch nurse vitals from DB
    await checkNurseVitals();
    // Step 2: Fetch lab results from DB
    await checkLabResults();
    // Step 3: Auto-fill Age, Pregnancies, Pedigree from last prediction
    await checkLastPredictionData();
    // Show/hide form based on results
    evaluateFormAccess();

    // Check if returning from payment page
    const paid    = localStorage.getItem('predictionPaid');
    const pending = restorePendingData();

    if (pending) {
        // Restore manually-entered fields (pregnancies, age, pedigree)
        applyRestoredData(pending);
    }

    if (paid === 'true' && pending) {
        localStorage.removeItem('predictionPaid');
        localStorage.removeItem('pendingHealthData');
        const body = collectFormData();
        const err  = validateForm(body);
        if (!err) {
            showAlert('Payment confirmed! Running your prediction now...', 'success');
            await delay(800);
            hideAlert();
            await runPrediction(body);
        }
    }
});
