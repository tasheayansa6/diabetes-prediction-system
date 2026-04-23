const API = '/api';
function getToken() { return localStorage.getItem('token'); }
function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }

const RISK = {
    'LOW RISK':       { cls: 'low',      pill: 'pill-low',      icon: 'bi-check-circle-fill',             label: 'Low Risk' },
    'MODERATE RISK':  { cls: 'moderate', pill: 'pill-moderate', icon: 'bi-exclamation-circle-fill',       label: 'Moderate Risk' },
    'HIGH RISK':      { cls: 'high',     pill: 'pill-high',     icon: 'bi-exclamation-triangle-fill',     label: 'High Risk' },
    'VERY HIGH RISK': { cls: 'veryhigh', pill: 'pill-veryhigh', icon: 'bi-heart-pulse-fill',              label: 'Very High Risk' }
};

let allPredictions = [];

function renderCards(predictions) {
    const list = document.getElementById('predictionsList');
    const countEl = document.getElementById('filterCount');
    if (countEl) countEl.textContent = predictions.length + ' result' + (predictions.length !== 1 ? 's' : '');

    if (!predictions.length) {
        list.innerHTML = `<div class="empty-state">
            <i class="bi bi-clipboard-x"></i>
            <h4>No predictions found</h4>
            <p>Try a different filter or <a href="/templates/patient/health_data_form.html" style="color:#1565c0;">create a new prediction</a>.</p>
        </div>`;
        return;
    }

    list.innerHTML = predictions.map(p => {
        const cfg  = RISK[p.risk_level] || RISK['LOW RISK'];
        const inp  = p.input_data || {};
        const date = new Date(p.created_at).toLocaleDateString('en-US', { year:'numeric', month:'short', day:'numeric' });
        const time = new Date(p.created_at).toLocaleTimeString('en-US', { hour:'2-digit', minute:'2-digit' });
        const pct  = p.probability_percent ? p.probability_percent.toFixed(1) + '%' : '--';
        const glucose = inp.glucose ? inp.glucose + ' mg/dL' : '--';
        const bmi     = inp.bmi    ? 'BMI ' + inp.bmi       : '';
        const age     = inp.age    ? 'Age ' + inp.age        : '';
        const review = p.review || {};
        const reviewStatus = review.status ? String(review.status).replace('_', ' ') : 'pending review';

        return `<div class="pred-card ${cfg.cls}">
            <div class="pred-icon ${cfg.cls}">
                <i class="bi ${cfg.icon}"></i>
            </div>
            <div class="pred-body">
                <div class="pred-title">
                    Diabetes Risk Assessment
                    <span class="risk-pill ${cfg.pill}" style="margin-left:.5rem;">${cfg.label}</span>
                </div>
                <div class="pred-meta">
                    <span><i class="bi bi-calendar3"></i> ${esc(date)} ${esc(time)}</span>
                    ${glucose !== '--' ? `<span><i class="bi bi-droplet"></i> Glucose: ${esc(glucose)}</span>` : ''}
                    ${bmi ? `<span><i class="bi bi-person"></i> ${esc(bmi)}</span>` : ''}
                    ${age ? `<span><i class="bi bi-clock"></i> ${esc(age)}</span>` : ''}
                    <span><i class="bi bi-person-check"></i> Review: ${esc(reviewStatus)}</span>
                </div>
            </div>
            <div class="pred-pct ${cfg.cls}">${esc(pct)}</div>
            <div class="pred-actions">
                <a href="/templates/patient/prediction_result.html?id=${p.id}" class="btn btn-sm btn-primary" title="View Result">
                    <i class="bi bi-eye"></i> View
                </a>
                <a href="/templates/patient/report_download.html?id=${p.id}" class="btn btn-sm btn-outline" title="Download Report">
                    <i class="bi bi-download"></i>
                </a>
            </div>
        </div>`;
    }).join('');
}

function applyFilter() {
    const risk   = document.getElementById('riskFilter').value;
    const search = document.getElementById('searchInput').value.toLowerCase();
    const filtered = allPredictions.filter(p => {
        const matchRisk   = !risk   || p.risk_level === risk;
        const inp = p.input_data || {};
        const searchStr = [
            p.risk_level,
            p.created_at,
            inp.glucose, inp.bmi, inp.age
        ].join(' ').toLowerCase();
        const matchSearch = !search || searchStr.includes(search);
        return matchRisk && matchSearch;
    });
    renderCards(filtered);
}

async function loadPredictions() {
    const user = checkAuth('patient');
    if (!user) return;

    document.getElementById('navUserName').textContent = user.name || user.username;
    const sb = document.getElementById('sidebarName');
    if (sb) sb.textContent = user.name || user.username;

    try {
        const res  = await fetch(API + '/patient/predictions?limit=100', {
            headers: { 'Authorization': 'Bearer ' + getToken() }
        });
        if (res.status === 401) { logout(); return; }
        
        let data;
        try {
            data = await res.json();
        } catch (jsonErr) {
            console.error('JSON parse error:', jsonErr);
            throw new Error('Server returned invalid JSON (status ' + res.status + ')');
        }

        console.log('API response:', data);

        const predictions = data.predictions || [];
        if (!data.success) {
            console.error('API returned success=false:', data.message);
            document.getElementById('predictionsList').innerHTML = `<div class="empty-state">
                <i class="bi bi-exclamation-circle" style="color:#dc2626;"></i>
                <h4>Could Not Load Predictions</h4>
                <p style="color:#dc2626;">${data.message || 'Unknown error'}</p>
                <a href="javascript:loadPredictions()" class="btn btn-primary mt-3">Try Again</a>
            </div>`;
            return;
        }
        
        if (!predictions.length) {
            document.getElementById('predictionsList').innerHTML = `<div class="empty-state">
                <i class="bi bi-clipboard-x"></i>
                <h4>No predictions yet</h4>
                <p>Complete a nurse check-up and lab tests, then <a href="/templates/patient/health_data_form.html" style="color:#1565c0;">create your first prediction</a>.</p>
            </div>`;
            return;
        }

        allPredictions = predictions;

        // Summary counts
        const counts = { low: 0, mod: 0, high: 0 };
        allPredictions.forEach(p => {
            if (p.risk_level === 'LOW RISK')       counts.low++;
            else if (p.risk_level === 'MODERATE RISK') counts.mod++;
            else counts.high++;
        });
        document.getElementById('sumTotal').textContent = allPredictions.length;
        document.getElementById('sumLow').textContent   = counts.low;
        document.getElementById('sumMod').textContent   = counts.mod;
        document.getElementById('sumHigh').textContent  = counts.high;
        document.getElementById('summaryStrip').style.display = '';
        document.getElementById('filterBar').style.display    = '';

        renderCards(allPredictions);
    } catch (e) {
        const msg = e.message || 'Network error';
        const isAuth = msg.toLowerCase().includes('401') || msg.toLowerCase().includes('unauthorized');
        document.getElementById('predictionsList').innerHTML = `<div class="empty-state">
            <i class="bi bi-exclamation-circle" style="color:#e65100;"></i>
            <h4>${isAuth ? 'Session Expired' : 'Failed to Load Predictions'}</h4>
            <p>${isAuth ? 'Please <a href="/login" style="color:#1565c0;">log in again</a>.' : 'Check your connection and <a href="javascript:loadPredictions()" style="color:#1565c0;">try again</a>.'}</p>
        </div>`;
    }
}

document.addEventListener('DOMContentLoaded', loadPredictions);
