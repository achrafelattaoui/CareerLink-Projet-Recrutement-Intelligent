# API Documentation - Gestion des Candidats & Offres d'Emploi

## Vue d'ensemble

Cette API Flask permet de gérer :
- **Candidats** : Créer, lire, mettre à jour, supprimer
- **Offres d'emploi** : Créer, lire, mettre à jour, supprimer
- **Compétences** : Créer, lister
- **Relations** : Postulations, compétences des candidats
- **Recherche** : Trouver des candidats ou offres

## Configuration

### Environnement

```env
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=achraf2004
NEO4J_DATABASE=neo4j
DB_MODE=mock  # ou 'neo4j' pour une vrai base
FLASK_RUN_PORT=5000
```

### Lancement du serveur

```bash
cd backend
python app.py
```

L'API sera disponible à : `http://localhost:5000`

## Endpoints

### 🏥 Vérification

#### Health Check
```
GET /health
```

**Réponse (200):**
```json
{
  "status": "ok",
  "result": [{"ok": 1}]
}
```

---

### 👥 Candidats

#### Lister tous les candidats
```
GET /candidates
```

**Réponse (200):**
```json
{
  "count": 2,
  "candidates": [
    {"id": "cand1", "name": "Alice Dupont", "email": "alice@example.com"},
    {"id": "cand2", "name": "Bob Martin", "email": "bob@example.com"}
  ]
}
```

#### Ajouter un candidat
```
POST /candidates/add
Content-Type: application/json

{
  "name": "Charlie Brown",
  "email": "charlie@example.com",
  "phone": "+33612345678"
}
```

**Réponse (201):**
```json
{
  "success": true,
  "data": {
    "id": "uuid-generated",
    "name": "Charlie Brown"
  }
}
```

#### Récupérer un candidat
```
GET /candidate/{id}
```

**Réponse (200):**
```json
{
  "success": true,
  "data": {
    "id": "cand1",
    "name": "Alice Dupont",
    "email": "alice@example.com",
    "phone": "+33612345678"
  }
}
```

#### Mettre à jour un candidat
```
PUT /candidate/{id}
Content-Type: application/json

{
  "name": "Alice Martin",
  "email": "alice.martin@example.com",
  "phone": "+33698765432"
}
```

**Réponse (200):**
```json
{
  "success": true,
  "data": {
    "id": "cand1",
    "name": "Alice Martin"
  }
}
```

#### Supprimer un candidat
```
DELETE /candidate/{id}
```

**Réponse (200):**
```json
{
  "success": true,
  "message": "Candidat cand1 supprimé"
}
```

#### Récupérer les compétences d'un candidat
```
GET /candidate/{id}/skills
```

**Réponse (200):**
```json
{
  "candidate_id": "cand1",
  "count": 2,
  "skills": ["Python", "React"]
}
```

#### Ajouter une compétence à un candidat
```
POST /candidate/{id}/skills/add
Content-Type: application/json

{
  "skill_name": "Docker"
}
```

**Réponse (201):**
```json
{
  "success": true,
  "data": {
    "candidate": "Alice Dupont",
    "skill": "Docker"
  }
}
```

#### Récupérer les postulations d'un candidat
```
GET /candidate/{id}/applications
```

**Réponse (200):**
```json
{
  "candidate_id": "cand1",
  "count": 2,
  "applications": [
    {"id": "job1", "title": "Dev Python", "company": "TechCorp"},
    {"id": "job2", "title": "Dev Senior", "company": "BigCorp"}
  ]
}
```

---

### 💼 Offres d'Emploi

#### Lister toutes les offres
```
GET /jobs
```

**Réponse (200):**
```json
{
  "count": 2,
  "jobs": [
    {"id": "job1", "title": "Dev Python", "company": "TechCorp"},
    {"id": "job2", "title": "Dev Frontend", "company": "WebCorp"}
  ]
}
```

#### Ajouter une offre
```
POST /jobs/add
Content-Type: application/json

{
  "title": "Développeur Python",
  "description": "Recherche développeur Python senior",
  "company": "TechCorp",
  "salary": "50000"
}
```

**Réponse (201):**
```json
{
  "success": true,
  "data": {
    "id": "uuid-generated",
    "title": "Développeur Python"
  }
}
```

#### Récupérer une offre
```
GET /job/{id}
```

**Réponse (200):**
```json
{
  "success": true,
  "data": {
    "id": "job1",
    "title": "Dev Python",
    "description": "Senior developer needed",
    "company": "TechCorp",
    "salary": "50000"
  }
}
```

#### Mettre à jour une offre
```
PUT /job/{id}
Content-Type: application/json

{
  "title": "Senior Dev Python",
  "salary": "55000"
}
```

**Réponse (200):**
```json
{
  "success": true,
  "data": {
    "id": "job1",
    "title": "Senior Dev Python"
  }
}
```

#### Supprimer une offre
```
DELETE /job/{id}
```

**Réponse (200):**
```json
{
  "success": true,
  "message": "Offre job1 supprimée"
}
```

#### Récupérer les candidats pour une offre
```
GET /job/{id}/candidates
```

**Réponse (200):**
```json
{
  "job_id": "job1",
  "count": 2,
  "applicants": [
    {"id": "cand1", "name": "Alice", "email": "alice@example.com"},
    {"id": "cand2", "name": "Bob", "email": "bob@example.com"}
  ]
}
```

---

### 🎯 Compétences

#### Lister toutes les compétences
```
GET /skills
```

**Réponse (200):**
```json
{
  "count": 3,
  "skills": [
    {"id": "python", "name": "Python"},
    {"id": "react", "name": "React"},
    {"id": "nodejs", "name": "Node.js"}
  ]
}
```

#### Ajouter une compétence
```
POST /skills/add
Content-Type: application/json

{
  "name": "Docker"
}
```

**Réponse (201):**
```json
{
  "success": true,
  "data": {
    "name": "Docker"
  }
}
```

---

### 📝 Relations

#### Candidat postule pour une offre
```
POST /apply
Content-Type: application/json

{
  "candidate_id": "cand1",
  "job_id": "job1"
}
```

**Réponse (201):**
```json
{
  "success": true,
  "data": {
    "candidate": "Alice Dupont",
    "job": "Dev Python"
  }
}
```

---

### 🔍 Recherche

#### Rechercher des candidats/offres
```
GET /search?q=python&type=all
```

**Paramètres:**
- `q` (obligatoire) : Terme de recherche
- `type` (optionnel) : `all`, `candidates`, `jobs` (défaut: `all`)

**Réponse (200):**
```json
{
  "query": "python",
  "results": {
    "candidates": [
      {"id": "cand1", "name": "Alice Python Dev", "email": "alice@example.com"}
    ],
    "jobs": [
      {"id": "job1", "title": "Développeur Python", "company": "TechCorp"}
    ]
  }
}
```

---

## Exemples cURL

### Ajouter un candidat
```bash
curl -X POST http://localhost:5000/candidates/add \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@example.com","phone":"+33612345678"}'
```

### Ajouter une offre
```bash
curl -X POST http://localhost:5000/jobs/add \
  -H "Content-Type: application/json" \
  -d '{"title":"Dev Python","company":"TechCorp","salary":"50000"}'
```

### Lister les candidats
```bash
curl http://localhost:5000/candidates
```

### Récupérer un candidat
```bash
curl http://localhost:5000/candidate/cand1
```

### Mettre à jour un candidat
```bash
curl -X PUT http://localhost:5000/candidate/cand1 \
  -H "Content-Type: application/json" \
  -d '{"phone":"+33698765432"}'
```

### Candidat postule
```bash
curl -X POST http://localhost:5000/apply \
  -H "Content-Type: application/json" \
  -d '{"candidate_id":"cand1","job_id":"job1"}'
```

### Recherche
```bash
curl "http://localhost:5000/search?q=python"
```

---

## Codes de statut

| Code | Description |
|------|-------------|
| 200 | Succès |
| 201 | Créé avec succès |
| 400 | Mauvaise requête |
| 404 | Non trouvé |
| 500 | Erreur serveur |

---

## Mode de fonctionnement

### Mode MOCK (développement)
- Données stockées en mémoire
- Idéal pour tester sans Neo4j
- Les données disparaissent après redémarrage

### Mode Neo4j (production)
- Données persistan persistantes dans Neo4j
- Recommandé pour les données réelles

**Basculer entre les modes :** Modifiez `DB_MODE` dans `.env`

---

## Technologies

- **Flask** : Framework web
- **Neo4j** : Base de données graphe (optionnel)
- **Python 3.13** : Langage
- **python-dotenv** : Variables d'environnement
