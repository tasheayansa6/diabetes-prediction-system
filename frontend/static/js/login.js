// Login Page

const API_BASE_URL = "";

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
    el.innerHTML = `<i class="bi bi-exclamation-circle-fill me-2"></i>${msg}`;
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
    el.innerHTML = `<i class="bi bi-info-circle-fill me-2"></i>${msg}`;
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
        const res  = await fetch(`${API_BASE_URL}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();

        if (res.ok && data.success) {
            // Clear ALL previous user data before storing new session
            if (typeof _clearAllStorage === 'function') _clearAllStorage();
            // Also clear notification widget DOM so previous user's notifications
            // are not visible for even a moment after login
            const notifWrapper = document.getElementById('notifWrapper');
            if (notifWrapper) notifWrapper.remove();
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

        // Email verification required
        if (res.status === 403 && data.requires_verification) {
            showInfo('Email not verified. Sending verification code...');
            // Auto-send OTP
            await fetch('/api/auth/send-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, username: email.split('@')[0] })
            });
            // Redirect to verify page
            setTimeout(() => {
                window.location.href = `/verify-email?email=${encodeURIComponent(email)}&next=login`;
            }, 1200);
            return;
        }

        // Payment required (for prediction — shouldn't happen on login but handle gracefully)
        if (res.status === 402) {
            showError('Payment required to access this feature.');
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

// Auto-redirect if already logged in — DISABLED.
// We never auto-redirect on the login page. The user must always
// enter their credentials explicitly. This prevents one user's
// session from silently logging in as another user.
window.addEventListener('DOMContentLoaded', function () {
    // Only pre-fill email if coming back from a Chapa payment redirect
    // (tx_ref in URL means Chapa sent the user here — show a message)
    const params = new URLSearchParams(window.location.search);
    const txRef = params.get('tx_ref') || params.get('trx_ref');
    if (txRef) {
        showInfo('Your payment was processed. Please sign in to view your receipt.');
    }
});
