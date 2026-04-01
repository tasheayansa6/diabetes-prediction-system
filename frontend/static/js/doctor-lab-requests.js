const token = () => localStorage.getItem('token');

function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }

function handleLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/';
}

function statusBadge(status) {
    const map = { pending:'badge-yellow', completed:'badge-green', cancelled:'badge-red', in_progress:'badge-cyan' };
    return `<span class="badge ${map[status] || 'badge-gray'}">${status.toUpperCase()}</span>`;
}

function priorityBadge(priority) {
    return priority === 'urgent'
        ? '<span class="badge badge-red">URGENT</span>'
        : '<span class="badge badge-gray">NORMAL</span>';
}

async function loadStats() {
    try {
        const res  = await fetch('/api/doctor/lab-requests/statistics', {
            headers: { 'Authorization': 'Bearer ' + token() }
        });
        const data = await res.json();
        if (!data.success) return;
        const s = data.statistics;
        document.getElementById('statPending').textContent   = s.by_status?.pending   ?? 0;
        document.getElementById('statCompleted').textContent = s.by_status?.completed ?? 0;
        document.getElementById('statCancelled').textContent = s.by_status?.cancelled ?? 0;
        document.getElementById('statTotal').textContent     = s.total_requests        ?? 0;
    } catch (_) {}
}

async function loadRequests() {
    const tbody   = document.getElementById('labRequestsTableBody');
    const spinner = document.getElementById('loadingSpinner');
    const errDiv  = document.getElementById('errorAlert');
    const status  = document.getElementById('filterStatus').value;

    spinner.style.display = '';
    errDiv.style.display  = 'none';
    tbody.innerHTML = '';

    try {
        const params = new URLSearchParams({ limit: 50 });
        if (status) params.append('status', status);

        const res  = await fetch('/api/doctor/lab-requests?' + params, {
            headers: { 'Authorization': 'Bearer ' + token() }
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        if (!data.lab_requests.length) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">No lab requests found.</td></tr>';
        } else {
            tbody.innerHTML = data.lab_requests.map(r => `
                <tr>
                    <td><small class="text-muted">${esc(r.request_id)}</small></td>
                    <td>${esc(r.patient_name)}</td>
                    <td>${esc(r.test_name)}</td>
                    <td>${priorityBadge(r.priority)}</td>
                    <td>${r.requested_date ? new Date(r.requested_date).toLocaleDateString() : 'N/A'}</td>
                    <td>${statusBadge(r.status)}</td>
                    <td>${r.results
                        ? `<span style="color:#059669;"><i class="bi bi-check-circle"></i> ${esc(r.results)}</span>`
                        : '<span class="text-muted">Pending</span>'}</td>
                    <td>
                        <div style="display:flex;gap:4px;flex-wrap:wrap;">
                        ${r.status === 'pending'
                            ? `<button class="btn btn-sm btn-danger" onclick="cancelRequest(${r.id})">
                                <i class="bi bi-x-circle"></i> Cancel
                               </button>
                               <a href="/templates/payment/payment_page.html?service=lab&lab_request_id=${r.id}" class="btn btn-sm btn-success">
                                <i class="bi bi-credit-card"></i> Pay
                               </a>`
                            : '<span class="text-muted">—</span>'}
                        </div>
                    </td>
                </tr>
            `).join('');
        }

        const { total, offset, limit } = data.pagination;
        document.getElementById('paginationInfo').textContent =
            `Showing ${Math.min(offset + 1, total)}–${Math.min(offset + limit, total)} of ${total} requests`;

    } catch (err) {
        errDiv.textContent   = err.message;
        errDiv.style.display = '';
    } finally {
        spinner.style.display = 'none';
    }
}

async function cancelRequest(id) {
    if (!confirm('Cancel this lab request?')) return;
    try {
        const res  = await fetch(`/api/doctor/lab-requests/${id}/cancel`, {
            method: 'PUT',
            headers: { 'Authorization': 'Bearer ' + token() }
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        loadRequests();
        loadStats();
    } catch (err) {
        alert('Error: ' + err.message);
    }
}

async function loadPatients() {
    const select = document.getElementById('modal_patient_id');
    try {
        const res  = await fetch('/api/doctor/patients?limit=100', {
            headers: { 'Authorization': 'Bearer ' + token() }
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        select.innerHTML = '<option value="">Select patient...</option>';
        data.patients.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = `${p.username} (${p.patient_id || 'ID:' + p.id})`;
            select.appendChild(opt);
        });

        const preId = new URLSearchParams(window.location.search).get('patient_id');
        if (preId) {
            select.value = preId;
            document.getElementById('newRequestModal').style.display = 'flex';
        }
    } catch (err) {
        select.innerHTML = `<option value="">Error: ${err.message}</option>`;
    }
}

async function handleSubmit(event) {
    event.preventDefault();

    const patientId = document.getElementById('modal_patient_id').value;
    const testName  = document.getElementById('test_name').value;
    const priority  = document.getElementById('priority').value;
    const notes     = document.getElementById('modal_notes').value.trim();
    const alertEl   = document.getElementById('modalAlert');
    const btn       = document.getElementById('submitBtn');

    if (!patientId || !testName) {
        alertEl.className    = 'alert alert-danger';
        alertEl.textContent  = 'Please select a patient and test.';
        alertEl.style.display = '';
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Creating...';

    try {
        const res  = await fetch('/api/doctor/lab-requests', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token() },
            body: JSON.stringify({
                patient_id: parseInt(patientId),
                test_name: testName, test_type: testName,
                test_category: 'diabetes', priority, notes
            })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        alertEl.className    = 'alert alert-success';
        alertEl.textContent  = 'Lab request created! ID: ' + data.lab_request.request_id;
        alertEl.style.display = '';
        event.target.reset();

        setTimeout(() => {
            document.getElementById('newRequestModal').style.display = 'none';
            alertEl.style.display = 'none';
            loadRequests();
            loadStats();
        }, 1500);

    } catch (err) {
        alertEl.className    = 'alert alert-danger';
        alertEl.textContent  = 'Error: ' + err.message;
        alertEl.style.display = '';
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-plus-circle"></i> Create Request';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('doctor');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    const sb = document.getElementById('sidebarDoctorName');
    if (sb) sb.textContent = user.name || user.username;
    document.getElementById('labRequestForm').addEventListener('submit', handleSubmit);
    loadPatients();
    loadRequests();
    loadStats();
});
