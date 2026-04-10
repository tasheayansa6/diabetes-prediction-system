let currentOffset = 0;
const PAGE_SIZE = 20;

function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }

function handleLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/';
}

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

    spinner.style.display    = '';
    errorAlert.style.display = 'none';
    tbody.innerHTML = '';

    try {
        const token  = localStorage.getItem('token');
        const params = new URLSearchParams({ limit: PAGE_SIZE, offset: currentOffset });
        if (search) params.append('search', search);

        const res  = await fetch('/api/doctor/patients?' + params, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
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
                        <button class="btn btn-sm btn-outline quick-approve-btn" data-patient-id="${p.id}" style="margin-left:4px;">
                            <i class="bi bi-check2-circle"></i> Approve ML
                        </button>
                        <button class="btn btn-sm btn-outline quick-followup-btn" data-patient-id="${p.id}" style="margin-left:4px;">
                            <i class="bi bi-exclamation-circle"></i> Needs Follow-up
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
        errorAlert.style.display = '';
    } finally {
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
