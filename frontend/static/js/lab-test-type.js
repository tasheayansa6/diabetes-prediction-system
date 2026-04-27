// Lab Add Test Type - calls POST /api/labs/test-types

// Full test catalogue — name → {code, range, prep, cost}
const TEST_CATALOGUE = {
    'Blood Glucose (Fasting)':        { code: 'BG',     range: '70-99 mg/dL',              prep: 'Fast for 8 hours before test',                cost: 25  },
    'Random Blood Glucose':           { code: 'RBG',    range: '< 200 mg/dL',              prep: 'No fasting required',                          cost: 20  },
    'Postprandial Glucose (2hr)':     { code: 'PPG',    range: '< 140 mg/dL at 2hr',       prep: 'Test exactly 2 hours after a meal',            cost: 25  },
    'Oral Glucose Tolerance (OGTT)':  { code: 'OGTT',   range: '< 140 mg/dL at 2hr',       prep: 'Fast 8hrs; drink 75g glucose solution',        cost: 60  },
    'HbA1c (Glycated Haemoglobin)':   { code: 'HBA1C',  range: '< 5.7%',                   prep: 'No fasting required; reflects 3-month average',cost: 45  },
    'Fructosamine':                   { code: 'FRUCT',  range: '200-285 umol/L',            prep: 'No fasting required',                          cost: 50  },
    'Glycated Albumin':               { code: 'GLYCALB',range: '11-16%',                    prep: 'No fasting required',                          cost: 70  },
    'Insulin Level (Fasting)':        { code: 'INS',    range: '2-25 uU/mL',               prep: 'Fast for 8 hours before test',                cost: 55  },
    'C-Peptide':                      { code: 'CPEP',   range: '0.5-2.0 ng/mL',            prep: 'Fast for 8 hours before test',                cost: 65  },
    'Proinsulin':                     { code: 'PROINSU',range: '< 18 pmol/L',              prep: 'Fast for 8 hours before test',                cost: 80  },
    'HOMA-IR (Insulin Resistance)':   { code: 'HOMAIR', range: '< 2.0 (normal)',            prep: 'Requires fasting glucose + fasting insulin',  cost: 75  },
    'GAD Antibodies (Anti-GAD65)':    { code: 'GADAB',  range: '< 5 IU/mL (negative)',     prep: 'No fasting required; Type 1 marker',          cost: 120 },
    'Islet Cell Antibodies (ICA)':    { code: 'ICA',    range: 'Negative',                  prep: 'No fasting required; Type 1 marker',          cost: 130 },
    'IA-2 Antibodies':                { code: 'IA2AB',  range: 'Negative',                  prep: 'No fasting required; Type 1 marker',          cost: 125 },
    'Zinc Transporter 8 Ab (ZnT8)':   { code: 'ZNT8AB', range: 'Negative',                  prep: 'No fasting required; Type 1 marker',          cost: 135 },
    'Urine Microalbumin':             { code: 'UALB',   range: '< 30 mg/g creatinine',      prep: 'First morning urine sample preferred',        cost: 30  },
    'Urine Albumin-Creatinine Ratio': { code: 'UACR',   range: '< 30 mg/g',                 prep: 'Spot urine sample; no fasting needed',        cost: 35  },
    'Serum Creatinine':               { code: 'SCREAT', range: '0.6-1.2 mg/dL',             prep: 'No fasting required',                         cost: 20  },
    'eGFR (Kidney Function)':         { code: 'EGFR',   range: '> 60 mL/min/1.73m²',       prep: 'Calculated from serum creatinine + age',      cost: 25  },
    'Urine Glucose (Dipstick)':       { code: 'UGLUC',  range: 'Negative',                  prep: 'Random urine sample',                         cost: 10  },
    'Urine Ketones':                  { code: 'UKET',   range: 'Negative',                  prep: 'Random urine; critical in DKA screening',     cost: 10  },
    'Lipid Profile (Full)':           { code: 'LIPID',  range: 'LDL < 100 mg/dL',           prep: 'Fast for 9-12 hours before test',             cost: 40  },
    'Triglycerides':                  { code: 'TRIG',   range: '< 150 mg/dL',               prep: 'Fast for 9-12 hours before test',             cost: 25  },
    'HDL Cholesterol':                { code: 'HDL',    range: '> 40 mg/dL (M), > 50 (F)',  prep: 'Fast for 9-12 hours before test',             cost: 20  },
    'TSH (Thyroid Stimulating Hormone)':{ code: 'TSH',  range: '0.4-4.0 mIU/L',            prep: 'No fasting required',                         cost: 35  },
    'Free T4':                        { code: 'FT4',    range: '0.8-1.8 ng/dL',             prep: 'No fasting required',                         cost: 40  },
    'Liver Function Tests (LFT)':     { code: 'LFT',    range: 'ALT < 40 U/L',              prep: 'No fasting required',                         cost: 45  },
    'Amylase':                        { code: 'AMYL',   range: '30-110 U/L',                prep: 'No fasting required',                         cost: 30  },
    'Lipase':                         { code: 'LIPAS',  range: '0-160 U/L',                 prep: 'No fasting required',                         cost: 35  },
    'Vitamin D (25-OH)':              { code: 'VITD',   range: '30-100 ng/mL',              prep: 'No fasting required',                         cost: 50  },
    'Magnesium':                      { code: 'MAG',    range: '1.7-2.2 mg/dL',             prep: 'No fasting required',                         cost: 20  },
    'Zinc':                           { code: 'ZINC',   range: '70-120 ug/dL',              prep: 'No fasting required',                         cost: 25  },
};

// Fetch existing test codes to determine next increment
async function getNextCode(baseCode) {
    try {
        const res  = await fetch('/api/labs/test-types', {
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
        });
        const data = await res.json();
        if (!data.success) return baseCode + '001';
        const existing = (data.test_types || [])
            .map(t => t.test_code || '')
            .filter(c => c.startsWith(baseCode));
        if (!existing.length) return baseCode + '001';
        // Extract numeric suffixes and find max
        const nums = existing.map(c => parseInt(c.replace(baseCode, '')) || 0).filter(n => !isNaN(n));
        const next = Math.max(...nums) + 1;
        return baseCode + String(next).padStart(3, '0');
    } catch (_) {
        return baseCode + '001';
    }
}

// When test name changes — auto-fill all fields + generate incremented code
async function onTestNameChange(selectEl) {
    const name = selectEl.value;
    if (!name) return;
    const info = TEST_CATALOGUE[name];
    if (!info) return;

    const form = document.getElementById('testTypeForm');

    // Auto-fill details
    form.normal_range.value = info.range;
    form.description.value  = info.prep;
    form.price.value        = info.cost;
    form.category.value     = 'Diabetes';

    // Generate incremented code
    const codeInput = form.test_code;
    codeInput.value = '…';
    codeInput.readOnly = true;
    codeInput.style.background = '#f1f5f9';
    const nextCode = await getNextCode(info.code);
    codeInput.value = nextCode;
    codeInput.readOnly = false;
    codeInput.style.background = '';

    // Show autofill banner
    let banner = document.getElementById('autofillBanner');
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'autofillBanner';
        banner.style.cssText = 'background:#f0fdf4;border:1px solid #86efac;color:#166534;padding:.65rem 1rem;border-radius:10px;margin-bottom:1rem;font-size:.82rem;';
        form.prepend(banner);
    }
    banner.innerHTML = `<i class="bi bi-magic"></i> Auto-filled from catalogue: <strong>${name}</strong> — Code: <strong>${nextCode}</strong>. You can edit before saving.`;
}

function quickFill(val) {
    if (!val) return;
    const [name, code, range, prep] = val.split('|');
    const form = document.getElementById('testTypeForm');
    // Find matching select option
    const sel = form.querySelector('select[name="test_name"]');
    if (sel) sel.value = name;
    form.test_code.value    = code;
    form.normal_range.value = range;
    form.description.value  = prep;
    form.category.value     = 'Diabetes';
}

function authHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('token')
    };
}

function showAlert(message, type = 'success') {
    const el = document.getElementById('formAlert');
    el.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    el.scrollIntoView({ behavior: 'smooth' });
}

async function handleTestTypeSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const btn  = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Saving...';

    const payload = {
        test_name:    form.querySelector('select[name="test_name"]').value.trim(),
        test_type:    form.test_code.value.trim(),
        category:     form.category.value,
        cost:         parseFloat(form.price.value) || 0,
        normal_range: form.normal_range.value.trim(),
        preparation_instructions: form.description.value.trim()
    };

    if (!payload.test_name || !payload.test_type) {
        showAlert('Test name and code are required.', 'danger');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-circle"></i> Add Test Model';
        return;
    }

    try {
        const res  = await fetch('/api/labs/test-types', {
            method: 'POST', headers: authHeaders(), body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message || 'Failed to add test type');
        showAlert(`Test type "<strong>${payload.test_name}</strong>" (${payload.test_type}) added successfully!`, 'success');
        form.reset();
        const banner = document.getElementById('autofillBanner');
        if (banner) banner.remove();
        setTimeout(() => { window.location.href = '/templates/lab/lab_test_service.html'; }, 1500);
    } catch (err) {
        showAlert(err.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-circle"></i> Add Test Model';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('lab_technician');
    if (!user) return;

    const name = user.name || user.username;
    const _t = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
    _t('topUserName', name);
    _t('userName',    name);

    document.getElementById('testTypeForm').addEventListener('submit', handleTestTypeSubmit);

    // Bind test name select to auto-fill
    const testNameSel = document.querySelector('select[name="test_name"]');
    if (testNameSel) testNameSel.addEventListener('change', () => onTestNameChange(testNameSel));
});
