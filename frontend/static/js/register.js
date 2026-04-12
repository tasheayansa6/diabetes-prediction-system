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
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            const box = document.getElementById('alertBox');
            if (box) box.innerHTML = '<div class="alert alert-success"><i class="bi bi-check-circle-fill"></i> Registration successful! Redirecting...</div>';
            setTimeout(() => { window.location.href = DASHBOARDS[data.user.role] || '/login'; }, 1000);
        } else {
            const box = document.getElementById('alertBox');
            if (box) box.innerHTML = `<div class="alert alert-danger"><i class="bi bi-exclamation-circle-fill"></i> ${data.message || 'Registration failed'}</div>`;
            else alert(data.message || 'Registration failed');
        }

    } catch (err) {
        console.error(err);
        alert('Cannot connect to server. Is Flask running?');
    }
}

// Auto-redirect only if token is still valid
window.addEventListener('DOMContentLoaded', () => {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const token = localStorage.getItem('token');
    if (!user.username || !token) return;
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.exp && payload.exp * 1000 > Date.now()) {
            window.location.href = DASHBOARDS[user.role] || '/login';
        } else {
            localStorage.removeItem('user');
            localStorage.removeItem('token');
        }
    } catch { localStorage.removeItem('user'); localStorage.removeItem('token'); }
});
