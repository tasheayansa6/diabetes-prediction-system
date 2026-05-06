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

// ── Token refresh helper ──────────────────────────────────────────────────────
// Silently calls /api/auth/refresh and updates localStorage.
// Returns true if a fresh token was stored, false otherwise.
async function _refreshToken() {
    const token = localStorage.getItem('token');
    if (!token) return false;
    try {
        const r = await fetch('/api/auth/refresh', {
            method: 'POST', headers: { 'Authorization': 'Bearer ' + token }
        });
        if (!r.ok) return false;
        const d = await r.json();
        if (d.success && d.token) {
            localStorage.setItem('token', d.token);
            if (d.user) {
                const stored = JSON.parse(localStorage.getItem('user') || '{}');
                const merged = Object.assign({}, stored);
                Object.keys(d.user).forEach(k => { if (d.user[k] != null) merged[k] = d.user[k]; });
                localStorage.setItem('user', JSON.stringify(merged));
            }
            return true;
        }
    } catch (_) {}
    return false;
}

// ── Role-based page protection ────────────────────────────────────────────────
// Starts immediately (before DOMContentLoaded). If the token is expired or the
// user object is incomplete, attempts a silent refresh FIRST — then decides
// whether to redirect. Stored as a promise so _patchDCL can block all
// DOMContentLoaded handlers until the refresh is done.
let _guardPagePromise = (async function _guardPage() {
    if (typeof window === 'undefined') return;
    const path = window.location.pathname;
    if (!path.startsWith('/templates/')) return;

    // Payment pages excluded — Chapa redirects here without a valid session
    if (path.includes('/templates/payment/')) return;

    const ROLE_GUARDS = [
        { prefix: '/templates/admin/',      roles: ['admin'] },
        { prefix: '/templates/doctor/',     roles: ['doctor'] },
        { prefix: '/templates/nurse/',      roles: ['nurse'] },
        { prefix: '/templates/lab/',        roles: ['lab_technician'] },
        { prefix: '/templates/pharmacist/', roles: ['pharmacist'] },
        { prefix: '/templates/patient/',    roles: ['patient'] },
    ];

    const guard = ROLE_GUARDS.find(g => path.startsWith(g.prefix));
    if (!guard) return;

    // Coming from payment success — session was just refreshed, skip redirect
    if (sessionStorage.getItem('_fromPayment')) {
        sessionStorage.removeItem('_fromPayment');
        return;
    }

    let token = localStorage.getItem('token');
    let user  = JSON.parse(localStorage.getItem('user') || '{}');

    // Refresh if token is expired OR user object is missing role/id
    if (token) {
        try {
            const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
            const pl  = JSON.parse(atob(b64 + '='.repeat((4 - b64.length % 4) % 4)));
            const expired    = pl.exp && pl.exp * 1000 < Date.now();
            const incomplete = !user.role || !user.id;
            if (expired || incomplete) {
                await _refreshToken();
                token = localStorage.getItem('token');
                user  = JSON.parse(localStorage.getItem('user') || '{}');
            }
        } catch (_) {}
    }

    if (!token || !user.role) {
        window.location.replace('/login');
        return;
    }
    if (!guard.roles.includes(user.role)) {
        window.location.replace(ROLE_DASHBOARDS[user.role] || '/login');
    }
}());

// ── DOMContentLoaded gate ─────────────────────────────────────────────────────
// Patches both document.addEventListener and window.addEventListener so every
// DOMContentLoaded handler waits for _guardPagePromise before running.
// This guarantees checkAuth always reads a refreshed token — zero changes
// needed in any of the 35+ page-level JS files.
(function _patchDCL() {
    function _wrap(orig, ctx) {
        return function(type, fn, opts) {
            if (type === 'DOMContentLoaded') {
                orig.call(ctx, 'DOMContentLoaded', async function(e) {
                    await _guardPagePromise;
                    fn(e);
                }, opts);
            } else {
                orig.call(ctx, type, fn, opts);
            }
        };
    }
    document.addEventListener = _wrap(document.addEventListener, document);
    window.addEventListener   = _wrap(window.addEventListener,   window);
}());

// ── Full localStorage wipe ────────────────────────────────────────────────────
// Called ONLY on explicit logout or new login.
function _clearAllStorage() {
    const onPaymentFlow = window.location.pathname.includes('/payment/');
    const keysToRemove = [
        'token', 'user',
        'lastTransaction', 'chapaPendingContext',
        'lastError', 'currentPredictionId',
    ];
    if (!onPaymentFlow) {
        keysToRemove.push(
            'predictionPaid', 'labPaid', 'lab_request_id',
            'pendingHealthData', 'pendingHealthData_anon'
        );
    }
    keysToRemove.forEach(k => localStorage.removeItem(k));

    if (!onPaymentFlow) {
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
            )) { toDelete.push(key); }
        }
        toDelete.forEach(k => localStorage.removeItem(k));
    }
}

// ── Decode JWT payload safely ─────────────────────────────────────────────────
function _decodeToken(token) {
    try {
        const b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        const padded = b64 + '='.repeat((4 - b64.length % 4) % 4);
        return JSON.parse(atob(padded));
    } catch (_) { return null; }
}

// ── checkAuth ─────────────────────────────────────────────────────────────────
// Synchronous — safe because _patchDCL ensures every DOMContentLoaded handler
// awaits _guardPagePromise before running, so the token is already refreshed
// by the time any page calls checkAuth.
function checkAuth(requiredRole) {
    const token = localStorage.getItem('token');
    const user  = JSON.parse(localStorage.getItem('user') || '{}');

    if (!token || !(user.username || user.name) || !user.role) {
        window.location.href = '/login';
        return null;
    }

    const payload = _decodeToken(token);
    if (!payload) {
        window.location.href = '/login';
        return null;
    }

    if (payload.exp && payload.exp * 1000 < Date.now()) {
        window.location.href = '/login?reason=session_expired';
        return null;
    }

    if (payload.user_id && user.id && String(payload.user_id) !== String(user.id)) {
        window.location.href = '/login';
        return null;
    }

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

function handleLogout() { logout(); }

// ── getCurrentUser ────────────────────────────────────────────────────────────
function getCurrentUser() {
    return JSON.parse(localStorage.getItem('user') || '{}');
}

// ── updateUserDisplay ─────────────────────────────────────────────────────────
function updateUserDisplay(user) {
    const displayName = user.name || user.username || 'User';
    const uid = user.unique_id || null;

    document.title = uid
        ? displayName + ' (' + uid + ') — Diabetes Prediction System'
        : displayName + ' — Diabetes Prediction System';

    ['topUserName', 'userName', 'navUserName', 'sidebarName', 'sidebarDoctorName'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = displayName;
    });

    if (uid) {
        ['sidebarUniqueId', 'sidebarPatientId'].forEach(function(id) {
            const el = document.getElementById(id);
            if (el) { el.textContent = 'ID: ' + uid; el.style.display = ''; }
        });
    }
}

// ── initAuth ──────────────────────────────────────────────────────────────────
function initAuth(requiredRole) {
    const user = checkAuth(requiredRole);
    if (user) updateUserDisplay(user);
    return user;
}

// ── Mobile sidebar hamburger ──────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', function () {
    const topbar  = document.querySelector('.topbar');
    const sidebar = document.querySelector('.sidebar');
    if (!topbar || !sidebar) return;

    const btn = document.createElement('button');
    btn.className = 'sidebar-toggle';
    btn.title     = 'Menu';
    btn.innerHTML = '<i class="bi bi-list"></i>';
    btn.setAttribute('aria-label', 'Toggle sidebar');
    topbar.insertBefore(btn, topbar.firstChild);

    const backdrop = document.createElement('div');
    backdrop.className = 'sidebar-backdrop';
    document.body.appendChild(backdrop);

    function openSidebar()  { sidebar.classList.add('open');    backdrop.classList.add('show');    btn.innerHTML = '<i class="bi bi-x-lg"></i>'; }
    function closeSidebar() { sidebar.classList.remove('open'); backdrop.classList.remove('show'); btn.innerHTML = '<i class="bi bi-list"></i>'; }

    btn.addEventListener('click', function () {
        sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
    });
    backdrop.addEventListener('click', closeSidebar);
    sidebar.querySelectorAll('a').forEach(a => a.addEventListener('click', closeSidebar));
});

// ── Token auto-refresh ────────────────────────────────────────────────────────
async function _autoRefreshToken() {
    try {
        const token = localStorage.getItem('token');
        if (!token) return;
        const payload = _decodeToken(token);
        if (!payload || !payload.exp) return;
        const secsLeft = payload.exp - Math.floor(Date.now() / 1000);

        // Show warning if less than 3 days remain
        if (secsLeft > 0 && secsLeft < 259200) {
            const hoursLeft = Math.ceil(secsLeft / 3600);
            const daysLeft  = Math.ceil(secsLeft / 86400);
            const label = daysLeft <= 1
                ? hoursLeft + ' hour' + (hoursLeft !== 1 ? 's' : '')
                : daysLeft  + ' day'  + (daysLeft  !== 1 ? 's' : '');
            if (!document.getElementById('_sessionWarnBanner')) {
                const banner = document.createElement('div');
                banner.id = '_sessionWarnBanner';
                banner.style.cssText = 'position:fixed;bottom:1rem;left:50%;transform:translateX(-50%);background:#92400e;color:#fff;padding:.65rem 1.25rem;border-radius:10px;font-size:.82rem;font-weight:600;z-index:99999;display:flex;align-items:center;gap:.75rem;box-shadow:0 4px 20px rgba(0,0,0,.25);max-width:420px';
                banner.innerHTML = '<i class="bi bi-clock-history" style="font-size:1rem;flex-shrink:0;"></i>'
                    + '<span>Session expires in <strong>' + label + '</strong>. '
                    + '<a href="#" onclick="_extendSession(event)" style="color:#fde68a;text-decoration:underline;">Stay logged in</a></span>'
                    + '<button onclick="document.getElementById(\'_sessionWarnBanner\').remove()" style="background:none;border:none;color:#fff;font-size:1.1rem;cursor:pointer;padding:0;line-height:1;margin-left:.25rem;">&times;</button>';
                document.body.appendChild(banner);
            }
        }

        // Only refresh if less than 7 days remain
        if (secsLeft > 604800) return;

        await _refreshToken();
        const b = document.getElementById('_sessionWarnBanner');
        if (b) b.remove();
    } catch (_) { /* non-fatal */ }
}

async function _extendSession(e) {
    e.preventDefault();
    await _autoRefreshToken();
}

window.addEventListener('DOMContentLoaded', _autoRefreshToken);
