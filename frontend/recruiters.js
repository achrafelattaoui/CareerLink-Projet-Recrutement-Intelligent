window.allRecruiters = [];

document.addEventListener('DOMContentLoaded', async () => {
    // Vérification admin
    const user = JSON.parse(localStorage.getItem('user'));
    if (!user || user.role !== 'admin') {
        window.location.href = 'index.html';
        return;
    }

    document.getElementById('userInfo').textContent = user.username + ' (' + user.role + ')';
    if(user.username && user.username.length > 0) {
        document.getElementById('sidebarAvatar').textContent = user.username.charAt(0).toUpperCase();
        document.getElementById('sidebarName').textContent = user.username;
        document.getElementById('sidebarRole').textContent = user.role === 'admin' ? 'Administrateur' : user.role;
    }

    // Gestion de la recherche
    document.getElementById('searchInput').addEventListener('input', (e) => {
        const term = e.target.value.toLowerCase();
        const filtered = window.allRecruiters.filter(r => 
            (r.name && r.name.toLowerCase().includes(term)) ||
            (r.email && r.email.toLowerCase().includes(term)) ||
            (r.company_name && r.company_name.toLowerCase().includes(term))
        );
        renderRecruiters(filtered);
    });

    await loadRecruiters();
});

async function loadRecruiters() {
    const list = document.getElementById('recruitersList');
    try {
        const res = await api.getRecruiters();
        if(res.recruiters) {
            window.allRecruiters = res.recruiters;
            document.getElementById('recruiterCountBadge').textContent = res.count || window.allRecruiters.length;
            renderRecruiters(window.allRecruiters);
        }
    } catch (err) {
        console.error("Erreur de chargement des recruteurs", err);
        list.innerHTML = `<tr><td colspan="4" class="text-center py-4 text-danger"><i class="fas fa-exclamation-circle me-2"></i>Erreur: ${err.message}</td></tr>`;
    }
}

function renderRecruiters(recruiters) {
    const list = document.getElementById('recruitersList');
    if(!recruiters || recruiters.length === 0) {
        list.innerHTML = '<tr><td colspan="4" class="text-center py-5 text-muted">Aucun recruteur trouvé.</td></tr>';
        return;
    }

    list.innerHTML = recruiters.map(r => `
        <tr>
            <td class="fw-bold text-dark">
                <div class="d-flex align-items-center gap-2">
                    <div style="width:32px;height:32px;border-radius:8px;background:#e2e8f0;display:flex;align-items:center;justify-content:center;color:#475569;font-size:.8rem;font-weight:700;">
                        ${r.name ? r.name.charAt(0).toUpperCase() : '?'}
                    </div>
                    ${r.name || 'N/A'}
                </div>
            </td>
            <td><a href="mailto:${r.email}" class="text-decoration-none">${r.email || '—'}</a></td>
            <td><span class="badge" style="background:#f1f5f9;color:#475569;">${r.company_name || '—'}</span></td>
            <td class="text-center">
                <button class="btn btn-light btn-sm text-danger" onclick="deleteRecruiter('${r.id}')" title="Supprimer">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

async function deleteRecruiter(id) {
    if(!confirm("Êtes-vous sûr de vouloir supprimer ce recruteur ? Cette action est irréversible.")) return;
    
    try {
        await api.deleteRecruiter(id);
        await loadRecruiters();
    } catch (err) {
        alert("Erreur lors de la suppression : " + err.message);
    }
}
