const API = '/api';
const authHeaders = () => ({ 'Authorization': 'Bearer ' + localStorage.getItem('token') });

function showToast(msg, type) {
    type = type || 'success';
    const colors = { success:'#059669', danger:'#dc2626', warning:'#d97706' };
    const t = document.createElement('div');
    t.style.cssText = `position:fixed;top:1.5rem;right:1.5rem;z-index:9999;background:${colors[type]||colors.success};color:#fff;padding:.85rem 1.25rem;border-radius:12px;font-size:.875rem;font-weight:600;box-shadow:0 8px 24px rgba(0,0,0,.2);min-width:220px;`;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
}

function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }

async function loadApprovals() {
    const tbody = document.getElementById('approvalTable');
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Loading...</td></tr>';
    try {
        const res  = await fetch(`${API}/pharmacy/prescriptions?status=pending`, { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        const list = data.prescriptions;
        if (!list.length) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No pending prescriptions.</td></tr>';
            return;
        }
        tbody.innerHTML = list.map(p => `
            <tr id="row-${p.id}">
                <td>${esc(p.prescription_id || String(p.id))}</td>
                <td>${esc(p.patient?.name || '—')}</td>
                <td>${esc(p.medication)}</td>
                <td>${esc(p.dosage || '—')}</td>
                <td>${esc(p.doctor?.name || '—')}</td>
                <td>${p.created_at ? p.created_at.split('T')[0] : '—'}</td>
                <td>
                    <button class="btn btn-sm btn-info" onclick="viewPrediction(${p.id}, '${esc(p.patient?.name || '')}')" style="margin-right:4px;margin-bottom:4px;">
                        <i class="bi bi-graph-up"></i> ML
                    </button>
                    <button class="btn btn-sm btn-success" onclick="approveMedication(${p.id})" style="margin-right:4px;margin-bottom:4px;">
                        <i class="bi bi-check-circle"></i> Approve
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="rejectMedication(${p.id})" style="margin-bottom:4px;">
                        <i class="bi bi-x-circle"></i> Reject
                    </button>
                </td>
            </tr>`).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-danger text-center">${esc(err.message)}</td></tr>`;
    }
}

async function approveMedication(id) {
    try {
        const res  = await fetch(`${API}/pharmacy/verify/${id}`, {
            method: 'POST',
            headers: { ...authHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        showToast('Prescription approved successfully!', 'success');
        const row = document.getElementById('row-' + id);
        if (row) { row.style.background = '#dcfce7'; setTimeout(loadApprovals, 800); }
    } catch (err) {
        showToast('Error: ' + err.message, 'danger');
    }
}

async function rejectMedication(id) {
    const reason = prompt('Reason for rejection (optional):');
    if (reason === null) return;
    try {
        const res  = await fetch(`${API}/pharmacy/prescriptions/${id}/reject`, {
            method: 'POST',
            headers: { ...authHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes: reason || 'Rejected by pharmacist' })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        showToast('Prescription rejected.', 'warning');
        const row = document.getElementById('row-' + id);
        if (row) { row.style.background = '#fee2e2'; setTimeout(loadApprovals, 800); }
    } catch (err) {
        showToast('Error: ' + err.message, 'danger');
    }
}

async function viewPrediction(prescriptionId, patientName) {
    const modal = document.getElementById('predictionModal');
    const body  = document.getElementById('predictionBody');
    if (!modal || !body) return;

    body.innerHTML = '<p class="text-muted">Loading ML prediction...</p>';
    modal.style.display = 'flex';

    try {
        const res  = await fetch(`${API}/pharmacy/prescriptions/${prescriptionId}/prediction`, { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        const p = data.prediction;
        if (!p) { body.innerHTML = '<p class="text-muted">No ML prediction linked to this prescription.</p>'; return; }

        const riskBadge = { 'LOW RISK':'badge-green', 'MODERATE RISK':'badge-yellow', 'HIGH RISK':'badge-red', 'VERY HIGH RISK':'badge-purple' };
        const badge = riskBadge[p.risk_level] || 'badge-gray';

        body.innerHTML = `
            <div class="space-y-2 text-sm">
                <div><strong>Patient:</strong> ${esc(patientName)}</div>
                <div><strong>Result:</strong> <span class="badge ${p.result === 'Diabetic' ? 'badge-red' : 'badge-green'}">${esc(p.result)}</span></div>
                <div><strong>Probability:</strong> ${p.probability_percent}%</div>
                <div><strong>Risk Level:</strong> <span class="badge ${badge}">${esc(p.risk_level)}</span></div>
                <div><strong>Model:</strong> ${esc(p.model_used)}</div>
                <div><strong>Date:</strong> ${p.created_at ? p.created_at.split('T')[0] : '—'}</div>
            </div>`;
    } catch (err) {
        body.innerHTML = `<p style="color:#dc2626;">${esc(err.message)}</p>`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const user = checkAuth('pharmacist');
    if (!user) return;
    const name = user.name || user.username;
    document.getElementById('navUserName').textContent = name;
    const sb = document.getElementById('sidebarName');
    if (sb) sb.textContent = name;
    loadApprovals();
});
