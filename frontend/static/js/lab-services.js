// Lab Test Services - loads from GET /api/labs/test-types

function authHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('token')
    };
}

async function loadTestTypes() {
    const tbody = document.getElementById('testTypesBody');
    try {
        const res = await fetch('/api/labs/test-types', { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        if (!data.test_types.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No test types added yet.</td></tr>';
            return;
        }

        tbody.innerHTML = data.test_types.map(t => `
            <tr>
                <td>${t.test_code}</td>
                <td>${t.test_name}</td>
                <td><span class="badge badge-blue">${t.category}</span></td>
                <td>${t.cost ? 'ETB ' + parseFloat(t.cost).toFixed(2) : '—'}</td>
                <td>${t.normal_range || '—'}</td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="viewTestType(${t.id})" title="View">
                        <i class="bi bi-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteTestType(${t.id}, '${t.test_name}')" title="Delete" style="margin-left:4px;">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');

    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">${err.message}</td></tr>`;
    }
}

async function viewTestType(id) {
    try {
        const res = await fetch(`/api/labs/test-types/${id}`, { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        const t = data.test_type;
        document.getElementById('modalTestCode').textContent = t.test_code;
        document.getElementById('modalTestName').textContent = t.test_name;
        document.getElementById('modalCategory').textContent = t.category;
        document.getElementById('modalCost').textContent = t.cost ? 'ETB ' + parseFloat(t.cost).toFixed(2) : '—';
        document.getElementById('modalNormalRange').textContent = t.normal_range || '—';
        document.getElementById('modalPreparation').textContent = t.preparation_instructions || '—';
        document.getElementById('modalCreatedAt').textContent = t.created_at ? new Date(t.created_at).toLocaleDateString() : '—';

        document.getElementById('viewModal').style.display = 'flex';
    } catch (err) {
        alert('Error loading test type: ' + err.message);
    }
}

async function deleteTestType(id, name) {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try {
        const res = await fetch(`/api/labs/test-types/${id}`, {
            method: 'DELETE',
            headers: authHeaders()
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        loadTestTypes();
    } catch (err) {
        alert('Error deleting test type: ' + err.message);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('lab_technician');
    if (!user) return;

    const name = user.name || user.username;
    document.getElementById('topUserName').textContent = name;
    document.getElementById('userName').textContent = name;

    loadTestTypes();
});
