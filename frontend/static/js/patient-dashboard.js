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

        // Urgent pulsing on hero risk box
        const heroRight = document.querySelector('.hero-right');
        if (heroRight) {
            heroRight.classList.remove('risk-urgent', 'risk-urgent-vh');
            if (latest.risk_level === 'VERY HIGH RISK') heroRight.classList.add('risk-urgent-vh');
            else if (latest.risk_level === 'HIGH RISK') heroRight.classList.add('risk-urgent');
        }
        // Urgent pulsing on Book Appointment card
        const bookCard = document.getElementById('bookApptCard');
        if (bookCard) {
            bookCard.classList.remove('urgent-high', 'urgent-vh');
            if (latest.risk_level === 'VERY HIGH RISK') {
                bookCard.classList.add('urgent-vh');
                const sub = bookCard.querySelector('.ac-sub');
                if (sub) sub.textContent = 'See doctor immediately!';
            } else if (latest.risk_level === 'HIGH RISK') {
                bookCard.classList.add('urgent-high');
                const sub = bookCard.querySelector('.ac-sub');
                if (sub) sub.textContent = 'Book now — high risk!';
            }
        }

        // Risk alert banner — only for HIGH RISK and VERY HIGH RISK
        // Hide if patient already has a scheduled appointment (they took action)
        const banner = document.getElementById('riskAlertBanner');
        if (banner && (latest.risk_level === 'HIGH RISK' || latest.risk_level === 'VERY HIGH RISK')) {
            const hasScheduled = appointments.some(a => ['scheduled', 'confirmed', 'completed'].includes(a.status));
            if (hasScheduled) {
                banner.style.display = 'none';
            } else {
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

function renderAppointmentDailyBlock(summary) {
    const block = document.getElementById('appointmentDailyBlock');
    const todayWrap = document.getElementById('todayApptList');
    const yWrap = document.getElementById('yesterdayApptList');
    const todayCount = document.getElementById('todayApptCount');
    const yCount = document.getElementById('yesterdayApptCount');
    if (!block || !todayWrap || !yWrap || !todayCount || !yCount || !summary) return;

    const row = (a, isYesterday) => `
        <div class="appt-mini-row">
            <div class="appt-mini-main">
                <strong>${esc(a.time || 'Time TBD')}</strong> with Dr. ${esc(a.doctor_name || 'Unknown')}
                <span class="appt-mini-status">${esc(a.status || 'scheduled')}</span>
            </div>
            <div class="appt-mini-actions">
                <a href="/templates/patient/appointment.html" class="btn btn-outline btn-sm">${isYesterday ? 'Reschedule' : 'View'}</a>
            </div>
        </div>
    `;

    const todayItems = summary.today || [];
    const yItems = summary.yesterday || [];
    todayCount.textContent = String(todayItems.length);
    yCount.textContent = String(yItems.length);

    todayWrap.innerHTML = todayItems.length
        ? todayItems.map(a => row(a, false)).join('')
        : '<div class="appt-mini-empty">No appointments for today.</div>';

    yWrap.innerHTML = yItems.length
        ? yItems.map(a => row(a, true)).join('')
        : '<div class="appt-mini-empty">No appointments from yesterday.</div>';

    block.style.display = '';
}

function renderPayments(payments) {
    const body = document.getElementById('paymentSummaryBody');
    if (!body) return;
    if (!payments.length) {
        body.innerHTML = '<div style="padding:1.5rem;text-align:center;color:#90a4ae;font-size:.85rem;"><i class="bi bi-credit-card" style="font-size:1.2rem;display:block;margin-bottom:.4rem;"></i> No payments yet. <a href="/templates/payment/payment_page.html" style="color:#1565c0;">Make your first payment →</a></div>';
        return;
    }
    const statusColor = { completed:'#2e7d32', pending:'#d97706', failed:'#c62828', refunded:'#6a1b9a' };
    const statusBg    = { completed:'#e8f5e9', pending:'#fff3e0', failed:'#ffebee', refunded:'#f3e5f5' };
    const statusLabel = { completed:'COMPLETED', pending:'AWAITING CONFIRMATION', failed:'FAILED', refunded:'REFUNDED' };
    const methodIcon  = { cash:'bi-cash-coin', card:'bi-credit-card', chapa:'bi-phone', bank_transfer:'bi-bank', insurance:'bi-shield-check', mobile:'bi-phone' };
    body.innerHTML = payments.slice(0, 5).map(p => {
        const date = p.created_at ? new Date(p.created_at).toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' }) : 'N/A';
        const color = statusColor[p.status] || '#546e7a';
        const bg    = statusBg[p.status]    || '#f5f7fa';
        const icon  = methodIcon[p.payment_method] || 'bi-receipt';
        const label = statusLabel[p.status] || (p.status||'').toUpperCase();
        const isPending = p.status === 'pending';
        const badgeHtml = isPending
            ? `<span class="payment-pending-badge"><i class="bi bi-hourglass-split"></i> ${label}</span>`
            : `<span style="background:${bg};color:${color};border-radius:99px;padding:.15em .65em;font-size:.68rem;font-weight:700;">${label}</span>`;
        return `<div style="display:flex;align-items:center;gap:1rem;padding:.85rem 1.25rem;border-bottom:1px solid #f5f7fa;">
            <div style="width:38px;height:38px;border-radius:12px;background:#fff3e0;color:#e65100;display:flex;align-items:center;justify-content:center;font-size:1.1rem;flex-shrink:0;">
                <i class="bi ${esc(icon)}"></i>
            </div>
            <div style="flex:1;min-width:0;">
                <div style="font-weight:600;font-size:.85rem;color:#1a237e;">${esc(p.payment_type || 'Payment')} &bull; <span style="font-family:monospace;font-size:.78rem;color:#64748b;">${esc(p.payment_id)}</span></div>
                <div style="font-size:.75rem;color:#90a4ae;">${esc(date)} &bull; ${esc((p.payment_method || '').replace('_',' '))}</div>
            </div>
            <div style="text-align:right;flex-shrink:0;">
                <div style="font-weight:800;font-size:.95rem;color:#1a237e;">ETB ${parseFloat(p.total_amount || p.amount || 0).toFixed(2)}</div>
                ${badgeHtml}
            </div>
        </div>`;
    }).join('');
}

async function initDashboard() {
    const user = checkAuth('patient');
    if (!user) return;

    document.getElementById('navUserName').textContent = user.name || user.username;
    document.getElementById('heroName').textContent    = user.name || user.username;
    const sb = document.getElementById('sidebarName');
    if (sb) sb.textContent = user.name || user.username;
    document.getElementById('currentDate').textContent = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

    const [dashRes, predRes, rxRes, apptRes, dailyApptRes, payRes] = await Promise.all([
        apiFetch('/patient/dashboard'),
        apiFetch('/patient/predictions?limit=50'),
        apiFetch('/patient/prescriptions?limit=50'),
        apiFetch('/patient/appointments?limit=50'),
        apiFetch('/patient/appointments/daily-summary'),
        apiFetch('/payments/history?limit=5')
    ]);

    if (!dashRes.success) return;

    const predictions   = predRes.success  ? predRes.predictions   : [];
    const prescriptions = rxRes.success    ? rxRes.prescriptions   : [];
    const appointments  = apptRes.success  ? apptRes.appointments  : [];
    const payments      = payRes.success   ? payRes.payments       : [];

    renderPayments(payments);

    const activeRx = prescriptions.filter(r =>
        ['active','pending','pending_pharmacist','verified','dispensed'].includes(r.status)
    ).length;
    document.getElementById('prescriptionsCount').textContent = activeRx || prescriptions.length;

    renderStats(dashRes.dashboard, predictions, prescriptions, appointments);
    renderRecentPredictions(predictions);
    initCharts(predictions);
    if (dailyApptRes && dailyApptRes.success && dailyApptRes.summary) {
        renderAppointmentDailyBlock(dailyApptRes.summary);
    }
}

document.addEventListener('DOMContentLoaded', initDashboard);
