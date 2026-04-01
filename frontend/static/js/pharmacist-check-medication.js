const API = '/api';
const authHeaders = () => ({ 'Authorization': 'Bearer ' + localStorage.getItem('token') });

function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }

function stockBadge(s) {
    const map = { 'In Stock':'badge-green', 'Low Stock':'badge-yellow', 'Out of Stock':'badge-red' };
    return `<span class="badge ${map[s] || 'badge-gray'}">${s}</span>`;
}

function rowStyle(s) {
    if (s === 'Out of Stock') return 'background:#fef2f2;';
    if (s === 'Low Stock')    return 'background:#fffbeb;';
    return '';
}

async function loadInventory(search, category) {
    search   = search   || '';
    category = category || '';
    const tbody    = document.getElementById('inventoryTable');
    const alertBox = document.getElementById('lowStockAlert');
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Loading...</td></tr>';

    try {
        let url = `${API}/pharmacy/inventory?limit=100`;
        if (search)   url += '&search='   + encodeURIComponent(search);
        if (category) url += '&category=' + encodeURIComponent(category);

        const res  = await fetch(url, { headers: authHeaders() });
        const data = await res.json();
        if (!data.success) throw new Error(data.message);

        const list = data.inventory;

        // Low-stock alert banner
        const alerts = list.filter(m => m.status !== 'In Stock');
        if (alertBox) {
            if (alerts.length) {
                alertBox.innerHTML = `<i class="bi bi-exclamation-triangle-fill" style="margin-right:6px;"></i>
                    <strong>${alerts.length} item(s)</strong> need attention: ` +
                    alerts.map(m => `<span class="badge ${m.status === 'Out of Stock' ? 'badge-red' : 'badge-yellow'}" style="margin-left:4px;">${esc(m.name)}</span>`).join('');
                alertBox.style.display = '';
            } else {
                alertBox.style.display = 'none';
            }
        }

        if (!list.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No medications found.</td></tr>';
            return;
        }

        tbody.innerHTML = list.map(m => `
            <tr style="${rowStyle(m.status)}">
                <td><strong>${esc(m.name)}</strong></td>
                <td>${esc(m.generic_name || '—')} <span class="badge badge-gray" style="margin-left:4px;">${esc(m.category || '—')}</span></td>
                <td>${m.quantity} <small class="text-muted">${esc(m.unit || '')}</small></td>
                <td>${m.expiry_date ? m.expiry_date.split('T')[0] : '—'}</td>
                <td>${m.selling_price != null ? 'ETB ' + parseFloat(m.selling_price).toFixed(2) : '—'}</td>
                <td>${stockBadge(m.status)}</td>
            </tr>`).join('');

        const setText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
        setText('countTotal',   list.length);
        setText('countInStock', list.filter(m => m.status === 'In Stock').length);
        setText('countLow',     list.filter(m => m.status === 'Low Stock').length);
        setText('countOut',     list.filter(m => m.status === 'Out of Stock').length);

    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-danger text-center">${esc(err.message)}</td></tr>`;
    }
}

function searchMedication(event) {
    event.preventDefault();
    const search   = document.getElementById('medication_name').value.trim();
    const category = document.getElementById('categoryFilter')?.value || '';
    loadInventory(search, category);
}

function clearSearch() {
    document.getElementById('medication_name').value = '';
    const cf = document.getElementById('categoryFilter');
    if (cf) cf.value = '';
    loadInventory();
}

document.addEventListener('DOMContentLoaded', () => {
    const user = checkAuth('pharmacist');
    if (!user) return;
    const name = user.name || user.username;
    document.getElementById('navUserName').textContent = name;
    const sb = document.getElementById('sidebarName');
    if (sb) sb.textContent = name;

    const cf = document.getElementById('categoryFilter');
    if (cf) cf.addEventListener('change', () =>
        loadInventory(document.getElementById('medication_name').value.trim(), cf.value)
    );

    loadInventory();
});
