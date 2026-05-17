# Besoins du Projet CareerLink

Ce document recense les exigences fonctionnelles et non fonctionnelles du projet CareerLink (JobMatch).

## 1. Besoins Fonctionnels
Ce que le système doit faire.

### 1.1 Gestion des Utilisateurs
*   **Inscription** : Permettre aux utilisateurs de créer un compte (Candidat ou Administrateur).
*   **Authentification** : Connexion sécurisée via Email et Mot de passe.
*   **Gestion de Session** : Maintien de la connexion (Login/Logout).
*   **Rôles** : Distinction entre les droits d'accès "Admin" et "User".

### 1.2 Gestion du Profil Candidat
*   **Candidature** : Possibilité pour un candidat de postuler à une offre.
*   **Visualisation** : Consultation de son propre profil et des offres postulées.

### 1.3 Gestion des Offres (Administrateur)
*   **Ajout d'Offre** : Création d'une nouvelle offre d'emploi avec titre, description, salaire, localisation et compétences requises.
*   **Modification/Suppression** : Mise à jour ou retrait d'une offre existante.
*   **Association Entreprise** : Lier une offre à une entreprise spécifique.

### 1.4 Module "Smart CV" (Recommandation)
*   **Upload de CV** : Le système doit accepter les fichiers PDF.
*   **Analyse Automatique** : Extraction du texte et détection des compétences techniques (ex: Python, SQL) dans le CV.
*   **Recommandation** : Le système doit proposer une liste d'offres d'emploi triées par pertinence (Matching) en comparant les compétences du CV avec celles requises par les offres.

### 1.5 Recherche et Consultation
*   **Catalogue** : Affichage de la liste des offres et des entreprises.
*   **Recherche Avancée** : Filtrage des offres par mots-clés ou localisation.
*   **Statistiques (Analytics)** : Affichage des tendances du marché (Top compétences demandées).

---

## 2. Besoins Non Fonctionnels (Qualité de Service)
Comment le système doit se comporter.

### 2.1 Performance
*   **Rapidité de Matching** : L'algorithme de recommandation doit retourner des résultats en moins de 2 secondes, même avec un grand volume de données, grâce à l'utilisation de Neo4j (Graph Database).
*   **Fluidité** : L'interface utilisateur doit être réactive.

### 2.2 Sécurité
*   **Protection des Données** : Les mots de passe doivent être hachés (cryptés) avant stockage (utilisation de PBKDF2 via Werkzeug sur le backend).
*   **Contrôle d'Accès** : Les routes sensibles (ex: suppression de candidat) doivent être protégées et accessibles uniquement aux Administrateurs.

### 2.3 Ergonomie et Usabilité
*   **Interface Responsive** : L'application doit être utilisable sur mobile et ordinateur (Bootstrap).
*   **Simplicité** : Le processus d'upload de CV doit se faire en un minimum de clics ("One-click recommendation").

### 2.4 Fiabilité et Robustesse
*   **Intégrité des Données** : Utilisation de transactions ACID (via Neo4j) pour garantir que les données ne sont pas corrompues lors des écritures (ex: création simultanée User + Candidate).
*   **Gestion des Erreurs** : Le serveur doit renvoyer des messages d'erreur clairs (ex: "Format PDF uniquement") plutôt que de planter.

### 2.5 Maintenabilité
*   **Architecture Modulaire** : Séparation claire entre le Frontend (HTML/JS), le Backend (Flask) et la Base de Données (Neo4j).
*   **Code Documenté** : Le code source doit être commenté (Docstrings Python).
