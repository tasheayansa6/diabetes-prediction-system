const API = '';

let resendCooldown = 60;
let timerInterval = null;

function showAlert(message, type = 'success') {
    const el = document.getElementById('alertContainer');
    const icon = type === 'success' ? 'check-circle-fill' : type === 'info' ? 'info-circle-fill' : 'exclamation-triangle-fill';
    el.innerHTML = `<div class="alert alert-${type}" style="display:flex;align-items:center;gap:0.5rem;">
        <i class="bi bi-${icon}"></i> ${message}</div>`;
}

function startResendTimer() {
    const btn = document.getElementById('resendBtn');
    const timerEl = document.getElementById('resendTimer');
    btn.disabled = true;
    resendCooldown = 60;

    timerInterval = setInterval(() => {
        resendCooldown--;
        timerEl.textContent = `Resend available in ${resendCooldown}s`;
        if (resendCooldown <= 0) {
            clearInterval(timerInterval);
            btn.disabled = false;
            timerEl.textContent = '';
        }
    }, 1000);
}

async function sendOtp(email, username) {
    try {
        const res = await fetch(`${API}/api/auth/send-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, username })
        });
        const data = await res.json();
        return data.success;
    } catch {
        return false;
    }
}

async function resendCode() {
    const email = document.getElementById('email').value;
    const username = email.split('@')[0];
    showAlert('Sending new code...', 'info');
    const ok = await sendOtp(email, username);
    showAlert(ok ? 'New verification code sent to your email.' : 'Failed to send code. Try again.', ok ? 'success' : 'danger');
    if (ok) startResendTimer();
}

async function handleVerifyEmail(event) {
    event.preventDefault();

    const email = document.getElementById('email').value.trim();
    const otp = document.getElementById('verificationCode').value.trim();
    const btn = document.querySelector('button[type="submit"]');

    if (otp.length !== 6) {
        showAlert('Please enter the complete 6-digit code.', 'danger');
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Verifying...';

    try {
        const res = await fetch(`${API}/api/auth/verify-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, otp })
        });
        const data = await res.json();

        if (data.success) {
            showAlert('Email verified successfully! Redirecting to login...', 'success');
            // Update stored user object
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            if (user) { user.email_verified = true; localStorage.setItem('user', JSON.stringify(user)); }
            setTimeout(() => { window.location.href = '/login'; }, 2000);
        } else {
            showAlert(data.message || 'Invalid code. Please try again.', 'danger');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle"></i> Verify Email';
        }
    } catch {
        showAlert('Cannot connect to server.', 'danger');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-circle"></i> Verify Email';
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    const email = params.get('email') || localStorage.getItem('verificationEmail') || '';

    if (!email) {
        showAlert('No email found. Please register first.', 'danger');
        setTimeout(() => { window.location.href = '/register'; }, 2500);
        return;
    }

    document.getElementById('email').value = email;

    // Auto-send OTP on page load
    const username = params.get('username') || email.split('@')[0];
    showAlert('Sending verification code to your email...', 'info');
    const ok = await sendOtp(email, username);
    showAlert(
        ok ? 'Verification code sent! Check your inbox (and spam folder).' : 'Could not send code automatically. Use Resend.',
        ok ? 'success' : 'danger'
    );
    startResendTimer();
});
