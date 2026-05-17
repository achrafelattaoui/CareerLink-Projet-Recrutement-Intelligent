# Configuration Neo4j pour le Projet

## Étapes pour établir la connexion

### 1. Obtenir les paramètres de connexion Neo4j Aura

1. Accédez à votre console [Neo4j Aura](https://console.neo4j.io)
2. Sélectionnez votre instance
3. Cliquez sur "Details" ou "Connexion"
4. Vous verrez:
   - **Bolt URI**: Format `neo4j+s://xxxxx.databases.neo4j.io`
   - **Username**: `neo4j` (par défaut)
   - **Password**: Votre mot de passe (généralement défini lors de la création)

### 2. Mettre à jour le fichier `.env`

Remplacez les valeurs dans `backend/.env` par:

```
NEO4J_URI=neo4j+s://your-instance-id.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j
FLASK_APP=app.py
FLASK_ENV=development
FLASK_RUN_PORT=5000
```

### 3. Tester la connexion

Exécutez:
```bash
cd backend
python check_db.py
```

### 4. Démarrer l'application

```bash
python app.py
```

Accédez à:
- Health check: `http://localhost:5000/health`
- Get nodes: `http://localhost:5000/nodes`

## Structure de votre base de données

Nœuds:
- **Candidate**: Candidats
- **Candidate_Cv**: CV des candidats
- **Company**: Entreprises
- **Job**: Postes disponibles
- **Skill**: Compétences

Relations:
- **APPLIED_TO**: Candidat a postulé pour un emploi
- **HAS_SKILL**: Candidat a une compétence
- **POSTED**: Entreprise a publié un emploi
- **REQUIRES_SKILL**: Emploi nécessite une compétence

## Fichiers clés du projet

- `db.py`: Gestion de la connexion Neo4j
- `app.py`: Application Flask principale
- `routes.py`: Points d'accès (endpoints) API
- `check_db.py`: Script de test de connexion
- `.env`: Variables d'environnement

## Basculer entre mode MOCK et connexion réelle

Par défaut le projet peut démarrer en `MOCK` pour le développement local. Pour utiliser une vraie instance Neo4j (locale ou Aura), mettez à jour `backend/.env` :

```
DB_MODE=neo4j
NEO4J_URI=neo4j+s://<your-aura-id>.databases.neo4j.io   # ou bolt://127.0.0.1:7687 pour local
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j
```

Puis installez les dépendances et testez la connexion :

```bash
cd backend
python -m pip install -r requirements.txt
python check_db.py
```

Si la connexion échoue, le code basculera automatiquement en mode `MOCK` (voir `db.py`) ; vérifiez vos variables d'environnement et vos paramètres de réseau (firewall, accès Aura).

## Exemples de requêtes Cypher utiles

```cypher
# Tous les candidats
MATCH (c:Candidate) RETURN c LIMIT 10

# Compétences d'un candidat
MATCH (c:Candidate)-[:HAS_SKILL]->(s:Skill) RETURN c.name, s.name

# Offres d'emploi avec leurs compétences requises
MATCH (j:Job)-[:REQUIRES_SKILL]->(s:Skill) RETURN j.title, s.name

# Candidats ayant postulé
MATCH (c:Candidate)-[:APPLIED_TO]->(j:Job) RETURN c.name, j.title
```
