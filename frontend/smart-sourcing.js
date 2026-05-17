// smart-scoring.js — Système de scoring intelligent 5 dimensions

let currentUser = null;
let allCandidates = [];
let currentFilter = 'all';
let currentJobId  = null;

/* ── INIT ─────────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
    await checkAuth();
    await loadMyJobs();
    setupJobSelector();
});

/* ── AUTH ────────────────────────────────────────────────────────────────── */
async function checkAuth() {
    try {
        const res = await fetch(`${api.baseUrl}/auth/me`, {credentials:'include'});
        if (res.status === 401) { window.location.href = 'login.html'; return; }
        const data = await res.json();
        if (!data.authenticated) { window.location.href = 'login.html'; return; }

        currentUser = data.user;
        if (currentUser.role !== 'admin' && currentUser.role !== 'recruiter') {
            window.location.href = 'index.html';
            return;
        }

        const sa = document.getElementById('sidebarAvatar');
        const sn = document.getElementById('sidebarName');
        const sr = document.getElementById('sidebarRole');
        const ui = document.getElementById('userInfo');
        if (sa) sa.textContent = (currentUser.username || 'U').charAt(0).toUpperCase();
        if (sn) sn.textContent = currentUser.username || '—';
        if (sr) sr.textContent = currentUser.role === 'admin' ? 'Administrateur' : 'Recruteur';
        if (ui) ui.textContent = `${currentUser.username} (${currentUser.role})`;

        if (window.applySidebarVisibility) window.applySidebarVisibility(currentUser.role);
    } catch (e) {
        console.error('[SmartScoring] Auth error:', e);
        window.location.href = 'login.html';
    }
}

/* ── LOAD RECRUITER'S OWN JOBS ────────────────────────────────────────────── */
async function loadMyJobs() {
    const sel = document.getElementById('jobSelector');
    try {
        const data = await api.getMyJobs();
        const jobs = data.jobs || [];

        sel.innerHTML = '<option value="">— Sélectionner une offre —</option>';

        if (jobs.length === 0) {
            sel.innerHTML = '<option value="" disabled>Aucune offre disponible</option>';
            return;
        }

        jobs.forEach(job => {
            const opt = document.createElement('option');
            opt.value = job.id;
            const appLabel = job.app_count > 0 ? ` (${job.app_count} candidature${job.app_count > 1 ? 's' : ''})` : ' (0 candidature)';
            opt.text = `${job.title}${job.company ? ' — ' + job.company : ''}${appLabel}`;
            sel.appendChild(opt);
        });
    } catch (e) {
        console.error('[SmartScoring] Load jobs error:', e);
        sel.innerHTML = '<option value="">Erreur de chargement des offres</option>';
    }
}

/* ── JOB SELECTOR ──────────────────────────────────────────────────────────── */
function setupJobSelector() {
    const sel = document.getElementById('jobSelector');
    const btn = document.getElementById('runScoringBtn');
    if (!sel || !btn) return;
    sel.addEventListener('change', () => {
        btn.disabled = !sel.value;
        if (!sel.value) resetPage();
    });
}

/* ── RUN SCORING ──────────────────────────────────────────────────────────── */
async function runScoring() {
    const sel = document.getElementById('jobSelector');
    const jobId = sel?.value;
    if (!jobId) return;
    currentJobId = jobId;

    const loader   = document.getElementById('scoringLoader');
    const results  = document.getElementById('resultsSection');
    const empty    = document.getElementById('emptyState');
    const btn      = document.getElementById('runScoringBtn');

    empty.classList.add('d-none');
    results.classList.add('d-none');
    loader.classList.remove('d-none');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Analyse…';
    loader.scrollIntoView({behavior:'smooth', block:'center'});

    try {
        const data = await api.scoreApplicants(jobId);
        allCandidates = data.candidates || [];
        renderResults(data);
    } catch (err) {
        console.error('[SmartScoring] Score error:', err);
        showToast('error', 'Erreur : ' + (err.message || 'Impossible de scorer les candidats'));
        loader.classList.add('d-none');
        empty.classList.remove('d-none');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-bolt me-2"></i>Analyser';
    }
}

/* ── RENDER RESULTS ──────────────────────────────────────────────────────── */
function renderResults(data) {
    const loader  = document.getElementById('scoringLoader');
    const results = document.getElementById('resultsSection');
    const empty   = document.getElementById('emptyState');

    loader.classList.add('d-none');
    empty.classList.add('d-none');
    results.classList.remove('d-none');

    const job  = data.job || {};
    const cands = data.candidates || [];

    // Job info bar
    document.getElementById('jobInfoTitle').textContent = job.title || '—';
    document.getElementById('jobInfoMeta').innerHTML = [
        job.company ? `<span><i class="fas fa-building me-1"></i>${escHtml(job.company)}</span>` : '',
        job.location ? `<span><i class="fas fa-map-marker-alt me-1"></i>${escHtml(job.location)}</span>` : '',
        `<span><i class="fas fa-users me-1"></i>${cands.length} candidat${cands.length !== 1 ? 's' : ''}</span>`,
        data.scoring_engine ? `<span style="color:#6366f1;font-weight:600;"><i class="fas fa-brain me-1"></i>${escHtml(data.scoring_engine)}</span>` : ''
    ].filter(Boolean).join('');

    // Required skills
    const skillsBar = document.getElementById('requiredSkillsBar');
    const reqSkills = (job.required_skills || []).slice(0, 8);
    skillsBar.innerHTML = reqSkills.map(s => `<span class="required-skill-pill">${escHtml(s)}</span>`).join('');

    // KPIs
    const excellent = cands.filter(c => c.label_color === 'excellent').length;
    const bon       = cands.filter(c => c.label_color === 'good').length;
    const avgScore  = cands.length ? Math.round(cands.reduce((a,c) => a + (c.score_percent||0), 0) / cands.length) : 0;
    document.getElementById('kpiTotal').textContent     = cands.length;
    document.getElementById('kpiExcellent').textContent = excellent;
    document.getElementById('kpiBon').textContent       = bon;
    document.getElementById('kpiAvg').textContent       = avgScore + '%';

    currentFilter = 'all';
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    document.querySelector('.chip[data-filter="all"]')?.classList.add('active');

    renderCards(cands);
    results.scrollIntoView({behavior:'smooth', block:'start'});
}

/* ── RENDER CANDIDATE CARDS ──────────────────────────────────────────────── */
function renderCards(cands) {
    const container = document.getElementById('candidatesList');
    const meta      = document.getElementById('resultsMeta');

    // Apply filter
    let filtered = cands;
    if (currentFilter === 'excellent') filtered = cands.filter(c => c.label_color === 'excellent');
    else if (currentFilter === 'good')     filtered = cands.filter(c => c.label_color === 'good');
    else if (currentFilter === 'possible') filtered = cands.filter(c => c.label_color === 'possible');
    else if (currentFilter === 'pending')  filtered = cands.filter(c => (c.status || 'pending') === 'pending');
    else if (currentFilter === 'selected') filtered = cands.filter(c => c.status === 'selected');
    else if (currentFilter === 'rejected') filtered = cands.filter(c => c.status === 'rejected');

    meta.textContent = `${filtered.length} candidat${filtered.length !== 1 ? 's' : ''} affiché${filtered.length !== 1 ? 's' : ''}`;

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="padding:50px 20px;">
                <div class="icon"><i class="fas fa-filter"></i></div>
                <h5>Aucun candidat pour ce filtre</h5>
            </div>`;
        return;
    }

    container.innerHTML = filtered.map((c, idx) => buildCard(c, idx)).join('');

    // Animate dimension bars after DOM insertion
    setTimeout(() => {
        container.querySelectorAll('.dim-bar-fill').forEach(bar => {
            bar.style.width = (bar.dataset.target || '0') + '%';
        });
    }, 80);
}

/* ── BUILD ONE CARD ──────────────────────────────────────────────────────── */
function buildCard(c, idx) {
    const globalRank = allCandidates.indexOf(c) + 1;
    const rankClass  = globalRank === 1 ? 'rank-1' : globalRank === 2 ? 'rank-2' : globalRank === 3 ? 'rank-3' : '';
    const rankBadge  = globalRank <= 3
        ? `<div class="rank-badge r${globalRank}">${globalRank}</div>`
        : `<div class="rank-badge rn">#${globalRank}</div>`;

    const initials = (c.name || 'C').charAt(0).toUpperCase();
    const colorMap = {excellent:'#059669', good:'#3b82f6', possible:'#f59e0b', weak:'#94a3b8'};
    const avatarBg = colorMap[c.label_color] || '#6366f1';

    const matchedSkills = (c.matched_skills || []).slice(0, 5);
    const otherSkills   = (c.linked_skills  || []).filter(s => !matchedSkills.includes(s)).slice(0, 3);

    const skillsHtml = [
        ...matchedSkills.map(s => `<span class="skill-tag matched" title="Compétence requise détectée">${escHtml(s)}</span>`),
        ...otherSkills.map(s  => `<span class="skill-tag">${escHtml(s)}</span>`)
    ].join('');

    const status     = c.status || 'pending';
    const statusHtml = {
        pending:  '<span class="s-pill pending"><i class="fas fa-clock"></i> En attente</span>',
        selected: '<span class="s-pill selected"><i class="fas fa-check-circle"></i> Sélectionné</span>',
        rejected: '<span class="s-pill rejected"><i class="fas fa-times-circle"></i> Rejeté</span>'
    }[status] || '';

    const actionsHtml = status === 'pending' ? `
        <button class="btn-score-select" onclick="doSelect('${currentJobId}','${c.id}',this)">
            <i class="fas fa-check me-1"></i>Sélectionner
        </button>
        <button class="btn-score-reject" onclick="doReject('${currentJobId}','${c.id}',this)">
            <i class="fas fa-times me-1"></i>Rejeter
        </button>` : statusHtml;

    const bd = c.score_breakdown || {};

    const dims = [
        {key:'skills',    label:'Compétences',  val: bd.skills   || 0, cls:'skills'},
        {key:'semantic',  label:'Sémantique',    val: bd.semantic || 0, cls:'semantic'},
        {key:'seniority', label:'Séniorité',     val: bd.seniority|| 0, cls:'seniority'},
        {key:'location',  label:'Localisation',  val: bd.location || 0, cls:'location'},
        {key:'profile',   label:'Complétude',    val: bd.profile  || 0, cls:'profile'},
    ];

    const dimsHtml = dims.map(d => `
        <div class="dim-row">
            <div class="dim-label">${d.label}</div>
            <div class="dim-bar-wrap">
                <div class="dim-bar-fill ${d.cls}" style="width:0%" data-target="${d.val}"></div>
            </div>
            <div class="dim-score-txt" style="color:${d.val>=70?'#10b981':d.val>=45?'#3b82f6':d.val>=25?'#f59e0b':'#94a3b8'};">${d.val}%</div>
        </div>`).join('');

    const cardId = `card-${c.id || idx}`;
    return `
    <div class="score-card ${rankClass}" id="${cardId}">
        <div class="score-card-body">
            ${rankBadge}
            <div style="display:flex;align-items:flex-start;gap:12px;flex:1;min-width:0;">
                <div class="cand-avatar" style="background:linear-gradient(135deg,${avatarBg},${avatarBg}88);">${initials}</div>
                <div class="cand-info">
                    <div class="cand-name">${escHtml(c.name)}</div>
                    <div class="cand-sub">
                        ${c.current_title ? escHtml(c.current_title) : ''}
                        ${c.location ? `<span class="ms-2"><i class="fas fa-map-marker-alt" style="font-size:.6rem;"></i> ${escHtml(c.location)}</span>` : ''}
                        ${c.email ? `<a href="mailto:${escHtml(c.email)}" class="ms-2" style="color:#6366f1;font-size:.72rem;">${escHtml(c.email)}</a>` : ''}
                    </div>
                    ${skillsHtml ? `<div class="cand-skills-row">${skillsHtml}</div>` : ''}
                </div>
            </div>
            <div class="score-meter">
                <div class="score-circle ${c.label_color}">${c.score_percent}%</div>
                <div class="match-label ${c.label_color}">${escHtml(c.match_label)}</div>
            </div>
            <div class="card-actions">${actionsHtml}</div>
        </div>
        <div class="breakdown-toggle" onclick="toggleBreakdown('${cardId}')">
            <i class="fas fa-chart-bar"></i>
            <span>Détail du score 5 dimensions</span>
            <i class="fas fa-chevron-down ms-auto" style="font-size:.6rem;"></i>
        </div>
        <div class="breakdown-panel" id="bp-${cardId}">
            <div style="font-size:.75rem;font-weight:700;color:#0f172a;margin-bottom:12px;">
                <i class="fas fa-sliders-h me-2" style="color:#6366f1;"></i>Analyse détaillée
            </div>
            ${dimsHtml}
            <div style="margin-top:10px;padding-top:10px;border-top:1px solid #f1f5f9;font-size:.72rem;color:#94a3b8;">
                <i class="fas fa-check-circle me-1" style="color:#10b981;"></i>
                ${matchedSkills.length} compétence${matchedSkills.length !== 1 ? 's' : ''} correspondante${matchedSkills.length !== 1 ? 's' : ''} :
                ${matchedSkills.slice(0,5).map(s => `<strong>${escHtml(s)}</strong>`).join(', ')}
            </div>
        </div>
    </div>`;
}

/* ── TOGGLE BREAKDOWN ────────────────────────────────────────────────────── */
function toggleBreakdown(cardId) {
    const panel = document.getElementById(`bp-${cardId}`);
    if (!panel) return;
    const isOpen = panel.classList.toggle('open');
    if (isOpen) {
        // Trigger bar animations
        panel.querySelectorAll('.dim-bar-fill').forEach(bar => {
            bar.style.width = (bar.dataset.target || '0') + '%';
        });
    }
}

/* ── FILTER ──────────────────────────────────────────────────────────────── */
function applyFilter(filter, el) {
    currentFilter = filter;
    document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    if (el) el.classList.add('active');
    renderCards(allCandidates);
}

/* ── SELECT / REJECT ─────────────────────────────────────────────────────── */
async function doSelect(jobId, candidateId, btn) {
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; }
    try {
        const res = await api.selectCandidate(jobId, candidateId);
        if (res.success) {
            showToast('success', res.message || 'Candidat sélectionné !');
            const cand = allCandidates.find(c => c.id === candidateId);
            if (cand) cand.status = 'selected';
            renderCards(allCandidates);
        }
    } catch (err) {
        showToast('error', 'Erreur : ' + err.message);
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-check me-1"></i>Sélectionner'; }
    }
}

async function doReject(jobId, candidateId, btn) {
    if (!confirm('Rejeter ce candidat ?')) return;
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; }
    try {
        const res = await api.rejectCandidate(jobId, candidateId);
        if (res.success) {
            showToast('info', res.message || 'Candidat rejeté.');
            const cand = allCandidates.find(c => c.id === candidateId);
            if (cand) cand.status = 'rejected';
            renderCards(allCandidates);
        }
    } catch (err) {
        showToast('error', 'Erreur : ' + err.message);
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-times me-1"></i>Rejeter'; }
    }
}

/* ── RESET ───────────────────────────────────────────────────────────────── */
function resetPage() {
    allCandidates = [];
    currentJobId  = null;
    document.getElementById('resultsSection').classList.add('d-none');
    document.getElementById('scoringLoader').classList.add('d-none');
    document.getElementById('emptyState').classList.remove('d-none');
    document.getElementById('jobSelector').value = '';
    document.getElementById('runScoringBtn').disabled = true;
}

/* ── TOAST ───────────────────────────────────────────────────────────────── */
function showToast(type, message) {
    const colors = {success:'linear-gradient(135deg,#10b981,#059669)', error:'linear-gradient(135deg,#ef4444,#dc2626)', info:'linear-gradient(135deg,#6366f1,#4f46e5)'};
    const icons  = {success:'fa-check-circle', error:'fa-exclamation-circle', info:'fa-info-circle'};
    const t = document.createElement('div');
    t.style.cssText = `position:fixed;bottom:28px;right:28px;z-index:9999;background:${colors[type]||colors.info};color:#fff;padding:14px 22px;border-radius:14px;box-shadow:0 8px 30px rgba(0,0,0,.18);font-weight:600;font-size:.88rem;display:flex;align-items:center;gap:10px;animation:slideUp .35s ease;max-width:400px;`;
    t.innerHTML = `<i class="fas ${icons[type]||icons.info}" style="font-size:1.2rem;"></i><span>${message}</span>`;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 4000);
}

/* ── ESCAPE HTML ─────────────────────────────────────────────────────────── */
function escHtml(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
}
