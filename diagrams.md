# Diagrammes du Projet — Recruiter Dashboard (Neo4j)

---

## 1. Diagramme de Cas d'Utilisation (Use Case)

```plantuml
@startuml
left to right direction
skinparam packageStyle rectangle
skinparam actorStyle awesome

actor "👤 Candidat" as C
actor "💼 Recruteur" as R
actor "🔧 Administrateur" as A

rectangle "🖥️ Système — Recruiter Dashboard" {
    
    package "Authentification" {
        usecase "Se connecter" as UC1
        usecase "Se déconnecter" as UC2
    }

    package "Espace Candidat" {
        usecase "Consulter son profil CV" as UC3
        usecase "Smart CV — Analyse NLP du CV" as UC4
        usecase "Voir les offres recommandées" as UC5
        usecase "Postuler à une offre" as UC6
        usecase "Rechercher des offres" as UC7
    }

    package "Espace Recruteur" {
        usecase "Gérer les offres d'emploi (CRUD)" as UC8
        usecase "Voir les candidats de son entreprise" as UC9
        usecase "Smart Sourcing — Trouver des candidats" as UC10
        usecase "Voir le tableau de bord recruteur" as UC11
        usecase "Consulter les statistiques" as UC12
    }

    package "Espace Administrateur" {
        usecase "Gérer tous les candidats (CRUD)" as UC13
        usecase "Gérer toutes les entreprises (CRUD)" as UC14
        usecase "Gérer toutes les offres (CRUD)" as UC15
        usecase "Tableau de bord global" as UC16
        usecase "Recherche globale" as UC17
        usecase "Voir les analytics" as UC18
    }
}

C --> UC1
C --> UC2
C --> UC3
C --> UC4
C --> UC5
C --> UC6
C --> UC7

R --> UC1
R --> UC2
R --> UC8
R --> UC9
R --> UC10
R --> UC11
R --> UC12

A --> UC1
A --> UC2
A --> UC13
A --> UC14
A --> UC15
A --> UC16
A --> UC17
A --> UC18

' --- Relations Include / Extend ---
UC5 ..> UC4 : <<include>>
UC4 .> UC3 : <<extend>>

UC10 .> UC8 : <<extend>>
UC12 .> UC11 : <<extend>>

UC3 ..> UC1 : <<include>>
UC8 ..> UC1 : <<include>>
UC16 ..> UC1 : <<include>>

@enduml
```

---

## 2. Diagramme du Système de Scoring (Smart Sourcing)

```mermaid
flowchart TD
    START(["📋 Description du Poste\n+ Titre du poste"])

    subgraph STEP1["Étape 1 — Prétraitement NLP"]
        A1["SpaCy : Tokenisation & Lemmatisation"]
        A2["Extraction des Entités nommées\n(ORG, PRODUCT, GPE...)"]
        A3["Extraction des Noun Chunks"]
    end

    subgraph STEP2["Étape 2 — Détection des Compétences"]
        B1["Requête Neo4j : MATCH (s:Skill)"]
        B2["Liste de compétences\n(DB + 40 compétences fallback)"]
        B3["Correspondance exacte dans\nle texte du poste"]
        B4["detected_skills = liste finale"]
    end

    subgraph STEP3["Étape 3 — Récupération Candidats (Neo4j)"]
        C1["MATCH (c:Candidate) + compétences liées"]
        C2["Calcul graph_score\n(db_skill_matches × 12)\n+ (text_skill_matches × 6)"]
        C3["Profil texte enrichi\n(titre + résumé + éducation)"]
    end

    subgraph STEP4["Étape 4 — TF-IDF + Cosine Similarity"]
        D1["TF-IDF Vectorizer\n(bigrammes, 5000 features)"]
        D2["Vecteur du Poste vs Vecteurs Candidats"]
        D3["cos_scores = Cosine Similarity"]
    end

    subgraph STEP5["Étape 5 — Score Hybride"]
        E1["NLP Score\n= raw_tfidf × 3.5\n(boosted, capped à 1.0)"]
        E2["Graph Score\n= graph_score / (skill_count × 12)\n(normalisé à 1.0)"]
        E3["Bonus Séniorité\n= 0.1 si match\n= 0.05 si 'any'"]
        E4["Hybrid\n= 45%×NLP + 45%×Graph + Bonus"]
    end

    subgraph STEP6["Étape 6 — Score Final Logique"]
        F1["logical_score\n= √hybrid × 0.96 + hybrid×0.04\n(capped à 0.99)"]
        F2{{"Seuils de Label"}}
        F3["✅ Excellent Match\n≥ 75%"]
        F4["🔵 Bon profil\n≥ 45%"]
        F5["🟡 Match Possible\n< 45%"]
    end

    RESULT(["🎯 Top 30 Candidats\ntriés par score_percent DESC"])

    START --> STEP1
    A1 --> A2 --> A3
    STEP1 --> STEP2
    B1 --> B2 --> B3 --> B4
    STEP2 --> STEP3
    B4 --> C2
    C1 --> C2 --> C3
    STEP3 --> STEP4
    C3 --> D1
    D1 --> D2 --> D3
    STEP4 --> STEP5
    D3 --> E1
    C2 --> E2
    E1 & E2 & E3 --> E4
    STEP5 --> STEP6
    E4 --> F1 --> F2
    F2 --> F3
    F2 --> F4
    F2 --> F5
    STEP6 --> RESULT

    %% Styling
    style START fill:#6366f1,color:white,font-weight:bold
    style RESULT fill:#059669,color:white,font-weight:bold
    style STEP1 fill:#f5f3ff,stroke:#8b5cf6
    style STEP2 fill:#ecfdf5,stroke:#10b981
    style STEP3 fill:#eff6ff,stroke:#3b82f6
    style STEP4 fill:#fff7ed,stroke:#f97316
    style STEP5 fill:#fdf4ff,stroke:#d946ef
    style STEP6 fill:#f0fdf4,stroke:#22c55e
    style F3 fill:#dcfce7,stroke:#16a34a,color:#14532d
    style F4 fill:#dbeafe,stroke:#2563eb,color:#1e3a8a
    style F5 fill:#fef9c3,stroke:#ca8a04,color:#713f12
```

---

## Résumé des Poids du Score Hybride

| Composante | Méthode | Poids |
|---|---|---|
| **NLP Sémantique** | TF-IDF Cosine × 3.5 (boost) | **45%** |
| **Graphe Neo4j** | Compétences matchées / Total requis | **45%** |
| **Séniorité** | Correspondance titre/niveau du poste | **10%** |
| **Mise à l'échelle** | √(hybrid) × 0.96 (racine carrée) | Finale |

> **Principe :** Le score est **absolu** (basé sur les exigences du poste) et non relatif. Un candidat qui possède toutes les compétences requises doit atteindre ~85-95% même s'il est seul dans la liste.

---

## 3. Diagramme de Classes (Modèle de Données Graphe - Neo4j)

Ce diagramme représente les entités métiers principales (Nœuds) et leurs relations dans la base de données orientée graphe.

```mermaid
classDiagram
    %% Définition des Nœuds (Classes) et de leurs Méthodes
    class Utilisateur {
        +UUID id
        +String nom_utilisateur
        +String email
        +String mot_de_passe_hash
        +String role
        +Timestamp date_creation
        +s_inscrire(donnees) Utilisateur
        +s_authentifier(email, mot_de_passe) Boolean
        +mettre_a_jour_profil(donnees) Boolean
        +supprimer_compte() Boolean
    }

    class Candidat {
        +UUID cv_id
        +String nom_complet
        +String telephone
        +String titre_actuel
        +String localisation
        +Int annees_exp
        +importer_cv(fichier_pdf) List~Competence~
        +postuler_offre(offre_id) Boolean
        +obtenir_offres_recommandees() List~OffreEmploi~
        +ajouter_competence(nom_competence) Boolean
        +obtenir_candidatures() List~OffreEmploi~
    }

    class Recruteur {
        +String departement
        +String poste
        +gerer_offres() Boolean
        +rechercher_candidats(offre_id) List~Candidat~
        +consulter_statistiques() Dict
    }

    class Administrateur {
        +Int niveau_acces
        +gerer_utilisateurs() Boolean
        +gerer_entreprises() Boolean
        +voir_analytics_globaux() Dict
    }

    class Entreprise {
        +UUID id
        +String nom_entreprise
        +String secteur
        +String localisation
        +publier_offre(donnees_offre) OffreEmploi
        +voir_candidats(offre_id) List~Candidat~
        +obtenir_toutes_offres() List~OffreEmploi~
        +mettre_a_jour_details() Boolean
    }

    class OffreEmploi {
        +UUID offre_id
        +String titre
        +String description
        +Float salaire_min
        +String localisation
        +Timestamp date_creation
        +ajouter_exigence(nom_competence) Boolean
        +trouver_meilleurs_candidats() List~Candidat~
        +obtenir_details() Dict
        +mettre_a_jour_statut(statut) Boolean
    }

    class Competence {
        +String nom_competence
        +obtenir_candidats() List~Candidat~
        +obtenir_offres() List~OffreEmploi~
    }

    %% Héritage (Candidat, Recruteur et Administrateur sont des types d'Utilisateurs)
    Utilisateur <|-- Candidat
    Utilisateur <|-- Recruteur
    Utilisateur <|-- Administrateur

    %% Relations Métier
    Recruteur "*" --> "1" Entreprise : TRAVAILLE_POUR (WORKS_FOR)
    Administrateur "1" .. "*" Utilisateur : GÈRE (MANAGES)
    Candidat "*" --> "*" OffreEmploi : A POSTULÉ (APPLIED_TO)
    Entreprise "1" --> "*" OffreEmploi : A PUBLIÉ (POSTED)
    Candidat "*" --> "*" Competence : POSSÈDE (HAS_SKILL)
    OffreEmploi "*" --> "*" Competence : EXIGE (REQUIRES)
```

---

## 4. Diagrammes de Séquence

### A. Smart CV : Recommandation d'offres pour un candidat
Ce diagramme illustre le processus d'analyse d'un CV uploadé par le candidat pour lui suggérer les meilleures offres correspondantes.

```mermaid
sequenceDiagram
    actor C as Candidat
    participant UI as Interface Utilisateur
    participant API as Backend (Flask)
    participant NLP as Module NLP (spaCy)
    participant DB as Base Neo4j

    C->>UI: Upload de son CV (PDF)
    UI->>API: POST /upload_cv (fichier PDF)
    API->>API: Extraction du texte du PDF
    API->>NLP: Analyse sémantique du texte (spaCy)
    NLP-->>API: Retourne la liste des compétences extraites
    API->>DB: Requête Cypher MATCH (offres)
    Note over DB: Calcul du Score Hybride<br/>(Similarité Cosine + Correspondance Exacte)
    DB-->>API: Liste des offres avec un score de pertinence
    API-->>UI: JSON (Top offres recommandées)
    UI-->>C: Affiche les offres triées par pourcentage de match
```

### B. Smart Sourcing : Recherche intelligente pour un recruteur
Ce diagramme montre comment un recruteur obtient une liste de candidats idéaux pour une de ses offres d'emploi grâce à l'algorithme hybride NLP/Graphe.

```mermaid
sequenceDiagram
    actor R as Recruteur
    participant UI as Interface Utilisateur
    participant API as Backend (Flask)
    participant NLP as Module NLP (spaCy)
    participant DB as Base Neo4j

    R->>UI: Sélectionne une offre & clique "Trouver Candidats"
    UI->>API: GET API pour Smart Sourcing (ex: /job/{id}/smart_sourcing)
    API->>DB: Récupère la description & les compétences de l'offre
    DB-->>API: Détails du poste (Texte + Skills)
    API->>NLP: Prétraitement NLP de la description du poste
    NLP-->>API: Entités nommées & Compétences détectées
    API->>DB: Requête Cypher MATCH (c:Candidate)
    Note over DB: Récupération des candidats<br/>Calcul Graph Score initial
    DB-->>API: Candidats bruts avec attributs et compétences
    API->>API: Application TF-IDF & Calcul Cosine Similarity
    API->>API: Calcul du score final (Hybride NLP/Graph 45/45)
    API->>API: Attribution des labels (Excellent, Bon, Possible)
    API-->>UI: JSON (Top candidats avec scores détaillés)
    UI-->>R: Affiche les candidats recommandés triés par match %
```

---

## 5. Architecture Globale du Projet

Ce diagramme présente l'architecture technique de l'application, montrant la séparation entre le frontend, le backend Flask, le traitement NLP et la base de données orientée graphe Neo4j.

```mermaid
graph LR
    %% Acteurs
    C(["👤 Candidat"])
    R(["💼 Recruteur"])
    A(["🔧 Admin"])

    %% Frontend
    subgraph Frontend ["🖥️ Frontend (Interface Web)"]
        UI["Application Web\n(HTML / CSS / JS)"]
    end

    %% Backend Flask
    subgraph Backend ["⚙️ Backend (API Flask)"]
        API["Routes API\n(routes.py)"]
        NLP["🧠 Module NLP\n(spaCy / TF-IDF)"]
        DB_Driver["🔌 Driver DB\n(db.py)"]
        
        API <-->|"Traitement Texte\n& Extraction"| NLP
        API <-->|"Accès Données"| DB_Driver
    end

    %% Base de données
    subgraph Data ["🗄️ Stockage & Données"]
        Neo4j[("Base Graphe\n(Neo4j)")]
        Mock[("Mock DB\n(Mode Dév)")]
    end

    %% Export
    subgraph Analytics ["📊 Business Intelligence"]
        PowerBI[["Dashboards\n(PowerBI)"]]
    end

    %% Connexions
    C <--> UI
    R <--> UI
    A <--> UI

    UI <-->|"Requêtes REST (JSON)"| API
    DB_Driver <-->|"Requêtes Cypher"| Neo4j
    DB_Driver -.->|"Fallback"| Mock
    Neo4j -.->|"Export de données"| PowerBI

    %% Styling
    style Frontend fill:#eff6ff,stroke:#3b82f6,stroke-width:2px
    style Backend fill:#fdf4ff,stroke:#d946ef,stroke-width:2px
    style Data fill:#ecfdf5,stroke:#10b981,stroke-width:2px
    style Analytics fill:#fff7ed,stroke:#f97316,stroke-width:2px
    style Neo4j fill:#047857,color:#fff
    style Mock fill:#d1d5db
    style NLP fill:#e879f9,color:#fff
```
