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

// ── Role-based page protection ───────────────────────────────────────────────
// Maps URL path prefixes to required roles. Runs on every page load.
(function _guardPage() {
    if (typeof window === 'undefined') return;
    const path = window.location.pathname;
    if (!path.startsWith('/templates/')) return;

    const ROLE_GUARDS = [
        { prefix: '/templates/admin/',      roles: ['admin'] },
        { prefix: '/templates/doctor/',     roles: ['doctor'] },
        { prefix: '/templates/nurse/',      roles: ['nurse'] },
        { prefix: '/templates/lab/',        roles: ['lab_technician'] },
        { prefix: '/templates/pharmacist/', roles: ['pharmacist'] },
        { prefix: '/templates/patient/',    roles: ['patient'] },
        { prefix: '/templates/payment/',    roles: ['patient', 'admin'] },
    ];

    const guard = ROLE_GUARDS.find(g => path.startsWith(g.prefix));
    if (!guard) return;

    const token = localStorage.getItem('token');
    const user  = JSON.parse(localStorage.getItem('user') || '{}');

    if (!token || !user.role) {
        window.location.replace('/login');
        return;
    }
    if (!guard.roles.includes(user.role)) {
        // Redirect to their own dashboard instead of showing a blank page
        const dash = ROLE_DASHBOARDS[user.role] || '/login';
        window.location.replace(dash);
    }
}());

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

    // Also clear any user-scoped keys
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
        const padded = b64 + '='.repeat((4 - b64.length % 4) % 4);
        return JSON.parse(atob(padded));
    } catch (_) {
        return null;
    }
}

// ── checkAuth ─────────────────────────────────────────────────────────────────
function checkAuth(requiredRole) {
    const token = localStorage.getItem('token');
    const user  = JSON.parse(localStorage.getItem('user') || '{}');

    if (!token || !user.username || !user.role) {
        window.location.href = '/login';
        return null;
    }

    const payload = _decodeToken(token);

    if (!payload) {
        logout();
        return null;
    }

    // Token expired
    if (payload.exp && payload.exp * 1000 < Date.now()) {
        logout();
        return null;
    }

    // Mismatch between stored user and token — only redirect to login,
    // do NOT wipe storage here. Wiping here causes the logout-on-predict bug
    // because payment keys get cleared mid-flow on the result page.
    // The login page already calls _clearAllStorage() before writing new session.
    if (payload.user_id && user.id && String(payload.user_id) !== String(user.id)) {
        window.location.href = '/login';
        return null;
    }

    // Role check
    if (requiredRole) {
        const roles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
        if (!roles.includes(user.role)) {
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

// ── Mobile sidebar hamburger ────────────────────────────────────────────────────────
// Injects a hamburger toggle into the topbar and wires up the sidebar
// on mobile. Runs on every page that includes auth.js.
if (typeof window !== 'undefined') {
    window.addEventListener('DOMContentLoaded', function () {
        const topbarLeft = document.querySelector('.topbar');
        const sidebar    = document.querySelector('.sidebar');
        if (!topbarLeft || !sidebar) return;

        // Inject hamburger button before the brand
        const btn = document.createElement('button');
        btn.className   = 'sidebar-toggle';
        btn.title       = 'Menu';
        btn.innerHTML   = '<i class="bi bi-list"></i>';
        btn.setAttribute('aria-label', 'Toggle sidebar');
        topbarLeft.insertBefore(btn, topbarLeft.firstChild);

        // Inject backdrop
        const backdrop = document.createElement('div');
        backdrop.className = 'sidebar-backdrop';
        document.body.appendChild(backdrop);

        function openSidebar()  { sidebar.classList.add('open');  backdrop.classList.add('show');  btn.innerHTML = '<i class="bi bi-x-lg"></i>'; }
        function closeSidebar() { sidebar.classList.remove('open'); backdrop.classList.remove('show'); btn.innerHTML = '<i class="bi bi-list"></i>'; }

        btn.addEventListener('click', function () {
            sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
        });
        backdrop.addEventListener('click', closeSidebar);

        // Close sidebar when a nav link is clicked on mobile
        sidebar.querySelectorAll('a').forEach(function (a) {
            a.addEventListener('click', closeSidebar);
        });
    });
}

// ── Token auto-refresh ────────────────────────────────────────────────────────
// Silently renews the JWT when it has less than 7 days remaining.
// Called once on page load — fire-and-forget, never blocks the page.
async function _autoRefreshToken() {
    try {
        const token = localStorage.getItem('token');
        if (!token) return;
        const payload = _decodeToken(token);
        if (!payload || !payload.exp) return;
        const secsLeft = payload.exp - Math.floor(Date.now() / 1000);

        // Show warning banner if less than 3 days remain
        if (secsLeft > 0 && secsLeft < 259200) {
            const daysLeft = Math.ceil(secsLeft / 86400);
            const hoursLeft = Math.ceil(secsLeft / 3600);
            const label = daysLeft <= 1 ? `${hoursLeft} hour${hoursLeft !== 1 ? 's' : ''}` : `${daysLeft} day${daysLeft !== 1 ? 's' : ''}`;
            // Inject banner once
            if (!document.getElementById('_sessionWarnBanner')) {
                const banner = document.createElement('div');
                banner.id = '_sessionWarnBanner';
                banner.style.cssText = [
                    'position:fixed', 'bottom:1rem', 'left:50%', 'transform:translateX(-50%)',
                    'background:#92400e', 'color:#fff', 'padding:.65rem 1.25rem',
                    'border-radius:10px', 'font-size:.82rem', 'font-weight:600',
                    'z-index:99999', 'display:flex', 'align-items:center', 'gap:.75rem',
                    'box-shadow:0 4px 20px rgba(0,0,0,.25)', 'max-width:420px'
                ].join(';');
                banner.innerHTML =
                    `<i class="bi bi-clock-history" style="font-size:1rem;flex-shrink:0;"></i>` +
                    `<span>Your session expires in <strong>${label}</strong>. ` +
                    `<a href="#" onclick="_extendSession(event)" style="color:#fde68a;text-decoration:underline;">Stay logged in</a></span>` +
                    `<button onclick="document.getElementById('_sessionWarnBanner').remove()" ` +
                    `style="background:none;border:none;color:#fff;font-size:1.1rem;cursor:pointer;padding:0;line-height:1;margin-left:.25rem;">&times;</button>`;
                document.body.appendChild(banner);
            }
        }

        // Refresh if less than 7 days (604800s) remaining
        if (secsLeft > 604800) return;
        const res = await fetch('/api/auth/refresh', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token }
        });
        if (!res.ok) return;
        const data = await res.json();
        if (data.success && data.token) {
            localStorage.setItem('token', data.token);
            if (data.user) {
                const stored = JSON.parse(localStorage.getItem('user') || '{}');
                localStorage.setItem('user', JSON.stringify({ ...stored, ...data.user }));
            }
            // Remove warning banner after successful refresh
            const b = document.getElementById('_sessionWarnBanner');
            if (b) b.remove();
        }
    } catch (_) { /* non-fatal */ }
}

async function _extendSession(e) {
    e.preventDefault();
    await _autoRefreshToken();
}

// Run refresh check on every page load
if (typeof window !== 'undefined') {
    window.addEventListener('DOMContentLoaded', _autoRefreshToken);
}
