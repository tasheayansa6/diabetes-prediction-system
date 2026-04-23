let currentOffset = 0;
const PAGE_SIZE = 20;
let totalPatients = 0;

function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }
function handleLogout() { if(typeof logout==='function') logout(); else { localStorage.clear(); window.location.href='/login'; } }

// ── Load patients ─────────────────────────────────────────────────────────────
async function loadPatients(offset) {
    if (offset !== undefined) currentOffset = offset;

    const search     = (document.getElementById('searchInput')?.value || '').trim();
    const tbody      = document.getElementById('patientTableBody');
    const errorAlert = document.getElementById('errorAlert');
    const spinner    = document.getElementById('loadingSpinner');

    // Show spinner, hide error
    if (spinner)    { spinner.style.display = 'block'; spinner.classList.remove('hidden'); }
    if (errorAlert) { errorAlert.style.display = 'none'; errorAlert.classList.add('hidden'); }
    if (tbody)      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:2rem;color:#94a3b8;">Loading patients...</td></tr>';

    try {
        const token  = localStorage.getItem('token');
        if (!token) { window.location.href = '/login'; return; }

        const params = new URLSearchParams({ limit: PAGE_SIZE, offset: currentOffset });
        if (search) params.append('search', search);

        const res = await fetch('/api/doctor/patients?' + params, {
            headers: { 'Authorization': 'Bearer ' + token }
        });

        // Handle auth errors
        if (res.status === 401 || res.status === 403) {
            if (typeof _clearAllStorage === 'function') _clearAllStorage();
            else { localStorage.removeItem('token'); localStorage.removeItem('user'); }
            window.location.href = '/login?reason=session_expired';
            return;
        }

        let data;
        try { data = await res.json(); }
        catch (e) { throw new Error('Server returned invalid response (HTTP ' + res.status + ')'); }

        if (!data.success) throw new Error(data.message || 'Failed to load patients');

        totalPatients = data.pagination?.total || 0;
        const tc = document.getElementById('totalCount');
        if (tc) tc.textContent = totalPatients;
        renderPatients(data.patients || []);
        renderPagination(data.pagination);

    } catch (err) {
        if (tbody) tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:2rem;color:#dc2626;">' +
            '<i class="bi bi-exclamation-triangle-fill" style="margin-right:6px;"></i>' + esc(err.message) + '</td></tr>';
        if (errorAlert) {
            errorAlert.textContent = err.message;
            errorAlert.style.display = 'block';
            errorAlert.classList.remove('hidden');
        }
    } finally {
        if (spinner) { spinner.style.display = 'none'; spinner.classList.add('hidden'); }
    }
}

// ── Render patients table ─────────────────────────────────────────────────────
function renderPatients(patients) {
    const tbody = document.getElementById('patientTableBody');
    if (!tbody) return;

    if (!patients.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:2rem;color:#94a3b8;">' +
            '<i class="bi bi-people" style="font-size:1.5rem;display:block;margin-bottom:.5rem;"></i>' +
            'No patients found.</td></tr>';
        return;
    }

    tbody.innerHTML = patients.map(p => `
        <tr id="patient-row-${p.id}" style="${window._highlightPatientId == p.id ? 'background:#eff6ff;border-left:4px solid #2563eb;' : ''}">
            <td><span class="badge badge-blue">${esc(p.patient_id || 'N/A')}</span></td>
            <td><strong>${esc(p.username)}</strong></td>
            <td style="color:#64748b;">${esc(p.email)}</td>
            <td style="color:#64748b;font-size:.82rem;">${p.created_at ? new Date(p.created_at).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}) : 'N/A'}</td>
            <td>
                <div style="display:flex;gap:4px;flex-wrap:wrap;">
                    <a href="/templates/doctor/diagnosis.html?patient_id=${p.id}" class="btn btn-sm btn-primary" title="Diagnose">
                        <i class="bi bi-clipboard-pulse"></i> Diagnose
                    </a>
                    <a href="/templates/doctor/prescribe_medication.html?patient_id=${p.id}" class="btn btn-sm btn-success" title="Prescribe">
                        <i class="bi bi-capsule"></i> Prescribe
                    </a>
                    <a href="/templates/doctor/lab_requests.html?patient_id=${p.id}" class="btn btn-sm btn-outline" title="Lab Test">
                        <i class="bi bi-flask"></i> Lab
                    </a>
                    <button class="btn btn-sm btn-outline quick-approve-btn" data-patient-id="${p.id}" title="Approve ML Prediction">
                        <i class="bi bi-check2-circle"></i> Approve ML
                    </button>
                    <button class="btn btn-sm btn-outline" style="color:#0891b2;border-color:#bae6fd;"
                        onclick="openMessageModal(${p.id},'${esc(p.username).replace(/'/g,"\\'")}')">
                        <i class="bi bi-chat-dots"></i> Message
                    </button>
                </div>
            </td>
        </tr>
    `).join('');

    // Bind approve buttons
    tbody.querySelectorAll('.quick-approve-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            quickReview(this.dataset.patientId, 'approved');
        });
    });

    // Scroll to highlighted patient if coming from notification
    if (window._highlightPatientId) {
        const row = document.getElementById('patient-row-' + window._highlightPatientId);
        if (row) {
            setTimeout(() => {
                row.scrollIntoView({ behavior: 'smooth', block: 'center' });
                // Show banner
                const banner = document.getElementById('notifBanner');
                if (banner) banner.style.display = '';
            }, 300);
        } else {
            // Patient not on this page — show banner anyway
            const banner = document.getElementById('notifBanner');
            if (banner) banner.style.display = '';
        }
    }
}

// ── Render pagination ─────────────────────────────────────────────────────────
function renderPagination(pagination) {
    const info = document.getElementById('paginationInfo');
    if (!info || !pagination) return;

    const { total, limit, offset } = pagination;
    if (!total) { info.innerHTML = ''; return; }

    const start = offset + 1;
    const end   = Math.min(offset + limit, total);
    const hasPrev = offset > 0;
    const hasNext = (offset + limit) < total;

    info.innerHTML = `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:.75rem 0;flex-wrap:wrap;gap:.5rem;">
            <span style="font-size:.82rem;color:#64748b;">
                Showing <strong>${start}–${end}</strong> of <strong>${total}</strong> patients
            </span>
            <div style="display:flex;gap:.4rem;">
                <button class="btn btn-sm btn-secondary" ${hasPrev ? '' : 'disabled'}
                    onclick="loadPatients(${Math.max(0, offset - limit)})">
                    <i class="bi bi-chevron-left"></i> Prev
                </button>
                <button class="btn btn-sm btn-secondary" ${hasNext ? '' : 'disabled'}
                    onclick="loadPatients(${offset + limit})">
                    Next <i class="bi bi-chevron-right"></i>
                </button>
            </div>
        </div>`;
}

// ── Quick ML review ───────────────────────────────────────────────────────────
async function getLatestPrediction(patientId) {
    const res = await fetch(`/api/doctor/patients/${patientId}/predictions?limit=1`, {
        headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
    });
    const data = await res.json();
    if (!data.success || !data.predictions?.length) return null;
    return data.predictions[0];
}

async function quickReview(patientId, status) {
    try {
        const latest = await getLatestPrediction(patientId);
        if (!latest) { alert('No prediction found for this patient.'); return; }

        const summary = window.prompt(
            `Enter review summary (${status.replace('_', ' ')}):`,
            status === 'approved'
                ? 'Reviewed and approved. Continue current care plan.'
                : 'Needs follow-up visit and confirmatory tests.'
        );
        if (!summary?.trim()) return;

        const res = await fetch(`/api/doctor/predictions/${latest.id}/review`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token') },
            body: JSON.stringify({ status, summary: summary.trim() })
        });
        const data = await res.json();

        // Fallback to note if review endpoint unavailable
        if (res.status === 404) {
            const noteRes = await fetch('/api/doctor/notes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token') },
                body: JSON.stringify({
                    patient_id: parseInt(patientId, 10),
                    title: `Prediction Review #${latest.id}`,
                    content: `status:${status}\nsummary:${summary.trim()}`,
                    category: 'prediction_review',
                    is_important: status === 'rejected' || status === 'needs_followup'
                })
            });
            const noteData = await noteRes.json();
            if (!noteRes.ok || !noteData.success) throw new Error(noteData.message || 'Failed to save review');
            alert('Prediction review saved.');
            return;
        }

        if (!data.success) throw new Error(data.message || 'Failed to save review');
        alert('Prediction review saved.');
    } catch (err) {
        alert('Error: ' + err.message);
    }
}

// ── Doctor → Patient Message Modal ───────────────────────────────────────────
let _msgPatientId = null;

function openMessageModal(patientId, patientName) {
    _msgPatientId = patientId;
    let modal = document.getElementById('msgModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'msgModal';
        modal.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(15,23,42,.5);z-index:1000;align-items:center;justify-content:center;padding:1rem;';
        modal.innerHTML = `
            <div style="background:#fff;border-radius:18px;width:100%;max-width:480px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.2);">
                <div style="background:linear-gradient(90deg,#0891b2,#38bdf8);color:#fff;padding:1.1rem 1.5rem;display:flex;align-items:center;justify-content:space-between;">
                    <h5 style="margin:0;font-weight:700;"><i class="bi bi-chat-dots"></i> Message Patient</h5>
                    <button onclick="document.getElementById('msgModal').style.display='none'" style="background:none;border:none;color:#fff;font-size:1.4rem;cursor:pointer;">&times;</button>
                </div>
                <div style="padding:1.5rem;">
                    <p style="font-size:.875rem;color:#64748b;margin-bottom:1rem;">To: <strong id="msgPatientName"></strong></p>
                    <textarea id="msgContent" class="form-input" rows="4" placeholder="Type your message..."
                        style="width:100%;resize:vertical;"></textarea>
                    <div id="msgAlert" style="margin-top:.75rem;"></div>
                </div>
                <div style="padding:1rem 1.5rem;border-top:1px solid #f1f5f9;display:flex;gap:.75rem;justify-content:flex-end;">
                    <button class="btn btn-secondary" onclick="document.getElementById('msgModal').style.display='none'">Cancel</button>
                    <button class="btn btn-primary" onclick="sendMessage()" id="msgSendBtn"><i class="bi bi-send"></i> Send</button>
                </div>
            </div>`;
        document.body.appendChild(modal);
    }
    document.getElementById('msgPatientName').textContent = patientName;
    document.getElementById('msgContent').value = '';
    document.getElementById('msgAlert').innerHTML = '';
    modal.style.display = 'flex';
    setTimeout(() => document.getElementById('msgContent')?.focus(), 100);
}

async function sendMessage() {
    const content = (document.getElementById('msgContent')?.value || '').trim();
    const alertEl = document.getElementById('msgAlert');
    if (!content) { alertEl.innerHTML = '<div class="alert alert-warning">Please enter a message.</div>'; return; }

    const btn = document.getElementById('msgSendBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Sending...';

    try {
        const res = await fetch('/api/doctor/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token') },
            body: JSON.stringify({ patient_id: _msgPatientId, content })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        alertEl.innerHTML = '<div class="alert alert-success"><i class="bi bi-check-circle-fill"></i> Message sent!</div>';
        setTimeout(() => { document.getElementById('msgModal').style.display = 'none'; }, 1200);
    } catch (e) {
        alertEl.innerHTML = `<div class="alert alert-danger">${esc(e.message)}</div>`;
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-send"></i> Send';
    }
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('doctor');
    if (!user) return;

    document.getElementById('navUserName').textContent = user.name || user.username;
    const sb = document.getElementById('sidebarDoctorName');
    if (sb) sb.textContent = user.name || user.username;

    // Pre-fill search if ?highlight=<patient_id> from nurse vitals notification
    const urlParams = new URLSearchParams(window.location.search);
    const highlightId = urlParams.get('highlight');
    if (highlightId) {
        window._highlightPatientId = parseInt(highlightId, 10);
        // Search by patient DB id so they always appear on page 1
        const si = document.getElementById('searchInput');
        if (si) si.value = highlightId;
    }

    // Search on Enter
    document.getElementById('searchInput')?.addEventListener('keydown', e => {
        if (e.key === 'Enter') loadPatients(0);
    });

    loadPatients(0);
});
