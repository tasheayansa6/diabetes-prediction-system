// Admin Manage ML Models - uses /api/admin/models

const API = '/api/admin/models';

function authHeaders() {
    return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('token') };
}

// ===== Load & Render =====

async function loadModels() {
    try {
        const res = await fetch(API, { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        renderAll(data.models);
    } catch (e) {
        showToast('Failed to load models: ' + e.message, 'danger');
    }
}

function renderAll(models) {
    const active = models.find(m => m.status === 'active') || models[0];
    if (!active) return;

    // Stats cards
    document.getElementById('statAccuracy').textContent = active.accuracy + '%';
    document.getElementById('statVersion').textContent = active.version;
    document.getElementById('statDate').textContent = active.date;

    // Metrics panel
    document.getElementById('metricAccuracy').textContent = active.accuracy + '%';
    document.getElementById('metricPrecision').textContent = active.precision + '%';
    document.getElementById('metricRecall').textContent = active.recall + '%';
    document.getElementById('metricF1').textContent = active.f1Score + '%';
    document.getElementById('metricAlgorithm').textContent = active.algorithm;
    document.getElementById('metricSamples').textContent = Number(active.trainingSamples).toLocaleString();
    document.getElementById('metricFeatures').textContent = active.features;

    // Version table — active model only, archived hidden
    document.getElementById('modelTableBody').innerHTML = models
        .filter(m => m.status === 'active')
        .map(m => `
        <tr>
            <td><strong>${m.version}</strong><br><span style="font-size:.68rem;color:#059669;font-weight:600;"><i class="bi bi-robot"></i> Predictions use this model</span></td>
            <td>${m.date}</td>
            <td>${m.algorithm}</td>
            <td><strong style="color:#059669">${m.accuracy}%</strong></td>
            <td><span style="background:#059669;color:#fff;border-radius:99px;padding:.2em .75em;font-size:.72rem;font-weight:700;"><i class="bi bi-check-circle-fill"></i> Active</span></td>
            <td><button class="btn btn-sm btn-info" onclick="viewModel(${m.id})"><i class="bi bi-eye"></i> View</button></td>
        </tr>`).join('') ||
        '<tr><td colspan="6" style="text-align:center;color:#94a3b8;padding:1.5rem;">No active model found.</td></tr>';
}

// ===== View =====

async function viewModel(id) {
    const res = await fetch(API, { headers: authHeaders() });
    const data = await res.json();
    const m = data.models.find(x => x.id === id);
    if (!m) return;
    document.getElementById('viewModalTitle').textContent = 'Model ' + m.version + ' Details';
    document.getElementById('viewModalBody').innerHTML = `
        <div class="row g-3">
            <div class="col-6"><strong>Version:</strong> ${m.version}</div>
            <div class="col-6"><strong>Algorithm:</strong> ${m.algorithm}</div>
            <div class="col-6"><strong>Date:</strong> ${m.date}</div>
            <div class="col-6"><strong>Status:</strong> <span class="badge ${m.status === 'active' ? 'bg-success' : 'bg-secondary'}">${m.status}</span></div>
            <div class="col-6"><strong>Accuracy:</strong> ${m.accuracy}%</div>
            <div class="col-6"><strong>Precision:</strong> ${m.precision}%</div>
            <div class="col-6"><strong>Recall:</strong> ${m.recall}%</div>
            <div class="col-6"><strong>F1-Score:</strong> ${m.f1Score}%</div>
            <div class="col-6"><strong>Training Samples:</strong> ${Number(m.trainingSamples).toLocaleString()}</div>
            <div class="col-6"><strong>Features:</strong> ${m.features}</div>
            <div class="col-12"><strong>Notes:</strong><br><span class="text-muted">${m.notes || 'No notes.'}</span></div>
        </div>`;
    document.getElementById('viewModal').style.display = 'flex';
}

// ===== Edit =====

let _editModels = [];

async function editModel(id) {
    const res = await fetch(API, { headers: authHeaders() });
    const data = await res.json();
    _editModels = data.models;
    const m = _editModels.find(x => x.id === id);
    if (!m) return;
    document.getElementById('editModelId').value = m.id;
    document.getElementById('editVersion').value = m.version;
    document.getElementById('editAlgorithm').value = m.algorithm;
    document.getElementById('editAccuracy').value = m.accuracy;
    document.getElementById('editPrecision').value = m.precision;
    document.getElementById('editRecall').value = m.recall;
    document.getElementById('editF1').value = m.f1Score;
    document.getElementById('editSamples').value = m.trainingSamples;
    document.getElementById('editFeatures').value = m.features;
    document.getElementById('editDate').value = m.date;
    document.getElementById('editNotes').value = m.notes || '';
    document.getElementById('editModal').style.display = 'flex';
}

async function saveEditModel() {
    const id = parseInt(document.getElementById('editModelId').value);
    const payload = {
        version: document.getElementById('editVersion').value,
        algorithm: document.getElementById('editAlgorithm').value,
        accuracy: parseFloat(document.getElementById('editAccuracy').value),
        precision: parseFloat(document.getElementById('editPrecision').value),
        recall: parseFloat(document.getElementById('editRecall').value),
        f1Score: parseFloat(document.getElementById('editF1').value),
        trainingSamples: parseInt(document.getElementById('editSamples').value),
        features: parseInt(document.getElementById('editFeatures').value),
        date: document.getElementById('editDate').value,
        notes: document.getElementById('editNotes').value
    };
    try {
        const res = await fetch(`${API}/${id}`, { method: 'PUT', headers: authHeaders(), body: JSON.stringify(payload) });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        document.getElementById('editModal').style.display = 'none';
        showToast('Model updated successfully!', 'success');
        loadModels();
    } catch (e) {
        showToast('Update failed: ' + e.message, 'danger');
    }
}

// ===== Activate =====

async function activateModel(id) {
    if (!confirm('Set this model as the active model?')) return;
    try {
        const res = await fetch(`${API}/${id}/activate`, { method: 'POST', headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        showToast('Model activated!', 'success');
        loadModels();
    } catch (e) {
        showToast('Activation failed: ' + e.message, 'danger');
    }
}

// ===== Delete =====

async function deleteModel(id) {
    if (!confirm('Delete this archived model? This cannot be undone.')) return;
    try {
        const res = await fetch(`${API}/${id}`, { method: 'DELETE', headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        showToast('Model deleted.', 'warning');
        loadModels();
    } catch (e) {
        showToast('Delete failed: ' + e.message, 'danger');
    }
}

// ===== Upload =====

async function uploadModel(event) {
    event.preventDefault();

    const fileInput = document.getElementById('modelFile');
    const version   = document.getElementById('version').value.trim();
    const accuracy  = parseFloat(document.getElementById('accuracy').value);

    if (!version)              { showToast('Please enter a version number.', 'danger'); return; }
    if (!fileInput.files.length){ showToast('Please select a .pkl model file.', 'danger'); return; }
    if (isNaN(accuracy) || accuracy < 0 || accuracy > 100) { showToast('Enter a valid accuracy (0-100).', 'danger'); return; }

    const formData = new FormData();
    formData.append('model_file',      fileInput.files[0]);
    formData.append('version',         version);
    formData.append('algorithm',       document.getElementById('algorithm').value);
    formData.append('accuracy',        accuracy);
    formData.append('precision',       document.getElementById('precision').value || 0);
    formData.append('recall',          document.getElementById('recall').value || 0);
    formData.append('f1Score',         document.getElementById('f1Score').value || 0);
    formData.append('notes',           document.getElementById('notes').value.trim());
    formData.append('setActive',       document.getElementById('setActive').checked);
    formData.append('features',        8);

    const btn = event.submitter || document.querySelector('#uploadModelForm button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Uploading...';

    try {
        const res = await fetch('/api/admin/models/upload', {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') },
            body: formData   // No Content-Type header — browser sets multipart boundary
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);
        document.getElementById('uploadModelForm').reset();
        showToast(data.message || 'Model uploaded successfully!', 'success');
        loadModels();
    } catch (e) {
        showToast('Upload failed: ' + e.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-upload"></i> Upload Model';
    }
}

// ===== Toast =====

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const colors = { success: '#16a34a', danger: '#dc2626', warning: '#d97706' };
    const div = document.createElement('div');
    div.style.cssText = `background:${colors[type]||colors.success};color:#fff;padding:10px 16px;border-radius:6px;margin-bottom:8px;font-size:14px;box-shadow:0 2px 8px rgba(0,0,0,.2);`;
    div.textContent = message;
    container.appendChild(div);
    setTimeout(() => div.remove(), 3000);
}

// ===== Init =====

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('admin');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;
    loadModels();
});
