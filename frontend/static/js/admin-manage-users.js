// Admin Manage Users

const API = '/api/admin/users';

function authHeaders() {
    return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token') };
}

function esc(str) {
    const d = document.createElement('div');
    d.textContent = str ?? '';
    return d.innerHTML;
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const colors = { success: '#16a34a', danger: '#dc2626', warning: '#d97706', info: '#0369a1' };
    const div = document.createElement('div');
    div.style.cssText = 'background:' + (colors[type] || colors.success) + ';color:#fff;padding:10px 16px;border-radius:8px;margin-bottom:8px;font-size:14px;box-shadow:0 2px 8px rgba(0,0,0,.2);min-width:220px;';
    div.textContent = message;
    container.appendChild(div);
    setTimeout(() => div.remove(), 3500);
}

// ── Export CSV ────────────────────────────────────────────────────────────────
function exportData(resource) {
    const token = localStorage.getItem('token');
    fetch('/api/admin/export/' + resource, {
        headers: { 'Authorization': 'Bearer ' + token }
    }).then(r => {
        if (!r.ok) throw new Error('Export failed');
        return r.blob();
    }).then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = resource + '_export.csv';
        a.click();
        URL.revokeObjectURL(url);
    }).catch(() => showToast('Export failed', 'danger'));
}

// ── Import CSV ────────────────────────────────────────────────────────────────
async function importUsers(input) {
    const file = input.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
        const res  = await fetch('/api/admin/import/users', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') },
            body: formData
        });
        const data = await res.json();
        showToast(data.message || (data.success ? 'Import complete' : 'Import failed'),
                  data.success ? 'success' : 'danger');
        if (data.success) loadUsers(1);
    } catch (e) {
        showToast('Import error: ' + e.message, 'danger');
    }
    input.value = '';
}

// ── Pagination state ──────────────────────────────────────────────────────────
let _currentPage = 1;
const _perPage   = 20;
let   _totalUsers = 0;

// ── Load & Render ─────────────────────────────────────────────────────────────
async function loadUsers(page) {
    page = page || _currentPage;
    _currentPage = page;

    const search = (document.getElementById('searchInput')?.value || '').trim();
    const role   = document.getElementById('roleFilter')?.value || '';

    const tbody = document.getElementById('usersTable');
    if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:2rem;">Loading...</td></tr>';

    const params = new URLSearchParams({ page, per_page: _perPage });
    if (search) params.set('search', search);
    if (role)   params.set('role',   role);

    try {
        const res  = await fetch(API + '?' + params, { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message || 'Failed to load users');
        _totalUsers = data.pagination?.total || data.users?.length || 0;
        renderUsers(data.users || []);
        renderPagination();
    } catch (e) {
        showToast('Failed to load users: ' + e.message, 'danger');
        if (tbody) tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#dc2626;padding:2rem;">Error: ' + esc(e.message) + '</td></tr>';
    }
}

function renderPagination() {
    const totalPages = Math.ceil(_totalUsers / _perPage);
    let bar = document.getElementById('paginationBar');
    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'paginationBar';
        bar.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:.75rem 1.25rem;border-top:1px solid #f1f5f9;flex-wrap:wrap;gap:.5rem;';
        document.querySelector('.table-responsive')?.after(bar);
    }
    if (totalPages <= 1) { bar.style.display = 'none'; return; }
    bar.style.display = 'flex';
    const start = (_currentPage - 1) * _perPage + 1;
    const end   = Math.min(_currentPage * _perPage, _totalUsers);
    const pages = [];
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= _currentPage - 2 && i <= _currentPage + 2)) {
            pages.push(i);
        } else if (pages[pages.length - 1] !== '...') {
            pages.push('...');
        }
    }
    bar.innerHTML =
        '<span style="font-size:.82rem;color:#64748b;">Showing ' + start + '–' + end + ' of ' + _totalUsers + ' users</span>' +
        '<div style="display:flex;gap:.4rem;align-items:center;">' +
            '<button class="btn btn-sm btn-secondary" ' + (_currentPage <= 1 ? 'disabled' : '') + ' onclick="loadUsers(' + (_currentPage - 1) + ')"><i class="bi bi-chevron-left"></i></button>' +
            pages.map(p => p === '...'
                ? '<span style="padding:0 .4rem;color:#94a3b8;">...</span>'
                : '<button class="btn btn-sm ' + (p === _currentPage ? 'btn-primary' : 'btn-secondary') + '" onclick="loadUsers(' + p + ')">' + p + '</button>'
            ).join('') +
            '<button class="btn btn-sm btn-secondary" ' + (_currentPage >= totalPages ? 'disabled' : '') + ' onclick="loadUsers(' + (_currentPage + 1) + ')"><i class="bi bi-chevron-right"></i></button>' +
        '</div>';
}

const ROLE_COLORS = {
    admin: 'danger', doctor: 'primary', nurse: 'info',
    lab_technician: 'warning', pharmacist: 'success', patient: 'secondary'
};

function renderUsers(users) {
    const tbody = document.getElementById('usersTable');
    if (!tbody) return;
    if (!users.length) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:2rem;">No users found.</td></tr>';
        return;
    }
    tbody.innerHTML = users.map(u => {
        const roleLabel = (u.role || '').replace(/_/g, ' ');
        const roleColor = ROLE_COLORS[u.role] || 'secondary';
        const active    = u.is_active !== false;
        return '<tr>' +
            '<td>' + esc(String(u.id)) + '</td>' +
            '<td><strong>' + esc(u.username) + '</strong></td>' +
            '<td>' + esc(u.email) + '</td>' +
            '<td><span class="badge bg-' + roleColor + '">' + esc(roleLabel) + '</span></td>' +
            '<td><span class="badge ' + (active ? 'bg-success' : 'bg-danger') + '">' + (active ? 'Active' : 'Inactive') + '</span></td>' +
            '<td>' +
                '<button class="btn btn-sm btn-info me-1" onclick="openEditModal(' + u.id + ', \'' + esc(u.username) + '\', \'' + esc(u.email) + '\', \'' + u.role + '\', ' + active + ')">' +
                    '<i class="bi bi-pencil"></i> Edit' +
                '</button>' +
                '<button class="btn btn-sm btn-danger" onclick="deleteUser(' + u.id + ', \'' + esc(u.username) + '\')">' +
                    '<i class="bi bi-trash"></i>' +
                '</button>' +
            '</td>' +
        '</tr>';
    }).join('');
}

// ── Add User ──────────────────────────────────────────────────────────────────
function deriveUsername(email, fullName) {
    const local = (email || '').split('@')[0] || '';
    let u = local.replace(/[^a-zA-Z0-9._-]/g, '').slice(0, 50);
    if (u.length < 3) {
        u = (fullName || 'user').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 40);
    }
    return u.length >= 3 ? u : 'user_' + Date.now();
}

async function addUser(event) {
    event.preventDefault();
    const full_name = document.getElementById('name').value.trim();
    const email     = document.getElementById('email').value.trim();
    const role      = document.getElementById('role').value;
    const password  = document.getElementById('password').value;

    if (!full_name || !email || !role || !password) {
        showToast('Please fill in all fields.', 'danger');
        return;
    }

    const payload = { username: deriveUsername(email, full_name), email, full_name, role, password };

    try {
        const res  = await fetch(API, { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) });
        const data = await res.json();
        if (!data.success) throw new Error(data.message || data.error || 'Add failed');
        document.getElementById('addUserModal').style.display = 'none';
        document.getElementById('addUserForm').reset();
        showToast('User "' + payload.username + '" added successfully!', 'success');
        loadUsers(1);
    } catch (e) {
        showToast('Failed to add user: ' + e.message, 'danger');
    }
}

// ── Edit User ─────────────────────────────────────────────────────────────────
function openEditModal(id, username, email, role, isActive) {
    document.getElementById('editUserId').value    = id;
    document.getElementById('editUsername').value  = username;
    document.getElementById('editEmail').value     = email;
    document.getElementById('editRole').value      = role;
    document.getElementById('editStatus').value    = String(isActive);
    document.getElementById('editUserModal').style.display = 'flex';
}

async function saveEditUser() {
    const id       = document.getElementById('editUserId').value;
    const newRole  = document.getElementById('editRole').value;
    const isActive = document.getElementById('editStatus').value === 'true';

    try {
        const roleRes  = await fetch(API + '/' + id + '/role', {
            method: 'PUT', headers: authHeaders(), body: JSON.stringify({ role: newRole })
        });
        const roleData = await roleRes.json();
        if (!roleData.success) throw new Error(roleData.message || 'Role update failed');

        const statusRes  = await fetch(API + '/' + id + '/toggle-status', {
            method: 'POST', headers: authHeaders(), body: JSON.stringify({ is_active: isActive })
        });
        const statusData = await statusRes.json();
        if (!statusData.success) throw new Error(statusData.message || 'Status update failed');

        document.getElementById('editUserModal').style.display = 'none';
        showToast('User updated successfully!', 'success');
        loadUsers(_currentPage);
    } catch (e) {
        showToast('Update failed: ' + e.message, 'danger');
    }
}

// ── Delete User ───────────────────────────────────────────────────────────────
async function deleteUser(id, username) {
    if (!confirm('Delete user "' + username + '"? This cannot be undone.')) return;
    try {
        const res  = await fetch(API + '/' + id, { method: 'DELETE', headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message || 'Delete failed');
        showToast('User "' + username + '" deleted.', 'warning');
        // Go back a page if last item on current page was deleted
        const newPage = _totalUsers % _perPage === 1 && _currentPage > 1 ? _currentPage - 1 : _currentPage;
        loadUsers(newPage);
    } catch (e) {
        showToast('Delete failed: ' + e.message, 'danger');
    }
}

// ── Search / Filter — server-side ─────────────────────────────────────────────
function applyFilter() { loadUsers(1); }
function loadUsersWithFilter() { loadUsers(1); }

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('admin');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    loadUsers(1);

    // Search on Enter key
    document.getElementById('searchInput')?.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') loadUsers(1);
    });
});
