/**
 * Notification System — reads real notifications from the database
 * API: GET /api/auth/notifications
 */

function getToken() { return localStorage.getItem('token'); }

async function initNotifications(role) {
    const navRight = document.querySelector('.topbar-right');
    if (!navRight) return;

    // Insert bell HTML first (with 0 badge)
    navRight.insertAdjacentHTML('afterbegin', `
        <div class="notif-wrapper" id="notifWrapper">
            <button class="notif-bell" id="notifBell" onclick="toggleNotifDropdown()" aria-label="Notifications">
                <i class="bi bi-bell-fill"></i>
                <span class="notif-badge d-none" id="notifBadge">0</span>
            </button>
            <div class="notif-dropdown" id="notifDropdown">
                <div class="notif-header">
                    <span>Notifications</span>
                    <button class="notif-mark-all" onclick="markAllRead()">Mark all read</button>
                </div>
                <div class="notif-list" id="notifList">
                    <div class="notif-empty"><i class="bi bi-arrow-repeat"></i><p>Loading...</p></div>
                </div>
                <div class="notif-footer" id="notifFooter">0 notifications</div>
            </div>
        </div>
    `);

    // Close dropdown on outside click
    document.addEventListener('click', function (e) {
        const wrapper = document.getElementById('notifWrapper');
        if (wrapper && !wrapper.contains(e.target)) {
            const dd = document.getElementById('notifDropdown');
            if (dd) dd.classList.remove('open');
        }
    });

    // Load notifications from DB
    await loadNotifications();

    // Poll every 30 seconds for new notifications
    setInterval(loadNotifications, 30000);
}

async function loadNotifications() {
    try {
        const res  = await fetch('/api/auth/notifications', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();

        if (!data.success) return;

        renderNotifications(data.notifications);
        updateBadge(data.unread_count);

        const footer = document.getElementById('notifFooter');
        if (footer) footer.textContent = data.notifications.length + ' notifications';

    } catch { /* silent fail — don't break the page */ }
}

function renderNotifications(notifications) {
    const list = document.getElementById('notifList');
    if (!list) return;

    if (!notifications || notifications.length === 0) {
        list.innerHTML = '<div class="notif-empty"><i class="bi bi-bell-slash"></i><p>No notifications yet</p></div>';
        return;
    }

    // Icon map by notification type
    const iconMap = {
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

    list.innerHTML = notifications.map(n => {
        const cfg   = iconMap[n.type] || iconMap['info'];
        const time  = n.created_at ? timeAgo(n.created_at) : '';
        const unread = !n.is_read;
        return `
            <div class="notif-item ${unread ? 'unread' : ''}" onclick="markOneRead(${n.id})">
                <div class="notif-icon" style="background:${cfg.color}20;color:${cfg.color};">
                    <i class="bi ${cfg.icon}"></i>
                </div>
                <div class="notif-content">
                    <div class="notif-title">${escHtml(n.title)}</div>
                    <div class="notif-msg">${escHtml(n.message)}</div>
                    <div class="notif-time"><i class="bi bi-clock"></i> ${time}</div>
                </div>
                ${unread ? '<div class="notif-dot"></div>' : ''}
            </div>
        `;
    }).join('');
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

function toggleNotifDropdown() {
    const dd = document.getElementById('notifDropdown');
    if (dd) dd.classList.toggle('open');
}

async function markOneRead(id) {
    try {
        await fetch('/api/auth/notifications/' + id + '/read', {
            method: 'PUT',
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        await loadNotifications();
    } catch { /* silent */ }
}

async function markAllRead() {
    try {
        await fetch('/api/auth/notifications/read-all', {
            method: 'PUT',
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        await loadNotifications();
    } catch { /* silent */ }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function escHtml(str) {
    const d = document.createElement('div');
    d.textContent = str || '';
    return d.innerHTML;
}

function timeAgo(isoString) {
    const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
    if (diff < 60)   return diff + 's ago';
    if (diff < 3600) return Math.floor(diff / 60) + ' min ago';
    if (diff < 86400) return Math.floor(diff / 3600) + ' hr ago';
    return Math.floor(diff / 86400) + ' day ago';
}
