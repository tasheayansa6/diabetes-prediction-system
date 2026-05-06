// Login Page
const API_BASE_URL = '';

function showError(msg) {
    let el = document.getElementById('loginAlert');
    if (!el) {
        el = document.createElement('div');
        el.id = 'loginAlert';
        el.style.cssText = 'margin-bottom:1rem;padding:.75rem 1rem;border-radius:10px;font-size:.875rem;font-weight:500;';
        const form = document.querySelector('form');
        if (form) form.prepend(el);
    }
    el.style.background = '#fee2e2';
    el.style.color = '#991b1b';
    el.style.border = '1px solid #fca5a5';
    el.innerHTML = '<i class="bi bi-exclamation-circle-fill me-2"></i>' + msg;
}

function showInfo(msg) {
    let el = document.getElementById('loginAlert');
    if (!el) {
        el = document.createElement('div');
        el.id = 'loginAlert';
        el.style.cssText = 'margin-bottom:1rem;padding:.75rem 1rem;border-radius:10px;font-size:.875rem;font-weight:500;';
        const form = document.querySelector('form');
        if (form) form.prepend(el);
    }
    el.style.background = '#eff6ff';
    el.style.color = '#1d4ed8';
    el.style.border = '1px solid #bfdbfe';
    el.innerHTML = '<i class="bi bi-info-circle-fill me-2"></i>' + msg;
}

function redirectToDashboard(role) {
    const dashboards = {
        patient:        '/templates/patient/dashboard.html',
        doctor:         '/templates/doctor/dashboard.html',
        nurse:          '/templates/nurse/dashboard.html',
        lab_technician: '/templates/lab/dashboard.html',
        pharmacist:     '/templates/pharmacist/dashboard.html',
        admin:          '/templates/admin/dashboard.html'
    };
    window.location.href = dashboards[role] || '/login';
}

async function handleLogin(event) {
    event.preventDefault();

    const email    = document.getElementById('email').value.trim();
    const password = document.getElementById('password').value;
    const btn      = event.target.querySelector('button[type="submit"]');

    if (!email || !password) { showError('Please enter email and password.'); return; }

    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Signing in...';

    try {
        const res  = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();

        if (res.ok && data.success) {
            // Wipe only token+user — preserve payment keys in case user
            // is returning from a Chapa payment flow
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            localStorage.setItem('token', data.token);
            localStorage.setItem('user', JSON.stringify(data.user));

            const next = new URLSearchParams(window.location.search).get('next');
            if (next && next.startsWith('/')) {
                window.location.href = next;
            } else {
                redirectToDashboard(data.user.role);
            }
            return;
        }

        if (res.status === 403 && data.requires_verification) {
            showInfo('Email not verified. Sending verification code...');
            await fetch('/api/auth/send-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, username: email.split('@')[0] })
            });
            setTimeout(() => {
                window.location.href = '/verify-email?email=' + encodeURIComponent(email) + '&next=login';
            }, 1200);
            return;
        }

        showError(data.message || 'Login failed. Please check your credentials.');

    } catch (err) {
        showError('Connection error: ' + err.message + '. Please try again.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-box-arrow-in-right"></i> Sign In';
    }
}

window.addEventListener('DOMContentLoaded', function () {
    // If already logged in with a valid token, redirect to dashboard immediately
    const token = localStorage.getItem('token');
    const user  = JSON.parse(localStorage.getItem('user') || '{}');
    if (token && user.role) {
        try {
            const b64     = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
            const padded  = b64 + '='.repeat((4 - b64.length % 4) % 4);
            const payload = JSON.parse(atob(padded));
            if (payload.exp && payload.exp * 1000 > Date.now()) {
                // Valid token — go straight to dashboard, no need to log in again
                redirectToDashboard(user.role);
                return;
            }
        } catch (_) {}
    }

    const params = new URLSearchParams(window.location.search);
    const txRef  = params.get('tx_ref') || params.get('trx_ref');
    if (txRef) {
        showInfo('Your payment was processed. Please sign in to view your receipt.');
    }
    const reason = params.get('reason');
    if (reason === 'session_expired') {
        showInfo('Your session has expired. Please sign in again.');
    }
});
