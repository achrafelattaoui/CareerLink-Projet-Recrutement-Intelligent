// analytics.js — Premium Analytics Dashboard v30

const CHART_COLORS = {
    blue:   ['#3b82f6','#60a5fa','#93c5fd','#bfdbfe'],
    purple: ['#8b5cf6','#a78bfa','#c4b5fd','#ddd6fe'],
    green:  ['#10b981','#34d399','#6ee7b7','#a7f3d0'],
    orange: ['#f59e0b','#fbbf24','#fcd34d','#fde68a'],
    multi:  ['#3b82f6','#8b5cf6','#10b981','#f59e0b','#ef4444','#ec4899',
             '#06b6d4','#84cc16','#f97316','#6366f1','#14b8a6','#e11d48']
};

let charts = {};

document.addEventListener('DOMContentLoaded', async () => {
    // ── Auth ────────────────────────────────────────────────
    let user = null;
    try {
        const res = await fetch(`${api.baseUrl}/auth/me`, { credentials: 'include' });
        if (res.status === 401) { window.location.href = 'login.html'; return; }
        const d = await res.json();
        if (!d.authenticated) { window.location.href = 'login.html'; return; }
        user = d.user;
    } catch { window.location.href = 'login.html'; return; }

    if (user.role !== 'admin') {
        alert('Accès refusé. Réservé aux administrateurs.');
        window.location.href = 'index.html';
        return;
    }

    // ── Sidebar ─────────────────────────────────────────────
    if (window.applySidebarVisibility) window.applySidebarVisibility(user.role);
    const sa = document.getElementById('sidebarAvatar');
    const sn = document.getElementById('sidebarName');
    const sr = document.getElementById('sidebarRole');
    const ud = document.getElementById('userDisplay');
    if (sa) sa.textContent = (user.username || 'A').charAt(0).toUpperCase();
    if (sn) sn.textContent = user.username || '—';
    if (sr) sr.textContent = 'Administrateur';
    if (ud) ud.textContent = user.username;

    // ── Logout ──────────────────────────────────────────────
    document.getElementById('logoutBtn').addEventListener('click', async e => {
        e.preventDefault();
        await fetch(`${api.baseUrl}/auth/logout`, { method: 'POST', credentials: 'include' });
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    });

    await loadAll();
});

// Refresh button
window.refreshAll = async function () {
    Object.values(charts).forEach(c => c && c.destroy());
    charts = {};
    await loadAll();
};

async function loadAll() {
    try {
        const data = await api.request(`/analytics/market-trends?t=${Date.now()}`);
        renderKPIs(data);
        renderSkills(data.candidates_by_skill || []);
        renderSectors(data.sector_distribution || []);
        renderRecruiters(data.top_recruiters || []);
        renderGeo(data.geo_distribution || []);
        renderLevels(data);
        renderEvolution(data.job_evolution || []);
    } catch (err) {
        console.error('Analytics error:', err);
    }
}

// ── KPIs ─────────────────────────────────────────────────────
function renderKPIs(data) {
    const c = data.counts || {};
    animateCount('kpiCandidats',    c.cand_count  || 0);
    animateCount('kpiOffres',       c.job_count   || 0);
    animateCount('kpiEntreprises',  c.comp_count  || 0);
}

function animateCount(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    let start = 0;
    const step = Math.max(1, Math.floor(target / 40));
    const timer = setInterval(() => {
        start = Math.min(start + step, target);
        el.textContent = start.toLocaleString('fr-FR');
        if (start >= target) clearInterval(timer);
    }, 30);
}

// ── Chart helpers ─────────────────────────────────────────────
function makeLabelsValues(arr, labelKey, valueKey) {
    return {
        labels: arr.map(d => d[labelKey] || d.label || d.name || d.skill || d.company_name || d.sector || '?'),
        values: arr.map(d => d[valueKey] || d.count || d.value || 0)
    };
}

// ── 1. Top Skills (horizontal bar) ───────────────────────────
function renderSkills(data) {
    const top = data.slice(0, 15);
    const { labels, values } = makeLabelsValues(top, 'label', 'count');
    const ctx = document.getElementById('chartSkills');
    if (!ctx) return;
    charts.skills = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Candidats',
                data: values,
                backgroundColor: labels.map((_, i) => `hsl(${220 + i * 8}, 72%, ${58 + i}%)`),
                borderRadius: 5,
                borderSkipped: false
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { callbacks: {
                label: ctx => ` ${ctx.parsed.x.toLocaleString('fr-FR')} candidats`
            }}},
            scales: {
                x: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { font: { size: 11 } } },
                y: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#475569' } }
            }
        }
    });
}

// ── 2. Sectors (donut) ────────────────────────────────────────
function renderSectors(data) {
    const top = data.slice(0, 8);
    const { labels, values } = makeLabelsValues(top, 'label', 'count');
    const ctx = document.getElementById('chartSectors');
    if (!ctx) return;
    charts.sectors = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: CHART_COLORS.multi,
                borderWidth: 2,
                borderColor: '#fff',
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: { position: 'right', labels: { font: { size: 11 }, padding: 12, usePointStyle: true } }
            }
        }
    });
}

// ── 3. Top Recruiters (horizontal bar) ───────────────────────
function renderRecruiters(data) {
    const top = data.slice(0, 8);
    const { labels, values } = makeLabelsValues(top, 'label', 'count');
    const ctx = document.getElementById('chartRecruiters');
    if (!ctx) return;
    charts.recruiters = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Offres publiées',
                data: values,
                backgroundColor: '#10b981',
                borderRadius: 4,
                borderSkipped: false,
                barPercentage: 0.6
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { font: { size: 10 } } },
                y: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#475569' } }
            }
        }
    });
}

// ── 4. Geographic (pie) ───────────────────────────────────────
function renderGeo(data) {
    const top = data.slice(0, 6);
    const { labels, values } = makeLabelsValues(top, 'label', 'count');
    const ctx = document.getElementById('chartGeo');
    if (!ctx) return;
    charts.geo = new Chart(ctx, {
        type: 'pie',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: CHART_COLORS.blue.concat(CHART_COLORS.orange),
                borderWidth: 2,
                borderColor: '#fff',
                hoverOffset: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { font: { size: 10 }, padding: 8, usePointStyle: true } } }
        }
    });
}

// ── 5. Candidate Levels (polar area) ─────────────────────────
function renderLevels(data) {
    const raw = data.candidate_levels || [];
    if (raw.length === 0) return;
    const { labels, values } = makeLabelsValues(raw, 'label', 'count');
    const ctx = document.getElementById('chartLevels');
    if (!ctx) return;
    charts.levels = new Chart(ctx, {
        type: 'polarArea',
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: ['rgba(59,130,246,.7)','rgba(139,92,246,.7)','rgba(16,185,129,.7)','rgba(245,158,11,.7)','rgba(236,72,153,.7)'],
                borderWidth: 1,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { font: { size: 10 }, padding: 8, usePointStyle: true } } },
            scales: { r: { ticks: { display: false }, grid: { color: '#f1f5f9' } } }
        }
    });
}

// ── 6. Job Evolution (area line) ─────────────────────────────
function renderEvolution(data) {
    const ctx = document.getElementById('chartEvolution');
    if (!ctx) return;
    
    if (!data || data.length === 0) return;

    const { labels, values } = makeLabelsValues(data, 'label', 'count');
    if (!ctx) return;
    const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 200);
    gradient.addColorStop(0, 'rgba(16,185,129,.35)');
    gradient.addColorStop(1, 'rgba(16,185,129,.0)');

    charts.evolution = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Offres publiées',
                data: values,
                borderColor: '#10b981',
                borderWidth: 2.5,
                backgroundColor: gradient,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#10b981',
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: false, grid: { color: '#f1f5f9' }, ticks: { font: { size: 11 } } },
                x: { grid: { display: false }, ticks: { font: { size: 11 }, color: '#64748b' } }
            }
        }
    });
}

// ── FILTERING LOGIC ───────────────────────────────────────
let currentFilter = null;

window.toggleFilter = function(category, cardElement) {
    const allCards = document.querySelectorAll('.kpi-card');
    const allPanels = document.querySelectorAll('.chart-panel');
    
    if (currentFilter === category) {
        // Deselect
        currentFilter = null;
        allCards.forEach(c => c.classList.remove('active'));
        allPanels.forEach(p => p.style.display = 'block');
    } else {
        // Select new
        currentFilter = category;
        allCards.forEach(c => c.classList.remove('active'));
        cardElement.classList.add('active');
        
        allPanels.forEach(p => {
            if (p.getAttribute('data-category') === category) {
                p.style.display = 'block';
            } else {
                p.style.display = 'none';
            }
        });
    }
};
