// ── Applicants Management (Recruiter) ────────────────────────────────────────
let currentUser = null;
let allJobs = [];
let currentJobId = null;
let currentApplicants = [];
let currentFilter = 'all';

const candidateModal = new bootstrap.Modal(document.getElementById('candidateModal'));

document.addEventListener('DOMContentLoaded', async () => {
    try {
        await checkAuth();
        await loadJobsWithApplicants();
        setupFilterTabs();
    } catch (err) {
        console.error('[Applicants] Init error:', err);
    }
});

// ── Auth ──────────────────────────────────────────────────────────────────────
async function checkAuth() {
    try {
        const res = await fetch(`${api.baseUrl}/auth/me`, { credentials: 'include' });
        if (res.status === 401) { window.location.href = 'login.html'; return; }
        const data = await res.json();
        if (!data.authenticated) { window.location.href = 'login.html'; return; }

        currentUser = data.user;

        // Only recruiter and admin can access
        if (currentUser.role !== 'recruiter' && currentUser.role !== 'admin') {
            window.location.href = 'index.html';
            return;
        }

        setupUI();
    } catch (e) {
        console.error('[Applicants] Auth error:', e);
        window.location.href = 'login.html';
    }
}

function setupUI() {
    if (window.applySidebarVisibility && currentUser) {
        window.applySidebarVisibility(currentUser.role);
    }
    const isAdmin = currentUser.role === 'admin';
    const isRecruiter = currentUser.role === 'recruiter';

    const sa = document.getElementById('sidebarAvatar');
    const sn = document.getElementById('sidebarName');
    const sr = document.getElementById('sidebarRole');
    const ui = document.getElementById('userInfo');
    if (sa) sa.textContent = (currentUser.username || 'U').charAt(0).toUpperCase();
    if (sn) sn.textContent = currentUser.username || '—';
    if (sr) sr.textContent = isAdmin ? 'Administrateur' : isRecruiter ? 'Recruteur' : 'Candidat';
    if (ui) ui.textContent = `${currentUser.username} (${currentUser.role})`;
}

// ── Load Jobs with Applicant Counts ──────────────────────────────────────────
async function loadJobsWithApplicants() {
    const container = document.getElementById('jobsList');
    try {
        const data = await api.getJobsWithApplicants();
        allJobs = data.jobs || [];

        // Update KPIs
        const totalJobs = allJobs.length;
        const totalApplicants = allJobs.reduce((s, j) => s + (parseInt(j.total_applicants) || 0), 0);
        const totalSelected = allJobs.reduce((s, j) => s + (parseInt(j.selected_count) || 0), 0);
        const totalPending = allJobs.reduce((s, j) => s + (parseInt(j.pending_count) || 0), 0);

        document.getElementById('kpiTotalJobs').textContent = totalJobs;
        document.getElementById('kpiTotalApplicants').textContent = totalApplicants;
        document.getElementById('kpiSelected').textContent = totalSelected;
        document.getElementById('kpiPending').textContent = totalPending;

        if (allJobs.length === 0) {
            container.innerHTML = `
                <div class="empty-state" style="padding:40px 20px;">
                    <div class="icon"><i class="fas fa-briefcase"></i></div>
                    <h5>Aucune offre publiée</h5>
                    <p>Publiez des offres d'emploi pour recevoir des candidatures.</p>
                </div>`;
            return;
        }

        container.innerHTML = allJobs.map(job => {
            const count = parseInt(job.total_applicants) || 0;
            const pending = parseInt(job.pending_count) || 0;
            const selected = parseInt(job.selected_count) || 0;
            return `
            <div class="job-offer-card" id="job-card-${job.id}" onclick="selectJob('${job.id}')">
                <div class="badge-count ${count === 0 ? 'zero' : ''}">
                    ${count} candidat${count !== 1 ? 's' : ''}
                </div>
                <h6 class="fw-bold mb-1" style="font-size:.9rem;color:#0f172a;padding-right:80px;">${escapeHtml(job.title)}</h6>
                <div class="text-muted" style="font-size:.75rem;">
                    <i class="fas fa-building me-1"></i>${escapeHtml(job.company || '—')}
                    ${job.recruiter_name ? `<span class="ms-2" style="color:#6366f1;font-weight:500;"><i class="fas fa-user-tie me-1"></i>${escapeHtml(job.recruiter_name)}</span>` : ''}
                    ${job.location ? `<span class="ms-2"><i class="fas fa-map-marker-alt me-1"></i>${escapeHtml(job.location)}</span>` : ''}
                </div>
                ${count > 0 ? `
                <div class="mt-2 d-flex gap-2" style="font-size:.68rem;">
                    ${pending > 0 ? `<span class="status-pill pending"><i class="fas fa-clock"></i> ${pending}</span>` : ''}
                    ${selected > 0 ? `<span class="status-pill selected"><i class="fas fa-check"></i> ${selected}</span>` : ''}
                </div>` : ''}
            </div>`;
        }).join('');

    } catch (err) {
        console.error('[Applicants] Load error:', err);
        container.innerHTML = `<div class="alert alert-danger">Erreur: ${err.message}</div>`;
    }
}

// ── Select a Job to View Applicants ──────────────────────────────────────────
async function selectJob(jobId) {
    currentJobId = jobId;
    currentFilter = 'all';

    // Highlight active card
    document.querySelectorAll('.job-offer-card').forEach(c => c.classList.remove('active'));
    const card = document.getElementById(`job-card-${jobId}`);
    if (card) card.classList.add('active');

    // Reset filter tabs
    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    document.querySelector('.filter-tab[data-filter="all"]')?.classList.add('active');

    // Show panel, hide empty state
    document.getElementById('noJobSelected').style.display = 'none';
    document.getElementById('applicantsPanel').style.display = 'block';

    const tbody = document.getElementById('applicantsList');
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4"><i class="fas fa-spinner fa-spin me-2"></i>Chargement...</td></tr>';

    try {
        const data = await api.getJobApplicants(jobId);
        currentApplicants = data.applicants || [];

        // Update panel header
        document.getElementById('panelJobTitle').textContent = data.job_title || 'Offre';
        document.getElementById('panelJobMeta').textContent =
            `${data.job_company || ''} · ${currentApplicants.length} candidature${currentApplicants.length !== 1 ? 's' : ''}`;

        renderApplicants();
    } catch (err) {
        console.error('[Applicants] Load applicants error:', err);
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-danger">${err.message}</td></tr>`;
    }
}

// ── Render Applicants Table ──────────────────────────────────────────────────
function renderApplicants() {
    const tbody = document.getElementById('applicantsList');
    let filtered = currentApplicants;

    if (currentFilter !== 'all') {
        filtered = currentApplicants.filter(a => (a.status || 'pending') === currentFilter);
    }

    if (filtered.length === 0) {
        const msg = currentFilter === 'all'
            ? 'Aucun candidat n\'a postulé à cette offre.'
            : `Aucun candidat avec le statut « ${currentFilter} ».`;
        tbody.innerHTML = `
            <tr><td colspan="6">
                <div class="empty-state" style="padding:40px;">
                    <div class="icon"><i class="fas fa-user-slash"></i></div>
                    <h5>${msg}</h5>
                </div>
            </td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(applicant => {
        const status = applicant.status || 'pending';
        const skills = applicant.skills || [];
        const skillsHtml = skills.slice(0, 4).map(s => `<span class="skill-chip">${escapeHtml(s)}</span>`).join('')
            + (skills.length > 4 ? `<span class="skill-chip" style="background:#f1f5f9;color:#64748b;border-color:#e2e8f0;">+${skills.length - 4}</span>` : '');

        // Format date
        let dateStr = '—';
        if (applicant.applied_at) {
            try {
                const d = new Date(applicant.applied_at);
                if (!isNaN(d.getTime())) {
                    dateStr = d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
                }
            } catch (_) {}
        }

        // Status pill
        const statusHtml = {
            'pending':  '<span class="status-pill pending"><i class="fas fa-clock"></i> En attente</span>',
            'en_attente': '<span class="status-pill pending"><i class="fas fa-clock"></i> En attente</span>',
            'selected': '<span class="status-pill selected"><i class="fas fa-check-circle"></i> Sélectionné</span>',
            'accepte':  '<span class="status-pill selected"><i class="fas fa-check-circle"></i> Sélectionné</span>',
            'rejected': '<span class="status-pill rejected"><i class="fas fa-times-circle"></i> Rejeté</span>',
            'rejete':   '<span class="status-pill rejected"><i class="fas fa-times-circle"></i> Rejeté</span>'
        }[status] || '<span class="status-pill pending"><i class="fas fa-clock"></i> En attente</span>';

        // Action buttons
        let actionsHtml = '';
        if (status === 'pending' || status === 'en_attente') {
            actionsHtml = `
                <button class="btn-select" onclick="event.stopPropagation(); doSelect('${currentJobId}', '${applicant.id}', this)">
                    <i class="fas fa-check me-1"></i>Sélectionner
                </button>
                <button class="btn-reject ms-1" onclick="event.stopPropagation(); doReject('${currentJobId}', '${applicant.id}', this)">
                    <i class="fas fa-times"></i>
                </button>`;
        } else if (status === 'selected' || status === 'accepte') {
            actionsHtml = `<span style="font-size:.78rem;color:#059669;font-weight:600;"><i class="fas fa-check-circle me-1"></i>Confirmé</span>`;
        } else {
            actionsHtml = `<span style="font-size:.78rem;color:#94a3b8;font-weight:600;">Rejeté</span>`;
        }

        return `
        <tr style="cursor:pointer;" onclick="viewApplicantProfile('${applicant.id}', '${currentJobId}')">
            <td style="padding:14px 18px;">
                <div class="d-flex align-items-center">
                    <div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#6366f1,#06b6d4);color:white;font-weight:700;font-size:.8rem;display:flex;align-items:center;justify-content:center;margin-right:12px;flex-shrink:0;">
                        ${(applicant.name || 'U').charAt(0).toUpperCase()}
                    </div>
                    <div>
                        <div class="fw-bold" style="font-size:.88rem;color:#0f172a;">${escapeHtml(applicant.name)}</div>
                        <div style="font-size:.72rem;color:#64748b;">${escapeHtml(applicant.email || '—')}</div>
                    </div>
                </div>
            </td>
            <td>${skillsHtml || '<span class="text-muted" style="font-size:.75rem;">—</span>'}</td>
            <td><span style="font-size:.8rem;color:#475569;">${escapeHtml(applicant.experience_level || applicant.current_title || '—')}</span></td>
            <td><span style="font-size:.78rem;color:#64748b;">${dateStr}</span></td>
            <td>${statusHtml}</td>
            <td class="text-center" onclick="event.stopPropagation();">${actionsHtml}</td>
        </tr>`;
    }).join('');
}

// ── Filter Tabs ──────────────────────────────────────────────────────────────
function setupFilterTabs() {
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentFilter = tab.dataset.filter;
            renderApplicants();
        });
    });
}

// ── Select Candidate ─────────────────────────────────────────────────────────
async function doSelect(jobId, candidateId, btn) {
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; }
    try {
        const res = await api.selectCandidate(jobId, candidateId);
        if (res.success) {
            showToast('success', res.message || 'Candidat sélectionné !');
            // Update local state with French status
            const app = currentApplicants.find(a => a.id === candidateId);
            if (app) app.status = 'accepte';
            renderApplicants();
            refreshJobCard(jobId);
        }
    } catch (err) {
        showToast('error', 'Erreur: ' + err.message);
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-check me-1"></i>Sélectionner'; }
    }
}

// ── Reject Candidate ─────────────────────────────────────────────────────────
async function doReject(jobId, candidateId, btn) {
    if (!confirm('Êtes-vous sûr de vouloir rejeter ce candidat ?')) return;
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; }
    try {
        const res = await api.rejectCandidate(jobId, candidateId);
        if (res.success) {
            showToast('info', res.message || 'Candidat rejeté.');
            // Update local state with French status
            const app = currentApplicants.find(a => a.id === candidateId);
            if (app) app.status = 'rejete';
            renderApplicants();
            refreshJobCard(jobId);
        }
    } catch (err) {
        showToast('error', 'Erreur: ' + err.message);
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fas fa-times"></i>'; }
    }
}

// ── Refresh a single job card count ──────────────────────────────────────────
function refreshJobCard(jobId) {
    const pending = currentApplicants.filter(a => {
        const s = a.status || 'pending';
        return s === 'pending' || s === 'en_attente';
    }).length;
    const selected = currentApplicants.filter(a => {
        const s = a.status || 'pending';
        return s === 'selected' || s === 'accepte';
    }).length;
    const total = currentApplicants.length;

    // Update KPIs globally
    const allPending = allJobs.reduce((s, j) => {
        if (j.id === jobId) return s + pending;
        return s + (parseInt(j.pending_count) || 0);
    }, 0);
    const allSelected = allJobs.reduce((s, j) => {
        if (j.id === jobId) return s + selected;
        return s + (parseInt(j.selected_count) || 0);
    }, 0);
    document.getElementById('kpiSelected').textContent = allSelected;
    document.getElementById('kpiPending').textContent = allPending;

    // Update the job in allJobs array
    const job = allJobs.find(j => j.id === jobId);
    if (job) {
        job.pending_count = pending;
        job.selected_count = selected;
    }

    // Update job card badge
    const card = document.getElementById(`job-card-${jobId}`);
    if (card) {
        const statusDiv = card.querySelector('.mt-2.d-flex');
        if (statusDiv) {
            statusDiv.innerHTML = `
                ${pending > 0 ? `<span class="status-pill pending"><i class="fas fa-clock"></i> ${pending}</span>` : ''}
                ${selected > 0 ? `<span class="status-pill selected"><i class="fas fa-check"></i> ${selected}</span>` : ''}
            `;
        }
    }

    // Update panel meta
    document.getElementById('panelJobMeta').textContent =
        `${currentApplicants[0]?.job_company || ''} · ${total} candidature${total !== 1 ? 's' : ''}`;
}

// ── View Candidate Profile ───────────────────────────────────────────────────
async function viewApplicantProfile(candidateId, jobId) {
    const modalBody = document.getElementById('modalCandidateBody');
    const modalName = document.getElementById('modalCandidateName');
    modalBody.innerHTML = '<div class="text-center py-5"><div class="spinner-border text-primary"></div></div>';
    candidateModal.show();

    try {
        const applicant = currentApplicants.find(a => a.id === candidateId);
        const data = await api.getCandidate(candidateId);
        modalName.textContent = data.name || 'Profil du candidat';

        let skills = data.skills;
        if (!skills || skills.length === 0) {
            skills = applicant ? applicant.skills : [];
        }

        const skillsHtml = (skills && skills.length > 0)
            ? skills.map(s => `<span class="badge bg-light text-dark border me-1 mb-1" style="font-size:.78rem;padding:5px 10px;">${escapeHtml(s)}</span>`).join('')
            : '<span class="text-muted small">Aucune compétence détectée</span>';

        modalBody.innerHTML = `
            <div class="row g-3">
                <div class="col-md-6">
                    <label class="form-label text-muted small fw-bold">Nom complet</label>
                    <div class="fw-bold" style="font-size:1rem;">${escapeHtml(data.name || '—')}</div>
                </div>
                <div class="col-md-6">
                    <label class="form-label text-muted small fw-bold">Email</label>
                    <div>${escapeHtml(data.email || '—')}</div>
                </div>
                <div class="col-md-6">
                    <label class="form-label text-muted small fw-bold">Téléphone</label>
                    <div>${escapeHtml(data.phone || '—')}</div>
                </div>
                <div class="col-md-6">
                    <label class="form-label text-muted small fw-bold">Localisation</label>
                    <div>${escapeHtml(data.location || '—')}</div>
                </div>
                <div class="col-md-6">
                    <label class="form-label text-muted small fw-bold">Poste / Niveau</label>
                    <div>${escapeHtml(data.current_title || data.experience_level || '—')}</div>
                </div>
                <div class="col-12">
                    <label class="form-label text-muted small fw-bold">Compétences</label>
                    <div class="p-3" style="border:1.5px solid #e2e8f0;border-radius:10px;background:#f8fafc;min-height:50px;">
                        ${skillsHtml}
                    </div>
                </div>
                ${data.summary ? `
                <div class="col-12">
                    <label class="form-label text-muted small fw-bold">Résumé</label>
                    <div class="p-3" style="border:1.5px solid #e2e8f0;border-radius:10px;background:#f8fafc;font-size:.85rem;white-space:pre-wrap;">${escapeHtml(data.summary)}</div>
                </div>` : ''}
            </div>
        `;

        // Show action buttons if status is pending
        const selectBtn = document.getElementById('modalSelectBtn');
        const rejectBtn = document.getElementById('modalRejectBtn');

        if (applicant && (['pending', 'en_attente'].includes(applicant.status || 'pending'))) {
            selectBtn.style.display = 'inline-block';
            rejectBtn.style.display = 'inline-block';
            selectBtn.onclick = async () => {
                await doSelect(jobId, candidateId, selectBtn);
                candidateModal.hide();
            };
            rejectBtn.onclick = async () => {
                await doReject(jobId, candidateId, rejectBtn);
                candidateModal.hide();
            };
        } else {
            selectBtn.style.display = 'none';
            rejectBtn.style.display = 'none';
        }

    } catch (err) {
        modalBody.innerHTML = `<div class="alert alert-danger">Erreur: ${err.message}</div>`;
    }
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(type, message) {
    const colors = {
        success: 'linear-gradient(135deg,#10b981,#059669)',
        error: 'linear-gradient(135deg,#ef4444,#dc2626)',
        info: 'linear-gradient(135deg,#6366f1,#4f46e5)'
    };
    const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', info: 'fa-info-circle' };
    const toast = document.createElement('div');
    toast.style.cssText = `position:fixed;bottom:28px;right:28px;z-index:9999;background:${colors[type] || colors.info};color:#fff;padding:16px 24px;border-radius:14px;box-shadow:0 8px 30px rgba(0,0,0,.18);font-weight:600;font-size:.9rem;display:flex;align-items:center;gap:12px;animation:slideUp .35s ease;max-width:420px;`;
    toast.innerHTML = `<i class="fas ${icons[type] || icons.info}" style="font-size:1.3rem;"></i><span>${message}</span>`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// ── Escape HTML ──────────────────────────────────────────────────────────────
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getInitials(name) {
    if (!name) return 'U';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    return name.substring(0, 2).toUpperCase();
}

// ── Job Management in Applicants Page ──────────────────────────────────────────
let jobModalInstance = null;

function resetJobForm() {
    document.getElementById('jobForm').reset();
    document.getElementById('jobId').value = '';
    document.getElementById('jobModalTitle').textContent = 'Nouvelle offre';
}

async function saveJob() {
    const title = document.getElementById('jobTitle').value.trim();
    const company = document.getElementById('jobCompany').value.trim();
    if (!title || !company) {
        alert("Le titre et l'entreprise sont obligatoires.");
        return;
    }

    const jobData = {
        title: title,
        company: company,
        location: document.getElementById('jobLocation').value.trim(),
        salary: document.getElementById('jobSalary').value.trim(),
        type: document.getElementById('jobType').value,
        description: document.getElementById('jobDescription').value.trim()
    };

    const id = document.getElementById('jobId').value;
    const btn = document.getElementById('saveJobBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enregistrement...';

    try {
        if (id) {
            await api.updateJob(id, jobData);
        } else {
            await api.addJob(jobData);
        }
        
        // Hide modal
        if (!jobModalInstance) {
            jobModalInstance = new bootstrap.Modal(document.getElementById('jobModal'));
        }
        const modalEl = document.getElementById('jobModal');
        const modalObj = bootstrap.Modal.getInstance(modalEl) || jobModalInstance;
        modalObj.hide();
        
        // Refresh the list of jobs
        await loadJobsWithApplicants();
        
    } catch (err) {
        console.error('[Applicants] Erreur sauvegarde job:', err);
        alert("Erreur lors de l'enregistrement de l'offre: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save me-1"></i> Enregistrer';
    }
}
