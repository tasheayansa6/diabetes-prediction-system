const API = '';

const DASHBOARDS = {
    patient: '/templates/patient/dashboard.html',
    doctor: '/templates/doctor/dashboard.html',
    nurse: '/templates/nurse/dashboard.html',
    lab_technician: '/templates/lab/dashboard.html',
    labtech: '/templates/lab/dashboard.html',
    pharmacist: '/templates/pharmacist/dashboard.html',
    admin: '/templates/admin/dashboard.html'
};

async function handleRegister(event) {
    event.preventDefault();

    const fullname = document.getElementById('fullname').value.trim();
    const email = document.getElementById('email').value.trim();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirm_password').value;
    let role = document.getElementById('role').value;

    if (password !== confirmPassword) {
        alert('Passwords do not match!');
        return;
    }

    // Map labtech -> lab_technician for backend
    if (role === 'labtech') role = 'lab_technician';

    try {
        const res = await fetch(`${API}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password, role, full_name: fullname })
        });

        const data = await res.json();

        if (res.ok && data.success) {
            // Clear ALL previous user data before storing new session
            if (typeof _clearAllStorage === 'function') _clearAllStorage();
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));

            const box = document.getElementById('alertBox');
            if (box) box.innerHTML = '<div class="alert alert-success"><i class="bi bi-check-circle-fill"></i> Account created! Redirecting to your dashboard...</div>';

            setTimeout(() => { window.location.href = DASHBOARDS[data.user.role] || '/login'; }, 1200);
        } else {
            const box = document.getElementById('alertBox');
            if (box) box.innerHTML = `<div class="alert alert-danger"><i class="bi bi-exclamation-circle-fill"></i> ${data.message || 'Registration failed'}</div>`;
        }    } catch (err) {
        console.error(err);
        alert('Cannot connect to server. Is Flask running?');
    }
}

// Auto-redirect only if token is still valid (no auto-redirect — user must register or login)
window.addEventListener('DOMContentLoaded', () => {
    // Do NOT auto-redirect on register page — user is here to create a new account
    // Just clear any stale session so the form starts fresh
    const token = localStorage.getItem('token');
    const user  = JSON.parse(localStorage.getItem('user') || '{}');
    if (!token || !user.username) return;
    try {
        const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        const padded = b64 + '='.repeat((4 - b64.length % 4) % 4);
        const payload = JSON.parse(atob(padded));
        if (payload.exp && payload.exp * 1000 > Date.now()) {
            // Valid session exists — redirect to their dashboard
            window.location.href = DASHBOARDS[user.role] || '/login';
        } else {
            if (typeof _clearAllStorage === 'function') _clearAllStorage();
        }
    } catch {
        if (typeof _clearAllStorage === 'function') _clearAllStorage();
    }
});
