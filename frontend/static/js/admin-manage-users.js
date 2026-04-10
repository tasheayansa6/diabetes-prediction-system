// Admin Manage Users - uses /api/admin/users

const API = '/api/admin/users';

function authHeaders() {
    return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token') };
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const colors = { success: '#16a34a', danger: '#dc2626', warning: '#d97706' };
    const div = document.createElement('div');
    div.style.cssText = `background:${colors[type]||colors.success};color:#fff;padding:10px 16px;border-radius:6px;margin-bottom:8px;font-size:14px;box-shadow:0 2px 8px rgba(0,0,0,.2);`;
    div.textContent = message;
    container.appendChild(div);
    setTimeout(() => div.remove(), 3000);
}

// ===== Load & Render =====

async function loadUsers() {
    try {
        const res = await fetch(API + '?per_page=100', { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        renderUsers(data.users);
    } catch (e) {
        showToast('Failed to load users: ' + e.message, 'danger');
    }
}

const ROLE_COLORS = {
    admin: 'danger', doctor: 'primary', nurse: 'info',
    lab_technician: 'warning', pharmacist: 'success', patient: 'secondary'
};

function renderUsers(users) {
    document.getElementById('usersTable').innerHTML = users.map(u => `
        <tr>
            <td>${u.id}</td>
            <td>${u.username}</td>
            <td>${u.email}</td>
            <td><span class="badge bg-${ROLE_COLORS[u.role] || 'secondary'}">${u.role.replace('_', ' ')}</span></td>
            <td><span class="badge ${u.is_active ? 'bg-success' : 'bg-danger'}">${u.is_active ? 'Active' : 'Inactive'}</span></td>
            <td>
                <button class="btn btn-sm btn-info me-1" onclick="openEditModal(${u.id}, '${u.username}', '${u.email}', '${u.role}', ${u.is_active})">
                    <i class="bi bi-pencil"></i> Edit
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteUser(${u.id}, '${u.username}')">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// ===== Add User =====

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
    const email = document.getElementById('email').value.trim();
    const payload = {
        username: deriveUsername(email, full_name),
        email,
        full_name: full_name || deriveUsername(email, full_name),
        role: document.getElementById('role').value,
        password: document.getElementById('password').value
    };
    try {
        const res = await fetch(API, { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) });
        const data = await res.json();
        if (!data.success) throw new Error(data.message || data.error);
        document.getElementById('addUserModal').style.display = 'none';
        document.getElementById('addUserForm').reset();
        showToast('User added successfully!', 'success');
        loadUsers();
    } catch (e) {
        showToast('Failed to add user: ' + e.message, 'danger');
    }
}

// ===== Edit User =====

function openEditModal(id, username, email, role, isActive) {
    document.getElementById('editUserId').value = id;
    document.getElementById('editUsername').value = username;
    document.getElementById('editEmail').value = email;
    document.getElementById('editRole').value = role;
    document.getElementById('editStatus').value = String(isActive);
    document.getElementById('editUserModal').style.display = 'flex';
}

async function saveEditUser() {
    const id = document.getElementById('editUserId').value;
    const newRole = document.getElementById('editRole').value;
    const isActive = document.getElementById('editStatus').value === 'true';

    try {
        // Update role
        const roleRes = await fetch(`${API}/${id}/role`, {
            method: 'PUT', headers: authHeaders(),
            body: JSON.stringify({ role: newRole })
        });
        const roleData = await roleRes.json();
        if (!roleData.success) throw new Error(roleData.message);

        // Update status
        const statusRes = await fetch(`${API}/${id}/toggle-status`, {
            method: 'POST', headers: authHeaders(),
            body: JSON.stringify({ is_active: isActive })
        });
        const statusData = await statusRes.json();
        if (!statusData.success) throw new Error(statusData.message);

        document.getElementById('editUserModal').style.display = 'none';
        showToast('User updated successfully!', 'success');
        loadUsers();
    } catch (e) {
        showToast('Update failed: ' + e.message, 'danger');
    }
}

// ===== Delete User =====

async function deleteUser(id, username) {
    if (!confirm(`Delete user "${username}"? This cannot be undone.`)) return;
    try {
        const res = await fetch(`${API}/${id}`, { method: 'DELETE', headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        showToast('User deleted.', 'warning');
        loadUsers();
    } catch (e) {
        showToast('Delete failed: ' + e.message, 'danger');
    }
}

// ===== Init =====

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('admin');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    loadUsers();
});
