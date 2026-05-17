# Frontend - CareerLink

Interface web moderne pour gérer les candidats, offres d'emploi et compétences.

## 📁 Structure

```
frontend/
├── index.html          # Page d'accueil avec tableau de bord
├── candidates.html     # Gestion des candidats
├── jobs.html          # Gestion des offres d'emploi
├── skills.html        # Gestion des compétences
├── search.html        # Recherche avancée
├── api.js             # Client API (abstraction)
├── index.js           # Logique tableau de bord
├── candidates.js      # Logique candidats
├── jobs.js           # Logique offres
├── skills.js         # Logique compétences
├── search.js         # Logique recherche
└── styles.css        # Styles CSS
```

## 🚀 Démarrage

### Prérequis
- Backend Flask en cours d'exécution (http://localhost:5000)
- Un navigateur moderne

### Installation

1. Ouvrez simplement `index.html` dans un navigateur
   - Double-cliquez sur le fichier, ou
   - Utilisez un serveur local (optionnel)

2. **Avec serveur local (recommandé pour le développement):**
   ```bash
   # Avec Python 3
   python -m http.server 8080
   
   # Ou avec Node.js
   npx http-server
   ```
   
   Puis accédez à : `http://localhost:8080`

## 📚 Pages

### Accueil (index.html)
- Tableau de bord avec statistiques
- Candidats récents
- Offres récentes
- Accès rapide aux principales actions

### Candidats (candidates.html)
- Liste des candidats
- Ajouter un candidat
- Éditer un candidat
- Supprimer un candidat
- Voir détails (compétences, postulations)

### Offres (jobs.html)
- Liste des offres d'emploi
- Ajouter une offre
- Éditer une offre
- Supprimer une offre
- Voir candidats postulés

### Compétences (skills.html)
- Liste des compétences
- Ajouter une compétence
- Affichage en grille

### Recherche (search.html)
- Recherche unifiée
- Filtrage par type (candidats/offres)
- Résultats en temps réel

## 🛠️ Architecture

### API Client (api.js)
Abstraction pour tous les appels à l'API backend :

```javascript
// Exemples
await api.getCandidates()
await api.addCandidate({name, email, phone})
await api.getJobs()
await api.search(query, type)
```

### Structure HTML/CSS/JS
- **HTML** : Structure et layout Bootstrap
- **CSS** : Styles modernes et responsifs
- **JS** : Logique métier et appels API

## 🎨 Design

- **Couleurs** : Gradient moderne (bleu, rose, cyan)
- **Typographie** : Segoe UI, propre et lisible
- **Icons** : Font Awesome 6
- **Layout** : Bootstrap 5, responsive

## ⚙️ Configuration

Modifier l'URL de l'API dans `api.js` :

```javascript
const API_URL = 'http://localhost:5000'; // Changez si nécessaire
```

## 🔄 Flux de données

```
Frontend HTML/JS
       ↓
   api.js (client HTTP)
       ↓
Backend Flask (localhost:5000)
       ↓
Base de données (Neo4j ou Mock)
```

## 📱 Responsivité

- ✓ Desktop
- ✓ Tablet
- ✓ Mobile

Tous les éléments s'adaptent à la taille de l'écran.

## 🚨 Gestion des erreurs

- Messages d'alerte pour chaque action
- Auto-masquage après 4 secondes
- Validation des formulaires
- Gestion des exceptions API

## 🔒 Sécurité

- Échappement HTML pour prévenir XSS
- Validation côté client
- Pas de stockage de données sensibles

## 🎯 Prochaines évolutions possibles

- [ ] Authentification utilisateur
- [ ] Graphiques et statistiques avancées
- [ ] Export en PDF/CSV
- [ ] Notifications en temps réel
- [ ] Mode dark
- [ ] Sauvegarde locale (LocalStorage)
- [ ] Pagination pour les grandes listes
- [ ] Filtrage avancé

## 📞 Support

Pour plus d'informations, consultez :
- Documentation API : `/API_DOCUMENTATION.md`
- Backend README : `/PROJECT_README.md`

---

**Version:** 1.0  
**Framework:** Bootstrap 5, Vanilla JS  
**Icons:** Font Awesome 6  
**License:** MIT
