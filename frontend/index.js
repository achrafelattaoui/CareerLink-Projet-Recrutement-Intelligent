// JS pour le Dashboard

// Auth Check
async function checkAuth() {
    try {
        const response = await fetch(`${api.baseUrl}/auth/me`, { credentials: 'include' });
        if (response.status === 401) {
            window.location.href = 'login.html';
            return;
        }
        const data = await response.json();
        if (data.authenticated) {
            setupUI(data.user);
            return data.user;
        }
    } catch (e) {
        console.error("Auth check failed", e);
    }
    return null;
}

function setupUI(user) {
    // ── Sidebar user info ──
    const sidebarAvatar = document.getElementById('sidebarAvatar');
    const sidebarName   = document.getElementById('sidebarName');
    const sidebarRole   = document.getElementById('sidebarRole');
    const userInfo      = document.getElementById('userInfo');

    if (sidebarAvatar) sidebarAvatar.textContent = (user.username || 'U').charAt(0).toUpperCase();
    if (sidebarName)   sidebarName.textContent   = user.username || '—';
    const roleLabel = user.role === 'admin' ? 'Administrateur' : user.role === 'recruiter' ? 'Recruteur' : 'Candidat';
    if (sidebarRole)   sidebarRole.textContent   = roleLabel;
    if (userInfo)      userInfo.textContent       = `${user.username} (${user.role})`;

    // ── Dashboard title (Hero) ──
    const heroTitle    = document.getElementById('heroTitle');
    const currentDate  = document.getElementById('currentDate');
    
    if (heroTitle) {
        heroTitle.textContent = `Bonjour, ${user.username} 👋`;
    }
    
    if (currentDate) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        currentDate.textContent = new Date().toLocaleDateString('fr-FR', options);
    }

    // ── Apply Centralized Sidebar ──
    if (window.applySidebarVisibility) {
        window.applySidebarVisibility(user.role);
    }

    // ── Role-Specific Component Customization ──
    const candWrapper = document.getElementById('candStatWrapper');
    const jobWrapper  = document.getElementById('jobStatWrapper');
    const compWrapper = document.getElementById('compStatWrapper');
    const candTitle   = document.getElementById('recentCandidatesTitle');
    const jobTitle    = document.getElementById('recentJobsTitle');
    const compTitle   = document.getElementById('recentCompaniesTitle');
    const candList    = document.getElementById('recentCandidatesWrapper');
    const jobList     = document.getElementById('recentJobsWrapper');
    const compList    = document.getElementById('recentCompaniesWrapper');

    // Filter Quick Action buttons by role using data-roles attribute
    document.querySelectorAll('.btn-action').forEach(btn => {
        const allowedRoles = (btn.getAttribute('data-roles') || '').split(',').map(r => r.trim());
        const show = allowedRoles.includes(user.role);
        btn.style.setProperty('display', show ? 'flex' : 'none', 'important');
    });

    if (user.role === 'recruiter') {
        // Recruteur: voit Candidats, cache Entreprises, Offres et liste globale des Offres
        if (compWrapper) compWrapper.style.setProperty('display', 'none', 'important');
        if (compList) compList.style.setProperty('display', 'none', 'important');
        if (jobList) jobList.style.setProperty('display', 'none', 'important');
        if (jobWrapper) jobWrapper.style.setProperty('display', 'none', 'important');
        
        // Ensure Candidates are visible
        if (candWrapper) candWrapper.style.display = 'block';
        if (candList) candList.style.display = 'block';
        
        if (candTitle) candTitle.innerHTML = `<i class="fas fa-users me-2" style="color:#6366f1;"></i>Gestion des Candidats`;
    } else if (user.role === 'user') {
        // Candidat: voit Offres et Entreprises, cache Candidats
        if (candWrapper) candWrapper.style.setProperty('display', 'none', 'important');
        if (candList) candList.style.setProperty('display', 'none', 'important');
        
        // Ensure Jobs and Companies are visible
        if (jobWrapper)  jobWrapper.style.display = 'block';
        if (jobList)  jobList.style.display = 'block';
        if (compWrapper) compWrapper.style.display = 'block';
        if (compList) compList.style.display = 'block';
        
        if (jobTitle)  jobTitle.innerHTML  = `<i class="fas fa-briefcase me-2" style="color:#10b981;"></i>Offres recommandées`;
    } else {
        // Admin: Restore/Ensure everything is visible
        [candWrapper, jobWrapper, compWrapper, candList, jobList, compList].forEach(el => {
            if (el) el.style.display = 'block';
        });
        const recStatWrapper = document.getElementById('recStatWrapper');
        if (recStatWrapper) recStatWrapper.classList.remove('d-none');
    }

    // Listen for logout
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.onclick = async () => {
            await fetch(`${api.baseUrl}/auth/logout`, { method: 'POST', credentials: 'include' });
            window.location.href = 'login.html';
        };
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const user = await checkAuth();
    if (user) {
        await loadDashboard(user);
    }
});

async function loadDashboard(user) {
    const isAdmin = user.role === 'admin';

    // ── Stats (KPIs) ──────────────────────────────────────────────────────────
    try {
        const stats = await api.getStats();
        const candEl = document.getElementById('candCount');
        if (candEl) candEl.textContent = stats.candidates || 0;
        const jobsEl = document.getElementById('jobCount');
        if (jobsEl) jobsEl.textContent = stats.jobs || 0;
        const companiesEl = document.getElementById('companyCount');
        if (companiesEl) companiesEl.textContent = stats.companies || 0;
        const recEl = document.getElementById('recruiterCount');
        if (recEl) recEl.textContent = stats.recruiters || 0;
    } catch (err) {
        console.warn('[Dashboard] Stats failed:', err.message);
    }

    // ── Candidates list ───────────────────────────────────────────────────────
    if (user.role === 'admin' || user.role === 'recruiter') {
        try {
            const data = await api.getCandidates();
            await loadRecentCandidates(data.candidates || []);
        } catch (err) {
            console.warn('[Dashboard] Candidates failed:', err.message);
            await loadRecentCandidates([]);
        }
    }

    // ── Jobs list ─────────────────────────────────────────────────────────────
    try {
        const data = await api.getJobs();
        await loadRecentJobs(data.jobs || []);
    } catch (err) {
        console.warn('[Dashboard] Jobs failed:', err.message);
        await loadRecentJobs([]);
    }

    // ── Companies list ────────────────────────────────────────────────────────
    try {
        const data = await api.getCompanies();
        await loadRecentCompanies(data.companies || []);
    } catch (err) {
        console.warn('[Dashboard] Companies failed:', err.message);
        await loadRecentCompanies([]);
    }

    // ── Recent Applications (admin only) ──────────────────────────────────────
    if (isAdmin) {
        try {
            const appsWrapper = document.getElementById('recentApplicationsWrapper');
            if (appsWrapper) appsWrapper.classList.remove('d-none');
            const data = await api.request('/applications/recent');
            await loadRecentApplications(data.applications || []);
        } catch (err) {
            console.warn('[Dashboard] Applications failed:', err.message);
            await loadRecentApplications([]);
        }
    }
}

async function loadRecentCandidates(candidates) {
    const container = document.getElementById('recentCandidates');
    if (!container) return;

    if (!candidates || candidates.length === 0) {
        container.innerHTML = '<p class="text-muted">Aucun candidat</p>';
        return;
    }

    const html = candidates.slice(0, 5).map(candidate => `
        <a href="#" class="list-group-item list-group-item-action" onclick="viewCandidate('${candidate.id}'); return false;">
            <div class="item-icon">
                <i class="fas fa-user"></i>
            </div>
            <div class="flex-grow-1">
                <h6 class="mb-0 text-dark" style="font-weight:600;">${escapeHtml(candidate.name)}</h6>
                <div class="d-flex align-items-center mt-1">
                    <small class="text-muted"><i class="fas fa-envelope me-1"></i>${escapeHtml(candidate.email || '-')}</small>
                </div>
            </div>
            <i class="fas fa-chevron-right text-muted" style="font-size: 0.75rem;"></i>
        </a>
    `).join('');

    container.innerHTML = html;
}

async function loadRecentJobs(jobs) {
    const container = document.getElementById('recentJobs');
    if (!container) return;

    if (!jobs || jobs.length === 0) {
        container.innerHTML = '<p class="text-muted">Aucune offre</p>';
        return;
    }

    const html = jobs.slice(0, 5).map(job => `
        <a href="#" class="list-group-item list-group-item-action" onclick="viewJob('${job.id}'); return false;">
            <div class="item-icon">
                <i class="fas fa-briefcase"></i>
            </div>
            <div class="flex-grow-1">
                <h6 class="mb-0 text-dark" style="font-weight:600;">${escapeHtml(job.title)}</h6>
                <div class="d-flex align-items-center mt-1">
                    <small class="text-muted"><i class="fas fa-building me-1"></i>${escapeHtml(job.company || '-')}</small>
                </div>
            </div>
            <i class="fas fa-chevron-right text-muted" style="font-size: 0.75rem;"></i>
        </a>
    `).join('');

    container.innerHTML = html;
}

function viewCandidate(id) {
    window.location.href = `candidates.html?id=${id}`;
}

function viewJob(id) {
    window.location.href = `jobs.html?id=${id}`;
}

async function loadRecentCompanies(companies) {
    const container = document.getElementById('recentCompanies');
    if (!container) return;

    if (!companies || companies.length === 0) {
        container.innerHTML = '<p class="text-muted">Aucune entreprise</p>';
        return;
    }

    const html = companies.slice(0, 5).map(company => `
        <a href="#" class="list-group-item list-group-item-action" onclick="viewCompany('${company.id}'); return false;">
            <div class="item-icon">
                <i class="fas fa-building"></i>
            </div>
            <div class="flex-grow-1">
                <h6 class="mb-0 text-dark" style="font-weight:600;">${escapeHtml(company.name)}</h6>
                <div class="d-flex align-items-center mt-1">
                    <small class="text-muted"><i class="fas fa-map-marker-alt me-1"></i>${escapeHtml(company.location || '-')}</small>
                </div>
            </div>
            <i class="fas fa-chevron-right text-muted" style="font-size: 0.75rem;"></i>
        </a>
    `).join('');

    container.innerHTML = html;
}

async function loadRecentApplications(apps) {
    const container = document.getElementById('recentApplications');
    if (!container) return;

    if (!apps || apps.length === 0) {
        container.innerHTML = '<p class="text-muted p-3">Aucune candidature récente</p>';
        return;
    }

    const html = apps.map(app => `
        <div class="list-group-item" style="border:none; padding: 12px 0;">
            <div class="d-flex w-100 justify-content-between align-items-center">
                <div class="flex-grow-1">
                    <div class="fw-bold text-dark" style="font-size:.88rem;">${escapeHtml(app.candidate_name)}</div>
                    <div class="text-muted" style="font-size:.78rem;">
                        <i class="fas fa-briefcase me-1"></i>${escapeHtml(app.job_title)}
                    </div>
                </div>
                <div class="text-end">
                    <div style="font-size:.72rem;color:#94a3b8;">${app.applied_at ? new Date(app.applied_at).toLocaleDateString() : '-'}</div>
                    <span class="badge" style="background:#fef2f2;color:#ef4444;font-size:.65rem;border-radius:6px;padding:4px 8px;">Postulé</span>
                </div>
            </div>
        </div>
    `).join('');

    container.innerHTML = html;
}

function renderHubTable(hubData) {
    const tbody = document.getElementById('hubTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!hubData || hubData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="2" class="text-center p-4">Aucune donnée trouvée</td></tr>';
        return;
    }

    hubData.forEach((item, index) => {
        const tr = document.createElement('tr');

        let rankClass = 'normal';
        let rankIcon = '';

        if (index === 0) { rankClass = 'rank-1'; rankIcon = '👑 '; }
        else if (index === 1) { rankClass = 'rank-2'; rankIcon = '🥈 '; }
        else if (index === 2) { rankClass = 'rank-3'; rankIcon = '🥉 '; }

        const label = item.label || item.skill || item.title || item.name || 'Inconnu';

        tr.innerHTML = `
            <td>
                <span class="skill-badge ${rankClass}">
                    ${rankIcon}${escapeHtml(label)}
                </span>
            </td>
            <td class="text-end font-monospace text-primary" style="font-size: 1.1em;">
                ${item.count}
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function viewCompany(id) {
    window.location.href = `companies.html?id=${id}`;
}

function showStatus(message, type = 'info') {
    const alert = document.getElementById('statusAlert');
    const messageEl = document.getElementById('statusMessage');
    if (!alert || !messageEl) return;

    messageEl.textContent = message;
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.style.display = 'block';

    setTimeout(() => {
        alert.style.display = 'none';
    }, 5000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
