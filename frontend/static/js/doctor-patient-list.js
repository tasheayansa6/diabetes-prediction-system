let currentOffset = 0;
const PAGE_SIZE = 20;

function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }

function handleLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/';
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
                    </td>
                </tr>
            `).join('');
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
