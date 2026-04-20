const API = '/api';

function getToken() { return localStorage.getItem('token'); }

function apiFetch(path, options = {}) {
    return fetch(API + path, {
        ...options,
        headers: { 'Authorization': 'Bearer ' + getToken(), 'Content-Type': 'application/json', ...(options.headers || {}) }
    }).then(r => {
        if (r.status === 401) { logout(); return { success: false, message: 'Session expired' }; }
        return r.json();
    });
}

function showAlert(msg, type = 'success') {
    const existing = document.getElementById('profileAlert');
    if (existing) existing.remove();
    const div = document.createElement('div');
    div.id = 'profileAlert';
    div.className = `alert alert-${type} alert-dismissible fade show mt-3`;
    div.innerHTML = `${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    const target = document.querySelector('.main-content h2') || document.querySelector('.main-content');
    target.insertAdjacentElement('afterend', div);
    setTimeout(() => div.remove(), 4000);
}

async function loadProfile() {
    const user = checkAuth('patient');
    if (!user) return;

    document.getElementById('navUserName').textContent = user.name || user.username;

    const res = await apiFetch('/patient/profile');
    if (!res.success) { showAlert('Failed to load profile', 'danger'); return; }

    const p = res.profile;
    document.getElementById('profileUserName').textContent = p.username;
    document.getElementById('profileUserRole').textContent = 'Patient';
    document.getElementById('profileUserEmail').textContent = p.email;

    document.getElementById('fullName').value = p.username || '';
    document.getElementById('email').value = p.email || '';
    document.getElementById('bloodGroup').value = p.blood_group || '';
    document.getElementById('phone').value = p.emergency_contact || '';
    // dateOfBirth, gender, address not stored in DB — leave as empty
}

async function handleProfileSubmit(e) {
    e.preventDefault();
    const body = {
        username: document.getElementById('fullName').value.trim(),
        email: document.getElementById('email').value.trim(),
        blood_group: document.getElementById('bloodGroup').value,
        emergency_contact: document.getElementById('phone').value.trim()
    };

    const res = await apiFetch('/patient/profile', { method: 'PUT', body: JSON.stringify(body) });
    if (res.success) {
        // Update localStorage user if username/email changed
        const stored = JSON.parse(localStorage.getItem('user') || '{}');
        stored.username = body.username;
        stored.email = body.email;
        localStorage.setItem('user', JSON.stringify(stored));
        if (res.token) localStorage.setItem('token', res.token);
        document.getElementById('profileUserName').textContent = body.username;
        document.getElementById('profileUserEmail').textContent = body.email;
        document.getElementById('navUserName').textContent = body.username;
        showAlert('Profile updated successfully');
    } else {
        showAlert(res.message || 'Update failed', 'danger');
    }
}

async function handlePasswordSubmit(e) {
    e.preventDefault();
    const newPw = document.getElementById('newPassword').value;
    const confirmPw = document.getElementById('confirmPassword').value;

    if (newPw !== confirmPw) { showAlert('New passwords do not match', 'danger'); return; }
    if (newPw.length < 8) { showAlert('Password must be at least 8 characters', 'danger'); return; }

    const res = await apiFetch('/patient/change-password', {
        method: 'POST',
        body: JSON.stringify({
            current_password: document.getElementById('currentPassword').value,
            new_password: newPw,
            confirm_password: confirmPw
        })
    });

    if (res.success) {
        showAlert('Password changed successfully');
        document.getElementById('passwordForm').reset();
    } else {
        showAlert(res.message || 'Password change failed', 'danger');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadProfile();
    document.getElementById('profileForm').addEventListener('submit', handleProfileSubmit);
    document.getElementById('passwordForm').addEventListener('submit', handlePasswordSubmit);
});
