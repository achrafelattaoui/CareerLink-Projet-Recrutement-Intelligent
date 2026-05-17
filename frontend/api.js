// API Client - Gère tous les appels à l'API backend
const hostname = (typeof window !== 'undefined' && window.location.hostname) ? window.location.hostname : 'localhost';
const API_URL = `http://${hostname}:5001`;

class APIClient {
    constructor() {
        this.baseUrl = API_URL;
    }

    // Utilitaire pour les requêtes
    async request(endpoint, method = 'GET', data = null) {
        const url = `${this.baseUrl}${endpoint}`;
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            cache: 'no-store'
        };

        if (data) {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, options);
            if (response.status === 401) {
                // Not authenticated
                window.location.href = 'login.html';
                throw new Error('Non authentifié');
            }
            if (!response.ok) {
                let errMsg = response.statusText;
                try {
                    const errData = await response.json();
                    if (errData && errData.error) errMsg = errData.error;
                } catch(e) {}
                throw new Error(`API Error: ${errMsg}`);
            }
            return await response.json();
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    }

    // Health Check
    async healthCheck() {
        return this.request('/health');
    }

    // Stats
    async getStats() {
        return this.request('/stats');
    }

    // ===== CANDIDATS =====
    async getCandidates() {
        return this.request('/candidates');
    }

    async getCandidate(id) {
        return this.request(`/candidates/${id}`);
    }

    async addCandidate(data) {
        return this.request('/candidates/add', 'POST', data);
    }

    async updateCandidate(id, data) {
        return this.request(`/candidates/${id}`, 'PUT', data);
    }

    async deleteCandidate(id) {
        return this.request(`/candidates/${id}`, 'DELETE');
    }

    async getCandidateCompanies(id) {
        return this.request(`/candidate/${id}/companies`);
    }

    async addCompanyToCandidate(candidateId, companyName) {
        return this.request(`/candidate/${candidateId}/companies/add`, 'POST', {
            company_name: companyName
        });
    }

    async getCandidateApplications(id) {
        return this.request(`/candidates/${id}/applications`);
    }

    async getMyApplications() {
        return this.request(`/my/applications`);
    }

    // ===== OFFRES =====
    async getJobs() {
        return this.request('/jobs');
    }

    async getJob(id) {
        return this.request(`/jobs/${id}`);
    }

    async addJob(data) {
        return this.request('/jobs/add', 'POST', data);
    }

    async updateJob(id, data) {
        return this.request(`/jobs/${id}`, 'PUT', data);
    }

    async deleteJob(id) {
        return this.request(`/jobs/${id}`, 'DELETE');
    }

    async getJobApplicants(id) {
        return this.request(`/job/${id}/candidates`);
    }

    async getJobsWithApplicants() {
        return this.request('/recruiter/jobs-with-applicants');
    }

    async selectCandidate(jobId, candidateId) {
        return this.request(`/job/${jobId}/select/${candidateId}`, 'POST');
    }

    async rejectCandidate(jobId, candidateId) {
        return this.request(`/job/${jobId}/reject/${candidateId}`, 'POST');
    }

    // ===== RECRUTEURS =====
    async getRecruiters() {
        return this.request('/recruiters');
    }
    async deleteRecruiter(id) {
        return this.request(`/recruiters/${id}`, 'DELETE');
    }

    // ===== ENTREPRISES =====
    async getCompanies() {
        return this.request('/companies');
    }

    async getCompany(id) {
        return this.request(`/companies/${id}`);
    }

    async updateCompany(id, data) {
        return this.request(`/companies/${id}`, 'PUT', data);
    }

    async deleteCompany(id) {
        return this.request(`/companies/${id}`, 'DELETE');
    }

    async addCompany(data) {
        // Support both old string name and new object payload
        const payload = typeof data === 'string' ? { name: data } : data;
        return this.request('/companies/add', 'POST', payload);
    }

    // ===== RELATIONS =====
    async applyToJob(candidateId, jobId) {
        return this.request('/apply', 'POST', {
            candidate_id: candidateId,
            job_id: jobId
        });
    }

    // ===== RECHERCHE =====
    async search(query, type = 'all', limit = 20, offset = 0) {
        return this.request(`/search?q=${encodeURIComponent(query)}&type=${type}&limit=${limit}&offset=${offset}`);
    }
    // ===== CAREER PATH =====
    async getCareerPath(title = '') {
        return this.request(`/career-path?title=${encodeURIComponent(title)}`);
    }

    // ===== RECOMMANDATIONS CV =====
    async uploadCV(file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${this.baseUrl}/recommendations/upload-cv`, {
            method: 'POST',
            body: formData,
            // Don't set Content-Type header manually, let browser set it with boundary
            credentials: 'include'
        });

        if (response.status === 401) {
            window.location.href = 'login.html';
            throw new Error('Non authentifié');
        }
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || `API Error: ${response.statusText}`);
        }
        return await response.json();
    }

    // ===== ANALYTICS =====
    async getMarketTrends() {
        return this.request(`/analytics/market-trends?t=${new Date().getTime()}`);
    }

    // ===== SMART SCORING =====
    async getMyJobs() {
        return this.request('/recruiter/my-jobs');
    }

    async scoreApplicants(jobId) {
        return this.request(`/recommendations/score-applicants/${jobId}`);
    }
}

// Instance globale
const api = new APIClient();


// Global Sidebar Visibility Handler
window.applySidebarVisibility = function(role) {
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    sidebarLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (!href || href === '#' || href.startsWith('javascript:')) return;
        
        // Normalize filename
        const filename = href.split('/').pop().split('?')[0] || 'index.html';
        
        let show = false;
        const normalizedRole = (role || '').toLowerCase().trim();
        if (normalizedRole === 'admin' || normalizedRole === 'administrateur') {
            // Admin sees everything except Smart CV (recommendations)
            const hiddenForAdmin = ['recommendations.html'];
            show = !hiddenForAdmin.includes(filename);
        } else if (normalizedRole === 'recruiter' || normalizedRole === 'recruteur') {
            // Recruteur: Candidates, Sourcing, Search, Dashboard, Applicants, Smart Scoring
            const allowed = ['index.html', 'candidates.html', 'smart-sourcing.html', 'search.html', 'applicants.html', 'smart-scoring.html'];
            show = allowed.includes(filename);
        } else if (normalizedRole === 'user' || normalizedRole === 'candidat') {
            // Candidat: Jobs, Companies, Smart CV, Search, Dashboard, My Applications
            const allowed = ['index.html', 'jobs.html', 'companies.html', 'recommendations.html', 'search.html', 'my-applications.html'];
            show = allowed.includes(filename);
        }
        
        if (show) {
            link.style.setProperty('display', 'flex', 'important');
            link.classList.remove('d-none');
        } else {
            link.style.setProperty('display', 'none', 'important');
            link.classList.add('d-none');
        }
    });

    // Hide empty sections
    document.querySelectorAll('.sidebar-section').forEach(section => {
        let next = section.nextElementSibling;
        let hasVisible = false;
        while (next && !next.classList.contains('sidebar-section') && !next.classList.contains('sidebar-bottom')) {
            if (next.classList.contains('sidebar-link') && next.style.display !== 'none') {
                hasVisible = true;
                break;
            }
            next = next.nextElementSibling;
        }
        section.style.display = hasVisible ? 'block' : 'none';
    });
};
