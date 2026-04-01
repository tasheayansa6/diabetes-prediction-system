const API = '';

function showAlert(message, type = 'success') {
    const el = document.getElementById('alertContainer');
    const icon = type === 'success' ? 'check-circle-fill' : 'exclamation-triangle-fill';
    el.innerHTML = `<div class="alert alert-${type}" style="display:flex;align-items:center;gap:0.5rem;">
        <i class="bi bi-${icon}"></i> ${message}</div>`;
}

function togglePassword(fieldId) {
    const field = document.getElementById(fieldId);
    const icon = document.getElementById(fieldId + 'Icon');
    const isHidden = field.type === 'password';
    field.type = isHidden ? 'text' : 'password';
    icon.className = isHidden ? 'bi bi-eye-slash' : 'bi bi-eye';
}

function checkPasswordStrength(password) {
    let strength = 0;
    if (password.length >= 8)  strength += 25;
    if (password.length >= 12) strength += 15;
    if (/[a-z]/.test(password)) strength += 20;
    if (/[A-Z]/.test(password)) strength += 20;
    if (/[0-9]/.test(password)) strength += 20;

    const bar = document.getElementById('strengthBar');
    const text = document.getElementById('strengthText');
    bar.style.width = strength + '%';

    if (strength < 40) {
        bar.style.background = '#dc2626'; text.textContent = 'Weak'; text.style.color = '#dc2626';
    } else if (strength < 70) {
        bar.style.background = '#d97706'; text.textContent = 'Medium'; text.style.color = '#d97706';
    } else {
        bar.style.background = '#059669'; text.textContent = 'Strong'; text.style.color = '#059669';
    }
}

async function handleResetPassword(event) {
    event.preventDefault();

    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    const email = params.get('email');
    const btn = document.querySelector('button[type="submit"]');

    if (!token || !email) {
        showAlert('Invalid reset link. Please request a new password reset.', 'danger');
        return;
    }
    if (newPassword !== confirmPassword) {
        showAlert('Passwords do not match.', 'danger'); return;
    }
    if (newPassword.length < 8) {
        showAlert('Password must be at least 8 characters.', 'danger'); return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Resetting...';

    try {
        const res = await fetch(`${API}/api/auth/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token, email, new_password: newPassword })
        });
        const data = await res.json();

        if (data.success) {
            showAlert('Password reset successfully! Redirecting to login...', 'success');
            setTimeout(() => { window.location.href = '/login'; }, 2000);
        } else {
            showAlert(data.message || 'Reset failed. Please try again.', 'danger');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle"></i> Reset Password';
        }
    } catch {
        showAlert('Cannot connect to server.', 'danger');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-circle"></i> Reset Password';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('newPassword')?.addEventListener('input', e => checkPasswordStrength(e.target.value));
});
