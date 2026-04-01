// Nurse View Predictions Page

let allPredictions = [];

function getToken() { return localStorage.getItem('token'); }

function handleLogout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/';
}

const RISK_CONFIG = {
    'LOW':       { badge: 'badge-green',  icon: 'bi-check-circle-fill',        label: 'Low Risk' },
    'MODERATE':  { badge: 'badge-yellow', icon: 'bi-exclamation-circle-fill',   label: 'Moderate Risk' },
    'HIGH':      { badge: 'badge-red',    icon: 'bi-exclamation-triangle-fill', label: 'High Risk' },
    'VERY_HIGH': { badge: 'badge-purple', icon: 'bi-x-octagon-fill',            label: 'Very High Risk' }
};

function esc(str) {
    const d = document.createElement('div');
    d.textContent = str ?? '';
    return d.innerHTML;
}

function renderTable(data) {
    const tbody = document.getElementById('predictionsTableBody');
    const count = document.getElementById('resultCount');
    if (count) count.textContent = data.length + ' record' + (data.length !== 1 ? 's' : '');

    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted" style="padding:2rem;">No predictions found.</td></tr>';
        return;
    }

    tbody.innerHTML = data.map(p => {
        const cfg  = RISK_CONFIG[p.risk_level] || RISK_CONFIG['LOW'];
        const name = esc(p.patient ? p.patient.name : 'Unknown');
        const pid  = esc(p.patient ? p.patient.patient_id : '');
        const date = p.created_at ? new Date(p.created_at).toLocaleDateString('en-US') : '—';
        return `<tr>
            <td>
                <div class="font-medium">${name}</div>
                <div class="text-xs text-muted">${pid}</div>
            </td>
            <td class="text-sm">${esc(date)}</td>
            <td><span class="badge ${cfg.badge}"><i class="bi ${cfg.icon} me-1"></i>${cfg.label}</span></td>
            <td><strong>${esc(String(p.probability_percent))}%</strong></td>
            <td>${esc(p.prediction_label)}</td>
            <td class="text-xs text-muted">${esc(p.model_used || 'N/A')}</td>
            <td>
                <button class="btn btn-sm btn-outline" onclick="viewDetails(${p.id})">
                    <i class="bi bi-eye"></i> Details
                </button>
            </td>
        </tr>`;
    }).join('');
}

function filterTable() {
    const search = (document.getElementById('searchInput').value || '').toLowerCase();
    const risk   = document.getElementById('riskFilter').value;
    const filtered = allPredictions.filter(p => {
        const name = p.patient ? p.patient.name.toLowerCase() : '';
        const pid  = p.patient ? p.patient.patient_id.toLowerCase() : '';
        return (!search || name.includes(search) || pid.includes(search)) &&
               (!risk   || p.risk_level === risk);
    });
    renderTable(filtered);
}

function viewDetails(id) {
    const p = allPredictions.find(x => x.id === id);
    if (!p) return;
    const cfg  = RISK_CONFIG[p.risk_level] || RISK_CONFIG['LOW'];
    const name = esc(p.patient ? p.patient.name : 'Unknown');
    const pid  = esc(p.patient ? p.patient.patient_id : 'N/A');
    const date = p.created_at ? new Date(p.created_at).toLocaleString('en-US') : '—';

    document.getElementById('detailModalBody').innerHTML = `
        <div class="space-y-4">
          <div class="p-3 rounded flex items-center gap-3" style="background:#eff6ff;">
            <span class="badge ${cfg.badge} text-sm"><i class="bi ${cfg.icon} me-1"></i>${cfg.label}</span>
            <span class="text-sm text-muted">${esc(date)}</span>
          </div>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <table style="width:100%;border-collapse:collapse;">
                <tr><td class="text-muted py-1" style="width:45%;">Patient</td><td class="font-semibold">${name}</td></tr>
                <tr><td class="text-muted py-1">Patient ID</td><td class="font-semibold">${pid}</td></tr>
                <tr><td class="text-muted py-1">Result</td><td class="font-semibold">${esc(p.prediction_label)}</td></tr>
              </table>
            </div>
            <div>
              <table style="width:100%;border-collapse:collapse;">
                <tr><td class="text-muted py-1" style="width:45%;">Probability</td><td class="font-semibold">${esc(String(p.probability_percent))}%</td></tr>
                <tr><td class="text-muted py-1">Model Used</td><td class="font-semibold">${esc(p.model_used || 'N/A')}</td></tr>
              </table>
            </div>
          </div>
        </div>`;
    document.getElementById('detailModal').style.display = 'flex';
}

async function loadPredictions() {
    try {
        const res  = await fetch('/api/nurse/predictions?limit=100', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        const data = await res.json();
        if (data.success) {
            allPredictions = data.predictions;
            renderTable(allPredictions);
        } else {
            document.getElementById('predictionsTableBody').innerHTML =
                '<tr><td colspan="7" class="text-center text-danger" style="padding:2rem;">Failed to load predictions.</td></tr>';
        }
    } catch {
        document.getElementById('predictionsTableBody').innerHTML =
            '<tr><td colspan="7" class="text-center text-danger" style="padding:2rem;">Network error.</td></tr>';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('nurse');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    const sb = document.getElementById('sidebarName');
    if (sb) sb.textContent = user.name || user.username;

    loadPredictions();
    document.getElementById('searchInput').addEventListener('input', filterTable);
    document.getElementById('riskFilter').addEventListener('change', filterTable);
});
