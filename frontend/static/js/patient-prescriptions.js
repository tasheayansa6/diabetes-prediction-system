// Patient Prescriptions - GET /api/patient/prescriptions

const STATUS_CONFIG = {
    'active':             { badge: 'badge-green',  label: 'Active',             icon: 'bi-check-circle-fill' },
    'dispensed':          { badge: 'badge-blue',   label: 'Dispensed',          icon: 'bi-bag-check-fill' },
    'pending_pharmacist': { badge: 'badge-yellow', label: 'Pending Pharmacist', icon: 'bi-clock-fill' },
    'pending':            { badge: 'badge-yellow', label: 'Pending',            icon: 'bi-clock-fill' },
    'verified':           { badge: 'badge-cyan',   label: 'Verified',           icon: 'bi-shield-check' },
    'expired':            { badge: 'badge-gray',   label: 'Expired',            icon: 'bi-x-circle-fill' },
    'cancelled':          { badge: 'badge-red',    label: 'Cancelled',          icon: 'bi-x-circle-fill' },
    'rejected':           { badge: 'badge-red',    label: 'Rejected',           icon: 'bi-x-circle-fill' }
};

let allPrescriptions = [];

function esc(str) {
    const d = document.createElement('div');
    d.textContent = str ?? '—';
    return d.innerHTML;
}

function authHeaders() {
    return { 'Authorization': 'Bearer ' + localStorage.getItem('token') };
}

async function loadPrescriptions() {
    const container = document.getElementById('prescriptionsList');
    container.innerHTML = '<div class="text-center py-8 text-muted"><i class="bi bi-hourglass-split text-3xl"></i><p class="mt-2">Loading prescriptions...</p></div>';

    try {
        const res  = await fetch('/api/patient/prescriptions?limit=100', { headers: authHeaders() });
        if (res.status === 401) { localStorage.removeItem('token'); localStorage.removeItem('user'); window.location.href = '/login'; return; }
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        allPrescriptions = data.prescriptions || [];
    } catch (e) {
        allPrescriptions = [];
        document.getElementById('prescriptionsList').innerHTML =
            `<div class="alert alert-danger"><i class="bi bi-exclamation-triangle me-2"></i>Failed to load prescriptions: ${esc(e.message)}</div>`;
        return;
    }
    filterPrescriptions();
}

function renderPrescriptions(list) {
    const container = document.getElementById('prescriptionsList');
    const empty     = document.getElementById('emptyState');
    document.getElementById('resultCount').textContent = list.length + ' record' + (list.length !== 1 ? 's' : '');

    if (!list.length) {
        container.innerHTML = '';
        empty.style.display = 'block';
        return;
    }
    empty.style.display = 'none';

    container.innerHTML = list.map(rx => {
        const cfg  = STATUS_CONFIG[rx.status] || { badge: 'badge-gray', label: rx.status, icon: 'bi-question-circle' };
        const date = rx.created_at ? rx.created_at.split('T')[0] : '—';
        const dispensedRow = rx.dispensed_at
            ? `<span class="text-xs text-muted"><i class="bi bi-bag-check me-1"></i>Dispensed: ${rx.dispensed_at.split('T')[0]}</span>`
            : '';

        return `
        <div class="card mb-3">
          <div class="card-body" style="padding:1.1rem;">
            <div class="flex items-center gap-4 flex-wrap">
              <!-- Icon -->
              <div style="font-size:2rem;color:#3b82f6;flex-shrink:0;">
                <i class="bi bi-capsule-pill"></i>
              </div>
              <!-- Medication info -->
              <div style="flex:1;min-width:180px;">
                <div class="font-semibold text-dark">${esc(rx.medication)}
                  <span class="text-muted text-sm font-normal">${esc(rx.dosage || '')}</span>
                </div>
                <div class="text-xs text-muted mt-1">
                  <i class="bi bi-person-badge me-1"></i>Dr. ${esc(rx.doctor_name || 'Unknown')}
                  &nbsp;·&nbsp;
                  <i class="bi bi-calendar me-1"></i>${date}
                </div>
                ${dispensedRow ? `<div class="mt-1">${dispensedRow}</div>` : ''}
              </div>
              <!-- Frequency / Duration -->
              <div style="min-width:130px;" class="text-sm">
                <div><strong>Frequency:</strong> ${esc(rx.frequency || '—')}</div>
                <div><strong>Duration:</strong> ${esc(rx.duration || '—')}</div>
              </div>
              <!-- Status badge -->
              <div style="min-width:120px;text-align:center;">
                <span class="badge ${cfg.badge}">
                  <i class="bi ${cfg.icon} me-1"></i>${cfg.label}
                </span>
              </div>
              <!-- Details button -->
              <div>
                <button class="btn btn-sm btn-outline" onclick="viewPrescription(${rx.id})">
                  <i class="bi bi-eye"></i> Details
                </button>
              </div>
            </div>
          </div>
        </div>`;
    }).join('');
}

function filterPrescriptions() {
    const search = document.getElementById('searchInput').value.toLowerCase();
    const status = document.getElementById('statusFilter').value;
    const sort   = document.getElementById('sortFilter').value;

    let filtered = allPrescriptions.filter(rx => {
        const matchSearch = !search ||
            (rx.medication  || '').toLowerCase().includes(search) ||
            (rx.doctor_name || '').toLowerCase().includes(search);
        const matchStatus = !status || rx.status === status;
        return matchSearch && matchStatus;
    });

    if (sort === 'date_asc')  filtered.sort((a, b) => (a.created_at || '').localeCompare(b.created_at || ''));
    else if (sort === 'date_desc') filtered.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));
    else if (sort === 'name') filtered.sort((a, b) => (a.medication || '').localeCompare(b.medication || ''));

    renderPrescriptions(filtered);
}

function viewPrescription(id) {
    const rx  = allPrescriptions.find(r => r.id === id);
    if (!rx) return;
    const cfg  = STATUS_CONFIG[rx.status] || { badge: 'badge-gray', label: rx.status };
    const date = rx.created_at ? rx.created_at.split('T')[0] : '—';

    document.getElementById('prescriptionModalBody').innerHTML = `
        <div class="space-y-4">
          <!-- Header -->
          <div class="flex items-center gap-3 p-3 rounded" style="background:#eff6ff;">
            <i class="bi bi-capsule-pill" style="font-size:2.5rem;color:#3b82f6;"></i>
            <div>
              <h4 class="font-bold text-dark mb-0">${esc(rx.medication)}
                <span class="text-muted text-sm font-normal">${esc(rx.dosage || '')}</span>
              </h4>
              <span class="badge ${cfg.badge}"><i class="bi ${cfg.icon || 'bi-circle'} me-1"></i>${cfg.label}</span>
            </div>
          </div>
          <!-- Details grid -->
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <table style="width:100%;border-collapse:collapse;">
                <tr><td class="text-muted py-1" style="width:45%;">Prescription ID</td><td class="font-semibold">${esc(rx.prescription_id || String(rx.id))}</td></tr>
                <tr><td class="text-muted py-1">Prescribed By</td><td class="font-semibold">Dr. ${esc(rx.doctor_name || '—')}</td></tr>
                <tr><td class="text-muted py-1">Date Issued</td><td class="font-semibold">${esc(date)}</td></tr>
                ${rx.dispensed_at ? `<tr><td class="text-muted py-1">Dispensed On</td><td class="font-semibold">${esc(rx.dispensed_at.split('T')[0])}</td></tr>` : ''}
              </table>
            </div>
            <div>
              <table style="width:100%;border-collapse:collapse;">
                <tr><td class="text-muted py-1" style="width:45%;">Frequency</td><td class="font-semibold">${esc(rx.frequency || '—')}</td></tr>
                <tr><td class="text-muted py-1">Duration</td><td class="font-semibold">${esc(rx.duration || '—')}</td></tr>
                <tr><td class="text-muted py-1">Status</td><td><span class="badge ${cfg.badge}">${cfg.label}</span></td></tr>
                ${rx.notes ? `<tr><td class="text-muted py-1">Notes</td><td class="font-semibold">${esc(rx.notes)}</td></tr>` : ''}
              </table>
            </div>
          </div>
          ${rx.instructions ? `
          <div class="alert alert-warning text-sm">
            <i class="bi bi-info-circle me-2"></i><strong>Instructions:</strong> ${esc(rx.instructions)}
          </div>` : ''}
          ${rx.status === 'dispensed' ? `
          <div class="alert alert-success text-sm">
            <i class="bi bi-bag-check-fill me-2"></i>
            This prescription has been <strong>dispensed</strong> by the pharmacist.
            ${rx.dispensed_at ? 'Dispensed on ' + rx.dispensed_at.split('T')[0] + '.' : ''}
          </div>` : ''}
          ${rx.status === 'pending_pharmacist' || rx.status === 'pending' ? `
          <div class="alert alert-warning text-sm">
            <i class="bi bi-clock-fill me-2"></i>
            This prescription is <strong>awaiting pharmacist review</strong>. Please visit the pharmacy.
          </div>` : ''}
        </div>`;

    document.getElementById('prescriptionModal').style.display = 'flex';
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('patient');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    document.getElementById('currentDate').textContent = new Date().toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
    loadPrescriptions();
});
