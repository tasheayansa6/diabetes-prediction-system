// Payment Failed Page

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('patient');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;

    const error = JSON.parse(localStorage.getItem('lastError') || '{}');
    document.getElementById('errorCode').textContent = error.code || 'PAYMENT_ERROR';
    document.getElementById('errorMessage').textContent = error.message || 'Payment could not be processed. Please try again.';
    document.getElementById('errorDate').textContent = error.date || new Date().toLocaleDateString();
});
