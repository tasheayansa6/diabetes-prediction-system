// Authentication and User Management
// Common functions used across all pages

const ROLE_DASHBOARDS = {
    patient:        '/templates/patient/dashboard.html',
    doctor:         '/templates/doctor/dashboard.html',
    nurse:          '/templates/nurse/dashboard.html',
    lab_technician: '/templates/lab/dashboard.html',
    pharmacist:     '/templates/pharmacist/dashboard.html',
    admin:          '/templates/admin/dashboard.html'
};

// Check if user is authenticated and has correct role
function checkAuth(requiredRole) {
    const user  = JSON.parse(localStorage.getItem('user') || '{}');
    const token = localStorage.getItem('token');

    if (!user.username || !user.role || !token) {
        window.location.href = '/login';
        return null;
    }

    // Validate token expiry client-side before any API call
    // JWT uses URL-safe base64 — must convert before atob()
    try {
        const b64 = token.split('.')[1]
            .replace(/-/g, '+')
            .replace(/_/g, '/');
        const payload = JSON.parse(atob(b64));
        if (payload.exp && payload.exp * 1000 < Date.now()) {
            // Token expired — clean up and redirect to login
            logout();
            return null;
        }
    } catch (_) {
        // Could not decode token — leave it alone, let the server validate
        // Do NOT logout here: a decode error doesn't mean the token is invalid
    }

    if (requiredRole) {
        const roles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
        if (!roles.includes(user.role)) {
            // Redirect to their correct dashboard silently
            window.location.href = ROLE_DASHBOARDS[user.role] || '/login';
            return null;
        }
    }

    return user;
}

// Get current logged in user
function getCurrentUser() {
    return JSON.parse(localStorage.getItem('user') || '{}');
}

// Update user display name in navbar
function updateUserDisplay(user) {
    const displayName = user.name || user.username || 'User';
    const ids = ['topUserName', 'userName', 'navUserName', 'sidebarName', 'sidebarDoctorName'];
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = displayName;
    });
}

// Logout — no confirm dialog, clean and direct
function logout() {
    // Clear all user-scoped payment keys before removing user object
    try {
        const u = JSON.parse(localStorage.getItem('user') || '{}');
        const uid = u.id || u.user_id || 'anon';
        ['lastTransaction_', 'chapaPendingContext_', 'predictionPaid_', 'labPaid_', 'lab_request_id_'].forEach(prefix => {
            localStorage.removeItem(prefix + uid);
        });
    } catch (_) {}
    // Clear legacy unscoped keys too
    localStorage.removeItem('lastTransaction');
    localStorage.removeItem('chapaPendingContext');
    localStorage.removeItem('predictionPaid');
    localStorage.removeItem('labPaid');
    localStorage.removeItem('lab_request_id');
    localStorage.removeItem('pendingHealthData');
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    window.location.href = '/login';
}

// Alias used by admin pages
function handleLogout() {
    logout();
}

// Initialize authentication on page load
function initAuth(requiredRole) {
    const user = checkAuth(requiredRole);
    if (user) {
        updateUserDisplay(user);
    }
    return user;
}
