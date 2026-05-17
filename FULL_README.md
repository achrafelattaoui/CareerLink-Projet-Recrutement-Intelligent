# 🎯 JobMatch - Plateforme de Gestion des Candidats & Offres

Système complet de gestion de candidats et offres d'emploi avec interface web moderne et API REST.

## 📦 Structure du Projet

```
Projet_nosql/
├── backend/                    # API Flask + Base de données
│   ├── app.py                 # Application principale
│   ├── db.py                  # Drivers (Neo4j + Mock)
│   ├── routes.py              # Endpoints API
│   ├── requirements.txt        # Dépendances Python
│   ├── .env                   # Configuration
│   ├── check_db.py            # Test de connexion
│   └── test_api.py            # Suite de tests
│
├── frontend/                   # Interface web
│   ├── index.html             # Accueil
│   ├── candidates.html        # Candidats
│   ├── jobs.html             # Offres
│   ├── skills.html           # Compétences
│   ├── search.html           # Recherche
│   ├── api.js                # Client API
│   ├── styles.css            # Styles
│   └── [page].js             # Logique métier
│
├── API_DOCUMENTATION.md        # Docs API complète
├── PROJECT_README.md           # Guide backend
├── start-dev.ps1              # Script démarrage (PowerShell)
├── start-dev.sh               # Script démarrage (Bash)
└── README.md                  # Ce fichier
```

## 🚀 Installation Rapide

### 1. Cloner/Préparer le projet

```bash
cd c:\Users\USER\Projet_nosql
```

### 2. (Optionnel) Créer l'environnement virtuel

```bash
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r backend/requirements.txt
```

### 3. Démarrer l'application

**Option A : Via PowerShell (Windows)**
```powershell
.\start-dev.ps1
```

**Option B : Manuellement (2 terminaux)**

Terminal 1 - Backend:
```bash
cd backend
python app.py
```

Terminal 2 - Frontend:
```bash
cd frontend
python -m http.server 8080
```

### 4. Accéder à l'application

- **Frontend** : http://localhost:8080
- **Backend API** : http://localhost:5000
- **Documentation API** : http://localhost:5000 (page d'accueil)

## 📋 Fonctionnalités

### ✅ Candidats
- [x] Créer/Lire/Mettre à jour/Supprimer
- [x] Lister avec pagination
- [x] Ajouter compétences
- [x] Voir postulations
- [x] Détails complets

### ✅ Offres d'Emploi
- [x] CRUD complet
- [x] Gestion descriptions
- [x] Voir candidats postulés
- [x] Filtrage

### ✅ Compétences
- [x] Gestion des compétences
- [x] Assignation aux candidats
- [x] Associer aux offres

### ✅ Relation & Recherche
- [x] Postulation aux offres
- [x] Recherche unifiée
- [x] Filtrage avancé
- [x] Graphique de relations

### ✅ Interface
- [x] Tableau de bord
- [x] Responsive design
- [x] Modes light
- [x] Gestion des erreurs

## 🎨 Technologies

### Backend
- **Framework** : Flask 2.0+
- **DB** : Neo4j (graphe)
- **Python** : 3.8+
- **API** : REST JSON

### Frontend
- **HTML5** + **CSS3** + **JavaScript**
- **Bootstrap** 5 pour le design
- **Fetch API** pour les appels HTTP
- **Font Awesome** 6 pour les icônes

## 📊 API Endpoints

### Candidats
```
GET    /candidates              Lister tous
POST   /candidates/add          Ajouter
GET    /candidate/{id}          Récupérer
PUT    /candidate/{id}          Mettre à jour
DELETE /candidate/{id}          Supprimer
```

### Offres
```
GET    /jobs                    Lister tous
POST   /jobs/add               Ajouter
GET    /job/{id}               Récupérer
PUT    /job/{id}               Mettre à jour
DELETE /job/{id}               Supprimer
```

### Relations
```
POST   /apply                  Postuler
POST   /candidate/{id}/skills/add   Ajouter skill
GET    /candidate/{id}/skills   Voir skills
GET    /candidate/{id}/applications  Voir postulations
GET    /job/{id}/candidates    Voir candidats
```

### Autres
```
GET    /skills                 Lister compétences
POST   /skills/add            Ajouter compétence
GET    /search?q=term         Rechercher
GET    /health                Vérifier API
```

## ⚙️ Configuration

### Fichier .env (backend/)

```env
# Mode de base de données
DB_MODE=mock          # 'mock' pour développement, 'neo4j' pour prod

# Paramètres Neo4j (si DB_MODE=neo4j)
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password
NEO4J_DATABASE=neo4j

# Flask
FLASK_APP=app.py
FLASK_ENV=development
FLASK_RUN_PORT=5000
```

### Mode Mock vs Neo4j

**Mode Mock (développement rapide)**
- Données en mémoire
- Aucune DB externe
- Parfait pour tester
- Les données disparaissent au redémarrage

**Mode Neo4j (production)**
- Base de données graphe réelle
- Données persistantes
- Performance optimisée
- Requêtes Cypher natives

## 🧪 Tests

### Test complet de l'API
```bash
cd backend
python test_api.py
```

### Test de connexion DB
```bash
cd backend
python check_db.py
```

### Test via cURL
```bash
curl http://localhost:5000/health
curl http://localhost:5000/candidates
```

## 📱 Interface Utilisateur

### Pages disponibles

1. **Accueil (index.html)**
   - Tableau de bord avec statistiques
   - Actions rapides
   - Derniers candidats/offres

2. **Candidats (candidates.html)**
   - Liste complète
   - Formulaire CRUD
   - Détails et relations

3. **Offres (jobs.html)**
   - Gestion des offres
   - Candidats postulés
   - Édition simple

4. **Compétences (skills.html)**
   - Galerie de compétences
   - Ajout facile

5. **Recherche (search.html)**
   - Recherche globale
   - Filtres multiples

## 🔄 Flux de Données

```
┌─────────────────┐
│   Frontend      │ (HTML/CSS/JS - port 8080)
│  (Bootstrap)    │
└────────┬────────┘
         │ HTTP JSON
         ↓
┌─────────────────┐
│  Backend API    │ (Flask - port 5000)
│  (routes.py)    │
└────────┬────────┘
         │ Cypher/SQL
         ↓
┌─────────────────┐
│   Database      │ (Neo4j ou Mock)
│  (Graphe/Mem)   │
└─────────────────┘
```

## 🚀 Déploiement

### Production (avec Gunicorn)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 backend.app:create_app()
```

### Docker (optionnel)

```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .
RUN pip install -r backend/requirements.txt
CMD ["python", "backend/app.py"]
```

## 📚 Documentation

- **API Complète** : Voir [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- **Backend** : Voir [backend/README.md](backend/README.md)
- **Frontend** : Voir [frontend/README.md](frontend/README.md)

## 🐛 Dépannage

### "Cannot find module flask"
```bash
pip install -r backend/requirements.txt
```

### "Connection refused" (Neo4j)
- Vérifiez votre URI Neo4j dans `.env`
- Assurez-vous que Neo4j est en cours d'exécution

### Frontend ne se charge pas
- Vérifiez que le serveur HTTP est lancé sur le port 8080
- Ouvrez la console (F12) pour voir les erreurs

### Les données disparaissent
- C'est normal en mode mock. Passez en mode Neo4j pour la persistance.

## 🎯 Prochaines Étapes

- [x] API REST complète
- [x] Interface web responsive
- [x] Mode mock pour développement
- [ ] Authentification utilisateur
- [ ] Dashboard avancé avec graphiques
- [ ] Export PDF/CSV
- [ ] Notifications temps réel
- [ ] Mode dark
- [ ] Mobile app (React Native)

## 📄 Licence

MIT License

## 👤 Auteur

Projet NoSQL pour gestion des candidats - 2026

## 📞 Support

Pour toute question :
1. Consultez la documentation API
2. Vérifiez les logs (console backend/frontend)
3. Testez avec `curl` ou Postman

---

**Statut** : ✅ Prêt pour développement et test  
**Version** : 1.0.0  
**Dernière mise à jour** : Janvier 2026
