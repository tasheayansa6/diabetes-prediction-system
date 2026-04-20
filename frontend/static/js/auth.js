// Authentication and User Management
// Single source of truth for all auth logic across every page.

const ROLE_DASHBOARDS = {
    patient:        '/templates/patient/dashboard.html',
    doctor:         '/templates/doctor/dashboard.html',
    nurse:          '/templates/nurse/dashboard.html',
    lab_technician: '/templates/lab/dashboard.html',
    pharmacist:     '/templates/pharmacist/dashboard.html',
    admin:          '/templates/admin/dashboard.html'
};

// ── Full localStorage wipe ────────────────────────────────────────────────────
// Called on logout AND on login (to clear any previous user's data).
function _clearAllStorage() {
    // Clear every known key — both scoped and legacy
    const keysToRemove = [
        'token', 'user',
        'lastTransaction', 'chapaPendingContext',
        'predictionPaid', 'labPaid', 'lab_request_id',
        'pendingHealthData', 'pendingHealthData_anon',
        'lastError', 'currentPredictionId',
    ];
    keysToRemove.forEach(k => localStorage.removeItem(k));

    // Also clear any user-scoped keys (id 1–999)
    const toDelete = [];
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && (
            key.startsWith('lastTransaction_') ||
            key.startsWith('chapaPendingContext_') ||
            key.startsWith('predictionPaid_') ||
            key.startsWith('labPaid_') ||
            key.startsWith('lab_request_id_') ||
            key.startsWith('pendingHealthData_')
        )) {
            toDelete.push(key);
        }
    }
    toDelete.forEach(k => localStorage.removeItem(k));
}

// ── Decode JWT payload safely (handles URL-safe base64) ───────────────────────
function _decodeToken(token) {
    try {
        const b64 = token.split('.')[1]
            .replace(/-/g, '+')
            .replace(/_/g, '/');
        // Pad to multiple of 4
        const padded = b64 + '='.repeat((4 - b64.length % 4) % 4);
        return JSON.parse(atob(padded));
    } catch (_) {
        return null;
    }
}

// ── checkAuth ─────────────────────────────────────────────────────────────────
// Call at the top of every page's DOMContentLoaded.
// Returns the user object if authenticated and role matches, otherwise redirects.
function checkAuth(requiredRole) {
    const token = localStorage.getItem('token');
    const user  = JSON.parse(localStorage.getItem('user') || '{}');

    // No token or no user → go to login
    if (!token || !user.username || !user.role) {
        window.location.href = '/login';
        return null;
    }

    // Decode token and validate
    const payload = _decodeToken(token);

    if (!payload) {
        // Malformed token — clear and go to login
        logout();
        return null;
    }

    // Token expired
    if (payload.exp && payload.exp * 1000 < Date.now()) {
        logout();
        return null;
    }

    // Mismatch between stored user and token (different user logged in on same browser)
    // This is the main cause of "another patient's page"
    if (payload.user_id && user.id && String(payload.user_id) !== String(user.id)) {
        // Token belongs to a different user — clear everything and go to login
        _clearAllStorage();
        window.location.href = '/login';
        return null;
    }

    // Role check
    if (requiredRole) {
        const roles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
        if (!roles.includes(user.role)) {
            // User is authenticated but wrong role for this page
            // Redirect to their own dashboard (not another patient's page)
            window.location.href = ROLE_DASHBOARDS[user.role] || '/login';
            return null;
        }
    }

    return user;
}

// ── logout ────────────────────────────────────────────────────────────────────
function logout() {
    _clearAllStorage();
    window.location.href = '/login';
}

// ── handleLogout ──────────────────────────────────────────────────────────────
// Alias used by admin/doctor/nurse pages
function handleLogout() {
    logout();
}

// ── getCurrentUser ────────────────────────────────────────────────────────────
function getCurrentUser() {
    return JSON.parse(localStorage.getItem('user') || '{}');
}

// ── updateUserDisplay ─────────────────────────────────────────────────────────
function updateUserDisplay(user) {
    const displayName = user.name || user.username || 'User';
    ['topUserName', 'userName', 'navUserName', 'sidebarName', 'sidebarDoctorName'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = displayName;
    });
}

// ── initAuth ──────────────────────────────────────────────────────────────────
function initAuth(requiredRole) {
    const user = checkAuth(requiredRole);
    if (user) updateUserDisplay(user);
    return user;
}
