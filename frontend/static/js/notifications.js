/**
 * Notification System
 */

function getToken() { return localStorage.getItem('token'); }

const ICON_MAP = {
    'high_risk_alert': { icon: 'bi-exclamation-triangle-fill', color: '#dc2626' },
    'prediction':      { icon: 'bi-graph-up-arrow',            color: '#059669' },
    'vitals':          { icon: 'bi-heart-pulse-fill',          color: '#2563eb' },
    'lab_result':      { icon: 'bi-flask-fill',                color: '#0891b2' },
    'lab_order':       { icon: 'bi-clipboard2-pulse',          color: '#d97706' },
    'prescription':    { icon: 'bi-capsule',                   color: '#7c3aed' },
    'appointment':     { icon: 'bi-calendar-check-fill',       color: '#059669' },
    'payment':         { icon: 'bi-credit-card-fill',          color: '#d97706' },
    'info':            { icon: 'bi-info-circle-fill',          color: '#64748b' },
};

const NOTIF_URLS = {
    'high_risk_alert': '/templates/patient/prediction_history.html',
    'prediction':      '/templates/patient/prediction_history.html',
    'vitals':          '/templates/doctor/patient_list.html',
    'lab_result':      '/templates/patient/lab_results.html',
    'lab_order':       '/templates/lab/enter_lab_results.html',
    'prescription':    '/templates/pharmacist/prescription_review.html',
    'appointment':     '/templates/patient/appointment.html',
    'payment':         '/templates/payment/payment_history.html',
    'info':            '/templates/patient/dashboard.html',
};

let _notifInterval = null;

async function initNotifications() {
    const navRight = document.querySelector('.topbar-right');
    if (!navRight) return;

    // Clear any previous interval (e.g. from a previous user's session on same tab)
    if (_notifInterval) { clearInterval(_notifInterval); _notifInterval = null; }

    // Remove existing notification widget if present (prevents duplicate on re-init)
    const existing = document.getElementById('notifWrapper');
    if (existing) existing.remove();

    navRight.insertAdjacentHTML('afterbegin', `
        <div class="notif-wrapper" id="notifWrapper">
            <button class="notif-bell" id="notifBell" aria-label="Notifications">
                <i class="bi bi-bell-fill"></i>
                <span class="notif-badge d-none" id="notifBadge">0</span>
            </button>
            <div class="notif-dropdown" id="notifDropdown">
                <div class="notif-header">
                    <span>Notifications</span>
                    <button class="notif-mark-all" id="notifMarkAll">Mark all read</button>
                </div>
                <div class="notif-list" id="notifList">
                    <div class="notif-empty"><i class="bi bi-arrow-repeat"></i><p>Loading...</p></div>
                </div>
                <div class="notif-footer" id="notifFooter">0 notifications</div>
            </div>
        </div>
    `);

    document.getElementById('notifBell').addEventListener('click', function (e) {
        e.stopPropagation();
        document.getElementById('notifDropdown').classList.toggle('open');
    });

    document.getElementById('notifMarkAll').addEventListener('click', function (e) {
        e.stopPropagation();
        markAllRead();
    });

    // Close on outside click
    document.addEventListener('click', function (e) {
        const wrapper = document.getElementById('notifWrapper');
        if (wrapper && !wrapper.contains(e.target)) {
            const dd = document.getElementById('notifDropdown');
            if (dd) dd.classList.remove('open');
        }
    });

    await loadNotifications();
    _notifInterval = setInterval(loadNotifications, 60000);
}

async function loadNotifications() {
    // Guard: if no token or user in storage, clear the widget and stop
    const token = getToken();
    const storedUser = JSON.parse(localStorage.getItem('user') || '{}');
    if (!token || !storedUser.id) {
        const list = document.getElementById('notifList');
        if (list) list.innerHTML = '<div class="notif-empty"><i class="bi bi-bell-slash"></i><p>Not signed in</p></div>';
        updateBadge(0);
        return;
    }
    try {
        const res  = await fetch('/api/auth/notifications?limit=20&offset=0', {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        // 401 means token is invalid/expired — clear widget, don't redirect
        if (res.status === 401) {
            const list = document.getElementById('notifList');
            if (list) list.innerHTML = '<div class="notif-empty"><i class="bi bi-bell-slash"></i><p>Session expired</p></div>';
            updateBadge(0);
            return;
        }
        const data = await res.json();
        if (!data.success) return;
        renderNotifications(data.notifications);
        updateBadge(data.unread_count);
        const footer = document.getElementById('notifFooter');
        if (footer) {
            const total = data.pagination?.total || data.notifications.length;
            footer.textContent = data.notifications.length + ' of ' + total + ' notifications';
        }
    } catch (e) { console.warn('loadNotifications error:', e); }
}

function renderNotifications(notifications) {
    const list = document.getElementById('notifList');
    if (!list) return;

    if (!notifications || notifications.length === 0) {
        list.innerHTML = '<div class="notif-empty"><i class="bi bi-bell-slash"></i><p>No notifications yet</p></div>';
        return;
    }

    list.innerHTML = notifications.map(n => {
        const cfg    = ICON_MAP[n.type] || ICON_MAP['info'];
        const time   = n.created_at ? timeAgo(n.created_at) : '';
        const unread = !n.is_read;
        const url    = n.link || NOTIF_URLS[n.type] || '';
        return `
            <div class="notif-item ${unread ? 'unread' : ''}" id="notif-${n.id}">
                <div class="notif-icon" style="background:${cfg.color}20;color:${cfg.color};">
                    <i class="bi ${cfg.icon}"></i>
                </div>
                <div class="notif-content" data-notif-id="${n.id}" data-url="${url.replace(/"/g,'&quot;')}">
                    <div class="notif-title">${escHtml(n.title)}</div>
                    <div class="notif-msg">${escHtml(n.message)}</div>
                    <div class="notif-time"><i class="bi bi-clock"></i> ${time}</div>
                </div>
                ${unread ? '<div class="notif-dot"></div>' : ''}
                <button class="notif-delete-btn" id="del-${n.id}" title="Delete">
                    <i class="bi bi-trash"></i>
                </button>
            </div>`;
    }).join('');

    // Bind each delete button directly — most reliable approach
    notifications.forEach(function(n) {
        const delBtn = document.getElementById('del-' + n.id);
        if (delBtn) {
            delBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                e.preventDefault();
                doDelete(n.id);
            });
        }

        // Row click for navigation (only on content area)
        const content = list.querySelector('#notif-' + n.id + ' .notif-content');
        if (content) {
            const url = n.link || NOTIF_URLS[n.type] || '';
            content.style.cursor = 'pointer';
            content.addEventListener('click', function(e) {
                e.stopPropagation();
                markOneRead(n.id, url);
            });
        }
    });
}

function updateBadge(count) {
    const badge = document.getElementById('notifBadge');
    if (!badge) return;
    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.classList.remove('d-none');
    } else {
        badge.classList.add('d-none');
    }
}

async function markOneRead(id, url) {
    try {
        await fetch('/api/auth/notifications/' + id + '/read', {
            method: 'PUT',
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
    } catch (e) { console.warn('markOneRead error:', e); }
    if (url) window.location.href = url;
    else await loadNotifications();
}

async function markAllRead() {
    try {
        await fetch('/api/auth/notifications/read-all', {
            method: 'PUT',
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        await loadNotifications();
    } catch (e) { console.warn('markAllRead error:', e); }
}

async function doDelete(id) {
    // Remove from DOM immediately
    const el = document.getElementById('notif-' + id);
    if (el) {
        const wasUnread = el.classList.contains('unread');
        el.remove();

        const list      = document.getElementById('notifList');
        const remaining = list ? list.querySelectorAll('.notif-item').length : 0;
        const footer    = document.getElementById('notifFooter');
        if (footer) footer.textContent = remaining + ' notifications';

        if (wasUnread) {
            const badge = document.getElementById('notifBadge');
            if (badge && !badge.classList.contains('d-none')) {
                const next = Math.max(0, (parseInt(badge.textContent) || 0) - 1);
                if (next > 0) {
                    badge.textContent = next > 99 ? '99+' : next;
                } else {
                    badge.classList.add('d-none');
                }
            }
        }

        if (remaining === 0 && list) {
            list.innerHTML = '<div class="notif-empty"><i class="bi bi-bell-slash"></i><p>No notifications yet</p></div>';
        }
    }

    // Call API
    try {
        await fetch('/api/auth/notifications/' + id, {
            method: 'DELETE',
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
    } catch (e) { console.warn('doDelete error:', e); }
}

function escHtml(str) {
    const d = document.createElement('div');
    d.textContent = str || '';
    return d.innerHTML;
}

function timeAgo(isoString) {
    const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
    if (diff < 60)    return diff + 's ago';
    if (diff < 3600)  return Math.floor(diff / 60) + ' min ago';
    if (diff < 86400) return Math.floor(diff / 3600) + ' hr ago';
    return Math.floor(diff / 86400) + ' day ago';
}
