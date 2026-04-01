const API = '/api';
const authHeaders = () => ({ 'Authorization': 'Bearer ' + localStorage.getItem('token') });

let currentPrescription = null;

// ── Toast ──────────────────────────────────────────────────────────────────
function toast(msg, type) {
    type = type || 'success';
    const colors = { success:'#059669', danger:'#dc2626', warning:'#d97706' };
    const t = document.createElement('div');
    t.style.cssText = `position:fixed;top:1.5rem;right:1.5rem;z-index:9999;background:${colors[type]||colors.success};color:#fff;padding:.85rem 1.25rem;border-radius:12px;font-size:.875rem;font-weight:600;box-shadow:0 8px 24px rgba(0,0,0,.2);min-width:220px;`;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
}

// ── Load pending/verified prescriptions list ───────────────────────────────
async function loadPrescriptionList() {
    const tbody = document.getElementById('prescriptionListTable');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Loading...</td></tr>';
    try {
        const res  = await fetch(`${API}/pharmacy/prescriptions?status=pending`, { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        // Also fetch verified
        const res2  = await fetch(`${API}/pharmacy/prescriptions?status=verified`, { headers: authHeaders() });
        const data2 = await res2.json();
        const list  = [...(data.prescriptions || []), ...(data2.prescriptions || [])];

        if (!list.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No prescriptions ready to dispense.</td></tr>';
            return;
        }
        const statusBadge = s => {
            const m = { pending:'badge-yellow', pending_pharmacist:'badge-yellow', verified:'badge-cyan' };
            return `<span class="badge ${m[s]||'badge-gray'}">${s.replace('_',' ')}</span>`;
        };
        tbody.innerHTML = list.map(p => `
            <tr>
                <td>${p.prescription_id || p.id}</td>
                <td>${p.patient?.name || '—'}</td>
                <td>${p.medication}</td>
                <td>${p.dosage || '—'}</td>
                <td>${statusBadge(p.status)}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="selectPrescription(${p.id})">
                        <i class="bi bi-capsule"></i> Select
                    </button>
                </td>
            </tr>`).join('');
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-danger text-center">${err.message}</td></tr>`;
    }
}

// ── Select a prescription → load details + inventory + ML ─────────────────
async function selectPrescription(id) {
    const detailEl = document.getElementById('prescriptionDetails');
    const formCard = document.getElementById('dispensingFormCard');
    detailEl.innerHTML = '<p class="text-muted">Loading...</p>';
    if (formCard) formCard.style.display = 'none';

    try {
        const res  = await fetch(`${API}/pharmacy/prescriptions/${id}`, { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        const p = data.prescription;
        currentPrescription = p;

        document.getElementById('prescription_id').value = p.id;

        // Status badge color
        const statusColor = { pending:'badge-yellow', pending_pharmacist:'badge-yellow', verified:'badge-cyan', dispensed:'badge-green' };
        const sc = statusColor[p.status] || 'badge-gray';

        detailEl.innerHTML = `
            <div class="space-y-2 text-sm" style="padding:.5rem;">
                <div class="flex justify-between"><span class="text-muted">Prescription ID</span><strong>${p.prescription_id || p.id}</strong></div>
                <div class="flex justify-between"><span class="text-muted">Patient</span><strong>${p.patient?.name || '—'}</strong></div>
                <div class="flex justify-between"><span class="text-muted">Doctor</span><span>${p.doctor?.name || '—'}</span></div>
                <div class="flex justify-between"><span class="text-muted">Medication</span><strong class="text-blue-600">${p.medication}</strong></div>
                <div class="flex justify-between"><span class="text-muted">Dosage</span><span>${p.dosage || '—'}</span></div>
                <div class="flex justify-between"><span class="text-muted">Frequency</span><span>${p.frequency || '—'}</span></div>
                <div class="flex justify-between"><span class="text-muted">Duration</span><span>${p.duration || '—'}</span></div>
                <div class="flex justify-between"><span class="text-muted">Instructions</span><span>${p.instructions || '—'}</span></div>
                <div class="flex justify-between"><span class="text-muted">Status</span><span class="badge ${sc}">${p.status.replace('_',' ')}</span></div>
                <div class="flex justify-between"><span class="text-muted">Prescribed On</span><span>${p.created_at ? p.created_at.split('T')[0] : '—'}</span></div>
            </div>`;

        // Check inventory stock for this medication
        await checkInventoryStock(p.medication);

        // Load ML prediction
        await loadMLPrediction(id, p.patient?.name || '');

        // Show dispensing form
        if (formCard) formCard.style.display = 'block';

        // Scroll to form
        detailEl.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
        detailEl.innerHTML = `<p class="text-danger">${err.message}</p>`;
    }
}

// ── Inventory stock check ──────────────────────────────────────────────────
async function checkInventoryStock(medicationName) {
    const el = document.getElementById('inventoryStatus');
    if (!el) return;
    try {
        const res  = await fetch(`${API}/pharmacy/inventory?search=${encodeURIComponent(medicationName)}`, { headers: authHeaders() });
        const data = await res.json();
        if (!data.success || !data.inventory.length) {
            el.innerHTML = `<div class="alert alert-secondary py-2 mb-0">
                <i class="bi bi-info-circle"></i> No inventory record found for <strong>${medicationName}</strong>.</div>`;
            return;
        }
        const item = data.inventory[0];
        const colorMap = { 'In Stock': 'alert-success', 'Low Stock': 'alert-warning', 'Out of Stock': 'alert-danger' };
        const badgeMap = { 'In Stock': 'badge-green', 'Low Stock': 'badge-yellow', 'Out of Stock': 'badge-red' };
        const color = colorMap[item.status] || 'alert-info';
        const badge = badgeMap[item.status] || 'badge-gray';
        el.innerHTML = `<div class="alert ${color}">
            <i class="bi bi-box-seam me-2"></i>
            <strong>${item.name}</strong> — Stock: <strong>${item.quantity} ${item.unit || ''}</strong>
            &nbsp;<span class="badge ${badge}">${item.status}</span>
            ${item.status === 'Out of Stock' ? '<br><small>Warning: This medication is out of stock!</small>' : ''}
        </div>`;
    } catch {
        el.innerHTML = '';
    }
}

// ── ML Prediction panel ────────────────────────────────────────────────────
async function loadMLPrediction(prescriptionId, patientName) {
    const el = document.getElementById('mlPredictionPanel');
    if (!el) return;
    el.innerHTML = '<p class="text-muted small">Loading ML prediction...</p>';
    try {
        const res  = await fetch(`${API}/pharmacy/prescriptions/${prescriptionId}/prediction`, { headers: authHeaders() });
        const data = await res.json();
        if (!data.success || !data.prediction) {
            el.innerHTML = '<p class="text-muted small"><i class="bi bi-info-circle"></i> No ML prediction linked to this prescription.</p>';
            return;
        }
        const pred = data.prediction;
        const riskBadge = { 'LOW RISK':'badge-green', 'MODERATE RISK':'badge-yellow', 'HIGH RISK':'badge-red', 'VERY HIGH RISK':'badge-purple' };
        const rc = riskBadge[pred.risk_level] || 'badge-gray';
        el.innerHTML = `
            <div class="card" style="background:#eff6ff;">
                <div class="card-header" style="background:linear-gradient(90deg,#1e3a8a,#2563eb);">
                    <i class="bi bi-graph-up me-1"></i> ML Diabetes Prediction
                </div>
                <div class="grid grid-cols-2 gap-3 text-sm" style="padding:1rem;">
                    <div><div class="text-muted text-xs">Patient</div><strong>${patientName}</strong></div>
                    <div><div class="text-muted text-xs">Result</div>
                        <span class="badge ${pred.result === 'Diabetic' ? 'badge-red' : 'badge-green'}">${pred.result}</span></div>
                    <div><div class="text-muted text-xs">Probability</div><strong>${pred.probability_percent}%</strong></div>
                    <div><div class="text-muted text-xs">Risk Level</div>
                        <span class="badge ${rc}">${pred.risk_level}</span></div>
                    <div style="grid-column:1/-1;"><div class="text-muted text-xs">Model: ${pred.model_used} &nbsp;|&nbsp; Date: ${pred.created_at ? pred.created_at.split('T')[0] : '—'}</div></div>
                </div>
            </div>`;
    } catch {
        el.innerHTML = '<p class="text-muted small">Could not load ML prediction.</p>';
    }
}

// ── Dispense ───────────────────────────────────────────────────────────────
async function saveDispensing(event) {
    event.preventDefault();
    const id    = document.getElementById('prescription_id').value;
    const notes = document.getElementById('instructions').value;
    if (!id) { toast('Please select a prescription first.', 'warning'); return; }

    const btn = event.submitter;
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Dispensing...';

    try {
        const res  = await fetch(`${API}/pharmacy/dispense/${id}`, {
            method: 'POST',
            headers: { ...authHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ notes })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        // Show receipt modal
        showReceipt(data.dispensed);

        // Reload list
        loadPrescriptionList();
        document.getElementById('dispensingFormCard').style.display = 'none';
        document.getElementById('prescriptionDetails').innerHTML = '<p class="text-muted">Select a prescription from the list above.</p>';
        document.getElementById('instructions').value = '';

    } catch (err) {
        toast('Error: ' + err.message, 'danger');
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-circle"></i> Dispense Medication';
    }
}

// ── Receipt modal ──────────────────────────────────────────────────────────
function showReceipt(dispensed) {
    const body = document.getElementById('receiptBody');
    const modal = document.getElementById('receiptModal');
    if (!body || !modal) { toast('Dispensed successfully!', 'success'); return; }
    body.innerHTML = `
        <div class="text-center mb-3">
            <i class="bi bi-check-circle-fill text-success" style="font-size:3rem;"></i>
            <h5 class="mt-2 text-success">Medication Dispensed!</h5>
        </div>
        <div class="space-y-2 text-sm" style="padding:1rem;">
                <div class="flex justify-between"><span class="text-muted">Prescription</span><span>${dispensed.prescription_id || '—'}</span></div>
                <div class="flex justify-between"><span class="text-muted">Medication</span><strong>${dispensed.medication}</strong></div>
                <div class="flex justify-between"><span class="text-muted">Patient</span><span>${dispensed.patient}</span></div>
                <div class="flex justify-between"><span class="text-muted">Dispensed By</span><span>${dispensed.dispensed_by}</span></div>
                <div class="flex justify-between"><span class="text-muted">Date &amp; Time</span><span>${dispensed.dispensed_at ? dispensed.dispensed_at.replace('T',' ').split('.')[0] : '—'}</span></div>
            </div>`;
    modal.style.display = 'flex';
}

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const user = checkAuth('pharmacist');
    if (!user) return;
    const name = user.name || user.username;
    document.getElementById('navUserName').textContent = name;
    const sb = document.getElementById('sidebarName');
    if (sb) sb.textContent = name;

    // If ?id= in URL, auto-select that prescription
    const urlId = new URLSearchParams(window.location.search).get('id');
    loadPrescriptionList().then(() => {
        if (urlId) selectPrescription(urlId);
    });
});
