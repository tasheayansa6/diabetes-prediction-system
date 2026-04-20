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
    const user = JSON.parse(localStorage.getItem('user') || '{}');

    if (!user.username || !user.role) {
        window.location.href = '/login';
        return null;
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
