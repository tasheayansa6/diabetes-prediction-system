const token = () => localStorage.getItem('token');
function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }
function handleLogout() { if(typeof logout==='function') logout(); else { localStorage.clear(); window.location.href='/login'; } }

let allTests     = [];   // test types from API
let selectedIds  = [];   // checked test IDs

// ── Badges ────────────────────────────────────────────────────────────────────
function statusBadge(s) {
    const m = { pending:'badge-yellow', completed:'badge-green', cancelled:'badge-red', in_progress:'badge-cyan' };
    return `<span class="badge ${m[s]||'badge-gray'}">${(s||'').toUpperCase()}</span>`;
}
function priorityBadge(p) {
    return p === 'urgent'
        ? '<span class="badge badge-red">URGENT</span>'
        : '<span class="badge badge-gray">NORMAL</span>';
}

// ── Stats ─────────────────────────────────────────────────────────────────────
async function loadStats() {
    try {
        const r = await fetch('/api/doctor/lab-requests/statistics', { headers: { Authorization: 'Bearer ' + token() } });
        const d = await r.json();
        if (!d.success) return;
        document.getElementById('statPending').textContent   = d.statistics.by_status?.pending   ?? 0;
        document.getElementById('statCompleted').textContent = d.statistics.by_status?.completed ?? 0;
        document.getElementById('statCancelled').textContent = d.statistics.by_status?.cancelled ?? 0;
        document.getElementById('statTotal').textContent     = d.statistics.total_requests        ?? 0;
    } catch (_) {}
}

// ── Requests table ────────────────────────────────────────────────────────────
async function loadRequests() {
    const tbody  = document.getElementById('labRequestsTableBody');
    const errDiv = document.getElementById('errorAlert');
    const status = document.getElementById('filterStatus').value;
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-gray-400 py-4">Loading...</td></tr>';
    errDiv.style.display = 'none';
    try {
        const p = new URLSearchParams({ limit: 50 });
        if (status) p.append('status', status);
        const r = await fetch('/api/doctor/lab-requests?' + p, { headers: { Authorization: 'Bearer ' + token() } });
        const d = await r.json();
        if (!d.success) throw new Error(d.message);
        const rowsList = Array.isArray(d.lab_requests) ? d.lab_requests : [];
        const pag = d.pagination || { total: rowsList.length, offset: 0, limit: rowsList.length };
        if (!rowsList.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-gray-400 py-4">No lab requests found.</td></tr>';
        } else {
            // Sort based on filter dropdown
            const sortBy = document.getElementById('filterSort')?.value || 'date';
            const rows = [...rowsList];
            if (sortBy === 'priority') {
                rows.sort((a, b) => {
                    const order = { urgent: 0, normal: 1 };
                    const pa = order[a.priority] ?? 1;
                    const pb = order[b.priority] ?? 1;
                    if (pa !== pb) return pa - pb;
                    return new Date(b.requested_date) - new Date(a.requested_date);
                });
            }
            // 'date' is already newest-first from API
        tbody.innerHTML = rows.map(r => {
                const date     = r.requested_date ? new Date(r.requested_date) : null;
                const dateStr  = date ? date.toLocaleDateString('en-US', { year:'numeric', month:'short', day:'numeric' }) : 'N/A';
                const timeStr  = date ? date.toLocaleTimeString('en-US', { hour:'2-digit', minute:'2-digit' }) : '';
                return `
                <tr>
                    <td><small class="text-muted">${esc(r.request_id)}</small></td>
                    <td>${esc(r.patient_name)}</td>
                    <td>${esc(r.test_name)}</td>
                    <td>${priorityBadge(r.priority)}</td>
                    <td>
                        <div style="font-weight:600;font-size:.85rem;">${esc(dateStr)}</div>
                        <div style="font-size:.72rem;color:#94a3b8;">${esc(timeStr)}</div>
                    </td>
                    <td>${statusBadge(r.status)}</td>
                    <td>${r.results
                        ? `<span style="color:#059669;"><i class="bi bi-check-circle"></i> ${esc(String(r.results).substring(0,40))}</span>`
                        : '<span class="text-muted">Pending</span>'}</td>
                    <td>
                        ${r.status === 'pending' ? `
                        <div style="display:flex;gap:4px;">
                            <button class="btn btn-sm btn-danger" onclick="cancelRequest(${r.id})">
                                <i class="bi bi-x-circle"></i> Cancel
                            </button>
                        </div>` : '<span class="text-muted">—</span>'}
                    </td>
                </tr>`;
            }).join('');
        }
        const { total, offset, limit } = pag;
        document.getElementById('paginationInfo').textContent =
            `Showing ${Math.min(offset+1,total)}–${Math.min(offset+limit,total)} of ${total}`;
    } catch (err) {
        errDiv.textContent = err.message; errDiv.style.display = '';
    }
}

async function cancelRequest(id) {
    if (!confirm('Cancel this lab request?')) return;
    try {
        const r = await fetch(`/api/doctor/lab-requests/${id}/cancel`, {
            method: 'PUT', headers: { Authorization: 'Bearer ' + token() }
        });
        const d = await r.json();
        if (!d.success) throw new Error(d.message);
        loadRequests(); loadStats();
    } catch (err) { alert('Error: ' + err.message); }
}

// ── Load patients ─────────────────────────────────────────────────────────────
async function loadPatients() {
    const sel = document.getElementById('modal_patient_id');
    try {
        const r = await fetch('/api/doctor/patients?limit=100', { headers: { Authorization: 'Bearer ' + token() } });
        const d = await r.json();
        if (!d.success) throw new Error(d.message);
        sel.innerHTML = '<option value="">Select patient...</option>';
        d.patients.forEach(p => {
            const o = document.createElement('option');
            o.value = p.id;
            o.textContent = `${p.username} (${p.patient_id || 'ID:'+p.id})`;
            sel.appendChild(o);
        });
        const pre = new URLSearchParams(window.location.search).get('patient_id');
        if (pre) {
            sel.value = pre;
            if (sel.value) {
                openModal();
            }
        }
    } catch (err) { sel.innerHTML = `<option value="">Error: ${err.message}</option>`; }
}

// ── Load test types & render checkboxes ───────────────────────────────────────
async function loadTestTypes() {
    const grid = document.getElementById('testGrid');
    try {
        const r = await fetch('/api/doctor/test-types', { headers: { Authorization: 'Bearer ' + token() } });
        const d = await r.json();
        if (!d.success) throw new Error(d.message);
        allTests = d.test_types;
        renderCheckboxes('');
    } catch (err) {
        grid.innerHTML = `<div style="grid-column:1/-1;color:#ef4444;padding:1rem;font-size:.82rem;">
            Error loading tests: ${esc(err.message)}</div>`;
    }
}

function renderCheckboxes(filter) {
    const grid = document.getElementById('testGrid');
    if (!allTests.length) {
        grid.innerHTML = '<div style="grid-column:1/-1;color:#94a3b8;padding:1rem;text-align:center;">No test types found.</div>';
        return;
    }

    const q = (filter || '').toLowerCase();
    const filtered = q ? allTests.filter(t =>
        t.test_name.toLowerCase().includes(q) ||
        t.test_code.toLowerCase().includes(q) ||
        (t.category || '').toLowerCase().includes(q)
    ) : allTests;

    if (!filtered.length) {
        grid.innerHTML = '<div style="grid-column:1/-1;color:#94a3b8;padding:1rem;text-align:center;">No tests match your search.</div>';
        return;
    }

    // Group by category
    const groups = {};
    filtered.forEach(t => { (groups[t.category] = groups[t.category]||[]).push(t); });

    const catIcons = {
        'Diabetes': 'bi-droplet-fill',
        'Cardiology': 'bi-heart-pulse-fill',
        'Nephrology': 'bi-funnel-fill',
        'Hematology': 'bi-activity',
        'Hepatology': 'bi-shield-fill',
        'Endocrinology': 'bi-thermometer-half',
        'Electrolytes': 'bi-lightning-fill',
        'Immunology': 'bi-shield-check',
        'Urology': 'bi-droplet-half',
    };

    let html = '';
    Object.entries(groups).forEach(([cat, tests]) => {
        const icon = catIcons[cat] || 'bi-flask-fill';
        html += `<div class="cat-header"><i class="bi ${icon}"></i> ${cat}</div>`;
        tests.forEach(t => {
            const isChecked = selectedIds.includes(t.id);
            html += `
            <div class="test-item${isChecked ? ' active' : ''}" id="ti-${t.id}" onclick="toggleTest(${t.id})">
                <input type="checkbox" id="chk-${t.id}" ${isChecked ? 'checked' : ''} onclick="event.stopPropagation();toggleTest(${t.id})">
                <div style="flex:1;min-width:0;">
                    <div class="ti-name">${esc(t.test_name)}</div>
                    <div class="ti-code">${esc(t.test_code)}</div>
                    <div class="ti-cost">ETB ${(t.cost||0).toFixed(0)}</div>
                </div>
            </div>`;
        });
    });
    grid.innerHTML = html;
}

function filterTests(q) {
    renderCheckboxes(q);
}

function toggleTest(id) {
    const chk  = document.getElementById('chk-' + id);
    const item = document.getElementById('ti-' + id);
    chk.checked = !chk.checked;
    if (chk.checked) {
        item.classList.add('active');
        if (!selectedIds.includes(id)) selectedIds.push(id);
    } else {
        item.classList.remove('active');
        selectedIds = selectedIds.filter(x => x !== id);
    }
    updateDetail();
    updateSummary();
}

// Auto-fill detail panel with last selected test
function updateDetail() {
    const box = document.getElementById('detailBox');
    if (!selectedIds.length) {
        box.className = 'detail-box';
        box.innerHTML = '<span style="color:#94a3b8;">Select a test to see details</span>';
        return;
    }
    const t = allTests.find(x => x.id === selectedIds[selectedIds.length - 1]);
    if (!t) return;
    box.className = 'detail-box filled';
    box.innerHTML = `
        <div style="font-weight:800;font-size:.85rem;color:#1565c0;margin-bottom:8px;">
            <i class="bi bi-flask-fill"></i> ${esc(t.test_name)}
        </div>
        <div class="drow"><span class="dlbl">Code</span><span class="dval">${esc(t.test_code)}</span></div>
        <div class="drow"><span class="dlbl">Category</span><span class="dval">${esc(t.category)}</span></div>
        <div class="drow"><span class="dlbl">Cost</span><span class="dval" style="color:#059669;">ETB ${(t.cost||0).toFixed(2)}</span></div>
        ${t.normal_range ? `<div class="drow"><span class="dlbl">Normal Range</span><span class="dval">${esc(t.normal_range)}</span></div>` : ''}
        ${t.preparation_instructions ? `
        <div style="margin-top:8px;padding:8px;background:#fff;border-radius:8px;border:1px solid #bfdbfe;">
            <div style="font-size:.7rem;font-weight:700;color:#1565c0;margin-bottom:3px;">
                <i class="bi bi-clipboard-check"></i> Preparation Instructions
            </div>
            <div style="font-size:.78rem;color:#334155;line-height:1.5;">${esc(t.preparation_instructions)}</div>
        </div>` : ''}`;
}

// Update selected summary
function updateSummary() {
    const box   = document.getElementById('summaryBox');
    const total = document.getElementById('totalCostLine');
    const sel   = allTests.filter(t => selectedIds.includes(t.id));
    if (!sel.length) {
        box.innerHTML = '<span style="color:#94a3b8;">No tests selected</span>';
        total.textContent = '';
        return;
    }
    const sum = sel.reduce((s, t) => s + (t.cost||0), 0);
    box.innerHTML = sel.map(t =>
        `<div class="srow">
            <span style="font-weight:600;color:#1e293b;">${esc(t.test_name)}</span>
            <span style="color:#059669;font-weight:700;">ETB ${(t.cost||0).toFixed(2)}</span>
        </div>`
    ).join('');
    total.textContent = `Total: ETB ${sum.toFixed(2)} (${sel.length} test${sel.length>1?'s':''})`;
}

// ── Modal open/close ──────────────────────────────────────────────────────────
function openModal() {
    selectedIds = [];
    document.querySelectorAll('.test-item').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.test-item input').forEach(el => el.checked = false);
    const search = document.getElementById('testSearch');
    if (search) search.value = '';
    renderCheckboxes('');
    updateDetail(); updateSummary();
    document.getElementById('modal_notes').value = '';
    document.getElementById('modalAlert').style.display = 'none';
    document.getElementById('newRequestModal').style.display = 'flex';
}
function closeModal() { document.getElementById('newRequestModal').style.display = 'none'; }

// ── Submit ────────────────────────────────────────────────────────────────────
async function handleSubmit(e) {
    e.preventDefault();
    const patientId = document.getElementById('modal_patient_id').value;
    const priority  = document.getElementById('priority').value;
    const notes     = document.getElementById('modal_notes').value.trim();
    const alertEl   = document.getElementById('modalAlert');
    const btn       = document.getElementById('submitBtn');

    if (!patientId) {
        alertEl.className='alert alert-danger'; alertEl.textContent='Please select a patient.'; alertEl.style.display=''; return;
    }
    if (!selectedIds.length) {
        alertEl.className='alert alert-danger'; alertEl.textContent='Please select at least one test.'; alertEl.style.display=''; return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Creating...';

    const sel = allTests.filter(t => selectedIds.includes(t.id));
    const errors = [];

    for (const t of sel) {
        try {
            const r = await fetch('/api/doctor/lab-requests', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token() },
                body: JSON.stringify({
                    patient_id:    parseInt(patientId),
                    test_name:     t.test_name,
                    test_type:     t.test_code,
                    test_category: t.category,
                    priority,
                    notes: notes || `Ordered: ${t.test_name}`
                })
            });
            const d = await r.json();
            if (!d.success) errors.push(`${t.test_name}: ${d.message}`);
        } catch (err) { errors.push(`${t.test_name}: ${err.message}`); }
    }

    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-plus-circle"></i> Create Lab Request';

    if (errors.length) {
        alertEl.className = 'alert alert-danger';
        alertEl.textContent = 'Errors: ' + errors.join(' | ');
        alertEl.style.display = '';
    } else {
        alertEl.className = 'alert alert-success';
        alertEl.textContent = `${sel.length} lab request${sel.length>1?'s':''} created successfully!`;
        alertEl.style.display = '';
        setTimeout(() => { closeModal(); loadRequests(); loadStats(); }, 1400);
    }
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('doctor');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    const sb = document.getElementById('sidebarDoctorName');
    if (sb) sb.textContent = user.name || user.username;
    document.getElementById('labRequestForm').addEventListener('submit', handleSubmit);
    loadPatients();
    loadTestTypes();
    loadRequests();
    loadStats();
});
