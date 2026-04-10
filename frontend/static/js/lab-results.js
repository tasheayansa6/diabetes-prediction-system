// Enter Lab Results — Professional implementation

function authHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('token')
    };
}

function showAlert(msg, type) {
    const el = document.getElementById('formAlert');
    el.innerHTML = `<div class="alert alert-${type || 'success'}">${msg}</div>`;
    el.scrollIntoView({ behavior: 'smooth' });
}

function clearAlert() {
    document.getElementById('formAlert').innerHTML = '';
}

// ── Test hints keyed by name keyword ─────────────────────────────────────────
const TEST_HINTS = {
    'blood glucose':  { unit: 'mg/dL',  normal_range: '70–99 mg/dL (fasting)',      placeholder: 'e.g. 95'                          },
    'fasting':        { unit: 'mg/dL',  normal_range: '70–99 mg/dL',                placeholder: 'e.g. 88'                          },
    'hba1c':          { unit: '%',      normal_range: '< 5.7%',                     placeholder: 'e.g. 5.4'                         },
    'oral glucose':   { unit: 'mg/dL',  normal_range: '< 140 mg/dL at 2hr',        placeholder: 'e.g. 130'                         },
    'ogtt':           { unit: 'mg/dL',  normal_range: '< 140 mg/dL at 2hr',        placeholder: 'e.g. 130'                         },
    'insulin':        { unit: 'uU/mL',  normal_range: '2–25 uU/mL',                placeholder: 'e.g. 10'                          },
    'c-peptide':      { unit: 'ng/mL',  normal_range: '0.5–2.0 ng/mL',             placeholder: 'e.g. 1.2'                         },
    'lipid':          { unit: 'mg/dL',  normal_range: 'LDL < 100, HDL > 40 mg/dL', placeholder: 'e.g. LDL: 95, HDL: 55'           },
    'cholesterol':    { unit: 'mg/dL',  normal_range: '< 200 mg/dL',               placeholder: 'e.g. 185'                         },
    'triglyceride':   { unit: 'mg/dL',  normal_range: '< 150 mg/dL',               placeholder: 'e.g. 120'                         },
    'complete blood': { unit: 'x10⁹/L', normal_range: 'WBC 4.5–11 x10⁹/L',        placeholder: 'e.g. WBC: 7.2, RBC: 4.8, Hgb: 14'},
    'cbc':            { unit: 'x10⁹/L', normal_range: 'WBC 4.5–11 x10⁹/L',        placeholder: 'e.g. WBC: 7.2, RBC: 4.8, Hgb: 14'},
    'kidney':         { unit: 'mg/dL',  normal_range: 'Creatinine 0.6–1.2 mg/dL',  placeholder: 'e.g. Creatinine: 0.9, BUN: 15'   },
    'creatinine':     { unit: 'mg/dL',  normal_range: '0.6–1.2 mg/dL',             placeholder: 'e.g. 0.9'                         },
    'liver':          { unit: 'U/L',    normal_range: 'ALT 7–56 U/L',              placeholder: 'e.g. ALT: 32, AST: 28'           },
    'thyroid':        { unit: 'mIU/L',  normal_range: '0.4–4.0 mIU/L',             placeholder: 'e.g. 2.1'                         },
    'tsh':            { unit: 'mIU/L',  normal_range: '0.4–4.0 mIU/L',             placeholder: 'e.g. 2.1'                         },
    'urine':          { unit: '',       normal_range: 'Normal',                     placeholder: 'e.g. Normal / Glucose: Negative'  },
    'microalbumin':   { unit: 'mg/g',   normal_range: '< 30 mg/g',                 placeholder: 'e.g. 18'                          },
};

function getHints(testName) {
    const name = (testName || '').toLowerCase();
    for (const [key, h] of Object.entries(TEST_HINTS)) {
        if (name.includes(key)) return h;
    }
    return null;
}

// ── In-memory test map: test_id → test object ─────────────────────────────────
const _testMap = {};

// ── Render pending requests list ──────────────────────────────────────────────
function renderRequestsList(tests) {
    const el = document.getElementById('requestsList');

    if (!tests.length) {
        el.innerHTML = `
            <div class="card" style="text-align:center;padding:2.5rem;color:#64748b;">
                <i class="bi bi-check-circle" style="font-size:2.5rem;color:#22c55e;"></i>
                <p class="mt-2 font-medium">No pending lab requests</p>
                <p class="text-xs mt-1">All doctor-ordered tests have been completed.</p>
            </div>`;
        return;
    }

    el.innerHTML = tests.map(t => {
        const hints       = getHints(t.test_name);
        const isUrgent    = t.priority === 'urgent';
        const pColor      = isUrgent ? '#dc2626' : '#d97706';
        const pBg         = isUrgent ? '#fef2f2' : '#fffbeb';
        const patient     = t.patient?.name  || '—';
        const doctor      = t.doctor?.name   || '—';
        const category    = t.test_category  || t.test_type || '—';
        const date        = t.created_at ? new Date(t.created_at).toLocaleDateString() : '—';
        const normalRange = t.normal_range   || (hints && hints.normal_range) || '—';
        const unit        = t.unit           || (hints && hints.unit)         || '—';
        // Safe: reference by test_id string, no JSON in attribute
        const safeId      = CSS.escape(t.test_id);

        return `
        <div class="card mb-3" style="border-left:4px solid ${pColor};padding:1rem 1.25rem;">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;flex-wrap:wrap;">
            <div style="flex:1;min-width:0;">
              <div style="font-size:.7rem;font-weight:700;text-transform:uppercase;
                          letter-spacing:.06em;color:#2563eb;margin-bottom:.3rem;">
                <i class="bi bi-person-badge-fill"></i> Ordered by Dr. ${escHtml(doctor)}
              </div>
              <div style="font-size:1.05rem;font-weight:700;color:#1e293b;margin-bottom:.45rem;">
                <i class="bi bi-flask" style="color:#2563eb;"></i> ${escHtml(t.test_name)}
              </div>
              <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));
                          gap:.2rem .75rem;font-size:.82rem;color:#374151;">
                <div><span style="color:#6b7280;">Patient:</span> <strong>${escHtml(patient)}</strong></div>
                <div><span style="color:#6b7280;">Doctor:</span> <strong>Dr. ${escHtml(doctor)}</strong></div>
                <div><span style="color:#6b7280;">Category:</span> <strong>${escHtml(category)}</strong></div>
                <div><span style="color:#6b7280;">Ordered:</span> <strong>${date}</strong></div>
                <div><span style="color:#6b7280;">Normal Range:</span> <strong>${escHtml(normalRange)}</strong></div>
                <div><span style="color:#6b7280;">Unit:</span> <strong>${escHtml(unit)}</strong></div>
              </div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:.5rem;flex-shrink:0;">
              <span style="background:${pBg};color:${pColor};padding:.2rem .7rem;
                           border-radius:99px;font-size:.75rem;font-weight:700;">
                ${(t.priority || 'normal').toUpperCase()}
              </span>
              <button data-testid="${escAttr(t.test_id)}"
                      class="btn btn-primary enter-result-btn" style="white-space:nowrap;">
                <i class="bi bi-pencil-square"></i> Enter Result
              </button>
            </div>
          </div>
        </div>`;
    }).join('');

    // Bind buttons safely — no inline JSON
    el.querySelectorAll('.enter-result-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const test = _testMap[this.dataset.testid];
            if (test) openForm(test);
        });
    });
}

// ── Open result form pre-filled ───────────────────────────────────────────────
function openForm(test) {
    const hints = getHints(test.test_name);

    // Banner
    document.getElementById('bannerTestName').textContent = test.test_name;
    const meta = [];
    if (test.test_category || test.test_type) meta.push(test.test_category || test.test_type);
    if (test.patient?.name) meta.push('Patient: ' + test.patient.name);
    if (test.doctor?.name)  meta.push('Dr. ' + test.doctor.name);
    document.getElementById('bannerTestMeta').textContent = meta.join('  ·  ');

    // Form fields
    document.getElementById('hiddenTestId').value           = test.test_id;
    document.getElementById('unit').value                   = test.unit         || (hints && hints.unit)         || '';
    document.getElementById('normalRange').value            = test.normal_range || (hints && hints.normal_range) || '';
    document.getElementById('resultValue').value            = '';
    document.getElementById('resultValue').placeholder      = (hints && hints.placeholder) || 'Enter result value';
    document.getElementById('notes').value                  = '';
    document.getElementById('test_date').valueAsDate        = new Date();

    // Switch panels
    document.getElementById('panelList').style.display = 'none';
    document.getElementById('panelForm').style.display = '';
    clearAlert();
    document.getElementById('resultValue').focus();
}

// ── Back to list — clear test_id from URL so reload works correctly ───────────
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
        if (res.status === 401) { window.location.href = '/login'; return; }
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        const tests = data.pending_tests || [];

        // Populate map
        Object.keys(_testMap).forEach(k => delete _testMap[k]);
        tests.forEach(t => { _testMap[t.test_id] = t; });

        if (autoOpenId) {
            const test = _testMap[autoOpenId];
            if (test) { openForm(test); return; }
            // test not found (already completed) — fall through to list
        }

        renderRequestsList(tests);

    } catch (err) {
        document.getElementById('requestsList').innerHTML = `
            <div class="card" style="text-align:center;padding:2rem;color:#dc2626;">
                <i class="bi bi-exclamation-circle" style="font-size:2rem;"></i>
                <p class="mt-2">Error loading requests: ${escHtml(err.message)}</p>
            </div>`;
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function escHtml(str) {
    const d = document.createElement('div');
    d.textContent = str ?? '';
    return d.innerHTML;
}
function escAttr(str) {
    return (str ?? '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('lab_technician');
    if (!user) return;

    const name = user.name || user.username;
    document.getElementById('topUserName').textContent = name;
    document.getElementById('userName').textContent    = name;

    // Read test_id from URL (set by notification link or dashboard Process button)
    const urlTestId = new URLSearchParams(window.location.search).get('test_id') || null;
    loadPendingRequests(urlTestId);

    // Submit
    document.getElementById('labResultsForm').addEventListener('submit', async function (e) {
        e.preventDefault();

        const testId = document.getElementById('hiddenTestId').value;
        const result = document.getElementById('resultValue').value.trim();

        if (!testId) { showAlert('No test selected.', 'warning'); return; }
        if (!result) { showAlert('Result value is required.', 'warning'); return; }

        const btn = this.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Saving...';

        const payload = {
            test_id:      testId,
            results:      result,
            unit:         document.getElementById('unit').value.trim(),
            normal_range: document.getElementById('normalRange').value.trim(),
            remarks:      document.getElementById('notes').value.trim()
        };

        try {
            const res  = await fetch('/api/labs/results', {
                method: 'POST', headers: authHeaders(), body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!data.success) throw new Error(data.message || 'Failed to save results');

            // Go back to list (clears URL), reload without auto-open
            backToList();
            showAlert(
                `<i class="bi bi-check-circle-fill"></i> Results saved for <strong>${escHtml(data.test?.test_name || testId)}</strong>. Patient and doctor have been notified.`,
                'success'
            );
            loadPendingRequests(null);

        } catch (err) {
            showAlert(escHtml(err.message), 'danger');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle"></i> Save Result';
        }
    });
});
