// Enter Lab Results — Batch by Patient (all tests in one form)

function authHeaders() {
    return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token') };
}
function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }
function showAlert(msg, type) {
    const el = document.getElementById('formAlert');
    el.innerHTML = `<div class="alert alert-${type||'success'}">${msg}</div>`;
    el.scrollIntoView({ behavior: 'smooth' });
}
function clearAlert() { document.getElementById('formAlert').innerHTML = ''; }

// ── Test hints ────────────────────────────────────────────────────────────────
const TEST_HINTS = {
    'blood glucose':  { unit:'mg/dL',  range:'70–99 mg/dL (fasting)',                        ph:'e.g. 95'   },
    'fasting':        { unit:'mg/dL',  range:'70–99 mg/dL',                                  ph:'e.g. 88'   },
    'random blood':   { unit:'mg/dL',  range:'< 200 mg/dL',                                  ph:'e.g. 145'  },
    'postprandial':   { unit:'mg/dL',  range:'< 140 mg/dL at 2hr',                           ph:'e.g. 130'  },
    'ogtt':           { unit:'mg/dL',  range:'< 140 mg/dL at 2hr',                           ph:'e.g. 128'  },
    'oral glucose':   { unit:'mg/dL',  range:'< 140 mg/dL at 2hr',                           ph:'e.g. 128'  },
    'hba1c':          { unit:'%',      range:'< 5.7% normal | 5.7–6.4% prediabetes | ≥6.5% diabetes', ph:'e.g. 6.2' },
    'glycated':       { unit:'%',      range:'< 5.7%',                                       ph:'e.g. 5.8'  },
    'fructosamine':   { unit:'umol/L', range:'200–285 umol/L',                               ph:'e.g. 240'  },
    'insulin':        { unit:'uU/mL',  range:'2–25 uU/mL (fasting)',                         ph:'e.g. 12'   },
    'c-peptide':      { unit:'ng/mL',  range:'0.5–2.0 ng/mL',                               ph:'e.g. 1.2'  },
};
function getHints(name) {
    const n = (name || '').toLowerCase();
    for (const [k, h] of Object.entries(TEST_HINTS)) if (n.includes(k)) return h;
    return null;
}

// ── State ─────────────────────────────────────────────────────────────────────
let _allTests = [];
let _testMap  = {};
let _activeFilter = 'all';

// ── Group tests by patient ────────────────────────────────────────────────────
function groupByPatient(tests) {
    const map = {};
    tests.forEach(t => {
        const pid = t.patient?.id || t.patient_id || 'unknown';
        if (!map[pid]) map[pid] = { patient: t.patient, tests: [] };
        map[pid].tests.push(t);
    });
    return Object.values(map);
}

// ── Filter ────────────────────────────────────────────────────────────────────
function filterRequests(filter, btn) {
    _activeFilter = filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    renderBatchList(_allTests);
}

// ── Render batch list (grouped by patient) ────────────────────────────────────
function renderBatchList(tests) {
    const el = document.getElementById('requestsList');

    // Apply filter
    let filtered = tests;
    if (_activeFilter === 'urgent') {
        filtered = tests.filter(t => t.priority === 'urgent');
    } else if (_activeFilter !== 'all') {
        const filterMap = {
            'glucose': ['glucose', 'blood sugar', 'random blood'],
            'hba1c':   ['hba1c', 'glycated', 'hemoglobin a1c'],
            'insulin': ['insulin', 'c-peptide'],
            'ogtt':    ['ogtt', 'oral glucose', 'tolerance'],
            'fasting': ['fasting', 'fbs'],
        };
        const terms = filterMap[_activeFilter] || [_activeFilter];
        filtered = tests.filter(t => {
            const name = (t.test_name || '').toLowerCase();
            return terms.some(term => name.includes(term));
        });
    }

    const countEl = document.getElementById('pendingCount');
    if (countEl) countEl.textContent = filtered.length + ' pending';

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

    const groups = groupByPatient(filtered);

    el.innerHTML = groups.map((g, gi) => {
        const p       = g.patient || {};
        const pName   = p.name   || '—';
        const pId     = p.patient_id || ('ID:' + (p.id || '?'));
        const hasUrgent = g.tests.some(t => t.priority === 'urgent');

        const testRows = g.tests.map((t, ti) => {
            const hints    = getHints(t.test_name);
            const unit     = t.unit || (hints && hints.unit) || '';
            const range    = t.normal_range || (hints && hints.range) || '';
            const ph       = (hints && hints.ph) || 'Enter result...';
            const doctor   = t.doctor?.name || '—';
            const ordered  = t.created_at ? new Date(t.created_at).toLocaleDateString('en-US',{month:'short',day:'numeric'}) : '—';
            const isUrgent = t.priority === 'urgent';

            return `
            <div class="test-row" id="row_${gi}_${ti}"
                 style="display:grid;grid-template-columns:1fr 1fr;gap:0;border:1.5px solid ${isUrgent?'#fca5a5':'#e2e8f0'};
                        border-radius:10px;margin-bottom:.6rem;overflow:hidden;background:#fff;">

              <!-- LEFT: test info -->
              <div style="padding:.85rem 1rem;border-right:1.5px solid ${isUrgent?'#fca5a5':'#e2e8f0'};background:${isUrgent?'#fff5f5':'#f8fafc'};">
                <div style="font-weight:700;font-size:.9rem;color:#1e293b;margin-bottom:.3rem;">
                  <i class="bi bi-flask-fill" style="color:#2563eb;"></i> ${esc(t.test_name)}
                  ${isUrgent ? '<span style="background:#fee2e2;color:#991b1b;border-radius:99px;padding:.1rem .5rem;font-size:.65rem;font-weight:700;margin-left:.4rem;">🔴 URGENT</span>' : ''}
                </div>
                <div style="font-size:.73rem;color:#64748b;line-height:1.6;">
                  <div><i class="bi bi-person-badge" style="color:#2563eb;"></i> Dr. ${esc(doctor)}</div>
                  <div><i class="bi bi-calendar3" style="color:#94a3b8;"></i> Ordered: ${ordered}</div>
                  ${range ? `<div style="color:#1d4ed8;font-weight:600;"><i class="bi bi-info-circle"></i> Ref: ${esc(range)}</div>` : ''}
                  ${unit  ? `<div style="color:#059669;font-weight:600;"><i class="bi bi-rulers"></i> Unit: ${esc(unit)}</div>` : ''}
                </div>
              </div>

              <!-- RIGHT: value input + checkbox + remarks -->
              <div style="padding:.85rem 1rem;display:flex;flex-direction:column;justify-content:center;gap:.5rem;">
                <label style="font-size:.7rem;font-weight:700;color:#475569;margin-bottom:.1rem;">Measured Value <span style="color:#ef4444;">*</span></label>
                <div style="display:flex;align-items:center;gap:.5rem;">
                  <!-- ✅ Checkbox confirm button -->
                  <button type="button"
                          id="chk_${gi}_${ti}"
                          onclick="toggleCheck(${gi},${ti})"
                          title="Mark as verified"
                          style="width:36px;height:36px;border-radius:8px;border:2px solid #e2e8f0;background:#f8fafc;
                                 display:flex;align-items:center;justify-content:center;cursor:pointer;
                                 flex-shrink:0;transition:all .15s;font-size:1.1rem;">
                    <i class="bi bi-check-lg" style="color:#94a3b8;"></i>
                  </button>
                  <!-- Value input -->
                  <div style="position:relative;flex:1;">
                    <input type="text"
                           id="result_${gi}_${ti}"
                           data-testid="${esc(t.test_id)}"
                           data-testname="${esc(t.test_name)}"
                           class="form-input result-val"
                           placeholder="${ph}"
                           oninput="onResultInput(${gi},${ti})"
                           style="font-size:1.05rem;font-weight:700;text-align:center;background:#f0fdf4;
                                  border-color:#86efac;padding-right:${unit?'3.2rem':'1rem'};">
                    ${unit ? `<span style="position:absolute;right:.65rem;top:50%;transform:translateY(-50%);
                              font-size:.75rem;font-weight:700;color:#64748b;pointer-events:none;">${esc(unit)}</span>` : ''}
                  </div>
                </div>
                <input type="text"
                       id="remarks_${gi}_${ti}"
                       class="form-input"
                       placeholder="Observations (optional)"
                       style="font-size:.78rem;">
                <input type="hidden" id="unit_${gi}_${ti}"  value="${esc(unit)}">
                <input type="hidden" id="range_${gi}_${ti}" value="${esc(range)}">
              </div>
            </div>`;
        }).join('');

        return `
        <div class="patient-batch-card" style="background:#fff;border-radius:16px;border:2px solid ${hasUrgent?'#fca5a5':'#e2e8f0'};margin-bottom:1.25rem;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.06);">

          <!-- Patient header -->
          <div style="background:linear-gradient(90deg,#1e3a8a,#2563eb);padding:1rem 1.25rem;display:flex;align-items:center;gap:1rem;">
            <div style="width:44px;height:44px;background:rgba(255,255,255,.15);border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
              <i class="bi bi-person-fill" style="color:#fff;font-size:1.3rem;"></i>
            </div>
            <div style="flex:1;">
              <div style="font-weight:800;font-size:1.05rem;color:#fff;">${esc(pName)}</div>
              <div style="display:flex;align-items:center;gap:.6rem;margin-top:.2rem;flex-wrap:wrap;">
                <span style="background:rgba(255,255,255,.2);color:#fff;border-radius:8px;padding:.15rem .65rem;font-family:monospace;font-size:.82rem;font-weight:700;">${esc(pId)}</span>
                <span style="color:#bfdbfe;font-size:.78rem;">${g.tests.length} test${g.tests.length>1?'s':''} ordered</span>
                ${hasUrgent ? '<span style="background:#dc2626;color:#fff;border-radius:99px;padding:.15rem .65rem;font-size:.7rem;font-weight:700;">🔴 URGENT</span>' : ''}
              </div>
            </div>
            <div style="text-align:right;flex-shrink:0;">
              <div style="font-size:.7rem;color:#93c5fd;font-weight:600;text-transform:uppercase;letter-spacing:.05em;">Batch Entry</div>
              <div style="font-size:.78rem;color:#bfdbfe;">Fill all → Submit once</div>
            </div>
          </div>

          <!-- Test rows -->
          <div style="padding:1rem 1.25rem 0;">
            ${testRows}
          </div>

          <!-- Submit all for this patient -->
          <div style="padding:.85rem 1.25rem;border-top:1px solid #f1f5f9;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.5rem;">
            <span style="font-size:.78rem;color:#64748b;">
              <i class="bi bi-info-circle"></i> Patient &amp; doctor notified automatically after submit
            </span>
            <button class="btn btn-primary submit-batch-btn"
                    data-gi="${gi}"
                    data-count="${g.tests.length}"
                    style="background:linear-gradient(90deg,#059669,#10b981);border:none;font-weight:700;">
              <i class="bi bi-check-circle-fill"></i>
              Submit All ${g.tests.length} Result${g.tests.length>1?'s':''} for ${esc(pName)}
            </button>
          </div>

          <!-- Per-patient result alert -->
          <div id="batchAlert_${gi}" style="display:none;padding:.5rem 1.25rem 1rem;"></div>
        </div>`;
    }).join('');

    // Bind submit buttons
    el.querySelectorAll('.submit-batch-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            submitBatch(parseInt(this.dataset.gi), parseInt(this.dataset.count));
        });
    });
}

// ── Checkbox toggle ─────────────────────────────────────────────────────────
function toggleCheck(gi, ti) {
    const btn   = document.getElementById(`chk_${gi}_${ti}`);
    const row   = document.getElementById(`row_${gi}_${ti}`);
    const input = document.getElementById(`result_${gi}_${ti}`);
    const val   = (input?.value || '').trim();
    if (!val) { input?.focus(); return; }
    const checked = btn.dataset.checked === '1';
    if (!checked) {
        btn.dataset.checked   = '1';
        btn.style.background  = '#059669';
        btn.style.borderColor = '#059669';
        btn.innerHTML         = '<i class="bi bi-check-lg" style="color:#fff;"></i>';
        if (row)   row.style.borderColor   = '#6ee7b7';
        if (input) { input.style.background = '#f0fdf4'; input.style.borderColor = '#22c55e'; }
    } else {
        btn.dataset.checked   = '0';
        btn.style.background  = '#f8fafc';
        btn.style.borderColor = '#e2e8f0';
        btn.innerHTML         = '<i class="bi bi-check-lg" style="color:#94a3b8;"></i>';
        if (row)   row.style.borderColor   = '#e2e8f0';
        if (input) { input.style.background = '#f0fdf4'; input.style.borderColor = '#86efac'; }
    }
}

function onResultInput(gi, ti) {
    const val = (document.getElementById(`result_${gi}_${ti}`)?.value || '').trim();
    const btn = document.getElementById(`chk_${gi}_${ti}`);
    if (val && btn?.dataset.checked !== '1') toggleCheck(gi, ti);
    if (!val && btn?.dataset.checked === '1') toggleCheck(gi, ti);
}

// ── Submit all results for one patient batch ──────────────────────────────────
async function submitBatch(gi, count) {
    const alertEl = document.getElementById(`batchAlert_${gi}`);
    const btn = document.querySelector(`.submit-batch-btn[data-gi="${gi}"]`);

    // Collect all result inputs for this group
    const entries = [];
    for (let ti = 0; ti < count; ti++) {
        const resultEl = document.getElementById(`result_${gi}_${ti}`);
        const val = (resultEl?.value || '').trim();
        if (!val) {
            alertEl.innerHTML = `<div class="alert alert-warning"><i class="bi bi-exclamation-triangle-fill"></i> Please fill all result values before submitting.</div>`;
            alertEl.style.display = '';
            resultEl?.focus();
            return;
        }
        entries.push({
            test_id:      resultEl.dataset.testid,
            test_name:    resultEl.dataset.testname,
            results:      val,
            unit:         document.getElementById(`unit_${gi}_${ti}`)?.value || '',
            normal_range: document.getElementById(`range_${gi}_${ti}`)?.value || '',
            remarks:      document.getElementById(`remarks_${gi}_${ti}`)?.value.trim() || '',
        });
    }

    btn.disabled = true;
    btn.innerHTML = `<i class="bi bi-hourglass-split"></i> Saving ${count} result${count>1?'s':''}...`;
    alertEl.style.display = 'none';

    let saved = 0, failed = [];

    for (const entry of entries) {
        try {
            const res  = await fetch('/api/labs/results', {
                method: 'POST', headers: authHeaders(),
                body: JSON.stringify({
                    test_id:      entry.test_id,
                    results:      entry.results,
                    unit:         entry.unit,
                    normal_range: entry.normal_range,
                    remarks:      entry.remarks,
                })
            });
            const data = await res.json();
            if (data.success) saved++;
            else failed.push(entry.test_name + ': ' + (data.message || 'failed'));
        } catch (e) {
            failed.push(entry.test_name + ': network error');
        }
    }

    if (failed.length === 0) {
        alertEl.innerHTML = `<div class="alert alert-success"><i class="bi bi-check-circle-fill"></i> <strong>All ${saved} result${saved>1?'s':''} saved.</strong> Patient &amp; doctor have been notified.</div>`;
        alertEl.style.display = '';
        // Remove this batch card after short delay
        setTimeout(() => {
            const card = btn.closest('.patient-batch-card');
            if (card) card.style.opacity = '0.4';
            loadPendingRequests();
        }, 1800);
    } else {
        alertEl.innerHTML = `<div class="alert alert-warning">
            <i class="bi bi-exclamation-triangle-fill"></i>
            ${saved} saved. ${failed.length} failed:<br><small>${failed.map(esc).join('<br>')}</small>
        </div>`;
        alertEl.style.display = '';
        btn.disabled = false;
        btn.innerHTML = `<i class="bi bi-arrow-repeat"></i> Retry Failed`;
    }
}

// ── Load pending tests ────────────────────────────────────────────────────────
async function loadPendingRequests() {
    try {
        const res  = await fetch('/api/labs/pending?limit=200', { headers: authHeaders() });
        if (res.status === 401) { logout(); return; }
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        _allTests = data.pending_tests || [];
        _testMap  = {};
        _allTests.forEach(t => { _testMap[t.test_id] = t; });

        // Auto-open single test from URL ?test_id=
        const urlTestId = new URLSearchParams(window.location.search).get('test_id');
        if (urlTestId && _testMap[urlTestId]) {
            // Scroll to that patient's batch card after render
            renderBatchList(_allTests);
            setTimeout(() => {
                const input = document.querySelector(`[data-testid="${urlTestId}"]`);
                if (input) {
                    input.closest('.patient-batch-card')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    input.focus();
                    input.style.boxShadow = '0 0 0 3px rgba(37,99,235,.4)';
                }
            }, 300);
        } else {
            renderBatchList(_allTests);
        }

    } catch (err) {
        document.getElementById('requestsList').innerHTML = `
            <div class="empty-state">
                <i class="bi bi-exclamation-circle" style="color:#dc2626;"></i>
                <p style="color:#dc2626;">Error: ${esc(err.message)}</p>
            </div>`;
    }
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('lab_technician');
    if (!user) return;

    const name = user.name || user.username;
    document.getElementById('topUserName').textContent = name;
    document.getElementById('userName').textContent    = name;

    loadPendingRequests();
});
