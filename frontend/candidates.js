let currentUser = null;
let currentCandidateId = null;
const modal = new bootstrap.Modal(document.getElementById('candidateModal'));

document.addEventListener('DOMContentLoaded', async function () {
    await checkAuth();

    // Vérifier si on vient de la recherche avec un candidat spécifique à ouvrir
    const openCandidateId = localStorage.getItem('openCandidate');
    if (openCandidateId) {
        localStorage.removeItem('openCandidate');
        await loadSingleCandidate(openCandidateId);
    } else {
        await loadCandidates();
    }
    
    // Attach filter event listeners
    const searchInput = document.getElementById('searchInput');
    const sortSelect = document.getElementById('sortSelect');
    const jobFilter = document.getElementById('jobFilterSelect');
    
    if (searchInput) searchInput.addEventListener('input', filterAndDisplayCandidates);
    if (sortSelect) sortSelect.addEventListener('change', filterAndDisplayCandidates);
    if (jobFilter) jobFilter.addEventListener('change', filterAndDisplayCandidates);
});

async function loadSingleCandidate(id) {
    try {
        const candidate = await api.getCandidate(id);
        displayCandidates([candidate]);
        showStatus('Candidat sélectionné', 'success');
        setTimeout(() => { viewCandidateDetails(id); }, 300);
    } catch (error) {
        console.error('Erreur:', error);
        showStatus('Erreur lors du chargement du candidat', 'danger');
        await loadCandidates();
    }
}

async function checkAuth() {
    try {
        const response = await fetch(`${api.baseUrl}/auth/me`, { credentials: 'include' });
        if (response.status === 401) {
            window.location.href = 'login.html';
            return;
        }
        const data = await response.json();
        if (!data.authenticated) {
            window.location.href = 'login.html';
            return;
        }

        currentUser = data.user;

        // Seuls admin et recruteur peuvent accéder à cette page
        if (currentUser.role !== 'admin' && currentUser.role !== 'recruiter') {
            window.location.href = 'index.html';
            return;
        }

        setupUI();

        // Si recruteur, charger et afficher la bannière entreprise
        if (currentUser.role === 'recruiter') {
            await loadRecruiterBanner();
        }

    } catch (e) {
        console.error("Auth check failed", e);
    }
}

async function loadRecruiterBanner() {
    try {
        const res = await fetch(`${api.baseUrl}/auth/me/company`, { credentials: 'include' });
        if (!res.ok) return;
        const data = await res.json();
        const banner = document.getElementById('companyBanner');
        const compNameEl = document.getElementById('companyName');
        const emailEl = document.getElementById('companyMeta');
        
        if (!banner) return;

        if (data.company && data.company.company_name) {
            compNameEl.textContent = `🏢 ${data.company.company_name}`;
            emailEl.textContent = `${data.company.recruiter_name || currentUser.username}  ·  ${data.company.recruiter_email || currentUser.email || ''}`;
        } else {
            compNameEl.textContent = '⚠️ Aucune entreprise associée à ce compte';
            emailEl.textContent = currentUser.email || '';
        }

        banner.style.cssText = 'display: flex !important;';
    } catch (e) {
        console.error('Could not load recruiter banner', e);
    }
}

function setupUI() {
    if (window.applySidebarVisibility && currentUser) {
        window.applySidebarVisibility(currentUser.role);
    }
    const isAdmin = currentUser && currentUser.role === 'admin';
    const isRecruiter = currentUser && currentUser.role === 'recruiter';
    const canManage = isAdmin || isRecruiter;

    // Sidebar user info
    const sa = document.getElementById('sidebarAvatar');
    const sn = document.getElementById('sidebarName');
    const sr = document.getElementById('sidebarRole');
    const ui = document.getElementById('userInfo');
    if (sa) sa.textContent = (currentUser.username || 'U').charAt(0).toUpperCase();
    if (sn) sn.textContent = currentUser.username || '—';
    if (sr) sr.textContent = isAdmin ? 'Administrateur' : isRecruiter ? 'Recruteur' : 'Candidat';
    if (ui) ui.textContent = `${currentUser.username} (${currentUser.role})`;

    const addBtn = document.getElementById('addCandidateBtn');
    if (addBtn) addBtn.style.display = canManage ? 'inline-flex' : 'none';

    ['candidateName','candidateEmail','candidatePhone','candidateTitle','candidateLocation'].forEach(id => {
        const f = document.getElementById(id);
        if (f) f.readOnly = !canManage;
    });

    const saveBtn = document.getElementById('saveCandidateBtn');
    if (saveBtn) saveBtn.style.display = canManage ? 'inline-block' : 'none';
}

async function loadCandidates() {
    try {
        const data = await api.getCandidates();
        window.allCandidates = data.candidates || [];
        window.totalCandidateCount = data.count; // Stocker le total réel
        
        populateJobFilter(window.allCandidates);
        filterAndDisplayCandidates();
        
        const candTotal = document.getElementById('companyCandidateCount');
        if (candTotal) candTotal.textContent = `${data.count || window.allCandidates.length} candidats`;
        
        const mainBadge = document.getElementById('candidateCountBadge');
        if (mainBadge) mainBadge.textContent = data.count || window.allCandidates.length;
        
    } catch (error) {
        console.error('Erreur:', error);
        showStatus('Erreur lors du chargement des candidats', 'danger');
    }
}

function populateJobFilter(candidates) {
    const jobFilter = document.getElementById('jobFilterSelect');
    if (!jobFilter) return;
    
    // Extract unique jobs from candidates
    const jobs = new Set();
    candidates.forEach(c => {
        if (c.applied_jobs && Array.isArray(c.applied_jobs)) {
            c.applied_jobs.forEach(j => jobs.add(j));
        }
    });
    
    // If there are specific jobs, populate and show the filter
    if (jobs.size > 0) {
        jobFilter.innerHTML = '<option value="">Toutes les offres</option>';
        Array.from(jobs).sort().forEach(job => {
            const opt = document.createElement('option');
            opt.value = job;
            opt.textContent = job;
            jobFilter.appendChild(opt);
        });
        jobFilter.style.display = 'inline-block';
    } else {
        jobFilter.style.display = 'none';
    }
}

function filterAndDisplayCandidates() {
    if (!window.allCandidates) return;
    
    const searchVal = (document.getElementById('searchInput')?.value || '').toLowerCase();
    const sortVal = document.getElementById('sortSelect')?.value || 'name';
    const jobVal = document.getElementById('jobFilterSelect')?.value || '';
    
    let filtered = window.allCandidates.filter(c => {
        const matchSearch = (c.name || '').toLowerCase().includes(searchVal) ||
                            (c.email || '').toLowerCase().includes(searchVal) ||
                            (c.current_title || '').toLowerCase().includes(searchVal);
        const matchJob = !jobVal || (c.applied_jobs && c.applied_jobs.includes(jobVal));
        return matchSearch && matchJob;
    });
    
    if (sortVal === 'name') {
        filtered.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    } else if (sortVal === 'title') {
        filtered.sort((a, b) => (a.current_title || '').localeCompare(b.current_title || ''));
    }
    
    displayCandidates(filtered);
    
    const countBadge = document.getElementById('candidateCountBadge');
    if (countBadge) {
        if (!searchVal && !jobVal) {
            countBadge.textContent = window.totalCandidateCount || filtered.length;
        } else {
            countBadge.textContent = filtered.length;
        }
    }
}

function displayCandidates(candidates) {
    const tbody = document.getElementById('candidatesList');
    const isAdmin = currentUser && currentUser.role === 'admin';
    const isRecruiter = currentUser && currentUser.role === 'recruiter';

    if (!candidates || candidates.length === 0) {
        const message = isRecruiter
            ? 'Aucun candidat n\'a postulé aux offres de votre entreprise'
            : 'Aucun candidat trouvé';
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">
            <i class="fas fa-user-slash fa-2x mb-2 d-block"></i>${message}</td></tr>`;
        return;
    }

    tbody.innerHTML = candidates.map(candidate => `
        <tr>
            <!-- Candidat (Nom + Avatar) -->
            <td>
                <div class="d-flex align-items-center">
                    <div class="avatar-sm me-3 bg-primary text-white rounded-circle d-flex align-items-center justify-content-center"
                         style="width:32px;height:32px;font-size:12px;flex-shrink:0;font-weight:700;">
                        ${(candidate.name || 'U').charAt(0).toUpperCase()}
                    </div>
                    <div>
                        <div class="fw-bold text-dark">${escapeHtml(candidate.name)}</div>
                    </div>
                </div>
            </td>
            <!-- Poste actuel -->
            <td>
                ${candidate.current_title
                    ? `<span class="badge bg-light text-dark border">${escapeHtml(candidate.current_title)}</span>`
                    : '<span class="text-muted small">—</span>'
                }
            </td>
            <!-- Localisation -->
            <td>
                <small class="text-muted"><i class="fas fa-map-marker-alt me-1"></i>${escapeHtml(candidate.location || '—')}</small>
            </td>
            <!-- Contact -->
            <td>
                <div class="d-flex flex-column" style="font-size: 0.8rem;">
                    ${candidate.email ? `<span><i class="far fa-envelope me-1"></i>${escapeHtml(candidate.email)}</span>` : ''}
                    ${candidate.phone ? `<span class="text-muted"><i class="fas fa-phone-alt me-1"></i>${escapeHtml(candidate.phone)}</span>` : ''}
                </div>
            </td>
            <!-- Actions -->
            <td class="text-center">
                <div class="btn-group">
                    <button class="btn btn-sm btn-outline-primary" onclick="viewCandidateDetails('${candidate.pure_id || candidate.id}')" title="Voir profil">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${isAdmin || isRecruiter ? `
                        <button class="btn btn-sm btn-outline-info ms-1" onclick="editCandidate('${candidate.pure_id || candidate.id}')" title="Modifier">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteCandidate('${candidate.pure_id || candidate.id}')" title="Supprimer">
                            <i class="fas fa-trash"></i>
                        </button>
                    ` : ''}
                </div>
            </td>
        </tr>
    `).join('');
}

function resetForm() {
    currentCandidateId = null;
    const form = document.getElementById('candidateForm');
    if (form) form.reset();
    const title = document.getElementById('modalTitle');
    if (title) title.textContent = 'Ajouter Candidat';
    setupUI();
}

async function editCandidate(id) {
    if (!currentUser || (currentUser.role !== 'admin' && currentUser.role !== 'recruiter')) return;
    try {
        const data = await api.getCandidate(id);
        currentCandidateId = id;
        fillForm(data);
        document.getElementById('modalTitle').textContent = 'Modifier le Profil';
        setupUI(); // Reset readOnly states and buttons based on permissions
        modal.show();

        // Charger l'historique des candidatures
        loadCandidateApplications(id);

    } catch (error) {
        console.error('Erreur:', error);
        showStatus('Erreur lors du chargement du candidat', 'danger');
    }
}

async function viewCandidateDetails(id) {
    try {
        const data = await api.getCandidate(id);
        fillForm(data);
        document.getElementById('modalTitle').textContent = 'Profil du Candidat';

        // Tout en lecture seule pour recruteur
        const fields = ['candidateName', 'candidateEmail', 'candidatePhone', 'candidateTitle', 'candidateLocation'];
        fields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) field.readOnly = true;
        });

        const saveBtn = document.querySelector('#candidateModal .btn-primary[onclick="saveCandidate()"]');
        if (saveBtn) saveBtn.style.display = 'none';

        modal.show();

        // Charger l'historique des candidatures
        loadCandidateApplications(id);

    } catch (error) {
        console.error('Erreur:', error);
        showStatus('Erreur lors du chargement des détails', 'danger');
    }
}

function fillForm(data) {
    const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = val || ''; };
    set('candidateId', data.id);
    set('candidateName', data.name);
    set('candidateEmail', data.email);
    set('candidatePhone', data.phone);
    set('candidateTitle', data.current_title);
    set('candidateLocation', data.location);
    set('candidateSummary', data.summary || "Aucun résumé disponible pour ce candidat.");

    const skillsList = document.getElementById('skillsList');
    if (skillsList) {
        skillsList.innerHTML = '';
        if (data.skills && data.skills.length > 0) {
            data.skills.forEach(skill => {
                const span = document.createElement('span');
                span.className = 'badge bg-light text-dark border';
                span.style.fontSize = '0.8rem';
                span.style.padding = '6px 10px';
                span.textContent = skill;
                skillsList.appendChild(span);
            });
        } else {
            skillsList.innerHTML = '<span class="text-muted small">Aucune compétence détectée</span>';
        }
    }
}

async function saveCandidate() {
    if (!currentUser || (currentUser.role !== 'admin' && currentUser.role !== 'recruiter')) return;

    const nameEl = document.getElementById('candidateName');
    const emailEl = document.getElementById('candidateEmail');
    if (!nameEl || !emailEl) return;

    const payload = {
        name: nameEl.value.trim(),
        email: emailEl.value.trim(),
        phone: (document.getElementById('candidatePhone')?.value || '').trim(),
        current_title: (document.getElementById('candidateTitle')?.value || '').trim(),
        location: (document.getElementById('candidateLocation')?.value || '').trim()
    };

    if (!payload.name || !payload.email) {
        showStatus('Le nom et l\'email sont obligatoires', 'warning');
        return;
    }

    try {
        if (currentCandidateId) {
            await api.updateCandidate(currentCandidateId, payload);
            showStatus('Profil mis à jour avec succès', 'success');
        } else {
            await api.addCandidate(payload);
            showStatus('Candidat ajouté avec succès', 'success');
        }
        modal.hide();
        setTimeout(loadCandidates, 500);
    } catch (error) {
        console.error('Erreur:', error);
        showStatus('Erreur lors de l\'enregistrement', 'danger');
    }
}

async function deleteCandidate(id) {
    if (!currentUser || (currentUser.role !== 'admin' && currentUser.role !== 'recruiter')) return;
    if (confirm('Êtes-vous sûr de vouloir supprimer ce candidat ?')) {
        try {
            await api.deleteCandidate(id);
            showStatus('Candidat supprimé avec succès', 'success');
            loadCandidates();
        } catch (error) {
            console.error('Erreur:', error);
            showStatus('Erreur lors de la suppression', 'danger');
        }
    }
}

function showStatus(message, type = 'info') {
    const alert = document.getElementById('statusAlert');
    const messageEl = document.getElementById('statusMessage');
    if (!alert || !messageEl) return;
    messageEl.textContent = message;
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.style.display = 'block';
    setTimeout(() => { alert.style.display = 'none'; }, 5000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/* ────────────────────────────────────────────────────────
   HISTORIQUE DES CANDIDATURES
─────────────────────────────────────────────────────── */

async function loadCandidateApplications(candidateId) {
    const section  = document.getElementById('appHistorySection');
    const listEl   = document.getElementById('appHistoryList');
    const countEl  = document.getElementById('appHistoryCount');
    const spinner  = document.getElementById('appHistorySpinner');
    if (!section || !listEl) return;

    // Show section + spinner
    section.style.display = 'block';
    if (spinner) spinner.style.display = 'inline-block';
    listEl.innerHTML = '<div class="app-empty"><i class="fas fa-circle-notch fa-spin fa-lg mb-2 d-block"></i>Chargement des candidatures...</div>';

    try {
        const res  = await fetch(`${api.baseUrl}/candidates/${candidateId}/applications`, { credentials: 'include' });
        const data = await res.json();
        const apps = data.applications || [];

        if (countEl) countEl.textContent = apps.length;
        renderApplicationHistory(apps, candidateId);
    } catch (err) {
        console.error('[Applications] Erreur:', err);
        listEl.innerHTML = '<div class="app-empty text-danger"><i class="fas fa-exclamation-circle fa-lg mb-2 d-block"></i>Erreur lors du chargement.</div>';
    } finally {
        if (spinner) spinner.style.display = 'none';
    }
}

function renderApplicationHistory(apps, candidateId) {
    const listEl = document.getElementById('appHistoryList');
    if (!listEl) return;

    const isManager = currentUser && (currentUser.role === 'admin' || currentUser.role === 'recruiter');

    const statusMeta = {
        'en_attente': { label: '⏳ En attente',  cls: 'en_attente' },
        'accepte':    { label: '✅ Accepté',      cls: 'accepte'    },
        'rejete':     { label: '❌ Rejeté',       cls: 'rejete'     },
    };

    if (!apps || apps.length === 0) {
        listEl.innerHTML = `<div class="app-empty">
            <i class="fas fa-inbox fa-lg mb-2 d-block"></i>
            Aucune candidature enregistrée pour ce candidat.
        </div>`;
        return;
    }

    listEl.innerHTML = apps.map((app, idx) => {
        const st = statusMeta[app.status] || statusMeta['en_attente'];
        const date = app.applied_at ? new Date(app.applied_at).toLocaleDateString('fr-FR', {day:'2-digit',month:'short',year:'numeric'}) : '—';
        const company = escapeHtml(app.company || '—');
        const location = app.location ? `<i class="fas fa-map-marker-alt me-1"></i>${escapeHtml(app.location)}` : '';
        const contract = app.contract_type ? `<span class="badge bg-light border text-dark ms-1" style="font-size:.65rem;">${escapeHtml(app.contract_type)}</span>` : '';

        const statusControl = isManager ? `
            <select class="app-status-select" id="sel_app_${idx}"
                onchange="updateApplicationStatus('${candidateId}', '${escapeHtml(app.job_id)}', this.value, ${idx})">
                <option value="en_attente" ${app.status==='en_attente'?'selected':''}>⏳ En attente</option>
                <option value="accepte"    ${app.status==='accepte'   ?'selected':''}>✅ Accepté</option>
                <option value="rejete"     ${app.status==='rejete'    ?'selected':''}>❌ Rejeté</option>
            </select>
        ` : `<span class="app-status-badge ${st.cls}">${st.label}</span>`;

        return `
        <div class="app-card" id="appCard_${idx}">
            <div class="app-card-icon"><i class="fas fa-briefcase"></i></div>
            <div class="app-card-body">
                <div class="app-card-title">${escapeHtml(app.job_title || '—')} ${contract}</div>
                <div class="app-card-meta">
                    <i class="fas fa-building me-1"></i>${company}
                    ${location ? ' &nbsp;·&nbsp; ' + location : ''}
                    &nbsp;&middot;&nbsp; <i class="far fa-calendar me-1"></i>${date}
                </div>
            </div>
            <div class="app-card-actions">
                ${statusControl}
            </div>
        </div>`;
    }).join('');
}

async function updateApplicationStatus(candidateId, jobId, newStatus, cardIdx) {
    try {
        const res = await fetch(
            `${api.baseUrl}/candidates/${candidateId}/applications/${encodeURIComponent(jobId)}/status`,
            {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ status: newStatus })
            }
        );
        const data = await res.json();
        if (!res.ok || !data.success) {
            showStatus(data.error || 'Erreur lors de la mise à jour', 'danger');
            return;
        }

        // Visual feedback: highlight card
        const card = document.getElementById(`appCard_${cardIdx}`);
        if (card) {
            card.style.transition = 'background .3s';
            card.style.background = '#f0fdf4';
            setTimeout(() => { card.style.background = ''; }, 1000);
        }
        showStatus(`Statut mis à jour : ${newStatus.replace('_', ' ')}`, 'success');
    } catch (err) {
        console.error('[Status Update] Erreur:', err);
        showStatus('Erreur réseau lors de la mise à jour', 'danger');
    }
}
