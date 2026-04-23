// Payment Failed Page

document.addEventListener('DOMContentLoaded', function () {
    // Don't require auth — payment failed page must be accessible without login
    try {
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        const nameEl = document.getElementById('navUserName');
        if (nameEl && user.username) nameEl.textContent = user.username;
    } catch (_) {}

    const error = JSON.parse(localStorage.getItem('lastError') || '{}');
    document.getElementById('errorCode').textContent = error.code || 'PAYMENT_ERROR';
    document.getElementById('errorMessage').textContent = error.message || 'Payment could not be processed. Please try again.';
    document.getElementById('errorDate').textContent = error.date || new Date().toLocaleDateString();
});
