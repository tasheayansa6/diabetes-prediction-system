// Admin Manage Roles - permissions UI + real user counts from /api/admin/dashboard

const DEFAULT_ROLES = {
    patient:    ['view_own_health', 'request_predictions', 'view_prescriptions', 'make_payments'],
    doctor:     ['view_patient_records', 'create_diagnoses', 'prescribe_medications', 'request_lab_tests'],
    nurse:      ['record_vitals', 'clinical_measurements', 'view_predictions', 'patient_education'],
    lab:        ['manage_lab_tests', 'enter_test_results', 'generate_reports', 'lab_operations'],
    pharmacist: ['review_prescriptions', 'approve_reject_medications', 'dispense_medications', 'inventory_management'],
    admin:      ['full_system_access', 'user_management', 'ml_model_updates', 'payment_refunds']
};

const ALL_PERMISSIONS = {
    view_own_health:            'View own health data',
    request_predictions:        'Request predictions',
    view_prescriptions:         'View prescriptions',
    make_payments:              'Make payments',
    view_patient_records:       'View patient records',
    create_diagnoses:           'Create diagnoses',
    prescribe_medications:      'Prescribe medications',
    request_lab_tests:          'Request lab tests',
    record_vitals:              'Record vital signs',
    clinical_measurements:      'Clinical measurements',
    view_predictions:           'View predictions',
    patient_education:          'Patient education',
    manage_lab_tests:           'Manage lab tests',
    enter_test_results:         'Enter test results',
    generate_reports:           'Generate reports',
    lab_operations:             'Lab operations',
    review_prescriptions:       'Review prescriptions',
    approve_reject_medications: 'Approve/reject medications',
    dispense_medications:       'Dispense medications',
    inventory_management:       'Inventory management',
    full_system_access:         'Full system access',
    user_management:            'User management',
    ml_model_updates:           'ML model updates',
    payment_refunds:            'Payment & refunds'
};

// Map DB role names → card role keys used in this page
const ROLE_KEY_MAP = {
    patient: 'patient', doctor: 'doctor', nurse: 'nurse',
    lab_technician: 'lab', pharmacist: 'pharmacist', admin: 'admin'
};

function getRoles() {
    const stored = localStorage.getItem('rolePermissions');
    return stored ? JSON.parse(stored) : JSON.parse(JSON.stringify(DEFAULT_ROLES));
}

function saveRoles(roles) {
    localStorage.setItem('rolePermissions', JSON.stringify(roles));
}

// ===== Load real user counts from API =====

async function loadUserCounts() {
    try {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/admin/dashboard', {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const data = await res.json();
        if (!data.success) return;

        const dist = data.dashboard.role_distribution; // [{role, count}, ...]
        dist.forEach(({ role, count }) => {
            const key = ROLE_KEY_MAP[role];
            if (!key) return;
            const el = document.getElementById('count_' + key);
            if (el) el.textContent = count + ' user' + (count !== 1 ? 's' : '');
        });
    } catch (_) {
        // Counts are non-critical — fail silently
    }
}

// ===== Permission toggle =====

function togglePermission(role, permission) {
    const roles = getRoles();
    const idx = roles[role].indexOf(permission);
    if (idx === -1) {
        roles[role].push(permission);
    } else {
        if (roles[role].length <= 1) {
            showToast('Each role must have at least one permission.', 'warning');
            document.getElementById(role + '_' + permission).checked = true;
            return;
        }
        roles[role].splice(idx, 1);
    }
    saveRoles(roles);
    updatePermCount(role, roles[role].length);
    showToast('Permission updated for ' + role + ' role.', 'success');
}

function updatePermCount(role, count) {
    const el = document.getElementById('count_' + role);
    if (el) {
        // Preserve user count text if present, just append perm count
        const userText = el.dataset.userCount || '';
        el.textContent = (userText ? userText + ' · ' : '') + count + ' perm' + (count !== 1 ? 's' : '');
    }
}

function resetRole(role) {
    if (!confirm('Reset ' + role + ' role to default permissions?')) return;
    const roles = getRoles();
    roles[role] = [...DEFAULT_ROLES[role]];
    saveRoles(roles);
    renderCheckboxes(role, roles[role]);
    updatePermCount(role, roles[role].length);
    showToast(role + ' role reset to defaults.', 'info');
}

function renderCheckboxes(role, activePerms) {
    const container = document.getElementById('perms_' + role);
    if (!container) return;
    container.innerHTML = activePerms.map(perm => `
        <div class="form-check">
            <input class="form-check-input" type="checkbox" id="${role}_${perm}" checked
                onchange="togglePermission('${role}', '${perm}')">
            <label class="form-check-label" for="${role}_${perm}">${ALL_PERMISSIONS[perm] || perm}</label>
        </div>
    `).join('');
}

// ===== Toast =====

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const colors = { success: 'bg-success', warning: 'bg-warning text-dark', info: 'bg-info text-dark', danger: 'bg-danger' };
    const id = 'toast_' + Date.now();
    container.insertAdjacentHTML('beforeend', `
        <div id="${id}" class="toast align-items-center text-white ${colors[type] || 'bg-success'} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>`);
    const el = document.getElementById(id);
    setTimeout(() => el.remove(), 3000);
}

// ===== Init =====

document.addEventListener('DOMContentLoaded', function () {
    const user = checkAuth('admin');
    if (!user) return;
    document.getElementById('navUserName').textContent = user.name || user.username;

    const roles = getRoles();
    Object.keys(roles).forEach(role => {
        renderCheckboxes(role, roles[role]);
        updatePermCount(role, roles[role].length);
    });

    loadUserCounts();
});
