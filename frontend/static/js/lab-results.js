// Enter Lab Results - uses GET /api/labs/pending + POST /api/labs/results

function authHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('token')
    };
}

function showAlert(message, type) {
    type = type || 'success';
    const el = document.getElementById('formAlert');
    el.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    el.scrollIntoView({ behavior: 'smooth' });
}

async function loadPendingTests() {
    const select = document.getElementById('pendingTestSelect');
    try {
        const res = await fetch('/api/labs/pending?limit=100', { headers: authHeaders() });
        if (res.status === 401) { localStorage.removeItem('token'); localStorage.removeItem('user'); window.location.href = '/login'; return; }
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        if (!data.pending_tests.length) {
            select.innerHTML = '<option value="">No pending tests</option>';
            return;
        }

        select.innerHTML = '<option value="">Select a pending test...</option>' +
            data.pending_tests.map(t =>
                `<option value="${t.test_id}" data-name="${t.test_name}" data-patient="${t.patient?.name || 'Unknown'}" data-priority="${t.priority}">
                    ${t.test_id} — ${t.test_name} (${t.patient?.name || 'Unknown'}) [${t.priority}]
                </option>`
            ).join('');
    } catch (err) {
        select.innerHTML = `<option value="">Error loading tests: ${err.message}</option>`;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('lab_technician');
    if (!user) return;

    const name = user.name || user.username;
    document.getElementById('topUserName').textContent = name;
    document.getElementById('userName').textContent = name;

    document.getElementById('test_date').valueAsDate = new Date();

    loadPendingTests();

    // Auto-fill info card when a pending test is selected
    document.getElementById('pendingTestSelect').addEventListener('change', function () {
        const opt = this.options[this.selectedIndex];
        const card = document.getElementById('testInfoCard');
        if (!this.value) { card.style.display = 'none'; return; }
        document.getElementById('infoPatient').textContent = opt.dataset.patient || '—';
        document.getElementById('infoTestName').textContent = opt.dataset.name || '—';
        document.getElementById('infoPriority').textContent = opt.dataset.priority || '—';
        card.style.display = '';
    });

    document.getElementById('labResultsForm').addEventListener('submit', async function (e) {
        e.preventDefault();
        const btn = this.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Saving...';

        const testId = document.getElementById('pendingTestSelect').value;
        if (!testId) {
            showAlert('Please select a pending test.', 'warning');
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle"></i> Save Results';
            return;
        }

        const payload = {
            test_id: testId,
            results: document.getElementById('resultValue').value.trim(),
            unit: document.getElementById('unit').value.trim(),
            normal_range: document.getElementById('normalRange').value.trim(),
            remarks: document.getElementById('notes').value.trim()
        };

        try {
            const res = await fetch('/api/labs/results', {
                method: 'POST',
                headers: authHeaders(),
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!data.success) throw new Error(data.message || 'Failed to save results');

            showAlert(`Results saved for <strong>${data.test?.test_name || testId}</strong>`, 'success');
            this.reset();
            document.getElementById('test_date').valueAsDate = new Date();
            document.getElementById('testInfoCard').style.display = 'none';
            loadPendingTests();

        } catch (err) {
            showAlert(err.message, 'danger');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-check-circle"></i> Save Results';
        }
    });
});
