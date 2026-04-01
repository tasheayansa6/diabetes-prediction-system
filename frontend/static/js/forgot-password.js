const API = '';

function showAlert(message, type = 'success') {
    const el = document.getElementById('alertContainer');
    const icon = type === 'success' ? 'check-circle-fill' : type === 'info' ? 'info-circle-fill' : 'exclamation-triangle-fill';
    el.innerHTML = `<div class="alert alert-${type}" style="display:flex;align-items:center;gap:0.5rem;">
        <i class="bi bi-${icon}"></i> ${message}</div>`;
}

async function handleForgotPassword(event) {
    event.preventDefault();

    const email = document.getElementById('email').value.trim();
    const btn = event.submitter || document.querySelector('button[type="submit"]');

    if (!email) { showAlert('Please enter your email address.', 'danger'); return; }

    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Sending...';

    try {
        const res = await fetch(`${API}/api/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();

        // Always show success message (backend never reveals if email exists)
        showAlert(data.message || 'If an account exists with this email, a reset link has been sent.', 'success');

        btn.innerHTML = '<i class="bi bi-check-circle"></i> Email Sent';

    } catch (err) {
        showAlert('Cannot connect to server. Make sure the app is running.', 'danger');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-send"></i> Send Reset Link';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('email')?.focus();
});
