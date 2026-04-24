// Lab Add Test Type - calls POST /api/labs/test-types

function quickFill(val) {
    if (!val) return;
    const [name, code, range, prep] = val.split('|');
    const form = document.getElementById('testTypeForm');
    form.test_name.value = name;
    form.test_code.value = code;
    form.normal_range.value = range;
    form.description.value = prep;
    form.category.value = 'Diabetes';
}

function authHeaders() {
    return {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('token')
    };
}

function showAlert(message, type = 'success') {
    const el = document.getElementById('formAlert');
    el.innerHTML = `<div class="alert alert-${type} alert-dismissible fade show" role="alert">
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>`;
    el.scrollIntoView({ behavior: 'smooth' });
}

async function handleTestTypeSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Saving...';

    const payload = {
        test_name:    form.test_name.value.trim(),
        test_type:    form.test_code.value.trim(),   // backend expects test_type
        category:     form.category.value,
        cost:         parseFloat(form.price.value) || 0,
        normal_range: form.normal_range.value.trim(),
        preparation_instructions: form.description.value.trim()
    };

    try {
        const res = await fetch('/api/labs/test-types', {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (!data.success) throw new Error(data.message || 'Failed to add test type');

        showAlert(`Test type "<strong>${payload.test_name}</strong>" added successfully!`, 'success');
        form.reset();

        // Redirect after short delay
        setTimeout(() => {
            window.location.href = '/templates/lab/lab_test_service.html';
        }, 1500);

    } catch (err) {
        showAlert(err.message, 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check-circle"></i> Add Test Model';
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('lab_technician');
    if (!user) return;

    const name = user.name || user.username;
    document.getElementById('topUserName').textContent = name;
    document.getElementById('userName').textContent = name;

    document.getElementById('testTypeForm').addEventListener('submit', handleTestTypeSubmit);
});
