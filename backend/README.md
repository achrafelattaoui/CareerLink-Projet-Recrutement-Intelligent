# Backend Flask avec Neo4j

Ce projet est une API Flask qui se connecte à une base de données Neo4j pour gérer des candidats, des offres d'emploi et des compétences.

## Prérequis

- Python 3.8+
- Une instance Neo4j accessible (localement ou distante)

## Installation

1. Créez un environnement virtuel puis activez-le :

```bash
python -m venv venv
# PowerShell
venv\Scripts\Activate.ps1
# ou cmd
venv\Scripts\activate.bat
```

2. Installez les dépendances :

```bash
pip install -r requirements.txt
```

## Configuration

- Mettez à jour le fichier `.env` avec vos paramètres Neo4j :

```
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j
FLASK_APP=app.py
FLASK_ENV=development
FLASK_RUN_PORT=5000
```

## Exécution

```bash
# depuis le dossier backend
python app.py
```

## Endpoints API

### Health & Info

- **GET** `/health` - Vérifier la connexion à la base de données

### Candidats

- **GET** `/candidates` - Récupérer tous les candidats
- **POST** `/candidates/add` - Ajouter un nouveau candidat
  ```json
  {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+33612345678"
  }
  ```

### Offres d'emploi

- **GET** `/jobs` - Récupérer toutes les offres
- **POST** `/jobs/add` - Ajouter une nouvelle offre
  ```json
  {
    "title": "Développeur Python",
    "description": "Nous cherchons un dev Python",
    "company": "TechCorp",
    "salary": "45000"
  }
  ```

### Compétences

- **GET** `/skills` - Récupérer toutes les compétences
- **POST** `/skills/add` - Ajouter une compétence
  ```json
  {
    "name": "Python"
  }
  ```

### Relations

- **POST** `/apply` - Candidat postule pour un emploi
  ```json
  {
    "candidate_id": "uuid-du-candidat",
    "job_id": "uuid-de-l-offre"
  }
  ```

- **POST** `/candidate/<candidate_id>/skills/add` - Ajouter une compétence à un candidat
  ```json
  {
    "skill_name": "Python"
  }
  ```

### Nœuds génériques

- **GET** `/nodes?label=Candidate&limit=10` - Récupérer des nœuds filtrés par label

## Exemples avec cURL

```bash
# Ajouter un candidat
curl -X POST http://localhost:5000/candidates/add \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@example.com"}'

# Ajouter une offre
curl -X POST http://localhost:5000/jobs/add \
  -H "Content-Type: application/json" \
  -d '{"title":"Dev Node.js","company":"WebCorp"}'

# Ajouter une compétence
curl -X POST http://localhost:5000/skills/add \
  -H "Content-Type: application/json" \
  -d '{"name":"Node.js"}'

# Vérifier la connexion
curl http://localhost:5000/health
```

Remarques

- Le helper `db.py` initialise le driver Neo4j à partir des variables d'environnement et expose `run_query()`.
- Adaptez la sérialisation des nœuds si vous avez des types complexes dans les propriétés.
