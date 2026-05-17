let currentUser = null;
let currentJobId = null;
const modal = new bootstrap.Modal(document.getElementById('jobModal'));
const applyModal = new bootstrap.Modal(document.getElementById('applyModal'));

// ── File picker interaction ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('applyCvFile');
    const dropZone  = document.getElementById('cvDropZone');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const f = e.target.files[0];
            if (!f) return;
            document.getElementById('cvFileName').textContent = f.name;
            document.getElementById('cvFileSize').textContent = (f.size / 1024).toFixed(0) + ' Ko';
            const preview = document.getElementById('cvFilePreview');
            preview.style.display = 'flex';
            if (dropZone) { dropZone.style.border = '2px dashed #86efac'; dropZone.style.background = '#f0fdf4'; }
        });
    }
    if (dropZone) {
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.style.borderColor = '#6366f1'; });
        dropZone.addEventListener('dragleave', () => { dropZone.style.borderColor = '#c7d2fe'; });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = '#c7d2fe';
            const f = e.dataTransfer.files[0];
            if (!f) return;
            const input = document.getElementById('applyCvFile');
            const dt = new DataTransfer(); dt.items.add(f); input.files = dt.files;
            input.dispatchEvent(new Event('change'));
        });
    }
});

document.addEventListener('DOMContentLoaded', async function () {
    await checkAuth();
    await loadCompanySuggestions();

    // Search logic
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', filterAndDisplayJobs);
    }

    // Vérifier si on vient de la recherche avec un job spécifique à ouvrir
    const urlParams = new URLSearchParams(window.location.search);
    const directJobId = urlParams.get('id');

    const openJobId = localStorage.getItem('openJob');

    const isNew = urlParams.get('new');

    if (directJobId) {
        // Deep link priority
        await loadSingleJob(directJobId);
    } else if (openJobId) {
        localStorage.removeItem('openJob');
        await loadSingleJob(openJobId);
    } else {
        await loadJobs();
        if (isNew === '1' && currentUser && (currentUser.role === 'admin' || currentUser.role === 'recruiter')) {
            resetForm();
            modal.show();
        }
    }
});

async function loadSingleJob(id) {
    try {
        const job = await api.getJob(id);
        displayJobs([job]);
        showStatus('Offre sélectionnée', 'success');

        // Force modal open slightly delayed to ensure DOM is ready
        setTimeout(() => {
            console.log("Opening details for job:", id);
            viewJobDetail(id);
        }, 500);
    } catch (error) {
        console.error('Erreur:', error);
        showStatus('Erreur lors du chargement de l\'offre: ' + error.message, 'danger');
        alert("Impossible de charger l'offre spécifique (" + id + ") : " + error.message);
        // Do NOT load all jobs as fallback, it confuses the user.
        // await loadJobs(); 
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
        if (data.authenticated) {
            currentUser = data.user;
            setupUI();
        }
    } catch (e) {
        console.error("Auth check failed", e);
    }
}

function setupUI() {
    if (window.applySidebarVisibility && currentUser) {
        window.applySidebarVisibility(currentUser.role);
    }
    const isAdmin = currentUser && currentUser.role === 'admin';
    const isRecruiter = currentUser && currentUser.role === 'recruiter';
    const isJobManager = isAdmin || isRecruiter;

    // Sidebar user info
    const sa = document.getElementById('sidebarAvatar');
    const sn = document.getElementById('sidebarName');
    const sr = document.getElementById('sidebarRole');
    const ui = document.getElementById('userInfo');
    if (sa) sa.textContent = (currentUser.username || 'U').charAt(0).toUpperCase();
    if (sn) sn.textContent = currentUser.username || '—';
    if (sr) sr.textContent = isAdmin ? 'Administrateur' : isRecruiter ? 'Recruteur' : 'Candidat';
    if (ui) ui.textContent = `${currentUser.username} (${currentUser.role})`;

    const addBtn = document.querySelector('button[data-bs-target="#jobModal"]');
    if (addBtn) addBtn.style.display = isJobManager ? 'inline-block' : 'none';

    // Auto-detect company for recruiters
    const companyInput = document.getElementById('company');
    if (companyInput) {
        if (isRecruiter) {
            companyInput.value = 'Auto-détectée';
            companyInput.disabled = true;
            companyInput.removeAttribute('required');
        } else {
            companyInput.disabled = false;
            companyInput.setAttribute('required', 'true');
        }
    }

    const fields = ['title', 'company', 'description', 'salary', 'location', 'type'];
    fields.forEach(id => {
        const f = document.getElementById(id);
        if (f) f.readOnly = !isJobManager;
    });



    const saveBtn = document.querySelector('#jobModal .btn-primary[onclick="saveJob()"]');
    if (saveBtn) saveBtn.style.display = isJobManager ? 'inline-block' : 'none';
}


async function loadJobs() {
    try {
        const data = await api.getJobs();
        window.allJobs = data.jobs || [];
        window.totalJobCount = data.count; // Stocker le total réel
        filterAndDisplayJobs();
        const badge = document.getElementById('jobCountBadge');
        if (badge) badge.textContent = data.count || window.allJobs.length;
        showStatus(`${data.count || window.allJobs.length} offre(s) au total`, 'success');
    } catch (error) {
        console.error('Erreur:', error);
        showStatus('Erreur lors du chargement des offres', 'danger');
    }
}

async function loadCompanySuggestions() {
    try {
        const data = await api.getCompanies();
        const datalist = document.getElementById('companyListSuggestions');
        if (datalist && data.companies) {
            datalist.innerHTML = data.companies.map(c => `<option value="${escapeHtml(c.name)}">`).join('');
        }
    } catch (e) {
        console.error("Failed to load company suggestions", e);
    }
}

function filterAndDisplayJobs() {
    if (!window.allJobs) return;
    
    const searchVal = (document.getElementById('searchInput')?.value || '').toLowerCase();
    
    const filtered = window.allJobs.filter(job => {
        return (job.title || '').toLowerCase().includes(searchVal) ||
               (job.company || '').toLowerCase().includes(searchVal) ||
               (job.location || '').toLowerCase().includes(searchVal) ||
               (job.type || '').toLowerCase().includes(searchVal);
    });
    
    displayJobs(filtered, searchVal);
}

function displayJobs(jobs, searchVal = '') {
    const tbody = document.getElementById('jobsList');
    const badge = document.getElementById('jobCountBadge');
    if (badge) {
        if (!searchVal) {
            badge.textContent = window.totalJobCount || jobs.length;
        } else {
            badge.textContent = jobs.length;
        }
    }

    if (!jobs || jobs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-5">Aucune offre trouvée</td></tr>';
        return;
    }

    tbody.innerHTML = jobs.map(job => `
        <tr>
            <td class="px-4 py-3">
                <div class="fw-bold text-dark" style="font-size: 1rem;">${escapeHtml(job.title)}</div>
            </td>
            <td>
                <span class="badge bg-light text-primary border px-2 py-1">
                    <i class="fas fa-building me-1"></i>${escapeHtml(job.company || '—')}
                </span>
            </td>
            <td>
                <small class="text-muted"><i class="fas fa-map-marker-alt me-1"></i>${escapeHtml(job.location || '—')}</small>
            </td>
            <td>
                <span class="badge" style="background:#e0e7ff; color:#4338ca;">
                    ${escapeHtml(job.type || 'Non spécifié')}
                </span>
            </td>
            <td>
                <div class="fw-bold text-success">
                    ${job.salary ? escapeHtml(job.salary) + ' DH' : 'À discuter'}
                </div>
            </td>
            <td class="text-center px-4">
                <div class="btn-group">
                    <button class="btn btn-sm btn-outline-primary" onclick="viewJobDetail('${job.id}')" title="Voir détails">
                        <i class="fas fa-eye"></i>
                    </button>
                    ${currentUser && currentUser.role === 'user' ? `
                        <button class="btn btn-sm ms-1" onclick="openApplyModal('${job.id}', '${escapeHtml(job.title)} — ${escapeHtml(job.company || '')}')" title="Postuler"
                            style="background:linear-gradient(135deg,#6366f1,#06b6d4);color:white;border:none;">
                            <i class="fas fa-paper-plane"></i>
                        </button>
                    ` : ''}
                    ${currentUser && (currentUser.role === 'admin' || currentUser.role === 'recruiter') ? `
                        <button class="btn btn-sm btn-outline-info ms-1" onclick="editJob('${job.id}')" title="Modifier">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteJob('${job.id}')" title="Supprimer">
                            <i class="fas fa-trash"></i>
                        </button>
                    ` : ''}
                </div>
            </td>
        </tr>
    `).join('');
}

function resetForm() {
    currentJobId = null;
    const form = document.getElementById('jobForm');
    if (form) form.reset();
    document.getElementById('modalTitle').textContent = 'Ajouter Offre';
    setupUI();
}

async function editJob(id) {
    if (!currentUser || (currentUser.role !== 'admin' && currentUser.role !== 'recruiter')) return;
    try {
        const data = await api.getJob(id);
        currentJobId = id;
        fillForm(data);
        document.getElementById('modalTitle').textContent = 'Modifier l\'offre';

        const saveBtn = document.querySelector('#jobModal .btn-primary[onclick="saveJob()"]');
        if (saveBtn) saveBtn.style.display = 'inline-block';

        modal.show();
    } catch (error) {
        console.error('Erreur:', error);
        showStatus('Erreur lors du chargement de l\'offre', 'danger');
    }
}

async function viewJobDetail(id) {
    try {
        const data = await api.getJob(id);
        fillForm(data);
        document.getElementById('modalTitle').textContent = 'Détails de l\'offre';

        const fields = ['title', 'company', 'description', 'salary', 'location', 'type'];
        fields.forEach(fieldId => {
            const f = document.getElementById(fieldId);
            if (f) f.readOnly = true;
        });

        const saveBtn = document.getElementById('saveJobBtn');
        if (saveBtn) saveBtn.style.display = 'none';

        modal.show();

        // For candidates: show a Postuler button inside the modal footer
        if (currentUser && currentUser.role === 'user') {
            // Add a one-time apply button in job modal footer if not present
            let quickApplyBtn = document.getElementById('jobModalApplyBtn');
            if (!quickApplyBtn) {
                quickApplyBtn = document.createElement('button');
                quickApplyBtn.id = 'jobModalApplyBtn';
                quickApplyBtn.className = 'btn';
                quickApplyBtn.style.cssText = 'background:linear-gradient(135deg,#6366f1,#06b6d4);color:white;border:none;padding:8px 20px;font-weight:600;border-radius:8px;';
                quickApplyBtn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Postuler';
                document.querySelector('#jobModal .modal-footer').prepend(quickApplyBtn);
            }
            quickApplyBtn.style.display = 'inline-block';
            quickApplyBtn.onclick = () => {
                modal.hide();
                setTimeout(() => openApplyModal(data.id, `${data.title} — ${data.company || ''}`), 300);
            };
        } else {
            const quickApplyBtn = document.getElementById('jobModalApplyBtn');
            if (quickApplyBtn) quickApplyBtn.style.display = 'none';
        }
    } catch (error) {
        console.error('Erreur:', error);
        showStatus('Erreur lors du chargement des détails', 'danger');
    }
}

function openApplyModal(jobId, jobLabel) {
    document.getElementById('applyJobId').value = jobId;
    document.getElementById('applyJobTitle').textContent = jobLabel || '';
    // Reset form
    document.getElementById('applyForm').reset();
    clearCvFile();
    applyModal.show();
}

function clearCvFile() {
    const input = document.getElementById('applyCvFile');
    const preview = document.getElementById('cvFilePreview');
    const dropZone = document.getElementById('cvDropZone');
    if (input) input.value = '';
    if (preview) preview.style.display = 'none';
    if (dropZone) { dropZone.style.border = '2px dashed #c7d2fe'; dropZone.style.background = '#fafbff'; }
}

async function submitApplication() {
    const jobId       = document.getElementById('applyJobId').value;
    const name        = document.getElementById('applyName').value.trim();
    const email       = document.getElementById('applyEmail').value.trim();
    const phone       = document.getElementById('applyPhone').value.trim();
    const experience  = document.getElementById('applyExperience').value;
    const location    = document.getElementById('applyLocation').value.trim();
    const currentTitle= document.getElementById('applyCurrentTitle').value.trim();
    const domain      = document.getElementById('applyDomain').value.trim();
    const coverLetter = document.getElementById('applyCoverLetter').value.trim();
    const fileInput   = document.getElementById('applyCvFile');
    const file        = fileInput && fileInput.files[0];

    if (!name || !email) {
        showStatus('Veuillez remplir votre nom et email.', 'warning');
        return;
    }
    if (!file) {
        showStatus('Veuillez joindre votre CV (PDF ou DOCX).', 'warning');
        return;
    }
    if (file.size > 5 * 1024 * 1024) {
        showStatus('Le fichier est trop volumineux (max 5 Mo).', 'warning');
        return;
    }

    const btn = document.getElementById('submitApplyBtn');
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-circle-notch fa-spin me-2"></i>Envoi en cours...';

    try {
        const formData = new FormData();
        formData.append('job_id',           jobId);
        formData.append('name',             name);
        formData.append('email',            email);
        formData.append('phone',            phone);
        formData.append('experience_level', experience);
        formData.append('location',         location);
        formData.append('current_title',    currentTitle);
        formData.append('domain',           domain);
        formData.append('cover_letter',     coverLetter);
        formData.append('file',             file);

        const res = await fetch(`${api.baseUrl}/apply/cv/upload`, {
            method: 'POST',
            credentials: 'include',
            body: formData
        });

        if (res.status === 401) {
            showStatus('Session expirée. Veuillez vous reconnecter.', 'warning');
            setTimeout(() => window.location.href = 'login.html', 1500);
            return;
        }

        let data;
        try {
            data = await res.json();
        } catch (_) {
            data = { error: `Erreur serveur (HTTP ${res.status})` };
        }

        if (res.ok && data.success) {
            applyModal.hide();
            showStatus(`🎉 Candidature envoyée avec succès pour "${data.job}" !`, 'success');
        } else {
            showStatus(data.error || `Erreur (${res.status})`, 'danger');
        }
    } catch (err) {
        console.error('[submitApplication]', err);
        // Distinguish CORS/network error vs other errors
        if (err.message && err.message.includes('fetch')) {
            showStatus('Impossible de joindre le serveur. Vérifiez que le backend est démarré (port 5001).', 'danger');
        } else {
            showStatus(`Erreur: ${err.message}`, 'danger');
        }
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-paper-plane me-2"></i>Envoyer ma candidature';
    }
}

function fillForm(data) {
    if (document.getElementById('jobId')) document.getElementById('jobId').value = data.id || '';
    if (document.getElementById('title')) document.getElementById('title').value = data.title || '';
    if (document.getElementById('company')) document.getElementById('company').value = data.company || '';
    if (document.getElementById('description')) document.getElementById('description').value = data.description || '';
    if (document.getElementById('salary')) document.getElementById('salary').value = data.salary || '';
    if (document.getElementById('location')) document.getElementById('location').value = data.location || '';
    if (document.getElementById('type')) document.getElementById('type').value = data.type || '';
}

async function saveJob() {
    if (!currentUser || (currentUser.role !== 'admin' && currentUser.role !== 'recruiter')) return;

    const payload = {
        title: document.getElementById('title').value.trim(),
        company: document.getElementById('company').value.trim(),
        description: document.getElementById('description').value.trim(),
        salary: document.getElementById('salary').value.trim(),
        location: document.getElementById('location').value.trim(),
        type: document.getElementById('type').value
    };

    if (!payload.title) {
        showStatus('Le titre est obligatoire', 'warning');
        return;
    }
    if (!payload.company && currentUser.role === 'admin') {
        showStatus('L\'entreprise est obligatoire', 'warning');
        return;
    }

    try {
        if (currentJobId) {
            await api.updateJob(currentJobId, payload);
            showStatus('Offre mise à jour avec succès', 'success');
        } else {
            await api.addJob(payload);
            showStatus('Offre ajoutée avec succès', 'success');
        }

        modal.hide();
        setTimeout(loadJobs, 500);
    } catch (error) {
        console.error('Erreur:', error);
        showStatus('Erreur lors de l\'enregistrement', 'danger');
    }
}

async function deleteJob(id) {
    if (!currentUser || (currentUser.role !== 'admin' && currentUser.role !== 'recruiter')) return;

    if (confirm('Êtes-vous sûr de vouloir supprimer cette offre ?')) {
        try {
            await api.deleteJob(id);
            showStatus('Offre supprimée avec succès', 'success');
            loadJobs();
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
    setTimeout(() => alert.style.display = 'none', 4000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
