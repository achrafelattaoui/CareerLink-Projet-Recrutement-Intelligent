let currentUser = null;
const modal = new bootstrap.Modal(document.getElementById('companyModal'));

document.addEventListener('DOMContentLoaded', async function () {
    await checkAuth();

    // Search logic
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', filterAndDisplayCompanies);
    }

    await loadCompanies();

    // Check for direct link or search redirection
    const openId = localStorage.getItem('openCompany');
    if (openId) {
        localStorage.removeItem('openCompany');
        viewCompanyDetails(openId);
    }
});

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

            // Recruteurs restricted from full companies list
            if (currentUser.role === 'recruiter') {
                window.location.href = 'index.html';
                return;
            }

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

    // Sidebar user info
    const sa = document.getElementById('sidebarAvatar');
    const sn = document.getElementById('sidebarName');
    const sr = document.getElementById('sidebarRole');
    const ui = document.getElementById('userInfo');
    if (sa) sa.textContent = (currentUser.username || 'U').charAt(0).toUpperCase();
    if (sn) sn.textContent = currentUser.username || '—';
    if (sr) sr.textContent = isAdmin ? 'Administrateur' : isRecruiter ? 'Recruteur' : 'Candidat';
    if (ui) ui.textContent = `${currentUser.username} (${currentUser.role})`;

    const addBtn = document.querySelector('button[data-bs-target="#companyModal"]');
    if (addBtn) {
        addBtn.removeAttribute('data-bs-toggle');
        addBtn.removeAttribute('data-bs-target');
        addBtn.onclick = openAddModal;
        addBtn.style.display = isAdmin ? 'inline-block' : 'none';
    }

    // Form fields
    const fields = ['companyName', 'companySector', 'recruiterName', 'recruiterEmail', 'companyDescription'];
    fields.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.readOnly = !isAdmin;
    });
}

async function loadCompanies() {
    try {
        const data = await api.getCompanies();
        window.allCompanies = data.companies || [];
        window.totalCompanyCount = data.count; // Stocker le total réel
        filterAndDisplayCompanies();
        const badge = document.getElementById('companyCountBadge');
        if (badge) badge.textContent = data.count || window.allCompanies.length;
        showStatus(`${data.count || window.allCompanies.length} entreprise(s) au total`, 'success');
    } catch (error) {
        showStatus('Erreur lors du chargement des entreprises', 'danger');
    }
}

function filterAndDisplayCompanies() {
    if (!window.allCompanies) return;

    const searchVal = (document.getElementById('searchInput')?.value || '').toLowerCase();

    const filtered = window.allCompanies.filter(company => {
        return (company.name || '').toLowerCase().includes(searchVal) ||
               (company.sector || '').toLowerCase().includes(searchVal) ||
               (company.recruiter_name || '').toLowerCase().includes(searchVal) ||
               (company.recruiter_email || '').toLowerCase().includes(searchVal);
    });

    displayCompanies(filtered, searchVal);
}

function displayCompanies(companies, searchVal = '') {
    const container = document.getElementById('companiesList');
    const badge = document.getElementById('companyCountBadge');
    if (badge) {
        if (!searchVal) {
            badge.textContent = window.totalCompanyCount || companies.length;
        } else {
            badge.textContent = companies.length;
        }
    }

    if (!companies || companies.length === 0) {
        container.innerHTML = '<tr><td colspan="5" class="text-center py-5 text-muted">Aucune entreprise trouvée</td></tr>';
        return;
    }

    container.innerHTML = companies.map(company => `
        <tr>
            <td class="fw-bold text-dark">${escapeHtml(company.name)}</td>
            <td><span class="badge bg-light text-dark border">${escapeHtml(company.sector || '—')}</span></td>
            <td>${escapeHtml(company.recruiter_name || '—')}</td>
            <td><small class="text-muted">${escapeHtml(company.recruiter_email || '—')}</small></td>
            <td class="text-center">
                <button class="btn btn-sm btn-outline-primary" onclick="openEditModal('${company.id}')" title="Modifier/Détails">
                    <i class="fas fa-edit"></i>
                </button>
                ${currentUser && currentUser.role === 'admin' ? `
                    <button class="btn btn-sm btn-outline-danger ms-1" onclick="deleteCompanyDirect('${company.id}')" title="Supprimer">
                        <i class="fas fa-trash"></i>
                    </button>
                ` : ''}
            </td>
        </tr>
    `).join('');
}

function openAddModal() {
    document.getElementById('companyForm').reset();
    document.getElementById('companyId').value = '';
    document.getElementById('modalTitle').textContent = 'Nouvelle entreprise';
    
    // Reset fields to editable if admin
    const isAdmin = currentUser && currentUser.role === 'admin';
    const fields = ['companyName', 'companySector', 'recruiterName', 'recruiterEmail', 'companyDescription'];
    fields.forEach(fid => {
        const el = document.getElementById(fid);
        if (el) el.readOnly = !isAdmin;
    });

    const deleteBtn = document.getElementById('deleteCompanyBtn');
    if (deleteBtn) deleteBtn.style.display = 'none';

    const saveBtn = document.querySelector('#companyModal .btn-primary[onclick="saveCompany()"]');
    if (saveBtn) saveBtn.style.display = isAdmin ? 'inline-block' : 'none';

    modal.show();
}

async function openEditModal(id) {
    try {
        const data = await api.getCompany(id);
        
        document.getElementById('companyId').value = id;
        document.getElementById('companyName').value = data.name || '';
        document.getElementById('companySector').value = data.sector || '';
        document.getElementById('recruiterName').value = data.recruiter_name || '';
        document.getElementById('recruiterEmail').value = data.recruiter_email || '';
        document.getElementById('companyDescription').value = data.description || '';

        const isAdmin = currentUser && currentUser.role === 'admin';
        document.getElementById('modalTitle').textContent = isAdmin ? 'Modifier l\'entreprise' : 'Détails de l\'entreprise';

        // Toggle buttons
        const deleteBtn = document.getElementById('deleteCompanyBtn');
        if (deleteBtn) deleteBtn.style.display = isAdmin ? 'inline-block' : 'none';

        const saveBtn = document.querySelector('#companyModal .btn-primary[onclick="saveCompany()"]');
        if (saveBtn) saveBtn.style.display = isAdmin ? 'inline-block' : 'none';

        // Set readonly state
        const fields = ['companyName', 'companySector', 'recruiterName', 'recruiterEmail', 'companyDescription'];
        fields.forEach(fid => {
            const el = document.getElementById(fid);
            if (el) el.readOnly = !isAdmin;
        });

        modal.show();
    } catch (error) {
        console.error('Erreur:', error);
        showStatus('Erreur lors du chargement des détails', 'danger');
    }
}

async function viewCompanyDetails(id) {
    try {
        const data = await api.getCompany(id);

        document.getElementById('companyName').value = data.name || '';
        document.getElementById('companySector').value = data.sector || '';
        document.getElementById('recruiterName').value = data.recruiter_name || '';
        document.getElementById('recruiterEmail').value = data.recruiter_email || '';
        document.getElementById('companyDescription').value = data.description || '';

        const titleEl = document.getElementById('modalTitle');
        if (titleEl) titleEl.textContent = 'Détails de l\'entreprise';

        // Always hide save button and make readonly in view mode
        const saveBtn = document.querySelector('#companyModal .btn-primary');
        if (saveBtn) saveBtn.style.display = 'none';

        const fields = ['companyName', 'companySector', 'recruiterName', 'recruiterEmail', 'companyDescription'];
        fields.forEach(fid => {
            const el = document.getElementById(fid);
            if (el) el.readOnly = true;
        });

        modal.show();
    } catch (error) {
        console.error('Erreur:', error);
        showStatus('Erreur lors du chargement des détails', 'danger');
    }
}

async function saveCompany() {
    if (currentUser.role !== 'admin') return;

    const id = document.getElementById('companyId').value;
    const payload = {
        name: document.getElementById('companyName').value.trim(),
        sector: document.getElementById('companySector').value.trim(),
        recruiter_name: document.getElementById('recruiterName').value.trim(),
        recruiter_email: document.getElementById('recruiterEmail').value.trim(),
        description: document.getElementById('companyDescription').value.trim()
    };

    if (!payload.name) {
        showStatus('Le nom est obligatoire', 'warning');
        return;
    }

    try {
        if (id) {
            await api.updateCompany(id, payload);
            showStatus('Entreprise mise à jour avec succès', 'success');
        } else {
            await api.addCompany(payload);
            showStatus('Entreprise ajoutée avec succès', 'success');
        }
        modal.hide();
        await loadCompanies();
    } catch (error) {
        showStatus('Erreur lors de l\'enregistrement', 'danger');
    }
}

async function deleteCompany() {
    const id = document.getElementById('companyId').value;
    if (!id) return;
    await deleteCompanyDirect(id);
    modal.hide();
}

async function deleteCompanyDirect(id) {
    if (currentUser.role !== 'admin') return;

    if (confirm('Êtes-vous sûr de vouloir supprimer cette entreprise ?')) {
        try {
            await api.deleteCompany(id);
            showStatus('Entreprise supprimée avec succès', 'success');
            await loadCompanies();
        } catch (error) {
            console.error('Erreur:', error);
            showStatus('Erreur lors de la suppression', 'danger');
        }
    }
}

async function deleteCompany(id) {
    if (currentUser.role !== 'admin') return;

    if (confirm('Êtes-vous sûr de vouloir supprimer cette entreprise ?')) {
        try {
            await api.deleteCompany(id);
            showStatus('Entreprise supprimée avec succès', 'success');
            loadCompanies();
        } catch (error) {
            console.error('Erreur:', error);
            showStatus('Erreur lors de la suppression', 'danger');
        }
    }
}

function showStatus(message, type = 'info') {
    const alert = document.getElementById('statusAlert');
    if (alert) {
        document.getElementById('statusMessage').textContent = message;
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.style.display = 'block';
        setTimeout(() => alert.style.display = 'none', 4000);
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
