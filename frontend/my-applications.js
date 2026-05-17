document.addEventListener('DOMContentLoaded', async () => {
    const user = await checkAuth();
    if (user && user.role === 'user') {
        loadMyApplications(user.id);
    } else if (user) {
        window.location.href = 'index.html';
    }
});

async function checkAuth() {
    try {
        const response = await fetch(`${api.baseUrl}/auth/me`, { credentials: 'include' });
        if (response.status === 401) {
            window.location.href = 'login.html';
            return null;
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
    const sidebarAvatar = document.getElementById('sidebarAvatar');
    const sidebarName   = document.getElementById('sidebarName');
    const sidebarRole   = document.getElementById('sidebarRole');
    const userInfo      = document.getElementById('userInfo');

    if (sidebarAvatar) sidebarAvatar.textContent = (user.username || 'U').charAt(0).toUpperCase();
    if (sidebarName)   sidebarName.textContent   = user.username || '—';
    if (sidebarRole)   sidebarRole.textContent   = 'Candidat';
    if (userInfo)      userInfo.textContent       = `${user.username} (Candidat)`;

    if (window.applySidebarVisibility) {
        window.applySidebarVisibility(user.role);
    }

    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.onclick = async () => {
            await fetch(`${api.baseUrl}/auth/logout`, { method: 'POST', credentials: 'include' });
            window.location.href = 'login.html';
        };
    }
}

async function loadMyApplications(userId) {
    const tbody = document.getElementById('myApplicationsList');
    try {
        // Fetch from session-based endpoint (most reliable)
        let data;
        try {
            data = await api.getMyApplications();
        } catch (sessionErr) {
            console.warn('[MyApps] /my/applications failed, fallback to /candidates/:id/applications', sessionErr);
            data = await api.getCandidateApplications(userId);
        }

        const apps = data.applications || [];

        // Sort newest first (client-side safety net — backend already orders DESC)
        apps.sort((a, b) => {
            const da = a.applied_at ? new Date(a.applied_at) : new Date(0);
            const db = b.applied_at ? new Date(b.applied_at) : new Date(0);
            return db - da;
        });

        if (apps.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center py-5 text-muted">
                <i class="fas fa-inbox fa-2x mb-3 d-block" style="color:#cbd5e1;"></i>
                Vous n'avez postulé à aucune offre pour le moment.<br>
                <a href="recommendations.html" class="btn btn-sm btn-primary mt-3">
                    <i class="fas fa-star me-1"></i> Découvrir des offres via Smart CV
                </a>
            </td></tr>`;
            return;
        }

        // Status config — matches French values stored in DB
        const statusConfig = {
            'en_attente': { label: 'En attente',  icon: 'fa-clock',        color: '#92400e', bg: '#fef3c7' },
            'accepte':    { label: 'Accepté ✓',   icon: 'fa-check-circle', color: '#065f46', bg: '#d1fae5' },
            'rejete':     { label: 'Rejeté',       icon: 'fa-times-circle', color: '#991b1b', bg: '#fee2e2' }
        };

        tbody.innerHTML = apps.map(app => {
            const status  = (app.status || 'en_attente');
            const st      = statusConfig[status] || statusConfig['en_attente'];

            let dateStr = '-';
            if (app.applied_at) {
                try {
                    const d = new Date(app.applied_at);
                    if (!isNaN(d.getTime())) {
                        dateStr = d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
                    }
                } catch (_) {}
            }

            // Backend returns "title"; keep job_title as fallback for older records
            const title   = escapeHtml(app.title || app.job_title || 'Offre sans titre');
            const company = escapeHtml(app.company || '-');
            const loc     = escapeHtml(app.location || '-');

            return `
            <tr>
                <td class="px-4 py-3 fw-bold" style="color:#0f172a;">${title}</td>
                <td><i class="fas fa-building text-muted me-2"></i>${company}</td>
                <td><i class="fas fa-map-marker-alt text-muted me-2"></i>${loc}</td>
                <td class="text-muted"><i class="far fa-calendar-alt me-2"></i>${dateStr}</td>
                <td class="text-end px-4">
                    <span style="display:inline-flex;align-items:center;gap:6px;padding:5px 14px;border-radius:20px;font-size:.78rem;font-weight:700;background:${st.bg};color:${st.color};">
                        <i class="fas ${st.icon}"></i>${st.label}
                    </span>
                </td>
            </tr>`;
        }).join('');

    } catch (err) {
        console.error('[MyApps] Error:', err);
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-5 text-danger">
            <i class="fas fa-exclamation-circle me-2"></i>Erreur lors du chargement des candidatures.
            <br><small class="text-muted mt-2 d-block">${escapeHtml(err.message || '')}</small>
        </td></tr>`;
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
