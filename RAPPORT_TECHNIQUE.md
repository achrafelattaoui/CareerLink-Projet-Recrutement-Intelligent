# Rapport Technique : Projet CareerLink (JobMatch)

## 1. Introduction
Ce projet est une plateforme de recrutement intelligente ("CareerLink") qui connecte les candidats, les entreprises et les offres d'emploi. La particularité de l'application réside dans l'utilisation d'une **base de données orientée graphe (Neo4j)** pour modéliser les relations complexes entre les compétences, les profils et les offres, permettant ainsi des fonctionnalités avancées comme le "Smart CV" (recommandation automatique).

## 2. Architecture Technique

L'application suit une architecture **Client-Serveur** classique :

*   **Frontend (Client)** : Interface utilisateur web.
*   **Backend (Serveur)** : API RESTful qui traite la logique métier.
*   **Base de Données** : Neo4j pour le stockage des données structurées en graphe.

### Diagramme Simplifié
`[Navigateur Web] <---> [API Flask (Python)] <---> [Neo4j Database]`

## 3. Technologies Utilisées

### Backend
*   **Langage** : Python 3.x
*   **Framework Web** : Flask (léger et flexible pour créer des API REST).
*   **Pilote de Base de Données** : `neo4j` (Driver officiel Python pour Neo4j).
*   **Traitement PDF** : `pypdf` (pour l'extraction de texte des CVs).
*   **Authentification** : `flask-login` (gestion de session).

### Frontend
*   **Structure** : HTML5 Standard.
*   **Style** : Bootstrap 5 (Framework CSS pour le responsive design) + CSS personnalisé.
*   **Logique** : JavaScript (Vanilla ES6+).
*   **Communication** : `fetch` API pour consommer l'API Flask.

### Base de Données
*   **SGBD** : Neo4j (Graph Database).
*   **Langage de Requête** : Cypher (équivalent du SQL pour les graphes).

## 4. Connexion et Modélisation Neo4j

### Connexion
La connexion s'effectue via le protocole **Bolt** (binaire, haute performance).
Le fichier `backend/db.py` gère l'initialisation du driver :
```python
# Exemple de configuration (backend/.env)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=votre_mot_de_passe
```

### Modèle de Données (Graphe)
Au lieu de tables, nous utilisons des **Nœuds** (Nodes) et des **Relations** (Relationships) :

*   **Nœuds Principaux** :
    *   `:Candidate` (Candidats inscrits)
    *   `:Company` (Entreprises)
    *   `:Job` (Offres d'emploi)
    *   `:Skill` (Compétences techniques, ex: "Python", "React")
    *   `:User` (Comptes de connexion)

*   **Relations Clés** :
    *   `(:Company)-[:POSTED]->(:Job)` : Une entreprise publie une offre.
    *   `(:Job)-[:REQUIRES]->(:Skill)` : Une offre requiert une compétence.
    *   `(:Candidate)-[:HAS_SKILL]->(:Skill)` (Potentiel) : Un candidat possède une compétence.
    *   `(:Candidate)-[:APPLIED_TO]->(:Job)` : Candidature.

## 5. Fonctionnalités Clés et API

### Smart CV (Logique de Recommandation)
Le moteur de recommandation (`POST /recommendations/upload-cv`) fonctionne ainsi :
1.  **Extraction** : Le backend reçoit un PDF, extrait le texte brut via `pypdf`.
2.  **Nettoyage** : Le texte est nettoyé (minuscules, suppression caractères spéciaux sauf +, #).
3.  **Détection** : L'algorithme recherche les compétences existantes en base (ex: "Java", "SQL") dans le texte du CV via une correspondance exacte (pour éviter les faux positifs comme "Go" dans "Google").
4.  **Matching (Scoring)** :
    *   Une requête Cypher compare les compétences détectées avec celles requises par chaque offre `:Job`.
    *   Score pondéré : Les correspondances de compétences DB valent plus de points que les simples correspondances de texte.
5.  **Résultat** : Une liste d'offres triées par pertinence est renvoyée.

### API Routes Principales
*   `GET /jobs` : Liste des offres.
*   `GET /candidates` : Liste des candidats (Admin).
*   `GET /companies` : Liste des entreprises.
*   `GET /stats` : Statistiques globales du graphe.
*   `POST /auth/login` : Authentification utilisateur.

## 6. Conclusion
Ce projet démontre la puissance des bases de données orientées graphe pour les problèmes de "Matching". Contrairement à une base SQL relationnelle qui nécessiterait de nombreuses jointures coûteuses (`JOIN`), Neo4j permet de traverser naturellement les relations (Candidat -> Compétence <- Offre) pour trouver instantanément les meilleures correspondances.