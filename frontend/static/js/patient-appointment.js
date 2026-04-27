const API = '/api';

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

const ALL_SLOTS = [
    '08:00 AM','08:30 AM','09:00 AM','09:30 AM','10:00 AM','10:30 AM','11:00 AM','11:30 AM',
    '02:00 PM','02:30 PM','03:00 PM','03:30 PM','04:00 PM','04:30 PM'
];

let DOCTORS = [];
let state = { selectedDoctor: null, selectedDate: null, selectedTime: null, cancelId: null };

// ── Init ──────────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
    const user = checkAuth('patient');
    if (!user) return;

    const name = user.name || user.username || 'Patient';
    ['navUserName','sidebarName'].forEach(id => { const el = document.getElementById(id); if(el) el.textContent = name; });
    document.getElementById('currentDate').textContent = new Date().toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
    document.getElementById('apptDate').min = new Date().toISOString().split('T')[0];

    // Auto-fill if coming from high-risk prediction result
    const params = new URLSearchParams(window.location.search);
    const autoReason = params.get('reason');
    const autoPredId = params.get('pred_id');
    if (autoReason) {
        // Switch to book tab and pre-fill
        showTab('book');
        setTimeout(() => {
            const visitType = document.getElementById('visitType');
            const notes = document.getElementById('apptNotes');
            // Match closest option
            for (let opt of visitType.options) {
                if (opt.value.toLowerCase().includes('prediction') || opt.value.toLowerCase().includes('result')) {
                    visitType.value = opt.value; break;
                }
            }
            notes.value = autoPredId
                ? `High risk result from prediction #${autoPredId}. Requires urgent doctor consultation.`
                : 'High diabetes risk detected. Requires urgent doctor consultation.';
            // Show urgent banner
            const banner = document.createElement('div');
            banner.style.cssText = 'background:linear-gradient(135deg,#7f1d1d,#991b1b);color:#fff;border-radius:14px;padding:1rem 1.25rem;margin-bottom:1.25rem;display:flex;align-items:center;gap:0.75rem;font-size:0.875rem;font-weight:600;';
            banner.innerHTML = '<i class="bi bi-exclamation-triangle-fill" style="font-size:1.3rem;flex-shrink:0;"></i><span>Your diabetes risk is <strong>HIGH</strong>. Please book an appointment with a doctor immediately.</span>';
            document.querySelector('.main').prepend(banner);
        }, 500);
    }

    // Close modal on backdrop click
    document.getElementById('cancelModal').addEventListener('click', function(e) {
        if (e.target === this) closeCancelModal();
    });

    await loadDoctors();
    await Promise.all([loadUpcoming(), loadHistory()]);
});

// ── Load Doctors ──────────────────────────────────────────────────────────────
async function loadDoctors() {
    const listEl = document.getElementById('doctorList');
    const loadEl = document.getElementById('doctorListLoading');
    try {
        const data = await apiFetch('/patient/doctors');
        if (loadEl) loadEl.style.display = 'none';
        if (!data.success || !data.doctors?.length) {
            listEl.innerHTML = `<div style="color:#64748b;padding:1rem;text-align:center;"><i class="bi bi-exclamation-circle"></i> No doctors available right now.</div>`;
            return;
        }
        DOCTORS = data.doctors;
        renderDoctors();
    } catch {
        if (loadEl) loadEl.style.display = 'none';
        listEl.innerHTML = `<div style="color:#dc2626;padding:1rem;text-align:center;"><i class="bi bi-wifi-off"></i> Failed to load doctors. Is the server running?</div>`;
    }
}

function renderDoctors() {
    document.getElementById('doctorList').innerHTML = DOCTORS.map(d => `
        <div class="doctor-card" id="doc-${d.id}" onclick="selectDoctor(${d.id})">
            <div class="doctor-avatar"><i class="bi bi-person-badge"></i></div>
            <div class="doctor-name">${esc(d.name)}</div>
            <div class="doctor-spec">${esc(d.specialization || 'General Practitioner')}</div>
            <div class="doctor-avail"><i class="bi bi-calendar3"></i> ${esc(d.available_days || 'Mon–Fri')} &nbsp;·&nbsp; <i class="bi bi-clock"></i> ${esc(d.available_hours || '08:00–17:00')}</div>
            ${d.consultation_fee ? `<div class="doctor-fee"><i class="bi bi-currency-exchange"></i> ETB ${esc(String(d.consultation_fee))}</div>` : ''}
        </div>
    `).join('');
}

// ── Select Doctor ─────────────────────────────────────────────────────────────
function selectDoctor(id) {
    state.selectedDoctor = DOCTORS.find(d => d.id === id);
    state.selectedTime = null;
    state.selectedDate = null;
    document.querySelectorAll('.doctor-card').forEach(c => c.classList.remove('selected'));
    document.getElementById(`doc-${id}`).classList.add('selected');
    enableStep('step2Card');
    disableStep('step3Card');
    document.getElementById('apptDate').value = '';
    document.getElementById('timeSlots').innerHTML = '<p style="color:#94a3b8;font-size:0.8rem;">Select a date first</p>';
    updateSummary();
}

// ── Time Slots ────────────────────────────────────────────────────────────────
async function loadTimeSlots() {
    const dateVal = document.getElementById('apptDate').value;
    if (!dateVal || !state.selectedDoctor) return;
    state.selectedDate = dateVal;
    state.selectedTime = null;

    const dow = new Date(dateVal + 'T00:00:00').getDay();
    if (dow === 0) {
        document.getElementById('timeSlots').innerHTML = '<p style="color:#d97706;font-size:0.8rem;"><i class="bi bi-exclamation-circle"></i> No appointments on Sundays.</p>';
        return;
    }

    // Fetch already-booked slots for this doctor on this date
    let bookedSlots = [];
    try {
        const data = await apiFetch(`/patient/doctors/${state.selectedDoctor.id}/booked-slots?date=${dateVal}`);
        if (data.success) bookedSlots = data.booked_slots || [];
    } catch (_) {}

    const slots = dow === 6 ? ALL_SLOTS.filter(s => s.includes('AM')) : ALL_SLOTS;

    document.getElementById('timeSlots').innerHTML = slots.map(slot => {
        const isBooked = bookedSlots.includes(slot);
        return `<button class="time-slot${isBooked ? ' unavailable' : ''}"
                    onclick="${isBooked ? '' : `selectTime('${slot}')`}"
                    id="slot-${slot.replace(/[: ]/g,'-')}"
                    title="${isBooked ? 'This slot is already booked' : 'Click to select ' + slot}"
                    ${isBooked ? 'disabled' : ''}>
                    ${slot}${isBooked ? ' <i class="bi bi-x-circle" style="font-size:.65rem;"></i>' : ''}
                </button>`;
    }).join('');

    // Show message if any slots are booked
    if (bookedSlots.length > 0) {
        const msg = document.createElement('p');
        msg.style.cssText = 'font-size:.75rem;color:#d97706;margin-top:.5rem;display:flex;align-items:center;gap:.3rem;';
        msg.innerHTML = `<i class="bi bi-info-circle-fill"></i> ${bookedSlots.length} slot${bookedSlots.length > 1 ? 's are' : ' is'} already booked (shown with ✕). Please choose an available time.`;
        document.getElementById('timeSlots').after(msg);
    }

    updateSummary();
}

function selectTime(time) {
    state.selectedTime = time;
    document.querySelectorAll('.time-slot').forEach(s => s.classList.remove('selected'));
    const el = document.getElementById(`slot-${time.replace(/[: ]/g,'-')}`);
    if (el) el.classList.add('selected');
    enableStep('step3Card');
    updateSummary();
}

// ── Summary ───────────────────────────────────────────────────────────────────
function updateSummary() {
    const d = state.selectedDoctor;
    const content = document.getElementById('summaryContent');
    if (!d) {
        content.innerHTML = `<div style="text-align:center;padding:2rem 1rem;color:#94a3b8;"><i class="bi bi-calendar2-plus" style="font-size:2.5rem;display:block;margin-bottom:0.75rem;"></i><p style="font-size:0.85rem;">Select a doctor to begin</p></div>`;
        return;
    }
    const dateStr = state.selectedDate
        ? new Date(state.selectedDate + 'T00:00:00').toLocaleDateString('en-US', { weekday:'short', month:'short', day:'numeric', year:'numeric' })
        : '—';
    content.innerHTML = `
        <div class="summary-row"><span class="summary-label"><i class="bi bi-person-badge"></i> Doctor</span><span class="summary-value">${esc(d.name)}</span></div>
        <div class="summary-row"><span class="summary-label"><i class="bi bi-heart-pulse"></i> Specialty</span><span class="summary-value">${esc(d.specialization || 'General')}</span></div>
        <div class="summary-row"><span class="summary-label"><i class="bi bi-calendar3"></i> Date</span><span class="summary-value">${esc(dateStr)}</span></div>
        <div class="summary-row"><span class="summary-label"><i class="bi bi-clock"></i> Time</span><span class="summary-value">${esc(state.selectedTime || '—')}</span></div>
        ${d.consultation_fee ? `<div class="summary-row"><span class="summary-label"><i class="bi bi-currency-exchange"></i> Fee</span><span class="summary-value" style="color:#059669;">ETB ${esc(String(d.consultation_fee))}</span></div>` : ''}
        ${state.selectedTime ? `<div style="margin-top:1rem;padding:0.75rem;background:#ecfdf5;border-radius:10px;font-size:0.8rem;color:#065f46;"><i class="bi bi-check-circle-fill"></i> Ready to confirm! Fill in the reason below.</div>` : ''}
    `;
}

// ── Submit ────────────────────────────────────────────────────────────────────
async function submitAppointment() {
    const visitType = document.getElementById('visitType').value;
    const notes     = document.getElementById('apptNotes').value.trim();

    if (!state.selectedDoctor) return showToast('Please select a doctor.', 'danger');
    if (!state.selectedDate)   return showToast('Please select a date.', 'danger');
    if (!state.selectedTime)   return showToast('Please select a time slot.', 'danger');
    if (!visitType)            return showToast('Please select a visit type.', 'danger');

    const btn = document.getElementById('confirmBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Checking...';

    // Double-check slot is still available before submitting
    try {
        const slotCheck = await apiFetch(`/patient/doctors/${state.selectedDoctor.id}/booked-slots?date=${state.selectedDate}`);
        if (slotCheck.success && (slotCheck.booked_slots || []).includes(state.selectedTime)) {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-calendar-check"></i> Confirm Appointment';
            showToast('That time slot was just booked by someone else. Please choose another.', 'danger');
            await loadTimeSlots(); // refresh slots
            return;
        }
    } catch (_) {}

    try {
        const data = await apiFetch('/patient/appointments', {
            method: 'POST',
            body: JSON.stringify({
                doctor_id: state.selectedDoctor.id,
                appointment_date: state.selectedDate,
                appointment_time: state.selectedTime,
                reason: visitType,
                notes,
                type: 'consultation'
            })
        });
        if (data.success) {
            showToast('Appointment booked successfully!', 'success');
            resetForm();
            await loadUpcoming();
            setTimeout(() => showTab('upcoming'), 900);
        } else {
            showToast(data.message || 'Failed to book appointment.', 'danger');
        }
    } catch {
        showToast('Network error. Please try again.', 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-calendar-check"></i> Confirm Appointment';
    }
}

function resetForm() {
    state = { selectedDoctor: null, selectedDate: null, selectedTime: null, cancelId: null };
    document.querySelectorAll('.doctor-card').forEach(c => c.classList.remove('selected'));
    document.getElementById('apptDate').value = '';
    document.getElementById('visitType').value = '';
    document.getElementById('apptNotes').value = '';
    document.getElementById('timeSlots').innerHTML = '<p style="color:#94a3b8;font-size:0.8rem;">Select a date first</p>';
    disableStep('step2Card');
    disableStep('step3Card');
    updateSummary();
}

// ── Load Upcoming ─────────────────────────────────────────────────────────────
async function loadUpcoming() {
    try {
        const data = await apiFetch('/patient/appointments?limit=50');
        if (!data.success) return;
        // Show all scheduled/pending appointments regardless of date
        const upcoming = (data.appointments || [])
            .filter(a => a.status !== 'cancelled' && a.status !== 'completed')
            .sort((a, b) => (a.appointment_date || '').localeCompare(b.appointment_date || ''));

        document.getElementById('upcomingCount').textContent = upcoming.length;
        const container = document.getElementById('upcomingList');
        const empty     = document.getElementById('upcomingEmpty');
        if (!upcoming.length) { container.innerHTML = ''; empty.style.display = 'block'; }
        else { empty.style.display = 'none'; container.innerHTML = upcoming.map(a => apptCardHTML(a, true)).join(''); }
    } catch {
        document.getElementById('upcomingList').innerHTML = '<p style="color:#dc2626;padding:1rem;">Failed to load appointments.</p>';
    }
}

// ── Load History ──────────────────────────────────────────────────────────────
async function loadHistory() {
    try {
        const data = await apiFetch('/patient/appointments?limit=50');
        if (!data.success) return;
        const history = (data.appointments || [])
            .filter(a => a.status === 'cancelled' || a.status === 'completed')
            .sort((a, b) => (b.appointment_date || '').localeCompare(a.appointment_date || ''));

        const container = document.getElementById('historyList');
        const empty     = document.getElementById('historyEmpty');
        if (!history.length) { container.innerHTML = ''; empty.style.display = 'block'; }
        else { empty.style.display = 'none'; container.innerHTML = history.map(a => apptCardHTML(a, false)).join(''); }
    } catch {
        document.getElementById('historyList').innerHTML = '<p style="color:#dc2626;padding:1rem;">Failed to load history.</p>';
    }
}

// ── Appointment Card ──────────────────────────────────────────────────────────
function apptCardHTML(a, canCancel) {
    const d     = new Date(a.appointment_date + 'T00:00:00');
    const day   = d.getDate();
    const month = d.toLocaleDateString('en-US', { month: 'short' });
    const STATUS_MAP = { confirmed:'badge-scheduled', scheduled:'badge-scheduled', pending:'badge-pending', cancelled:'badge-cancelled', completed:'badge-completed' };
    const statusClass = STATUS_MAP[a.status] || 'badge-pending';
    const statusLabel = (a.status || '').charAt(0).toUpperCase() + (a.status || '').slice(1);
    const doctorName  = a.doctor_name || `Doctor #${a.doctor_id}`;
    const doctorSpec  = a.doctor_specialization || '';

    return `
        <div class="appt-card">
            <div class="appt-date-box">
                <div class="appt-date-day">${day}</div>
                <div class="appt-date-month">${month}</div>
            </div>
            <div class="appt-info">
                <div class="appt-doctor">${esc(doctorName)}</div>
                ${doctorSpec ? `<div style="font-size:0.75rem;color:#3b82f6;font-weight:600;">${esc(doctorSpec)}</div>` : ''}
                <div class="appt-meta"><i class="bi bi-clock"></i> ${esc(a.appointment_time || 'Time TBD')} &nbsp;·&nbsp; <i class="bi bi-calendar3"></i> ${esc(a.appointment_date)}</div>
                <div class="appt-reason"><i class="bi bi-chat-text"></i> ${esc(a.reason || '')}${a.notes ? ' — ' + esc(a.notes) : ''}</div>
            </div>
            <div class="appt-actions">
                <span class="${statusClass}">${esc(statusLabel)}</span>
                ${canCancel && a.status !== 'cancelled' && a.status !== 'completed'
                    ? `<a href="/templates/payment/payment_page.html?service=consultation&return=appointment"
                         style="background:#059669;color:#fff;border:none;border-radius:8px;padding:0.3rem 0.7rem;font-size:0.78rem;cursor:pointer;font-weight:600;text-decoration:none;display:inline-flex;align-items:center;gap:4px;">
                         <i class="bi bi-credit-card"></i> Pay Fee
                       </a>
                       <button onclick="openCancelModal(${a.id}, '${esc(doctorName)} — ${esc(a.appointment_date)}')"
                         style="background:none;border:1px solid #fca5a5;color:#dc2626;border-radius:8px;padding:0.3rem 0.7rem;font-size:0.78rem;cursor:pointer;font-weight:600;transition:all 0.2s;"
                         onmouseover="this.style.background='#fee2e2'" onmouseout="this.style.background='none'">
                         <i class="bi bi-x-circle"></i> Cancel
                       </button>`
                    : ''}
            </div>
        </div>`;
}

// ── Cancel Modal ──────────────────────────────────────────────────────────────
function openCancelModal(id, label) {
    state.cancelId = id;
    document.getElementById('cancelApptDetails').innerHTML = `<i class="bi bi-calendar-event"></i> <strong>${esc(label)}</strong>`;
    const modal = document.getElementById('cancelModal');
    modal.style.display = 'flex';
}

function closeCancelModal() {
    document.getElementById('cancelModal').style.display = 'none';
}

async function confirmCancel() {
    closeCancelModal();
    try {
        const data = await apiFetch(`/patient/appointments/${state.cancelId}/cancel`, { method: 'POST' });
        if (data.success) {
            showToast('Appointment cancelled.', 'warning');
            await Promise.all([loadUpcoming(), loadHistory()]);
        } else {
            showToast(data.message || 'Failed to cancel.', 'danger');
        }
    } catch {
        showToast('Network error.', 'danger');
    }
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
function showTab(name) {
    ['book','upcoming','history'].forEach(t => {
        document.getElementById(`tab-${t}`).style.display = t === name ? 'block' : 'none';
        const btn = document.getElementById(`tab-btn-${t}`);
        if (btn) btn.classList.toggle('active', t === name);
    });
    if (name === 'upcoming') loadUpcoming();
    if (name === 'history')  loadHistory();
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function enableStep(id)  { const el = document.getElementById(id); el.classList.remove('step-disabled'); }
function disableStep(id) { const el = document.getElementById(id); el.classList.add('step-disabled'); }

let toastTimer;
function showToast(msg, type = 'success') {
    const toast = document.getElementById('toast');
    const icons = { success: 'bi-check-circle-fill', danger: 'bi-exclamation-triangle-fill', warning: 'bi-exclamation-circle-fill' };
    document.getElementById('toastMsg').innerHTML = `<i class="bi ${icons[type] || icons.success}" style="margin-right:6px;"></i>${esc(msg)}`;
    toast.className = `show ${type}`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.className = toast.className.replace('show','').trim(); }, 3500);
}

// Close modal on backdrop click — moved inside DOMContentLoaded above
