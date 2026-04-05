function esc(str) {
    const d = document.createElement('div');
    d.textContent = str ?? '';
    return d.innerHTML;
}

function getToken() { return localStorage.getItem('token'); }

async function apiFetch(path) {
    const res = await fetch('/api' + path, {
        headers: { 'Authorization': 'Bearer ' + getToken() }
    });
    return res.json();
}

const RISK_CONFIG = {
    'LOW RISK':       { label: 'Low Risk',       dotCls: 'low',      badgeCls: 'risk-low',      tips: [
        { icon: '🥗', title: 'Eat Balanced Meals',       text: 'Reduce sugar and refined carbs. Eat more vegetables, fiber, and lean protein.' },
        { icon: '🏃', title: '30 Min Exercise Daily',    text: 'Walking, cycling or swimming reduces diabetes risk by up to 58%.' },
        { icon: '💧', title: 'Stay Hydrated',            text: 'Drink 8 glasses of water daily. Avoid sugary drinks and sodas.' }
    ]},
    'MODERATE RISK':  { label: 'Moderate Risk',  dotCls: 'moderate', badgeCls: 'risk-moderate', tips: [
        { icon: '🩸', title: 'Track Blood Sugar',        text: 'Monitor fasting glucose weekly. Target: 70-99 mg/dL. Keep a log.' },
        { icon: '⚖️', title: 'Manage Your Weight',       text: 'Losing 5-7% of body weight significantly reduces progression risk.' },
        { icon: '🚶', title: 'Increase Activity',        text: 'Aim for 150 min/week of moderate exercise. Start with daily walks.' }
    ]},
    'HIGH RISK':      { label: 'High Risk',       dotCls: 'high',     badgeCls: 'risk-high',     tips: [
        { icon: '🏥', title: 'See a Doctor Soon',        text: 'Book an appointment. Your doctor may order HbA1c or glucose tolerance tests.' },
        { icon: '💊', title: 'Follow Medical Advice',    text: 'If prescribed medication, take it as directed. Do not skip doses.' },
        { icon: '📉', title: 'Reduce Sugar Intake',      text: 'Cut all sugary drinks, sweets, and white bread immediately.' }
    ]},
    'VERY HIGH RISK': { label: 'Very High Risk',  dotCls: 'veryhigh', badgeCls: 'risk-veryhigh', tips: [
        { icon: '🚨', title: 'Urgent: See Doctor Now',   text: 'Do not delay. You may need immediate diagnostic tests or medication.' },
        { icon: '🍽️', title: 'Strict Diet Control',      text: 'Eliminate all sugar, white rice, and processed foods immediately.' },
        { icon: '📋', title: 'Diabetes Management Plan', text: 'Ask your doctor about a structured diabetes prevention or management program.' }
    ]}
};

function bmiStatus(bmi) {
    if (bmi < 18.5) return { text: 'Underweight', icon: 'exclamation-circle' };
    if (bmi < 25)   return { text: 'Normal',      icon: 'check-circle' };
    if (bmi < 30)   return { text: 'Overweight',  icon: 'exclamation-triangle' };
    return              { text: 'Obese',       icon: 'exclamation-triangle-fill' };
}

function renderStats(dashboard, predictions, prescriptions, appointments) {
    const now = new Date();
    const monthly = predictions.filter(p => {
        const d = new Date(p.created_at);
        return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
    }).length;

    document.getElementById('totalPredictions').textContent = dashboard.stats.total_predictions;
    document.getElementById('monthlyPredictions').textContent = monthly;

    const apptEl = document.getElementById('appointmentsCount');
    if (apptEl) apptEl.textContent = appointments.filter(a => a.status === 'scheduled').length;

    const latest = dashboard.latest_prediction;
    const heroRisk = document.getElementById('heroRisk');
    const heroRiskPct = document.getElementById('heroRiskPct');

    if (latest && heroRisk) {
        const cfg = RISK_CONFIG[latest.risk_level] || RISK_CONFIG['LOW RISK'];
        heroRisk.textContent = cfg.label;
        heroRiskPct.textContent = latest.probability_percent
            ? latest.probability_percent.toFixed(1) + '% probability'
            : '';

        // Risk alert banner — only for HIGH RISK and VERY HIGH RISK
        const banner = document.getElementById('riskAlertBanner');
        if (banner && (latest.risk_level === 'HIGH RISK' || latest.risk_level === 'VERY HIGH RISK')) {
            const isVH = latest.risk_level === 'VERY HIGH RISK';
            banner.style.display = '';
            banner.innerHTML = `<div class="risk-alert ${isVH ? 'veryhigh' : 'high'}" style="margin-bottom:1.5rem;">
                <i class="bi bi-exclamation-triangle-fill" style="font-size:1.5rem;color:${isVH ? '#7b1fa2' : '#c62828'};flex-shrink:0;"></i>
                <div style="flex:1;">
                    <div style="font-weight:700;color:${isVH ? '#4a148c' : '#b71c1c'};font-size:.95rem;">${isVH ? 'Very High Risk — See a Doctor Immediately' : 'High Risk — Please Book a Doctor Appointment'}</div>
                    <div style="font-size:.82rem;color:${isVH ? '#6a1b9a' : '#c62828'};margin-top:.2rem;">Your latest prediction shows ${cfg.label}. ${isVH ? 'Immediate medical attention is required.' : 'Early action can prevent diabetes.'}</div>
                </div>
                <a href="/templates/patient/appointment.html" class="btn btn-sm" style="background:${isVH ? '#7b1fa2' : '#c62828'};color:#fff;border:none;white-space:nowrap;flex-shrink:0;">Book Now</a>
            </div>`;
        }

        // Dynamic health tips
        const tipsEl = document.getElementById('healthTips');
        if (tipsEl && cfg.tips) {
            tipsEl.innerHTML = cfg.tips.map((t, i) => {
                const gradients = [
                    'linear-gradient(135deg,#e3f2fd,#f3e5f5)',
                    'linear-gradient(135deg,#e8f5e9,#f1f8e9)',
                    'linear-gradient(135deg,#fff3e0,#fce4ec)'
                ];
                return `<div class="tip-card" style="background:${gradients[i]};${i===2?'margin-bottom:0;':''}">
                    <div class="tip-icon">${t.icon}</div>
                    <div><div class="tip-title">${esc(t.title)}</div><div class="tip-text">${esc(t.text)}</div></div>
                </div>`;
            }).join('');
        }
    }

    if (predictions.length > 0) {
        const bmi = parseFloat((predictions[0].input_data || {}).bmi);
        if (!isNaN(bmi)) {
            document.getElementById('currentBMI').textContent = bmi.toFixed(1);
            const s = bmiStatus(bmi);
            const bmiEl = document.getElementById('bmiStatus');
            if (bmiEl) bmiEl.innerHTML = `<i class="bi bi-${esc(s.icon)}"></i> ${esc(s.text)}`;
        }
    }
}

function renderRecentPredictions(predictions) {
    const container = document.getElementById('recentPredictionsList');
    const countEl = document.getElementById('predCount');
    if (countEl) countEl.textContent = predictions.length;
    if (!predictions.length) {
        container.innerHTML = '<div class="pred-item" style="justify-content:center;color:#90a4ae;font-size:.85rem;">No predictions yet. <a href="/templates/patient/health_data_form.html" style="color:#1565c0;margin-left:4px;">Create your first</a></div>';
        return;
    }
    const dotClass  = { 'LOW RISK': 'low', 'MODERATE RISK': 'moderate', 'HIGH RISK': 'high', 'VERY HIGH RISK': 'veryhigh' };
    const badgeClass = { 'LOW RISK': 'risk-low', 'MODERATE RISK': 'risk-moderate', 'HIGH RISK': 'risk-high', 'VERY HIGH RISK': 'risk-veryhigh' };
    container.innerHTML = predictions.slice(0, 5).map(p => {
        const cfg   = RISK_CONFIG[p.risk_level] || RISK_CONFIG['LOW RISK'];
        const dot   = dotClass[p.risk_level]   || 'low';
        const badge = badgeClass[p.risk_level] || 'risk-low';
        const date = new Date(p.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        const pct = p.probability_percent ? p.probability_percent.toFixed(1) : '0.0';
        return `<div class="pred-item">
            <div class="pred-dot ${dot}"></div>
            <div style="flex:1;">
                <div style="font-weight:600;font-size:.85rem;color:#1a237e;">Diabetes Risk Assessment</div>
                <div style="font-size:.75rem;color:#90a4ae;">${esc(date)} &bull; ${esc(pct)}% probability</div>
            </div>
            <span class="risk-badge ${badge}">${esc(cfg.label)}</span>
        </div>`;
    }).join('');
}

function initCharts(predictions) {
    const recent = predictions.slice(0, 6).reverse();

    const predCtx = document.getElementById('predictionChart');
    if (predCtx) {
        new Chart(predCtx, {
            type: 'line',
            data: {
                labels: recent.length ? recent.map(p => new Date(p.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })) : ['No Data'],
                datasets: [{
                    label: 'Risk Probability %',
                    data: recent.length ? recent.map(p => p.probability_percent || 0) : [0],
                    borderColor: '#2A7BE4',
                    backgroundColor: 'rgba(42,123,228,0.1)',
                    tension: 0.4
                }]
            },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { display: true } } }
        });
    }

    const riskCtx = document.getElementById('riskChart');
    if (riskCtx) {
        const dist = { low: 0, moderate: 0, high: 0, veryHigh: 0 };
        predictions.forEach(p => {
            if (p.risk_level === 'LOW RISK') dist.low++;
            else if (p.risk_level === 'MODERATE RISK') dist.moderate++;
            else if (p.risk_level === 'HIGH RISK') dist.high++;
            else if (p.risk_level === 'VERY HIGH RISK') dist.veryHigh++;
        });
        new Chart(riskCtx, {
            type: 'doughnut',
            data: {
                labels: ['Low', 'Moderate', 'High', 'Very High'],
                datasets: [{ data: [dist.low, dist.moderate, dist.high, dist.veryHigh], backgroundColor: ['#28a745', '#ffc107', '#fd7e14', '#dc3545'] }]
            },
            options: { responsive: true, maintainAspectRatio: true, plugins: { legend: { position: 'bottom' } } }
        });
    }
}

async function initDashboard() {
    const user = checkAuth('patient');
    if (!user) return;

    document.getElementById('navUserName').textContent = user.name || user.username;
    document.getElementById('heroName').textContent    = user.name || user.username;
    const sb = document.getElementById('sidebarName');
    if (sb) sb.textContent = user.name || user.username;
    document.getElementById('currentDate').textContent = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

    const [dashRes, predRes, rxRes, apptRes] = await Promise.all([
        apiFetch('/patient/dashboard'),
        apiFetch('/patient/predictions?limit=50'),
        apiFetch('/patient/prescriptions?limit=50'),
        apiFetch('/patient/appointments?limit=50')
    ]);

    if (!dashRes.success) return;

    const predictions   = predRes.success  ? predRes.predictions   : [];
    const prescriptions = rxRes.success    ? rxRes.prescriptions   : [];
    const appointments  = apptRes.success  ? apptRes.appointments  : [];

    const activeRx = prescriptions.filter(r =>
        ['active','pending','pending_pharmacist','verified','dispensed'].includes(r.status)
    ).length;
    document.getElementById('prescriptionsCount').textContent = activeRx || prescriptions.length;

    renderStats(dashRes.dashboard, predictions, prescriptions, appointments);
    renderRecentPredictions(predictions);
    initCharts(predictions);
}

document.addEventListener('DOMContentLoaded', initDashboard);
