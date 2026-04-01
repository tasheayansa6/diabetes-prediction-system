// Lab Report - GET /api/labs/completed + PUT /api/labs/validate/:id

let allReports = [];

function authHeaders() {
    return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token') };
}

function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }

function isAbnormal(result) {
    return result && /high|low|abnormal|positive|elevated|critical/i.test(result);
}

async function apiFetch(path, options = {}) {
    const res = await fetch('' + path, { ...options, headers: { ...authHeaders(), ...(options.headers || {}) } });
    if (res.status === 401) { localStorage.removeItem('token'); localStorage.removeItem('user'); window.location.href = '/login'; return {}; }
    return res.json();
}

async function loadReports() {
    const tbody = document.getElementById('reportsBody');
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:2rem;color:#94a3b8;"><div style="display:inline-block;width:20px;height:20px;border:2px solid #0891b2;border-top-color:transparent;border-radius:50%;animation:spin 0.7s linear infinite;margin-right:8px;vertical-align:middle;"></div>Loading...</td></tr>`;
    try {
        const data = await apiFetch('/api/labs/completed?limit=200');
        if (!data.success) throw new Error(data.message || 'Failed to load');

        allReports = data.completed_tests || [];
        updateStats();
        renderTable(allReports);
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:2rem;color:#dc2626;"><i class="bi bi-wifi-off"></i> ${esc(err.message)}</td></tr>`;
    }
}

function updateStats() {
    document.getElementById('statTotal').textContent = allReports.length;
    document.getElementById('statNormal').textContent = allReports.filter(t => t.results && !isAbnormal(t.results)).length;
    document.getElementById('statAbnormal').textContent = allReports.filter(t => isAbnormal(t.results)).length;
}

function renderTable(reports) {
    document.getElementById('tableCount').textContent = `${reports.length} of ${allReports.length} reports`;
    const tbody = document.getElementById('reportsBody');
    if (!reports.length) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:2rem;color:#94a3b8;"><i class="bi bi-inbox" style="font-size:1.5rem;display:block;margin-bottom:0.5rem;"></i>No completed tests found</td></tr>`;
        return;
    }
    tbody.innerHTML = reports.map(t => {
        const abnormal = isAbnormal(t.results);
        const resultBadge = t.results
            ? `<span class="${abnormal ? 'result-abnormal' : 'result-normal'}">${esc(t.results)}</span>`
            : `<span class="result-pending">Pending</span>`;
        const date = t.completed_at ? new Date(t.completed_at).toLocaleDateString('en-US', { year:'numeric', month:'short', day:'numeric' }) : '—';
        return `<tr>
            <td><small style="color:#64748b;">${esc(t.test_id)}</small></td>
            <td style="font-weight:600;">${esc(t.patient_name)}</td>
            <td>${esc(t.test_name)}</td>
            <td>${resultBadge}</td>
            <td style="color:#64748b;font-size:0.8rem;">${esc(t.unit || '—')}</td>
            <td style="color:#64748b;font-size:0.8rem;">${esc(t.normal_range || '—')}</td>
            <td><span class="result-normal">Completed</span></td>
            <td style="font-size:0.8rem;">${esc(date)}</td>
            <td class="no-print">
                <div style="display:flex;gap:4px;">
                    <button onclick="validateTest('${esc(t.test_id)}')" title="Validate" style="background:#eff6ff;border:1px solid #bfdbfe;color:#2563eb;border-radius:6px;padding:3px 8px;font-size:0.75rem;cursor:pointer;font-weight:600;">
                        <i class="bi bi-patch-check"></i> Validate
                    </button>
                    <button onclick="window.print()" title="Print" style="background:#f8fafc;border:1px solid #e2e8f0;color:#475569;border-radius:6px;padding:3px 8px;font-size:0.75rem;cursor:pointer;">
                        <i class="bi bi-printer"></i>
                    </button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

async function validateTest(testId) {
    try {
        const data = await apiFetch(`/api/labs/validate/${testId}`, { method: 'PUT', body: JSON.stringify({ validation_status: 'verified' }) });
        if (data.success) {
            showToast('Test validated successfully', 'success');
            loadReports();
        } else {
            showToast(data.message || 'Validation failed', 'danger');
        }
    } catch (err) {
        showToast('Error: ' + err.message, 'danger');
    }
}

function filterTable() {
    const search = document.getElementById('searchInput').value.toLowerCase();
    const resultF = document.getElementById('resultFilter').value;
    const dateF = document.getElementById('dateFilter').value;

    const filtered = allReports.filter(t => {
        const matchSearch = !search || (t.patient_name || '').toLowerCase().includes(search) || (t.test_name || '').toLowerCase().includes(search) || (t.test_id || '').toLowerCase().includes(search);
        const matchResult = !resultF || (resultF === 'abnormal' ? isAbnormal(t.results) : (t.results && !isAbnormal(t.results)));
        const matchDate = !dateF || (t.completed_at && t.completed_at.startsWith(dateF));
        return matchSearch && matchResult && matchDate;
    });
    renderTable(filtered);
}

function clearFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('resultFilter').value = '';
    document.getElementById('dateFilter').value = '';
    renderTable(allReports);
}

let toastTimer;
function showToast(msg, type = 'success') {
    const toast = document.getElementById('toast');
    document.getElementById('toastMsg').textContent = msg;
    toast.className = `show ${type}`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.className = toast.className.replace('show', '').trim(); }, 3500);
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('lab_technician');
    if (!user) return;
    const name = user.name || user.username;
    document.getElementById('topUserName').textContent = name;
    document.getElementById('userName').textContent = name;
    document.getElementById('statTech').textContent = name;
    document.getElementById('reportDate').textContent = new Date().toLocaleDateString('en-US', { weekday:'long', year:'numeric', month:'long', day:'numeric' });
    loadReports();
});

const style = document.createElement('style');
style.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
document.head.appendChild(style);
