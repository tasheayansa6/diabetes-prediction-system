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
    const form = event.target;
    const submitBtn = form?.querySelector('button[type="submit"]');

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
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="bi bi-hourglass-split"></i> Creating...';
        }

        const res = await fetch(`${API}/api/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password, role, full_name: fullname })
        });

        const data = await res.json();

        if (res.ok && data.success) {
            // Clear ALL previous user data before storing new session
            if (typeof _clearAllStorage === 'function') _clearAllStorage();

            const token = data.token || '';
            let roleFromToken = data?.user?.role || role;
            try {
                const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
                const padded = b64 + '='.repeat((4 - b64.length % 4) % 4);
                const payload = JSON.parse(atob(padded));
                if (payload?.role) roleFromToken = payload.role;
            } catch (_) {}

            const safeUser = { ...(data.user || {}), role: roleFromToken };
            localStorage.setItem('token', token);
            localStorage.setItem('user', JSON.stringify(safeUser));

            const box = document.getElementById('alertBox');
            if (box) box.innerHTML = '<div class="alert alert-success"><i class="bi bi-check-circle-fill"></i> Account created! Redirecting to your dashboard...</div>';

            setTimeout(() => { window.location.href = DASHBOARDS[roleFromToken] || '/login'; }, 1200);
        } else {
            const box = document.getElementById('alertBox');
            const msg = res.status === 429
                ? 'Too many attempts. Please wait 1 minute, then try again once.'
                : (data.message || 'Registration failed');
            if (box) box.innerHTML = `<div class="alert alert-danger"><i class="bi bi-exclamation-circle-fill"></i> ${msg}</div>`;
        }
    } catch (err) {
        console.error(err);
        alert('Cannot connect to server. Is Flask running?');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="bi bi-person-plus-fill"></i> Create Account';
        }
    }
}

// Register page should always start clean.
// If user intentionally opens /register while previously logged in (e.g., nurse),
// stale localStorage can force wrong dashboard redirects in other scripts.
window.addEventListener('DOMContentLoaded', () => {
    if (typeof _clearAllStorage === 'function') {
        _clearAllStorage();
        return;
    }
    localStorage.removeItem('token');
    localStorage.removeItem('user');
});
