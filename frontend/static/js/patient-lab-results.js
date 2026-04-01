const API = '/api';

const STATUS_CONFIG = {
    pending:     { badge: 'bg-warning text-dark', label: 'Pending',     icon: 'bi-clock-fill' },
    in_progress: { badge: 'bg-info text-dark',    label: 'In Progress', icon: 'bi-hourglass-split' },
    completed:   { badge: 'bg-success',           label: 'Completed',   icon: 'bi-check-circle-fill' },
    validated:   { badge: 'bg-primary',           label: 'Validated',   icon: 'bi-patch-check-fill' },
    cancelled:   { badge: 'bg-secondary',         label: 'Cancelled',   icon: 'bi-x-circle-fill' }
};

let allResults = [];

function esc(str) {
    const d = document.createElement('div');
    d.textContent = str ?? '';
    return d.innerHTML;
}

function apiFetch(url) {
    return fetch(url, { headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') } });
}

async function loadLabResults() {
    try {
        const res = await apiFetch(`${API}/patient/lab-results?limit=100`);
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        allResults = data.lab_results || [];
    } catch (e) {
        allResults = [];
        document.getElementById('resultsList').innerHTML =
            `<div class="alert alert-danger">Failed to load lab results: ${esc(e.message)}</div>`;
    }
    filterResults();
}

function renderResults(list) {
    const container = document.getElementById('resultsList');
    const empty = document.getElementById('emptyState');
    document.getElementById('resultCount').textContent = list.length + ' record' + (list.length !== 1 ? 's' : '');

    if (!list.length) {
        container.innerHTML = '';
        empty.style.display = 'block';
        return;
    }
    empty.style.display = 'none';

    container.innerHTML = list.map(r => {
        const cfg = STATUS_CONFIG[r.status] || { badge: 'bg-secondary', label: r.status, icon: 'bi-question-circle' };
        const date = r.created_at ? r.created_at.split('T')[0] : '—';
        const hasResult = r.status === 'completed' || r.status === 'validated';

        return `
        <div class="card mb-3">
            <div class="card-body">
                <div class="row align-items-center">
                    <div class="col-md-5">
                        <div class="d-flex align-items-center gap-3">
                            <i class="bi bi-flask fs-2 text-primary"></i>
                            <div>
                                <h5 class="mb-0">${esc(r.test_name)}</h5>
                                <p class="mb-0 text-muted small"><i class="bi bi-tag me-1"></i>${esc(r.test_category || r.test_type || '—')}</p>
                                <p class="mb-0 text-muted small"><i class="bi bi-calendar me-1"></i>Ordered: ${esc(date)}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        ${hasResult && r.results ? `<p class="mb-1 small"><strong>Result:</strong> ${esc(r.results)} ${esc(r.unit || '')}</p>` : ''}
                        ${hasResult && r.normal_range ? `<p class="mb-1 small"><strong>Normal Range:</strong> ${esc(r.normal_range)}</p>` : ''}
                        ${r.doctor_name ? `<p class="mb-0 text-muted small"><i class="bi bi-person-badge me-1"></i>${esc(r.doctor_name)}</p>` : ''}
                    </div>
                    <div class="col-md-2 text-center">
                        <span class="badge ${cfg.badge} px-3 py-2">
                            <i class="bi ${cfg.icon} me-1"></i>${cfg.label}
                        </span>
                    </div>
                    <div class="col-md-2 text-end">
                        <button class="btn btn-sm btn-outline-primary" onclick="viewResult(${r.id})">
                            <i class="bi bi-eye"></i> Details
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
    }).join('');
}

function filterResults() {
    const search = document.getElementById('searchInput').value.toLowerCase();
    const status = document.getElementById('statusFilter').value;
    const sort = document.getElementById('sortFilter').value;

    let filtered = allResults.filter(r => {
        const matchSearch = !search ||
            (r.test_name || '').toLowerCase().includes(search) ||
            (r.test_category || '').toLowerCase().includes(search) ||
            (r.test_type || '').toLowerCase().includes(search);
        const matchStatus = !status || r.status === status;
        return matchSearch && matchStatus;
    });

    if (sort === 'date_asc') {
        filtered.sort((a, b) => (a.created_at || '').localeCompare(b.created_at || ''));
    } else if (sort === 'date_desc') {
        filtered.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));
    } else if (sort === 'name') {
        filtered.sort((a, b) => (a.test_name || '').localeCompare(b.test_name || ''));
    }

    renderResults(filtered);
}

function viewResult(id) {
    const r = allResults.find(x => x.id === id);
    if (!r) return;
    const cfg = STATUS_CONFIG[r.status] || { badge: 'bg-secondary', label: r.status };
    const date = r.created_at ? r.created_at.split('T')[0] : '—';
    const completedDate = r.test_completed_at ? r.test_completed_at.split('T')[0] : null;
    const hasResult = r.status === 'completed' || r.status === 'validated';

    document.getElementById('labModalBody').innerHTML = `
        <div class="row g-3">
            <div class="col-12">
                <div class="d-flex align-items-center gap-3 p-3 bg-light rounded">
                    <i class="bi bi-flask display-4 text-primary"></i>
                    <div>
                        <h4 class="mb-0">${esc(r.test_name)}</h4>
                        <p class="mb-1 text-muted">${esc(r.test_category || r.test_type || '')}</p>
                        <span class="badge ${cfg.badge}">${cfg.label}</span>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <table class="table table-sm table-borderless">
                    <tr><td class="text-muted">Test ID</td><td><strong>${esc(r.test_id || String(r.id))}</strong></td></tr>
                    <tr><td class="text-muted">Ordered By</td><td><strong>${esc(r.doctor_name || '—')}</strong></td></tr>
                    <tr><td class="text-muted">Date Ordered</td><td><strong>${esc(date)}</strong></td></tr>
                    ${completedDate ? `<tr><td class="text-muted">Completed</td><td><strong>${esc(completedDate)}</strong></td></tr>` : ''}
                    ${r.priority ? `<tr><td class="text-muted">Priority</td><td><strong>${esc(r.priority)}</strong></td></tr>` : ''}
                    ${r.cost ? `<tr><td class="text-muted">Cost</td><td><strong>ETB ${esc(String(r.cost))}</strong></td></tr>` : ''}
                </table>
            </div>
            <div class="col-md-6">
                <table class="table table-sm table-borderless">
                    ${hasResult && r.results ? `<tr><td class="text-muted">Result</td><td><strong>${esc(r.results)} ${esc(r.unit || '')}</strong></td></tr>` : ''}
                    ${hasResult && r.normal_range ? `<tr><td class="text-muted">Normal Range</td><td><strong>${esc(r.normal_range)}</strong></td></tr>` : ''}
                    ${r.test_type ? `<tr><td class="text-muted">Test Type</td><td><strong>${esc(r.test_type)}</strong></td></tr>` : ''}
                </table>
            </div>
            ${r.remarks ? `
            <div class="col-12">
                <div class="alert alert-info mb-0">
                    <i class="bi bi-info-circle me-2"></i><strong>Remarks:</strong> ${esc(r.remarks)}
                </div>
            </div>` : ''}
            ${!hasResult ? `
            <div class="col-12">
                <div class="alert alert-warning mb-0">
                    <i class="bi bi-hourglass-split me-2"></i>Results are not yet available for this test.
                </div>
            </div>` : ''}
        </div>`;
    document.getElementById('labModal').style.display = 'flex';
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('patient');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    document.getElementById('currentDate').textContent = new Date().toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
    });
    loadLabResults();
});
