// search.js
let currentUser = null;

async function checkAuth() {
    try {
        const response = await fetch(`${api.baseUrl}/auth/me`, { credentials: 'include' });
        if (response.status === 401) {
            window.location.href = 'login.html';
            return;
        }
        const data = await response.json();
        if (data.authenticated) {
            currentUser = data.user;
            setupUI();
        } else {
            window.location.href = 'login.html';
        }
    } catch (e) {
        console.error("Auth check failed", e);
        showStatus('Erreur de connexion au serveur', 'danger');
    }
}

document.addEventListener('DOMContentLoaded', () => { checkAuth(); });

function setupUI() {
    if (window.applySidebarVisibility && currentUser) {
        window.applySidebarVisibility(currentUser.role);
    }
    const isAdmin = currentUser && currentUser.role === 'admin';
    const isRecruiter = currentUser && currentUser.role === 'recruiter';
    const isCandidate = currentUser && currentUser.role === 'user';

    // Sidebar user info
    const sa = document.getElementById('sidebarAvatar');
    const sn = document.getElementById('sidebarName');
    const sr = document.getElementById('sidebarRole');
    const ui = document.getElementById('userInfo');
    if (sa) sa.textContent = (currentUser.username || 'U').charAt(0).toUpperCase();
    if (sn) sn.textContent = currentUser.username || '—';
    if (sr) sr.textContent = isAdmin ? 'Administrateur' : isRecruiter ? 'Recruteur' : 'Candidat';
    if (ui) ui.textContent = `${currentUser.username} (${currentUser.role})`;

    const sel = document.getElementById('searchType');
    if (sel) {
        if (isRecruiter) {
            // Recruiter: only candidate search
            for (let i = sel.options.length - 1; i >= 0; i--) {
                if (sel.options[i].value !== 'candidates') sel.remove(i);
            }
            sel.value = 'candidates';
        } else if (isCandidate) {
            // Candidate: jobs and companies
            for (let i = sel.options.length - 1; i >= 0; i--) {
                if (sel.options[i].value === 'candidates') sel.remove(i);
            }
            sel.value = 'jobs';
        }
    }
}


function showSkeleton() {
    const skeletonHtml = `<div class="loading-pulse">${'<div class="pulse-row"></div>'.repeat(4)}</div>`;
    ['candidatesResults','jobsResults','companiesResults'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = skeletonHtml;
    });
}

async function performSearch() {
    if (!currentUser) {
        showStatus('Vous devez être connecté pour rechercher', 'warning');
        return;
    }
    const query = document.getElementById('searchInput').value.trim();
    const type = document.getElementById('searchType').value;
    const limit = 20;
    const offset = 0;

    if (!query) {
        showStatus('Veuillez entrer un terme de recherche', 'warning');
        return;
    }

    // Hide placeholder, show skeleton
    const placeholder = document.getElementById('searchPlaceholder');
    const container = document.getElementById('resultsContainer');
    const statsBar = document.getElementById('statsBar');
    if (placeholder) placeholder.style.display = 'none';
    if (container) container.style.display = (type === 'all') ? 'grid' : 'flex';
    if (statsBar) statsBar.style.display = 'none';
    showSkeleton();

    try {
        const data = await api.search(query, type, limit, offset);
        displayResults(data, query);
    } catch (error) {
        console.error('Search error:', error);
        showStatus(`Erreur lors de la recherche: ${error.message || ''}`, 'danger');
        if (container) container.style.display = 'none';
        if (placeholder) placeholder.style.display = 'block';
    }
}

// Palette d'avatars pour donner de la couleur aux initiales
const AVATAR_COLORS = [
    ['#6366f1','#eef2ff'], ['#10b981','#ecfdf5'], ['#f59e0b','#fffbeb'],
    ['#ef4444','#fef2f2'], ['#8b5cf6','#f5f3ff'], ['#06b6d4','#ecfeff']
];
function avatarColor(str) {
    let h = 0;
    for (let i = 0; i < (str||'').length; i++) h = str.charCodeAt(i) + ((h << 5) - h);
    return AVATAR_COLORS[Math.abs(h) % AVATAR_COLORS.length];
}
function initials(str) {
    return (str||'?').split(' ').slice(0,2).map(w=>w[0]).join('').toUpperCase();
}

function updateSectionCount(colEl, n) {
    const span = colEl ? colEl.querySelector('.section-count') : null;
    if (span) span.textContent = n;
}

function displayResults(data, searchQuery) {
    const results = data.results;
    const placeholder = document.getElementById('searchPlaceholder');
    const container = document.getElementById('resultsContainer');
    const statsBar = document.getElementById('statsBar');

    if (placeholder) placeholder.style.display = 'none';
    if (container) container.style.display = 'flex';

    const candCol = document.getElementById('candidatesResultsCol');
    const jobCol = document.getElementById('jobsResultsCol');
    const compCol = document.getElementById('companiesResultsCol');

    const isAdmin = currentUser && currentUser.role === 'admin';
    const isRecruiter = currentUser && currentUser.role === 'recruiter';
    const isCandidate = currentUser && currentUser.role === 'user';

    const respType = data.type || document.getElementById('searchType').value;
    
    // Toggle side-by-side (grid) layout for 'all' view
    if (container) {
        if (respType === 'all') {
            container.style.display = 'grid';
            container.classList.add('grid-layout');
        } else {
            container.style.display = 'flex';
            container.classList.remove('grid-layout');
        }
    }

    // Visibility
    const showCand = (isAdmin || isRecruiter) && (respType === 'all' || respType === 'candidates');
    const showJob  = (isAdmin || isCandidate) && (respType === 'all' || respType === 'jobs');
    const showComp = (isAdmin || isCandidate) && (respType === 'all' || respType === 'companies');

    if (candCol) candCol.style.display = showCand ? 'block' : 'none';
    if (jobCol)  jobCol.style.display  = showJob  ? 'block' : 'none';
    if (compCol) compCol.style.display = showComp ? 'block' : 'none';

    // ── Render Candidates ──
    const candItems = results.candidates || [];
    const srCandCount = document.getElementById('srCandCount');
    if (srCandCount) srCandCount.textContent = candItems.length;
    updateSectionCount(candCol, candItems.length);
    if (showCand) {
        const list = document.getElementById('candidatesResults');
        if (list) {
            list.innerHTML = candItems.length === 0
                ? `<div class="empty-state"><i class="fas fa-user-slash"></i><p>Aucun candidat trouvé</p></div>`
                : candItems.map(c => {
                    const [fg, bg] = avatarColor(c.name);
                    return `<div class="result-card" style="--card-accent:${fg}" onclick="localStorage.setItem('openCandidate','${c.id}');window.location.href='candidates.html'">
                        <div class="card-avatar" style="background:${fg};">${initials(c.name)}</div>
                        <div class="card-body">
                            <div class="card-title">${escapeHtml(c.name)}</div>
                            <div class="card-subtitle">
                                <i class="fas fa-briefcase"></i>${escapeHtml(c.current_title || 'Candidat')}
                                ${c.location ? `<span>·</span><i class="fas fa-map-marker-alt"></i>${escapeHtml(c.location)}` : ''}
                            </div>
                        </div>
                        <span class="card-badge" style="background:${bg};color:${fg};"><i class="fas fa-user"></i> Candidat</span>
                        <i class="fas fa-chevron-right card-arrow"></i>
                    </div>`;
                }).join('');
        }
    }

    // ── Render Jobs ──
    const jobItems = results.jobs || [];
    const srJobCount = document.getElementById('srJobCount');
    if (srJobCount) srJobCount.textContent = jobItems.length;
    updateSectionCount(jobCol, jobItems.length);
    if (showJob) {
        const list = document.getElementById('jobsResults');
        if (list) {
            list.innerHTML = jobItems.length === 0
                ? `<div class="empty-state"><i class="fas fa-folder-open"></i><p>Aucune offre trouvée</p></div>`
                : jobItems.map(j => {
                    const [fg, bg] = ['#10b981','#ecfdf5'];
                    return `<div class="result-card" style="--card-accent:${fg}" onclick="localStorage.setItem('openJob','${j.id}');window.location.href='jobs.html'">
                        <div class="card-avatar" style="background:${fg};">${initials(j.title)}</div>
                        <div class="card-body">
                            <div class="card-title">${escapeHtml(j.title)}</div>
                            <div class="card-subtitle">
                                <i class="fas fa-building"></i>${escapeHtml(j.company || 'Entreprise')}
                                <span>·</span><i class="fas fa-map-marker-alt"></i>${escapeHtml(j.location || 'Maroc')}
                            </div>
                        </div>
                        <span class="card-badge" style="background:${bg};color:${fg};"><i class="fas fa-briefcase"></i> Offre</span>
                        <i class="fas fa-chevron-right card-arrow"></i>
                    </div>`;
                }).join('');
        }
    }

    // ── Render Companies ──
    const compItems = results.companies || [];
    const srCompCount = document.getElementById('srCompCount');
    if (srCompCount) srCompCount.textContent = compItems.length;
    updateSectionCount(compCol, compItems.length);
    if (showComp) {
        const list = document.getElementById('companiesResults');
        if (list) {
            list.innerHTML = compItems.length === 0
                ? `<div class="empty-state"><i class="fas fa-building"></i><p>Aucune entreprise trouvée</p></div>`
                : compItems.map(c => {
                    const [fg, bg] = avatarColor(c.name);
                    return `<div class="result-card" style="--card-accent:${fg}" onclick="localStorage.setItem('openCompany','${c.id}');window.location.href='companies.html'">
                        <div class="card-avatar" style="background:${fg};">${initials(c.name)}</div>
                        <div class="card-body">
                            <div class="card-title">${escapeHtml(c.name)}</div>
                            <div class="card-subtitle">
                                <i class="fas fa-tag"></i>${escapeHtml(c.sector || 'Secteur non précisé')}
                                ${c.location ? `<span>·</span><i class="fas fa-map-marker-alt"></i>${escapeHtml(c.location)}` : ''}
                            </div>
                        </div>
                        <span class="card-badge" style="background:${bg};color:${fg};"><i class="fas fa-building"></i> Entreprise</span>
                        <i class="fas fa-chevron-right card-arrow"></i>
                    </div>`;
                }).join('');
        }
    }

    // ── Stats bar ──
    if (statsBar) {
        statsBar.style.display = 'flex';
        const sq = document.getElementById('statsQuery');
        if (sq) sq.textContent = `"${searchQuery || ''}"`;
        const sc = document.getElementById('statsCand');
        const sj = document.getElementById('statsJobs');
        const sco = document.getElementById('statsComp');
        if (sc)  sc.style.display  = showCand ? 'inline-flex' : 'none';
        if (sj)  sj.style.display  = showJob  ? 'inline-flex' : 'none';
        if (sco) sco.style.display = showComp ? 'inline-flex' : 'none';
    }
}

function showStatus(message, type = 'info') {
    const alert = document.getElementById('statusAlert');
    document.getElementById('statusMessage').textContent = message;
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.style.display = 'block';
    setTimeout(() => alert.style.display = 'none', 4000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
