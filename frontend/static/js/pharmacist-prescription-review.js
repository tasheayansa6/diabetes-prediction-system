const API = '/api/pharmacy';
const authHeaders = () => ({ 'Authorization': 'Bearer ' + localStorage.getItem('token') });

const statusBadge = s => {
    const map = { pending:'badge-yellow', pending_pharmacist:'badge-yellow', verified:'badge-cyan', dispensed:'badge-green', rejected:'badge-red' };
    return `<span class="badge ${map[s]||'badge-gray'}">${s.replace('_',' ').toUpperCase()}</span>`;
};

async function loadPrescriptions(status = '') {
    const tbody = document.getElementById('prescriptionsTable');
    tbody.innerHTML = '<tr><td colspan="7" class="text-center">Loading...</td></tr>';
    try {
        const url = status ? `${API}/prescriptions?status=${status}` : `${API}/prescriptions`;
        const res = await fetch(url, { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        const list = data.prescriptions;
        if (!list.length) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No prescriptions found.</td></tr>';
            return;
        }
        tbody.innerHTML = list.map(p => `
            <tr>
                <td>${p.prescription_id || p.id}</td>
                <td>${p.patient?.name || '—'}</td>
                <td>${p.medication}</td>
                <td>${p.doctor?.name || '—'}</td>
                <td>${p.created_at ? p.created_at.split('T')[0] : '—'}</td>
                <td>${statusBadge(p.status)}</td>
                <td>
                    <a href="/templates/pharmacist/dispense_medication.html?id=${p.id}" class="btn btn-sm btn-primary">
                        <i class="bi bi-eye"></i> View
                    </a>
                </td>
            </tr>`).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-danger text-center">${err.message}</td></tr>`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const user = checkAuth('pharmacist');
    if (!user) return;
    const name = user.name || user.username;
    document.getElementById('navUserName').textContent = name;
    const sb = document.getElementById('sidebarName');
    if (sb) sb.textContent = name;

    // Filter buttons
    document.querySelectorAll('[data-filter]').forEach(btn =>
        btn.addEventListener('click', () => {
            document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadPrescriptions(btn.dataset.filter);
        })
    );
    loadPrescriptions();
});
