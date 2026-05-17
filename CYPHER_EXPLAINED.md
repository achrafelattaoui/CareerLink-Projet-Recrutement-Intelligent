# Documentation des Requêtes Cypher (Neo4j)

Ce document répertorie les requêtes Cypher utilisées dans le projet **CareerLink**, classées par fonctionnalité.

---

## 1. Authentification et Gestion Utilisateurs
**Fichier :** `backend/db.py`

### Récupération d'un Utilisateur
Utilisée lors du login pour trouver un utilisateur par Email ou Nom d'utilisateur.
```cypher
MATCH (u:User) 
WHERE u.email = $identifier OR u.username = $identifier 
RETURN u
```

### Inscription d'un Utilisateur
Création du nœud `User` et, si c'est un candidat, création du nœud `Candidate` associé.
```cypher
CREATE (u:User {
    id: randomUUID(),
    username: $username,
    email: $email,
    password_hash: $pw,
    role: $role,
    created_at: timestamp()
})
RETURN u
```
Et pour le profil candidat :
```cypher
CREATE (c:Candidate {
    id: randomUUID(),
    cv_id: randomUUID(),
    full_name: $username,
    name: $username, 
    email: $email,
    created_at: timestamp()
})
```

---

## 2. Gestion des Candidats
**Fichier :** `backend/routes.py`

### Lister les Candidats
Récupère tous les candidats avec leurs informations principales.
```cypher
MATCH (c)
WHERE c:Candidate OR c:Candidate_Cv
AND COALESCE(c.full_name, c.name) IS NOT NULL
WITH toLower(trim(COALESCE(c.full_name, c.name))) as normalized_name, collect(c)[0] as representative
RETURN toString(COALESCE(representative.cv_id, representative.id)) as id, 
       COALESCE(representative.full_name, representative.name) as name,
       representative.email as email, 
       representative.phone as phone,
       representative.current_title as current_title,
       representative.location as location
ORDER BY name ASC
LIMIT 100
```

### Supprimer un Candidat
Supprime le candidat et son compte utilisateur associé.
```cypher
MATCH (c:Candidate)
WHERE c.id = $id OR c.cv_id = $id OR toString(c.cv_id) = $id

OPTIONAL MATCH (u:User) WHERE u.email = c.email

WITH c, u, COALESCE(c.cv_id, c.id) as deletedId
DETACH DELETE c, u
RETURN deletedId as id
```

---

## 3. Gestion des Offres d'Emploi (Jobs)
**Fichier :** `backend/routes.py`

### Ajouter une Offre
Crée une offre et la lie à son entreprise via la relation `POSTED`.
```cypher
MERGE (j:Job { job_id: randomUUID() })
SET j.title = $title,
    j.job_description = $description,
    j.company_name_text = $company,
    j.salary_min = $salary,
    j.created_at = timestamp()
WITH j
OPTIONAL MATCH (c:Company)
WHERE toLower(c.company_name) = toLower($company)
FOREACH (ignoreMe IN CASE WHEN c IS NOT NULL THEN [1] ELSE [] END |
    MERGE (c)-[:POSTED]->(j)
)
RETURN j.job_id as id, j.title as title
```

### Détails d'une Offre
Récupère les détails de l'offre, l'entreprise liée et les compétences requises.
```cypher
MATCH (j:Job)
WHERE toString(j.id) = $id OR toString(j.job_id) = $id
OPTIONAL MATCH (comp:Company)-[:POSTED]->(j)
OPTIONAL MATCH (j)-[:REQUIRES|REQUIRES_SKILL]->(s:Skill)
RETURN COALESCE(j.job_id, j.id) as id, j.title as title, 
       COALESCE(j.job_description, j.description) as description, 
       COALESCE(comp.company_name, j.company_name_text, j.company) as company, 
       j.salary_min as salary, j.location as location,
       collect(s.skill_name) as skills
```

---

## 4. Smart CV : Algorithme de Recommandation
**Fichier :** `backend/routes.py`
**Fonction :** `upload_cv_recommendations`

C'est la requête la plus complexe. Elle calcule un score de pertinence entre les compétences détectées dans le CV (`$skills`) et les offres d'emploi.

```cypher
MATCH (j:Job)
OPTIONAL MATCH (comp:Company)-[:POSTED]->(j)
OPTIONAL MATCH (j)-[:REQUIRES|REQUIRES_SKILL]->(s:Skill)

WITH j, comp, collect(toLower(s.skill_name)) as job_linked_skills,
     toLower(toString(coalesce(j.title, '')) + ' ' + 
     toString(coalesce(j.job_description, j.description, ''))) as job_text

// Tokenisation du texte de l'offre
WITH j, comp, job_linked_skills, job_text,
     split(job_text, ' ') as job_tokens
     
// Calcul du Score
// $skills contient les compétences extraites du PDF
WITH j, comp, 
     // Points si la compétence est explicitement liée dans le graphe (relation REQUIRES)
     size([skill IN $skills WHERE skill IN job_linked_skills]) as db_skill_matches,
     // Points si la compétence est mentionnée dans le texte de l'offre
     size([skill IN $skills WHERE job_text =~ ('(?i).*\\b' + skill + '\\b.*')]) as text_skill_matches,
     // Points si des mots clés simples correspondent
     size([word IN $tokens WHERE job_text CONTAINS word]) as text_token_matches

// Score Pondéré : Les relations DB valent plus que le texte brut
WITH j, comp, 
     (db_skill_matches * 10) + (text_skill_matches * 5) as skill_score,
     text_token_matches as text_score

// Priorité au score de compétences
WITH j, comp, skill_score, text_score,
     CASE WHEN size($skills) > 0 THEN skill_score ELSE text_score END as final_score

WHERE final_score > 0

// Déduplication et Tri
WITH j.title as title, 
     COALESCE(comp.company_name, j.company_name_text) as company, 
     collect(j)[0] as j, 
     max(final_score) as score

RETURN DISTINCT toString(COALESCE(j.job_id, j.id)) as id, 
       title, 
       company,
       j.location as location,
       j.salary_min as salary,
       score
ORDER BY score DESC
LIMIT 50
```

---

## 5. Analytics (Tendances)
**Fichier :** `backend/db.py`

### Top Compétences (Offre)
Les compétences les plus possédées par les candidats.
```cypher
MATCH (s:Skill)<-[:HAS_SKILL]-(c:Candidate)
RETURN s.name as skill, count(c) as count
ORDER BY count DESC LIMIT 8
```

### Hub Skills (Demande)
Les compétences qui relient le plus de candidats aux entreprises (Centralité).
```cypher
MATCH (comp:Company)-[:POSTED]->(j:Job)<-[:APPLIED_TO]-(c:Candidate)-[:HAS_SKILL]->(s:Skill)
RETURN s.name as skill, count(DISTINCT comp) as companies, count(DISTINCT j) as jobs
ORDER BY companies DESC, jobs DESC LIMIT 8
```
