let currentOffset = 0;
const PAGE_SIZE = 20;

function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }

function handleLogout() { if(typeof logout==='function') logout(); else { localStorage.clear(); window.location.href='/login'; } }

async function getLatestPrediction(patientId) {
    const token = localStorage.getItem('token');
    const res = await fetch(`/api/doctor/patients/${patientId}/predictions?limit=1`, {
        headers: { 'Authorization': 'Bearer ' + token }
    });
    const data = await res.json();
    if (!data.success || !data.predictions || !data.predictions.length) return null;
    return data.predictions[0];
}

async function quickReview(patientId, status) {
    try {
        const latest = await getLatestPrediction(patientId);
        if (!latest) {
            alert('No prediction found for this patient.');
            return;
        }

        const summary = window.prompt(
            `Enter review summary (${status.replace('_', ' ')}):`,
            status === 'approved'
                ? 'Reviewed and approved. Continue current care plan and follow routine follow-up.'
                : 'Needs follow-up visit and confirmatory tests.'
        );
        if (!summary || !summary.trim()) return;

        const token = localStorage.getItem('token');
        const payload = { status, summary: summary.trim() };
        const reviewUrl = `/api/doctor/predictions/${latest.id}/review`;
        const res = await fetch(reviewUrl, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify(payload)
        });
        let data = null;
        try { data = await res.json(); } catch (_) {}

        // Fallback path: if review endpoint is unavailable, store equivalent review as doctor note.
        if (res.status === 404) {
            const noteRes = await fetch('/api/doctor/notes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + token
                },
                body: JSON.stringify({
                    patient_id: parseInt(patientId, 10),
                    title: `Prediction Review #${latest.id}`,
                    content: `status:${status}\nsummary:${summary.trim()}`,
                    category: 'prediction_review',
                    is_important: status === 'rejected' || status === 'needs_followup'
                })
            });
            let noteData = null;
            try { noteData = await noteRes.json(); } catch (_) {}
            if (!noteRes.ok || !noteData || !noteData.success) {
                throw new Error((noteData && noteData.message) || 'Failed to save review fallback note');
            }
            alert('Prediction review saved (fallback mode).');
            return;
        }

        if (!res.ok || !data || !data.success) throw new Error((data && data.message) || 'Failed to save review');
        alert('Prediction review saved.');
    } catch (err) {
        alert('Error: ' + err.message);
    }
}

async function loadPatients() {
    const search     = document.getElementById('searchInput').value.trim();
    const tbody      = document.getElementById('patientTableBody');
    const spinner    = document.getElementById('loadingSpinner');
    const errorAlert = document.getElementById('errorAlert');

    // Tailwind's .hidden uses display:none !important — toggle class, not inline style only
    spinner.classList.remove('hidden');
    errorAlert.classList.add('hidden');
    errorAlert.style.display = 'none';
    tbody.innerHTML = '';

    try {
        const token  = localStorage.getItem('token');
        const params = new URLSearchParams({ limit: PAGE_SIZE, offset: currentOffset });
        if (search) params.append('search', search);

        const res  = await fetch('/api/doctor/patients?' + params, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        // Handle 401 — token expired
        if (res.status === 401) {
            if (typeof _clearAllStorage === 'function') _clearAllStorage();
            else { localStorage.removeItem('token'); localStorage.removeItem('user'); }
            window.location.href = '/login?reason=session_expired';
            return;
        }
        
        const data = await res.json();
        if (!data.success) throw new Error(data.message || 'Failed to load patients');

        if (!data.patients.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No patients found.</td></tr>';
        } else {
            tbody.innerHTML = data.patients.map(p => `
                <tr>
                    <td><span class="badge badge-blue">${esc(p.patient_id || 'N/A')}</span></td>
                    <td>${esc(p.username)}</td>
                    <td>${esc(p.email)}</td>
                    <td>${p.created_at ? new Date(p.created_at).toLocaleDateString() : 'N/A'}</td>
                    <td>
                        <a href="/templates/doctor/diagnosis.html?patient_id=${p.id}" class="btn btn-sm btn-primary">
                            <i class="bi bi-clipboard-pulse"></i> Diagnose
                        </a>
                        <a href="/templates/doctor/prescribe_medication.html?patient_id=${p.id}" class="btn btn-sm btn-success" style="margin-left:4px;">
                            <i class="bi bi-capsule"></i> Prescribe
                        </a>
                        <a href="/templates/doctor/lab_requests.html?patient_id=${p.id}" class="btn btn-sm btn-outline" style="margin-left:4px;">
                            <i class="bi bi-flask"></i> Lab Test
                        </a>
                        <button class="btn btn-sm btn-outline quick-approve-btn" data-patient-id="${p.id}" style="margin-left:4px;">
                            <i class="bi bi-check2-circle"></i> Approve ML
                        </button>
                        <button class="btn btn-sm btn-outline quick-followup-btn" data-patient-id="${p.id}" style="margin-left:4px;">
                            <i class="bi bi-exclamation-circle"></i> Needs Follow-up
                        </button>
                        <button class="btn btn-sm btn-outline" style="margin-left:4px;color:#0891b2;border-color:#bae6fd;" onclick="openMessageModal(${p.id},'${p.username.replace(/'/g,\"\\'\")}')"
                            title="Send message to patient">
                            <i class="bi bi-chat-dots"></i> Message
                        </button>
                    </td>
                </tr>
            `).join('');

            tbody.querySelectorAll('.quick-approve-btn').forEach(btn => {
                btn.addEventListener('click', function () {
                    quickReview(this.dataset.patientId, 'approved');
                });
            });
            tbody.querySelectorAll('.quick-followup-btn').forEach(btn => {
                btn.addEventListener('click', function () {
                    quickReview(this.dataset.patientId, 'needs_followup');
                });
            });
        }

        const { total, offset, limit } = data.pagination;
        document.getElementById('paginationInfo').textContent =
            `Showing ${offset + 1}–${Math.min(offset + limit, total)} of ${total} patients`;

    } catch (err) {
        errorAlert.textContent   = err.message;
        errorAlert.classList.remove('hidden');
        errorAlert.style.display = 'block';
    } finally {
        spinner.classList.add('hidden');
        spinner.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('doctor');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    const sb = document.getElementById('sidebarDoctorName');
    if (sb) sb.textContent = user.name || user.username;

    document.getElementById('searchInput').addEventListener('keydown', e => {
        if (e.key === 'Enter') loadPatients();
    });
    loadPatients();
});

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
                    <textarea id="msgContent" class="form-input" rows="4" placeholder="Type your message to the patient..."
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
    setTimeout(() => document.getElementById('msgContent').focus(), 100);
}

async function sendMessage() {
    const content = (document.getElementById('msgContent').value || '').trim();
    const alertEl = document.getElementById('msgAlert');
    if (!content) {
        alertEl.innerHTML = '<div class="alert alert-warning">Please enter a message.</div>';
        return;
    }
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
        alertEl.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-send"></i> Send';
    }
}
