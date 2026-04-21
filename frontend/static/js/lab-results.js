// Enter Lab Results — Diabetes Prediction System

function authHeaders() {
    return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token') };
}
function showAlert(msg, type) {
    const el = document.getElementById('formAlert');
    el.innerHTML = `<div class="alert alert-${type||'success'}">${msg}</div>`;
    el.scrollIntoView({ behavior: 'smooth' });
}
function clearAlert() { document.getElementById('formAlert').innerHTML = ''; }

// ── Test hints: unit + normal range + placeholder per test type ───────────────
const TEST_HINTS = {
    'blood glucose':  { unit:'mg/dL',  range:'70–99 mg/dL (fasting)',           ph:'e.g. 95'                           },
    'fasting':        { unit:'mg/dL',  range:'70–99 mg/dL',                     ph:'e.g. 88'                           },
    'random blood':   { unit:'mg/dL',  range:'< 200 mg/dL',                     ph:'e.g. 145'                          },
    'postprandial':   { unit:'mg/dL',  range:'< 140 mg/dL at 2hr',              ph:'e.g. 130'                          },
    'ogtt':           { unit:'mg/dL',  range:'< 140 mg/dL at 2hr',              ph:'e.g. 128'                          },
    'oral glucose':   { unit:'mg/dL',  range:'< 140 mg/dL at 2hr',              ph:'e.g. 128'                          },
    'hba1c':          { unit:'%',      range:'< 5.7% normal | 5.7–6.4% prediabetes | ≥6.5% diabetes', ph:'e.g. 6.2'  },
    'glycated':       { unit:'%',      range:'< 5.7%',                          ph:'e.g. 5.8'                          },
    'fructosamine':   { unit:'umol/L', range:'200–285 umol/L',                  ph:'e.g. 240'                          },
    'insulin':        { unit:'uU/mL',  range:'2–25 uU/mL (fasting)',            ph:'e.g. 12'                           },
    'c-peptide':      { unit:'ng/mL',  range:'0.5–2.0 ng/mL',                  ph:'e.g. 1.2'                          },
    'homa':           { unit:'',       range:'< 2.0 (normal insulin sensitivity)',ph:'e.g. 1.8'                        },
    'microalbumin':   { unit:'mg/g',   range:'< 30 mg/g (normal)',              ph:'e.g. 18'                           },
    'creatinine':     { unit:'mg/dL',  range:'0.6–1.2 mg/dL',                  ph:'e.g. 0.9'                          },
    'kidney':         { unit:'mg/dL',  range:'Creatinine 0.6–1.2 mg/dL',       ph:'e.g. 0.9'                          },
    'egfr':           { unit:'mL/min', range:'> 60 mL/min/1.73m²',             ph:'e.g. 85'                           },
    'bun':            { unit:'mg/dL',  range:'7–20 mg/dL',                     ph:'e.g. 14'                           },
    'urea':           { unit:'mg/dL',  range:'7–20 mg/dL',                     ph:'e.g. 14'                           },
    'lipid':          { unit:'mg/dL',  range:'LDL < 100 | HDL > 40 | TG < 150 mg/dL', ph:'e.g. LDL:95 HDL:52 TG:130' },
    'cholesterol':    { unit:'mg/dL',  range:'< 200 mg/dL',                    ph:'e.g. 185'                          },
    'triglyceride':   { unit:'mg/dL',  range:'< 150 mg/dL',                    ph:'e.g. 120'                          },
    'liver':          { unit:'U/L',    range:'ALT 7–56 U/L | AST 10–40 U/L',   ph:'e.g. ALT:32 AST:28'               },
    'alt':            { unit:'U/L',    range:'7–56 U/L',                        ph:'e.g. 32'                           },
    'cbc':            { unit:'',       range:'WBC 4.5–11 | Hgb 12–17 g/dL',    ph:'e.g. WBC:7.2 Hgb:14.1'            },
    'complete blood': { unit:'',       range:'WBC 4.5–11 | Hgb 12–17 g/dL',    ph:'e.g. WBC:7.2 Hgb:14.1'            },
    'urine analysis': { unit:'',       range:'Normal — no glucose/protein/ketones', ph:'e.g. Normal / Glucose: Negative' },
    'urine glucose':  { unit:'',       range:'Negative (< 0.8 mmol/L)',         ph:'e.g. Negative'                    },
    'urine ketone':   { unit:'',       range:'Negative',                        ph:'e.g. Negative'                    },
    'thyroid':        { unit:'mIU/L',  range:'0.4–4.0 mIU/L',                  ph:'e.g. 2.1'                          },
    'tsh':            { unit:'mIU/L',  range:'0.4–4.0 mIU/L',                  ph:'e.g. 2.1'                          },
};

function getHints(testName) {
    const n = (testName || '').toLowerCase();
    for (const [key, h] of Object.entries(TEST_HINTS)) {
        if (n.includes(key)) return h;
    }
    return null;
}

// Category icon map
const CAT_ICONS = {
    'Blood Glucose':     'bi-droplet-fill cat-glucose',
    'Glucose Control':   'bi-graph-up cat-hba1c',
    'Insulin & Pancreas':'bi-capsule cat-insulin',
    'Kidney Function':   'bi-funnel-fill cat-kidney',
    'Lipid Panel':       'bi-heart-pulse cat-lipid',
    'Liver Function':    'bi-shield-fill cat-liver',
    'Urine Analysis':    'bi-droplet-half cat-urine',
    'Thyroid':           'bi-thermometer-half cat-thyroid',
    'Blood Count':       'bi-activity cat-default',
};

function getCatIcon(cat) {
    return CAT_ICONS[cat] || 'bi-flask cat-default';
}

// ── In-memory test map ────────────────────────────────────────────────────────
const _testMap = {};
let _allTests  = [];
let _activeFilter = 'all';

// ── Filter tests ──────────────────────────────────────────────────────────────
function filterRequests(filter, btn) {
    _activeFilter = filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    renderRequestsList(_allTests);
}

// ── Render list ───────────────────────────────────────────────────────────────
function renderRequestsList(tests) {
    const el = document.getElementById('requestsList');

    // Apply filter
    let filtered = tests;
    if (_activeFilter === 'urgent') {
        filtered = tests.filter(t => t.priority === 'urgent');
    } else if (_activeFilter !== 'all') {
        filtered = tests.filter(t =>
            (t.test_name || '').toLowerCase().includes(_activeFilter) ||
            (t.test_category || '').toLowerCase().includes(_activeFilter)
        );
    }

    // Update count badge
    const countEl = document.getElementById('pendingCount');
    if (countEl) countEl.textContent = tests.length + ' pending';

    if (!filtered.length) {
        el.innerHTML = `
            <div class="empty-state">
                <i class="bi bi-check-circle-fill" style="color:#22c55e;"></i>
                <p style="font-weight:600;color:#374151;margin-bottom:.25rem;">
                    ${_activeFilter === 'all' ? 'No pending lab requests' : 'No ' + _activeFilter + ' tests pending'}
                </p>
                <p style="font-size:.82rem;color:#94a3b8;">
                    ${_activeFilter === 'all' ? 'All doctor-ordered tests have been completed.' : 'Try a different filter.'}
                </p>
            </div>`;
        return;
    }

    el.innerHTML = filtered.map(t => {
        const hints    = getHints(t.test_name);
        const isUrgent = t.priority === 'urgent';
        const patient  = t.patient?.name || '—';
        const doctor   = t.doctor?.name  || '—';
        const category = t.test_category || t.test_type || '—';
        const date     = t.created_at ? new Date(t.created_at).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}) : '—';
        const range    = t.normal_range || (hints && hints.range) || '—';
        const unit     = t.unit         || (hints && hints.unit)  || '';
        const catIcon  = getCatIcon(category);

        return `
        <div class="req-card${isUrgent ? ' urgent' : ''}">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;flex-wrap:wrap;">
            <div style="flex:1;min-width:0;">
              <div style="font-size:.7rem;font-weight:700;text-transform:uppercase;
                          letter-spacing:.06em;color:#2563eb;margin-bottom:.35rem;">
                <i class="bi bi-person-badge-fill"></i> Ordered by Dr. ${escHtml(doctor)}
              </div>
              <div class="req-test-name">
                <i class="bi ${catIcon}" style="font-size:1.1rem;"></i>
                ${escHtml(t.test_name)}
              </div>
              <div class="req-meta">
                <div><span>Patient:</span> <strong>${escHtml(patient)}</strong></div>
                <div><span>Category:</span> <strong>${escHtml(category)}</strong></div>
                <div><span>Ordered:</span> <strong>${date}</strong></div>
                <div><span>Normal Range:</span> <strong>${escHtml(range)}</strong></div>
                ${unit ? `<div><span>Unit:</span> <strong>${escHtml(unit)}</strong></div>` : ''}
                ${t.wait_time ? `<div><span>Waiting:</span> <strong style="color:#d97706;">${escHtml(t.wait_time)}</strong></div>` : ''}
              </div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:.5rem;flex-shrink:0;">
              <span class="priority-badge priority-${isUrgent ? 'urgent' : 'normal'}">
                ${isUrgent ? '🔴' : '🟡'} ${(t.priority || 'normal').toUpperCase()}
              </span>
              <button data-testid="${escAttr(t.test_id)}"
                      class="btn btn-primary enter-result-btn" style="white-space:nowrap;">
                <i class="bi bi-pencil-square"></i> Enter Result
              </button>
            </div>
          </div>
        </div>`;
    }).join('');

    // Bind buttons
    el.querySelectorAll('.enter-result-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const test = _testMap[this.dataset.testid];
            if (test) openForm(test);
        });
    });
}

// ── Open result form ──────────────────────────────────────────────────────────
function openForm(test) {
    const hints = getHints(test.test_name);

    // Banner
    document.getElementById('bannerTestName').textContent = test.test_name;
    const meta = [];
    if (test.test_category) meta.push(test.test_category);
    if (test.patient?.name) meta.push('Patient: ' + test.patient.name);
    if (test.doctor?.name)  meta.push('Dr. ' + test.doctor.name);
    document.getElementById('bannerTestMeta').textContent = meta.join('  ·  ');

    // Pre-fill fields
    const unit  = test.unit         || (hints && hints.unit)  || '';
    const range = test.normal_range || (hints && hints.range) || '';
    document.getElementById('hiddenTestId').value      = test.test_id;
    document.getElementById('unit').value              = unit;
    document.getElementById('normalRange').value       = range;
    document.getElementById('resultValue').value       = '';
    document.getElementById('resultValue').placeholder = (hints && hints.ph) || 'Enter result value';
    document.getElementById('notes').value             = '';
    document.getElementById('test_date').valueAsDate   = new Date();

    // Unit suffix inside input
    const suffix = document.getElementById('unitSuffix');
    if (suffix) suffix.textContent = unit;

    // Normal range hint box
    const hintBox  = document.getElementById('rangeHintBox');
    const hintText = document.getElementById('rangeHintText');
    if (range && hintBox && hintText) {
        hintText.textContent = 'Normal range: ' + range;
        hintBox.style.display = '';
    } else if (hintBox) {
        hintBox.style.display = 'none';
    }

    // Switch panels
    document.getElementById('panelList').style.display = 'none';
    document.getElementById('panelForm').style.display = '';
    clearAlert();
    document.getElementById('resultValue').focus();
}

function backToList() {
    history.replaceState(null, '', window.location.pathname);
    document.getElementById('panelForm').style.display = 'none';
    document.getElementById('panelList').style.display = '';
    clearAlert();
}

// ── Load pending tests ────────────────────────────────────────────────────────
async function loadPendingRequests(autoOpenId) {
    try {
        const res  = await fetch('/api/labs/pending?limit=200', { headers: authHeaders() });
        if (res.status === 401) { logout(); return; }
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        _allTests = data.pending_tests || [];
        Object.keys(_testMap).forEach(k => delete _testMap[k]);
        _allTests.forEach(t => { _testMap[t.test_id] = t; });

        if (autoOpenId) {
            const test = _testMap[autoOpenId];
            if (test) { openForm(test); return; }
        }

        renderRequestsList(_allTests);

    } catch (err) {
        document.getElementById('requestsList').innerHTML = `
            <div class="empty-state">
                <i class="bi bi-exclamation-circle" style="color:#dc2626;"></i>
                <p style="color:#dc2626;">Error: ${escHtml(err.message)}</p>
            </div>`;
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function escHtml(s) { const d=document.createElement('div'); d.textContent=s??''; return d.innerHTML; }
function escAttr(s) { return (s??'').replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('lab_technician');
    if (!user) return;

    const name = user.name || user.username;
    document.getElementById('topUserName').textContent = name;
    document.getElementById('userName').textContent    = name;

    const urlTestId = new URLSearchParams(window.location.search).get('test_id') || null;
    loadPendingRequests(urlTestId);

    // Update unit suffix when unit field changes
    document.getElementById('unit').addEventListener('input', function () {
        const s = document.getElementById('unitSuffix');
        if (s) s.textContent = this.value;
    });

    // Submit
    document.getElementById('labResultsForm').addEventListener('submit', async function (e) {
        e.preventDefault();

        const testId = document.getElementById('hiddenTestId').value;
        const result = document.getElementById('resultValue').value.trim();

        if (!testId) { showAlert('No test selected.', 'warning'); return; }
        if (!result) { showAlert('Result value is required.', 'warning'); return; }

        const btn = document.getElementById('saveBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Saving...';

        try {
            const res  = await fetch('/api/labs/results', {
                method: 'POST', headers: authHeaders(),
                body: JSON.stringify({
                    test_id:      testId,
                    results:      result,
                    unit:         document.getElementById('unit').value.trim(),
                    normal_range: document.getElementById('normalRange').value.trim(),
                    remarks:      document.getElementById('notes').value.trim()
                })
            });
            const data = await res.json();

            if (!data.success) throw new Error(data.message || 'Failed to save');

            backToList();
            showAlert(
                `<i class="bi bi-check-circle-fill"></i> Result saved for <strong>${escHtml(data.test?.test_name || testId)}</strong>. Patient and doctor have been notified.`,
                'success'
            );
            loadPendingRequests(null);

        } catch (err) {
            showAlert(escHtml(err.message), 'danger');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle-fill"></i> Save & Notify Patient';
        }
    });
});
