const API = '';
let allAppointments = [];
let activeApptId    = null;
let confirmAction   = null;

function getToken() { return localStorage.getItem('token'); }
function esc(str) { const d = document.createElement('div'); d.textContent = str ?? ''; return d.innerHTML; }

async function apiFetch(path, options = {}) {
    const res = await fetch(API + path, {
        ...options,
        headers: { 'Authorization': 'Bearer ' + getToken(), 'Content-Type': 'application/json', ...(options.headers || {}) }
    });
    if (res.status === 401) { logout(); return {}; }
    return res.json();
}

// ── Load ──────────────────────────────────────────────────────────────────────
async function loadAppointments() {
    const tbody = document.getElementById('apptTableBody');
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:2rem;color:#94a3b8;"><div style="display:inline-block;width:20px;height:20px;border:2px solid #3b82f6;border-top-color:transparent;border-radius:50%;animation:spin 0.7s linear infinite;margin-right:8px;vertical-align:middle;"></div>Loading...</td></tr>`;
    try {
        const data = await apiFetch('/api/doctor/appointments?limit=200');
        if (!data.success) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:2rem;color:#dc2626;">${esc(data.message || 'Failed to load')}</td></tr>`;
            return;
        }
        allAppointments = data.appointments || [];
        updateCounts();
        renderTodayCard();
        renderTable();
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:2rem;color:#dc2626;"><i class="bi bi-wifi-off"></i> Cannot connect to server.</td></tr>`;
    }
}

// ── Counts ────────────────────────────────────────────────────────────────────
function updateCounts() {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('countToday').textContent     = allAppointments.filter(a => a.appointment_date === today).length;
    document.getElementById('countPending').textContent   = allAppointments.filter(a => a.status === 'scheduled').length;
    document.getElementById('countCompleted').textContent = allAppointments.filter(a => a.status === 'completed').length;
    document.getElementById('countCancelled').textContent = allAppointments.filter(a => a.status === 'cancelled').length;
}

// ── Today Quick View ──────────────────────────────────────────────────────────
function renderTodayCard() {
    const today = new Date().toISOString().split('T')[0];
    const todayAppts = allAppointments.filter(a => a.appointment_date === today);
    const card = document.getElementById('todayCard');
    const list = document.getElementById('todayList');
    if (!todayAppts.length) { card.style.display = 'none'; return; }
    card.style.display = 'block';
    list.innerHTML = todayAppts.map(a => `
        <div style="display:flex;align-items:center;gap:1rem;padding:0.85rem 1.25rem;border-bottom:1px solid #f1f5f9;">
            <div style="width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#1e3a8a,#2563eb);color:#fff;display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0;">
                <i class="bi bi-person"></i>
            </div>
            <div style="flex:1;">
                <div style="font-weight:700;font-size:0.9rem;">${esc(a.patient_name || 'Patient #' + a.patient_id)}</div>
                <div style="font-size:0.78rem;color:#64748b;"><i class="bi bi-clock"></i> ${esc(a.appointment_time || 'TBD')} &nbsp;·&nbsp; ${esc(a.reason || 'Consultation')}</div>
            </div>
            <span class="status-badge status-${esc(a.status)}">${esc(a.status)}</span>
            ${a.status === 'scheduled' ? `
            <div style="display:flex;gap:0.4rem;">
                <button class="action-icon-btn done" onclick="promptAction(${a.id},'completed')" title="Mark Complete"><i class="bi bi-check-lg"></i></button>
                <button class="action-icon-btn cancel" onclick="promptAction(${a.id},'cancelled')" title="Cancel"><i class="bi bi-x-lg"></i></button>
            </div>` : ''}
        </div>
    `).join('');
}

// ── Table ─────────────────────────────────────────────────────────────────────
function renderTable() {
    const search  = document.getElementById('searchInput').value.toLowerCase();
    const dateVal = document.getElementById('dateFilter').value;
    const status  = document.getElementById('statusFilter').value;

    const filtered = allAppointments.filter(a => {
        const matchSearch = !search || (a.patient_name || '').toLowerCase().includes(search) || String(a.patient_id).includes(search);
        const matchDate   = !dateVal || a.appointment_date === dateVal;
        const matchStatus = !status  || a.status === status;
        return matchSearch && matchDate && matchStatus;
    });

    document.getElementById('tableCount').textContent = `${filtered.length} of ${allAppointments.length} appointments`;
    const tbody = document.getElementById('apptTableBody');

    if (!filtered.length) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:2rem;color:#94a3b8;"><i class="bi bi-calendar-x" style="font-size:1.5rem;display:block;margin-bottom:0.5rem;"></i>No appointments found</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(a => `
        <tr>
            <td>
                <div style="font-weight:600;font-size:0.875rem;">${esc(a.patient_name || 'Patient #' + a.patient_id)}</div>
                <div style="font-size:0.72rem;color:#94a3b8;">ID: ${esc(String(a.patient_id))}</div>
            </td>
            <td style="font-size:0.875rem;">${esc(a.appointment_date)}</td>
            <td style="font-size:0.875rem;">${esc(a.appointment_time || '—')}</td>
            <td style="font-size:0.8rem;color:#64748b;">${esc(a.type || 'consultation')}</td>
            <td style="font-size:0.8rem;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(a.reason || '')}">${esc(a.reason || '—')}</td>
            <td><span class="status-badge status-${esc(a.status)}">${esc(a.status)}</span></td>
            <td>
                <div style="display:flex;gap:0.35rem;">
                    <button class="action-icon-btn view" onclick="openDetail(${a.id})" title="View Details"><i class="bi bi-eye"></i></button>
                    ${a.status === 'scheduled' ? `
                    <button class="action-icon-btn done"   onclick="promptAction(${a.id},'completed')" title="Mark Complete"><i class="bi bi-check-lg"></i></button>
                    <button class="action-icon-btn cancel" onclick="promptAction(${a.id},'cancelled')" title="Cancel"><i class="bi bi-x-lg"></i></button>
                    ` : ''}
                    ${a.status === 'scheduled' ? `
                    <button class="action-icon-btn" style="color:#d97706;border-color:#fde68a;" onclick="promptAction(${a.id},'no-show')" title="No Show"><i class="bi bi-person-x"></i></button>
                    ` : ''}
                </div>
            </td>
        </tr>
    `).join('');
}

// ── Detail Modal ──────────────────────────────────────────────────────────────
function openDetail(id) {
    const a = allAppointments.find(x => x.id === id);
    if (!a) return;
    activeApptId = id;

    const statusColors = { scheduled:'#1e40af', completed:'#166534', cancelled:'#991b1b', 'no-show':'#475569', pending:'#854d0e' };
    const statusBg     = { scheduled:'#dbeafe', completed:'#dcfce7', cancelled:'#fee2e2', 'no-show':'#f1f5f9', pending:'#fef9c3' };

    document.getElementById('apptModalBody').innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;">
            <div class="detail-row" style="grid-column:1/-1;">
                <span class="detail-label">Patient</span>
                <span class="detail-value" style="font-size:1rem;">${esc(a.patient_name || 'Patient #' + a.patient_id)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Status</span>
                <span style="background:${statusBg[a.status]||'#f1f5f9'};color:${statusColors[a.status]||'#475569'};padding:0.25em 0.75em;border-radius:99px;font-size:0.75rem;font-weight:700;">${esc(a.status)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Date</span>
                <span class="detail-value">${esc(a.appointment_date)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Time</span>
                <span class="detail-value">${esc(a.appointment_time || '—')}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Type</span>
                <span class="detail-value">${esc(a.type || 'consultation')}</span>
            </div>
            <div class="detail-row" style="grid-column:1/-1;">
                <span class="detail-label">Reason</span>
                <span class="detail-value">${esc(a.reason || '—')}</span>
            </div>
            ${a.notes ? `<div class="detail-row" style="grid-column:1/-1;"><span class="detail-label">Notes</span><span class="detail-value" style="font-weight:400;color:#475569;">${esc(a.notes)}</span></div>` : ''}
            <div class="detail-row">
                <span class="detail-label">Booked</span>
                <span class="detail-value" style="font-weight:400;font-size:0.8rem;color:#64748b;">${a.created_at ? new Date(a.created_at).toLocaleDateString('en-US',{year:'numeric',month:'short',day:'numeric'}) : '—'}</span>
            </div>
        </div>
    `;

    const footer = document.getElementById('apptModalFooter');
    footer.innerHTML = `<button class="btn btn-secondary" onclick="closeModal()">Close</button>`;
    if (a.status === 'scheduled') {
        footer.innerHTML = `
            <button class="btn btn-secondary" onclick="closeModal()">Close</button>
            <button class="btn btn-warning" onclick="closeModal();promptAction(${a.id},'no-show')" style="background:linear-gradient(135deg,#d97706,#f59e0b);color:#fff;"><i class="bi bi-person-x"></i> No Show</button>
            <button class="btn btn-danger"   onclick="closeModal();promptAction(${a.id},'cancelled')"><i class="bi bi-x-circle"></i> Cancel</button>
            <button class="btn btn-success"  onclick="closeModal();promptAction(${a.id},'completed')"><i class="bi bi-check-circle"></i> Complete</button>
        `;
    }

    document.getElementById('apptModal').style.display = 'flex';
}

function closeModal() { document.getElementById('apptModal').style.display = 'none'; }

// ── Confirm Action Modal ──────────────────────────────────────────────────────
function promptAction(id, action) {
    activeApptId  = id;
    confirmAction = action;
    const a = allAppointments.find(x => x.id === id);
    const patient = a ? (a.patient_name || 'Patient #' + a.patient_id) : `Appointment #${id}`;

    const configs = {
        completed: { title:'Mark as Completed', color:'#059669', bg:'#059669', btnClass:'btn-success', btnText:'<i class="bi bi-check-circle"></i> Mark Complete', msg:`Mark appointment with <strong>${esc(patient)}</strong> as completed?` },
        cancelled:  { title:'Cancel Appointment', color:'#dc2626', bg:'#dc2626', btnClass:'btn-danger',  btnText:'<i class="bi bi-x-circle"></i> Yes, Cancel',    msg:`Cancel appointment with <strong>${esc(patient)}</strong>? The patient will be notified.` },
        'no-show':  { title:'Mark as No Show',    color:'#d97706', bg:'#d97706', btnClass:'btn-warning', btnText:'<i class="bi bi-person-x"></i> Mark No Show',   msg:`Mark <strong>${esc(patient)}</strong> as no-show for this appointment?` },
    };
    const cfg = configs[action] || configs.completed;

    document.getElementById('confirmModalHeader').style.background = cfg.bg;
    document.getElementById('confirmModalHeader').style.color = '#fff';
    document.getElementById('confirmModalTitle').textContent = cfg.title;
    document.getElementById('confirmModalBody').innerHTML = `<p style="color:#334155;">${cfg.msg}</p>`;
    const btn = document.getElementById('confirmModalBtn');
    btn.className = `btn ${cfg.btnClass}`;
    btn.innerHTML = cfg.btnText;

    document.getElementById('confirmModal').style.display = 'flex';
}

function closeConfirmModal() { document.getElementById('confirmModal').style.display = 'none'; }

async function executeConfirm() {
    closeConfirmModal();
    try {
        const data = await apiFetch(`/api/doctor/appointments/${activeApptId}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status: confirmAction })
        });
        if (data.success) {
            showToast(`Appointment marked as ${confirmAction}`, 'success');
            await loadAppointments();
        } else {
            showToast(data.message || 'Failed to update', 'danger');
        }
    } catch {
        showToast('Network error. Please try again.', 'danger');
    }
}

// ── Filters ───────────────────────────────────────────────────────────────────
function clearFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('dateFilter').value  = '';
    document.getElementById('statusFilter').value = '';
    renderTable();
}

// ── Toast ─────────────────────────────────────────────────────────────────────
let toastTimer;
function showToast(msg, type = 'success') {
    const toast = document.getElementById('toast');
    const icons = { success:'bi-check-circle-fill', danger:'bi-exclamation-triangle-fill', warning:'bi-exclamation-circle-fill' };
    document.getElementById('toastMsg').innerHTML = `<i class="bi ${icons[type]||icons.success}" style="margin-right:6px;"></i>${esc(msg)}`;
    toast.className = `show ${type}`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.className = toast.className.replace('show','').trim(); }, 3500);
}

// ── Init ──────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    const user = checkAuth('doctor');
    if (!user) return;

    const name = user.name || user.username || 'Doctor';
    ['navUserName','sidebarDoctorName'].forEach(id => { const el = document.getElementById(id); if(el) el.textContent = name; });
    document.getElementById('currentDate').textContent = new Date().toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });

    loadAppointments();
    setInterval(loadAppointments, 30000); // auto-refresh every 30s

    // Close modals on backdrop click
    document.getElementById('apptModal').addEventListener('click', function(e) { if(e.target===this) closeModal(); });
    document.getElementById('confirmModal').addEventListener('click', function(e) { if(e.target===this) closeConfirmModal(); });
});

// CSS animation
const style = document.createElement('style');
style.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
document.head.appendChild(style);

// ── Calendar View ─────────────────────────────────────────────────────────────
let calYear  = new Date().getFullYear();
let calMonth = new Date().getMonth(); // 0-indexed

function switchView(view) {
    const tableEls   = ['filterBar', 'todayCard', document.querySelector('.card:has(#apptTableBody)')];
    const tableView  = document.querySelector('.card:has(#apptTableBody)');
    const calView    = document.getElementById('calendarView');
    const btnTable   = document.getElementById('btnTableView');
    const btnCal     = document.getElementById('btnCalView');

    if (view === 'calendar') {
        if (tableView) tableView.style.display = 'none';
        document.getElementById('filterBar').style.display = 'none';
        document.getElementById('todayCard').style.display = 'none';
        calView.style.display = '';
        btnTable.className = 'btn btn-outline btn-sm';
        btnCal.className   = 'btn btn-primary btn-sm';
        renderCalendar();
    } else {
        if (tableView) tableView.style.display = '';
        document.getElementById('filterBar').style.display = '';
        calView.style.display = 'none';
        btnTable.className = 'btn btn-primary btn-sm';
        btnCal.className   = 'btn btn-outline btn-sm';
        renderTodayCard();
    }
}

function renderCalendar() {
    const months = ['January','February','March','April','May','June',
                    'July','August','September','October','November','December'];
    document.getElementById('calTitle').textContent = `${months[calMonth]} ${calYear}`;

    const firstDay = new Date(calYear, calMonth, 1).getDay();
    const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
    const today = new Date().toISOString().split('T')[0];

    // Build date → appointments map
    const apptMap = {};
    allAppointments.forEach(a => {
        const d = a.appointment_date;
        if (!apptMap[d]) apptMap[d] = [];
        apptMap[d].push(a);
    });

    let html = '';
    // Empty cells before first day
    for (let i = 0; i < firstDay; i++) {
        html += '<div style="min-height:70px;"></div>';
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = `${calYear}-${String(calMonth+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
        const appts   = apptMap[dateStr] || [];
        const isToday = dateStr === today;
        const hasPending = appts.some(a => a.status === 'scheduled');

        html += `<div onclick="showCalDay('${dateStr}')" style="
            min-height:70px; border-radius:10px; padding:6px;
            background:${isToday ? '#eff6ff' : '#f8fafc'};
            border:${isToday ? '2px solid #2563eb' : '1px solid #e2e8f0'};
            cursor:pointer; transition:all .15s;
            ${appts.length ? 'box-shadow:0 2px 8px rgba(37,99,235,.1);' : ''}
        " onmouseover="this.style.background='#eff6ff'" onmouseout="this.style.background='${isToday ? '#eff6ff' : '#f8fafc'}'">
            <div style="font-weight:${isToday ? '800' : '600'};font-size:.82rem;color:${isToday ? '#2563eb' : '#374151'};margin-bottom:3px;">${day}</div>
            ${appts.slice(0,3).map(a => `
                <div style="font-size:.65rem;padding:2px 5px;border-radius:4px;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
                    background:${a.status==='scheduled'?'#dbeafe':a.status==='completed'?'#dcfce7':'#fee2e2'};
                    color:${a.status==='scheduled'?'#1e40af':a.status==='completed'?'#166534':'#991b1b'};">
                    ${a.appointment_time ? a.appointment_time.substring(0,5) + ' ' : ''}${esc(a.patient_name || 'Patient')}
                </div>`).join('')}
            ${appts.length > 3 ? `<div style="font-size:.62rem;color:#64748b;">+${appts.length-3} more</div>` : ''}
        </div>`;
    }
    document.getElementById('calGrid').innerHTML = html;
}

function showCalDay(dateStr) {
    const appts = allAppointments.filter(a => a.appointment_date === dateStr);
    const detail = document.getElementById('calDayDetail');
    const list   = document.getElementById('calDayList');
    const title  = document.getElementById('calDayTitle');

    const d = new Date(dateStr + 'T00:00:00');
    title.textContent = d.toLocaleDateString('en-US', {weekday:'long', month:'long', day:'numeric', year:'numeric'});

    if (!appts.length) {
        list.innerHTML = '<div style="padding:1.5rem;text-align:center;color:#94a3b8;"><i class="bi bi-calendar-x"></i> No appointments this day</div>';
    } else {
        list.innerHTML = appts.map(a => `
            <div style="display:flex;align-items:center;gap:1rem;padding:.85rem 1.25rem;border-bottom:1px solid #f1f5f9;">
                <div style="font-size:1.5rem;color:#2563eb;flex-shrink:0;"><i class="bi bi-person-circle"></i></div>
                <div style="flex:1;">
                    <div style="font-weight:700;font-size:.9rem;">${esc(a.patient_name || 'Patient #'+a.patient_id)}</div>
                    <div style="font-size:.78rem;color:#64748b;">
                        <i class="bi bi-clock"></i> ${esc(a.appointment_time || 'TBD')}
                        &nbsp;·&nbsp; ${esc(a.reason || 'Consultation')}
                    </div>
                </div>
                <span class="status-badge status-${esc(a.status)}">${esc(a.status)}</span>
                ${a.status === 'scheduled' ? `
                <div style="display:flex;gap:.4rem;">
                    <button class="action-icon-btn done" onclick="promptAction(${a.id},'completed')" title="Complete"><i class="bi bi-check-lg"></i></button>
                    <button class="action-icon-btn cancel" onclick="promptAction(${a.id},'cancelled')" title="Cancel"><i class="bi bi-x-lg"></i></button>
                </div>` : ''}
            </div>`).join('');
    }
    detail.style.display = '';
    detail.scrollIntoView({ behavior: 'smooth' });
}

function calPrev() {
    calMonth--;
    if (calMonth < 0) { calMonth = 11; calYear--; }
    renderCalendar();
    document.getElementById('calDayDetail').style.display = 'none';
}

function calNext() {
    calMonth++;
    if (calMonth > 11) { calMonth = 0; calYear++; }
    renderCalendar();
    document.getElementById('calDayDetail').style.display = 'none';
}
