# 🎯 Projet NoSQL - Gestion des Candidats & Offres d'Emploi

## 📋 Vue d'ensemble

API Flask complète pour gérer une base de données graphe (Neo4j) avec :
- **Candidats** : Profils, expérience, compétences
- **Offres d'emploi** : Postes disponibles, salaires
- **Compétences** : Base de compétences réutilisables
- **Relations** : Postulations, compétences des candidats

## 🚀 Démarrage rapide

### Installation

```bash
# 1. Cloner/accéder au projet
cd c:\Users\USER\Projet_nosql

# 2. Créer l'environnement virtuel (déjà fait)
python -m venv .venv

# 3. Activer le venv
.\.venv\Scripts\Activate

# 4. Installer les dépendances
pip install -r backend/requirements.txt
```

### Lancer l'application

```bash
cd backend
python app.py
```

L'API démarre sur : **http://localhost:5000**

### Tester l'API

**Option 1 : Via un script de test**
```bash
python test_api.py
```

**Option 2 : Via cURL**
```bash
curl http://localhost:5000/health
curl http://localhost:5000/candidates
```

**Option 3 : Via le navigateur**
Ouvrez `http://localhost:5000` pour la documentation interactive

## 📁 Structure du projet

```
Projet_nosql/
├── backend/
│   ├── app.py              # Application Flask principale
│   ├── db.py               # Drivers (Neo4j + Mock)
│   ├── routes.py           # Endpoints API
│   ├── requirements.txt     # Dépendances
│   ├── .env                # Configuration (URI, user, password)
│   ├── check_db.py         # Script de vérification DB
│   └── test_api.py         # Suite de tests complète
├── API_DOCUMENTATION.md    # Documentation détaillée
├── README.md               # Ce fichier
└── .venv/                  # Environnement virtuel
```

## ⚙️ Configuration

### Fichier `.env`

```env
# Mode: 'mock' pour développement sans Neo4j, 'neo4j' pour la vraie base
DB_MODE=mock

# Paramètres Neo4j (pour mode neo4j)
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# Flask
FLASK_APP=app.py
FLASK_ENV=development
FLASK_RUN_PORT=5000
```

## 📚 Endpoints principaux

### 👥 Candidats
- `GET /candidates` - Lister tous
- `POST /candidates/add` - Ajouter nouveau
- `GET /candidate/{id}` - Récupérer
- `PUT /candidate/{id}` - Mettre à jour
- `DELETE /candidate/{id}` - Supprimer
- `GET /candidate/{id}/skills` - Compétences
- `GET /candidate/{id}/applications` - Postulations

### 💼 Offres d'emploi
- `GET /jobs` - Lister tous
- `POST /jobs/add` - Ajouter nouveau
- `GET /job/{id}` - Récupérer
- `PUT /job/{id}` - Mettre à jour
- `DELETE /job/{id}` - Supprimer
- `GET /job/{id}/candidates` - Candidats postulés

### 🎯 Compétences & Relations
- `GET /skills` - Lister compétences
- `POST /skills/add` - Ajouter compétence
- `POST /apply` - Candidat postule
- `POST /candidate/{id}/skills/add` - Ajouter skill au candidat
- `GET /search?q=python` - Recherche

### 🏥 Utilitaires
- `GET /health` - Vérification connexion
- `GET /` - Documentation interactive

## 🔄 Mode de fonctionnement

### 1️⃣ Mode MOCK (Développement - Défaut)
```env
DB_MODE=mock
```
- Données en mémoire
- Aucune dépendance Neo4j requise
- Parfait pour tester la logique
- Les données disparaissent au redémarrage

### 2️⃣ Mode Neo4j (Production)
```env
DB_MODE=neo4j
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
```
- Connexion à une vraie base Neo4j
- Données persistantes
- Requêtes Cypher réelles

## 📝 Exemples d'utilisation

### Ajouter un candidat
```bash
curl -X POST http://localhost:5000/candidates/add \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Martin",
    "email": "alice@example.com",
    "phone": "+33612345678"
  }'
```

### Ajouter une offre
```bash
curl -X POST http://localhost:5000/jobs/add \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Développeur Python",
    "company": "TechCorp",
    "description": "Recherche dev Python senior",
    "salary": "50000"
  }'
```

### Candidat postule
```bash
curl -X POST http://localhost:5000/apply \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_id": "cand1",
    "job_id": "job1"
  }'
```

### Recherche
```bash
curl "http://localhost:5000/search?q=python&type=jobs"
```

## 🧪 Tester l'API

### Script de test complet
```bash
python backend/test_api.py
```

Exécute tous les CRUD + relations + recherche

### Tests individuels
```bash
# Vérifier la connexion
curl http://localhost:5000/health

# Lister les candidats
curl http://localhost:5000/candidates

# Lister les offres
curl http://localhost:5000/jobs
```

## 🔗 Intégration Neo4j

Quand vous avez un vrai Neo4j Aura ou local :

1. Mettez à jour `.env`:
```env
DB_MODE=neo4j
NEO4J_URI=neo4j+s://your-id.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
```

2. Relancez l'application - elle basculera automatiquement vers Neo4j

## 📦 Dépendances

- **Flask** 2.0+ - Framework web
- **neo4j** 5.0+ - Driver Neo4j
- **python-dotenv** 1.0+ - Gestion des variables
- **Python** 3.8+

## 🛠️ Développement

### Ajouter un nouvel endpoint

1. Créez la fonction dans `routes.py`
2. Marquez avec le décorateur `@bp.route(...)`
3. Implémentez la requête Cypher (ou mock equivalent)
4. Testez avec `curl` ou le script `test_api.py`

Exemple :
```python
@bp.route("/candidates/senior", methods=["GET"])
def get_senior_candidates():
    driver = get_driver()
    cypher = "MATCH (c:Candidate) WHERE c.years_exp > 5 RETURN c"
    return jsonify(driver.run_query(cypher))
```

## 📖 Documentation

Pour la documentation détaillée : [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

## 🐛 Dépannage

### "Driver not initialized"
→ Vérifiez que `init_driver()` est appelé dans `app.py`

### "Connection refused" (mode neo4j)
→ Vérifiez votre `NEO4J_URI` et les identifiants dans `.env`

### "Module not found" 
→ Activez le venv : `.\.venv\Scripts\Activate`

### Données disparues après redémarrage (mode mock)
→ C'est normal ! Mode mock = données en mémoire. Passez à Neo4j pour la persistance.

## 📞 Support

Pour plus d'informations sur les endpoints, consultez :
- La page d'accueil interactive : `http://localhost:5000`
- Le fichier de documentation : [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- Le script de test : `backend/test_api.py`

---

**Version:** 1.0  
**Mode:** Développement (Mock par défaut)  
**Prêt pour production:** ✓ (avec Neo4j configuré)
