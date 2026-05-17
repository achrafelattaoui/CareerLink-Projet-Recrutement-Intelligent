document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Check Auth
        try {
            const user = await api.request('/auth/me');
            if (!user.authenticated) {
                window.location.href = 'login.html';
                return;
            }

            // Smart CV is for Candidates (user) and Admins only
            if (user.user.role === 'recruiter') {
                window.location.href = 'index.html';
                return;
            }

            // Update User Info to match index.js style
            const userInfo = document.getElementById('userInfo');
            if (userInfo) {
                userInfo.textContent = `${user.user.username} (${user.user.role})`;
            }
            setupLogout();
            setupNavigation(user.user);
        } catch (e) {
            console.error("Auth verification failed:", e);
            alert("Debug Error: " + e.message);
        }

        // Elements
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        const loader = document.getElementById('loader');
        const resultsSection = document.getElementById('resultsSection');
        const skillsContainer = document.getElementById('skillsContainer');
        const jobsContainer = document.getElementById('jobsContainer');
        const matchLabel = document.getElementById('matchLabel');

        // Drag & Drop Handlers
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
        });

        dropZone.addEventListener('drop', handleDrop, false);
        fileInput.addEventListener('change', handleFiles, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles({ target: { files: files } });
        }

        async function handleFiles(e) {
            const file = e.target.files[0];
            if (!file) return;

            const isValidType = file.type === 'application/pdf'
                || file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                || file.name.toLowerCase().endsWith('.docx');

            if (!isValidType) {
                alert("Veuillez uploader un fichier PDF ou DOCX.");
                return;
            }

            // UI Reset
            loader.classList.remove('d-none');
            resultsSection.classList.add('d-none');
            dropZone.classList.add('d-none');

            try {
                const data = await api.uploadCV(file);
                // Cache CV data globally so Postuler button can access it
                window._cvData = {
                    name:             data.candidate_name  || null,
                    email:            data.candidate_email || null,
                    phone:            data.candidate_phone || '',
                    experience_level: data.candidate_experience || data.nlp_insights?.cv_seniority || null,
                    skills:           data.tech_skills || []
                };
                displayResults(data);
            } catch (err) {
                alert("Erreur lors de l'analyse : " + err.message);
                dropZone.classList.remove('d-none');
            } finally {
                loader.classList.add('d-none');
            }
        }

        function displayResults(data) {
            resultsSection.classList.remove('d-none');

            // --- Profile Saved Notification ---
            if (data.candidate_saved) {
                const existingNotif = document.getElementById('profileSavedNotif');
                if (!existingNotif) {
                    const notif = document.createElement('div');
                    notif.id = 'profileSavedNotif';
                    notif.style.cssText = `
                        background: linear-gradient(135deg, #d1fae5, #a7f3d0);
                        border: 1px solid #6ee7b7;
                        border-radius: 12px;
                        padding: 14px 20px;
                        margin-bottom: 20px;
                        display: flex;
                        align-items: center;
                        gap: 12px;
                        font-size: 0.88rem;
                        color: #065f46;
                        font-weight: 500;
                    `;
                    notif.innerHTML = `
                        <i class="fas fa-check-circle" style="font-size:1.3rem;color:#10b981;"></i>
                        <div>
                            <strong>Profil enregistré avec succès !</strong><br>
                            <span style="font-weight:400;color:#047857;">Vos coordonnées et compétences ont été sauvegardées dans la base de données. Les recruteurs peuvent maintenant vous découvrir via Smart Sourcing.</span>
                        </div>
                    `;
                    resultsSection.prepend(notif);
                }
            }

            // --- AI Insights Banner ---
            const nlpBanner = document.getElementById('nlpInfoBanner');
            const nlpEngineLabel = document.getElementById('nlpEngineLabel');
            const nlpConceptsRow = document.getElementById('nlpConceptsRow');

            if (data.nlp_insights) {
                nlpBanner.classList.remove('d-none');
                nlpEngineLabel.textContent = 'Analyse intelligente de votre profil';
                // Show top key concepts
                if (data.nlp_insights.key_concepts && data.nlp_insights.key_concepts.length > 0) {
                    const top = data.nlp_insights.key_concepts.slice(0, 8);
                    nlpConceptsRow.innerHTML = '<small class="text-muted me-2">Mots-clés identifiés :</small>' + top.map(c =>
                        `<span class="badge me-1 mb-1" style="background:#c7d2fe;color:#3730a3;font-size:0.75rem;">${c}</span>`
                    ).join('');
                }
            }

            // --- Skills ---
            if (skillsContainer) {
                skillsContainer.innerHTML = '';
                const allSkills = data.tech_skills && data.tech_skills.length > 0 ? data.tech_skills : (data.detected_skills || []);
                if (allSkills.length > 0) {
                    allSkills.forEach(skill => {
                        const el = document.createElement('span');
                        el.className = 'skill-tag';
                        el.innerHTML = `<i class="fas fa-check-circle"></i> ${skill.toUpperCase()}`;
                        skillsContainer.appendChild(el);
                    });
                } else {
                    skillsContainer.innerHTML = '<p class="text-muted fst-italic">Aucune compétence technique spécifique détectée, mais nous avons analysé le texte global.</p>';
                }
            }

            // --- Jobs ---
            jobsContainer.innerHTML = '';
            const jobs = data.jobs || [];
            if (matchLabel) matchLabel.textContent = `${jobs.length} Correspondances trouvées`;

            if (jobs.length === 0) {
                jobsContainer.innerHTML = `
                <div class="col-12 text-center">
                    <div class="alert alert-warning">Aucune offre ne correspond exactement aux mots-clés trouvés. Essayez d'enrichir votre CV.</div>
                </div>
            `;
                return;
            }

            jobs.forEach(job => {
                const col = document.createElement('div');
                col.className = 'col-md-6 col-xl-4';

                // Salary display
                let salaryDisplay = job.salary ? `${job.salary} DH` : 'N/C';

                // Match label and color
                const matchLabelText = job.match_label || 'Match Possible';
                let badgeStyle, progressColor;
                if (matchLabelText === 'Excellent Match') {
                    badgeStyle = 'background:#dcfce7;color:#15803d;';
                    progressColor = '#10b981';
                } else if (matchLabelText === 'Bon Match' || matchLabelText === 'Good Match') {
                    badgeStyle = 'background:#eff6ff;color:#1d4ed8;';
                    progressColor = '#3b82f6';
                } else {
                    badgeStyle = 'background:#fef3c7;color:#b45309;';
                    progressColor = '#f59e0b';
                }

                // Absolute score
                const scorePercent = job.score_percent || Math.min(Math.round((job.score || 0) * 100), 100);
                const scoreDisplay = `${scorePercent}%`;
                
                // Matched skills chips
                const matchedSkills = job.matched_skills || [];
                const skillsHtml = matchedSkills.slice(0, 4)
                    .map(s => `<span class="badge" style="background:#f1f5f9;color:#475569;font-size:0.65rem;font-weight:600;margin-right:4px;">${s}</span>`)
                    .join('');

                // Breakdown text
                const breakdown = job.score_breakdown || {};
                const breakdownHtml = (breakdown.seniority && breakdown.seniority !== "0.0%") ? 
                    `<div class="d-flex gap-2 mt-1" style="font-size:0.65rem;color:#64748b;">
                        <span><i class="fas fa-level-up-alt"></i> Exp: ${breakdown.seniority}</span>
                    </div>` : '';

                col.innerHTML = `
                <div class="job-card-premium h-100 d-flex flex-column">
                    <div class="match-badge" style="${badgeStyle}">${matchLabelText}</div>
                    <div class="mb-2" style="margin-top:6px;">
                         <div class="d-flex align-items-center mb-2">
                            <span class="badge bg-light text-dark border me-2">CDI</span>
                            <small class="text-muted"><i class="fas fa-map-marker-alt me-1"></i>${job.location || 'Remote'}</small>
                         </div>
                        <h5 class="fw-bold text-dark mb-1" style="font-size:1.1rem;line-height:1.3;">${job.title}</h5>
                        <p class="text-primary fw-bold mb-0" style="font-size:0.9rem;"><i class="fas fa-building me-1"></i>${job.company || 'N/A'}</p>
                    </div>

                    ${matchedSkills.length > 0 ? `<div class="mb-3">${skillsHtml}</div>` : ''}

                    <!-- Score Bar -->
                    <div class="mt-auto mb-3">
                        <div class="d-flex justify-content-between mb-1">
                            <small class="text-muted" style="font-size:0.75rem;font-weight:600;">Compatibilité Globale</small>
                            <small class="fw-bold" style="font-size:0.75rem;color:${progressColor};">${scoreDisplay}</small>
                        </div>
                        <div style="height:6px;background:#e2e8f0;border-radius:99px;overflow:hidden;">
                            <div style="height:100%;width:${scorePercent}%;background:${progressColor};border-radius:99px;transition:width 1s cubic-bezier(0.4, 0, 0.2, 1);"></div>
                        </div>
                        ${breakdownHtml}
                    </div>

                    <div class="d-flex justify-content-between align-items-end mt-2 pt-3 border-top">
                        <div>
                            <small class="text-muted d-block text-uppercase" style="font-size: 0.65rem;letter-spacing:0.5px;">Salaire</small>
                            <span class="fw-bold text-success" style="font-size: 1.05rem;">${salaryDisplay}</span>
                        </div>
                        <div class="d-flex gap-2">
                            <button class="btn btn-outline-primary rounded-pill btn-sm px-3 fw-bold" onclick="viewJobDetail('${job.id}')">Voir</button>
                            <button id="apply-btn-${job.id}" class="btn rounded-pill btn-sm px-3 fw-bold text-white" style="background:linear-gradient(135deg,#6366f1,#8b5cf6);" onclick="applyToJob('${job.id}', '${(job.title||'').replace(/'/g, '')}', this)">Postuler</button>
                        </div>
                    </div>
                </div>
            `;
                jobsContainer.appendChild(col);
            });

            // Add button to re-upload
            const retryBtn = document.createElement('div');
            retryBtn.className = 'text-center mt-4';
            retryBtn.innerHTML = '<button class="btn btn-link text-muted" onclick="window.location.reload()">Analyser un autre CV</button>';
            jobsContainer.appendChild(retryBtn);
        }

        // ── Apply to Job ───────────────────────────────────────────
        window.applyToJob = async function(jobId, jobTitle, btn) {
            btn.disabled = true;
            btn.textContent = '...';

            const cvData = window._cvData || {};
            const payload = {
                job_id: jobId,
                name: cvData.name || null,
                email: cvData.email || null,
                experience_level: cvData.experience_level || null,
                skills: cvData.skills || [],
                phone: cvData.phone || ''
            };

            try {
                const res = await fetch(`${api.baseUrl}/apply/cv`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok && data.success) {
                    btn.textContent = 'Postule !';
                    btn.style.background = '#10b981';
                    btn.onclick = null;
                    // Show success toast
                    showApplyToast(data.job || jobTitle);
                } else {
                    btn.textContent = 'Erreur';
                    btn.style.background = '#ef4444';
                    setTimeout(() => { btn.textContent = 'Postuler'; btn.disabled = false; btn.style.background = 'linear-gradient(135deg,#6366f1,#8b5cf6)'; }, 2500);
                    alert('Erreur : ' + (data.error || 'Inconnue'));
                }
            } catch(e) {
                btn.textContent = 'Erreur';
                btn.style.background = '#ef4444';
                setTimeout(() => { btn.textContent = 'Postuler'; btn.disabled = false; btn.style.background = 'linear-gradient(135deg,#6366f1,#8b5cf6)'; }, 2500);
                alert('Erreur réseau : ' + e.message);
            }
        };

        function showApplyToast(jobTitle) {
            const toast = document.createElement('div');
            toast.style.cssText = 'position:fixed;bottom:28px;right:28px;z-index:9999;background:linear-gradient(135deg,#6366f1,#10b981);color:#fff;padding:16px 24px;border-radius:14px;box-shadow:0 8px 30px rgba(0,0,0,.18);font-weight:600;font-size:.93rem;display:flex;align-items:center;gap:12px;animation:slideUp .35s ease;';
            toast.innerHTML = `<i class="fas fa-check-circle" style="font-size:1.3rem;"></i><div><div>Candidature envoyée !</div><div style="font-weight:400;font-size:.8rem;opacity:.9;">Vous avez postulé pour : ${jobTitle}</div></div>`;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 4500);
        }

        // Modal Logic
        const modalElement = document.getElementById('jobModal');
        const modal = new bootstrap.Modal(modalElement);

        window.viewJobDetail = async function (id) {
            const modalBody = document.getElementById('jobModalBody');
            modalBody.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
            modal.show();

            try {
                const job = await api.getJob(id);

                // Company Info Block
                let websiteUrl = job.company_website;
                if (websiteUrl && !websiteUrl.startsWith('http')) {
                    websiteUrl = 'https://' + websiteUrl;
                }

                let companyInfo = '';
                if (job.company_description || job.company_sector || websiteUrl) {
                    companyInfo = `
                    <div class="mt-4 p-3 bg-light rounded border-start border-4 border-primary">
                        <h5 class="mb-3 text-primary"><i class="fas fa-building me-2"></i>À propos de l'entreprise</h5>
                        ${job.company_sector ? `<p class="mb-2"><strong>Secteur :</strong> ${job.company_sector}</p>` : ''}
                        ${job.company_description ? `<p class="mb-2 text-muted">${job.company_description}</p>` : ''}
                        ${websiteUrl ? `<p class="mb-0"><a href="${websiteUrl}" target="_blank" class="btn btn-sm btn-outline-primary">Visiter le site web</a></p>` : ''}
                    </div>
                `;
                }

                // Skills Block
                let skillsHtml = '';
                if (job.skills && job.skills.length > 0) {
                    skillsHtml = `
                    <div class="mt-4">
                        <h6 class="mb-3 text-secondary"><i class="fas fa-tools me-2"></i>Compétences requises</h6>
                        <div>
                            ${job.skills.map(skill => `<span class="badge bg-secondary me-2 mb-2 p-2">${skill}</span>`).join('')}
                        </div>
                    </div>
                    `;
                }

                modalBody.innerHTML = `
                <div class="d-flex justify-content-between align-items-start mb-4">
                    <div>
                        <h4 class="mb-1">${job.title}</h4>
                        <p class="text-muted mb-0"><i class="fas fa-building me-2"></i><strong>${job.company}</strong></p>
                        <div class="mt-2">
                           <span class="badge bg-light text-dark border me-2"><i class="fas fa-map-marker-alt me-1"></i>${job.location || 'Non spécifié'}</span>
                           <span class="badge bg-success text-white"><i class="fas fa-money-bill-wave me-1"></i>${job.salary ? job.salary + ' DH' : 'Non spécifié'}</span>
                        </div>
                    </div>
                </div>
                
                <div class="mb-4">
                     <h6 class="mb-2 text-secondary">Description du poste</h6>
                     <p style="white-space: pre-wrap;">${job.description || "Aucune description disponible."}</p>
                </div>

                ${skillsHtml}

                ${companyInfo}
                `;

            } catch (error) {
                modalBody.innerHTML = `<div class="alert alert-danger">Erreur impossible de charger les détails: ${error.message}</div>`;
            }
        };

        function setupLogout() {
            const btn = document.getElementById('logoutBtn');
            if (btn) {
                btn.onclick = async (e) => {
                    e.preventDefault();
                    await api.request('/auth/logout', 'POST');
                    window.location.href = 'login.html';
                };
            }
        }

        function setupNavigation(user) {
            if (window.applySidebarVisibility && user) {
                window.applySidebarVisibility(user.role);
            }
            const isAdmin = user && user.role === 'admin';
            const isRecruiter = user && user.role === 'recruiter';

            // Sidebar user info
            const sa = document.getElementById('sidebarAvatar');
            const sn = document.getElementById('sidebarName');
            const sr = document.getElementById('sidebarRole');
            const ui = document.getElementById('userInfo');
            if (sa) sa.textContent = (user.username || 'U').charAt(0).toUpperCase();
            if (sn) sn.textContent = user.username || '—';
            if (sr) sr.textContent = isAdmin ? 'Administrateur' : isRecruiter ? 'Recruteur' : 'Candidat';
            if (ui) ui.textContent = `${user.username} (${user.role})`;
        }

    }catch (globalErr) {
        alert("CRITICAL ERROR: " + globalErr.message);
        console.error(globalErr);
    }
});
