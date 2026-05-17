import os
import json
from uuid import uuid4
from datetime import datetime
from neo4j import GraphDatabase
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    def __init__(self, id, username, email, password_hash, role="user"):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class MockDriver:
    """Driver mock pour développement sans Neo4j"""
    def __init__(self):
        self.candidates = {}
        self.jobs = {}
        self.skills = {}
        self.relations = []
        self.users = {}
        self._mock = True
        self._init_sample_data()

    def _init_sample_data(self):
        """Initialiser avec des données d'exemple"""
        # Candidats
        self.candidates = {
            "cand1": {"id": "cand1", "name": "Alice Dupont", "email": "alice@example.com", "phone": "+33612345678"},
            "cand2": {"id": "cand2", "name": "Bob Martin", "email": "bob@example.com", "phone": "+33698765432"},
        }
        # Jobs
        self.jobs = {
            "job1": {"id": "job1", "title": "Développeur Python", "company": "TechCorp", "description": "Développeur Python expérimenté", "salary": "45000"},
            "job2": {"id": "job2", "title": "Dev Frontend React", "company": "WebApp Inc", "description": "Expert React.js", "salary": "40000"},
        }
        # Skills
        self.skills = {
            "python": {"name": "Python"},
            "react": {"name": "React"},
            "nodejs": {"name": "Node.js"},
        }
        # Users - Hash for "admin123", "user123", "recruiter123"
        admin_pw = generate_password_hash("admin123")
        user_pw = generate_password_hash("user123")
        recruiter_pw = generate_password_hash("recruiter123")
        
        self.users = {
            "admin": {"id": "admin", "username": "admin", "email": "admin@gmail.com", "password_hash": admin_pw, "role": "admin"},
            "user": {"id": "user", "username": "khadija.raji1", "email": "khadija.raji1@mail.com", "password_hash": user_pw, "role": "user"},
            "recruiter": {"id": "recruiter", "username": "recruiter", "email": "recruiter@gmail.com", "password_hash": recruiter_pw, "role": "recruiter"}
        }

    def get_user(self, user_id):
        if user_id in self.users:
            u = self.users[user_id]
            # Handle potential missing email key in old objects if any (though we just reset them)
            return User(u["id"], u["username"], u.get("email"), u["password_hash"], u["role"])
        return None

    def get_user_by_username(self, username):
        # Kept for backward compatibility if needed, but preference is email
        for u in self.users.values():
            if u["username"] == username:
                return User(u["id"], u["username"], u.get("email"), u["password_hash"], u["role"])
        return None

    def get_user_by_email(self, email):
        for u in self.users.values():
            if u.get("email") == email:
                return User(u["id"], u["username"], u.get("email"), u["password_hash"], u["role"])
        return None

    def run_query(self, cypher, parameters=None):
        """Simuler l'exécution de requêtes Cypher"""
        params = parameters or {}
        cypher_lower = cypher.lower()
        
        # MATCH (c:Candidate) RETURN...
        if "match (c:candidate)" in cypher_lower and "return" in cypher_lower:
            result = []
            limit = params.get("limit", 50)
            q = params.get("q", "").lower()
            tokens = params.get("tokens") or []
            if isinstance(tokens, list):
                tokens = [t.lower() for t in tokens if t]
            else:
                tokens = []
            
            for i, (id, cand) in enumerate(self.candidates.items()):
                # Filter if q is present - STRICT MATCH
                if q:
                    # Check exact match on fields
                    matches = (
                        q == cand.get("name", "").lower() or
                        q == cand.get("email", "").lower() or
                        q == cand.get("phone", "").lower() or
                        q == cand.get("title", "").lower() or
                        q == cand.get("location", "").lower() or
                        # Maybe allow simple contains for location? User said 'similaire juste'. 
                        # I'll stick to strict equal for robustness or 'word in text'?
                        # Let's do strict equality as requested.
                        False
                    )
                    if not matches:
                        continue

                if len(result) >= limit:
                    break
                result.append({"id": cand["id"], "name": cand["name"], "email": cand["email"]})
            return result
        
        # MATCH (c:Candidate {id: ...}) RETURN c
        if "match (c:candidate {id:" in cypher_lower and "return c" in cypher_lower:
            cand_id = params.get("id")
            if cand_id in self.candidates:
                return [{"c": self.candidates[cand_id]}]
            return []
        
        # SET c.name = ... (UPDATE)
        if "match (c:candidate {id:" in cypher_lower and "set c." in cypher_lower:
            cand_id = params.get("id")
            if cand_id in self.candidates:
                cand = self.candidates[cand_id]
                if params.get("name"):
                    cand["name"] = params["name"]
                if params.get("email"):
                    cand["email"] = params["email"]
                if params.get("phone"):
                    cand["phone"] = params["phone"]
                return [{"id": cand["id"], "name": cand["name"]}]
            return []
        
        # MATCH (c:Company {recruiter_email: $email}) or MATCH (comp:Company) WHERE comp.recruiter_email...
        if "match (" in cypher_lower and ":company" in cypher_lower and "recruiter_email" in cypher_lower:
            return [{"name": "TechCorp", "company_name": "TechCorp", "company_id": "comp1"}]
            
        # Recruiter candidates (MATCH (comp:Company)-[:POSTED]->(j:Job)<-[:APPLIED_TO]-(c))
        if "match (comp:company)-[:posted]->(j:job)<-[:applied_to]-(c)" in cypher_lower:
            result = []
            for cand in self.candidates.values():
                result.append({
                    "id": cand["id"],
                    "name": cand["name"],
                    "email": cand["email"],
                    "phone": cand.get("phone", ""),
                    "current_title": cand.get("title", ""),
                    "location": cand.get("location", "")
                })
            return result
        
        # MATCH (j:Job) RETURN...
        if "match (j:job)" in cypher_lower and "return" in cypher_lower and "detach" not in cypher_lower:
            result = []
            limit = params.get("limit", 50)
            q = params.get("q", "").lower()

            for i, (id, job) in enumerate(self.jobs.items()):
                # Filter if q is present - STRICT MATCH
                if q:
                   matches = (
                       q == job.get("title", "").lower() or
                       q == job.get("company", "").lower() or
                       q == job.get("location", "").lower()
                   )
                   if not matches:
                       continue

                if len(result) >= limit:
                    break
                result.append({"id": job["id"], "title": job["title"], "company": job["company"], "location": job.get("location", "")})
            return result
        
        # MATCH (j:Job {id: ...}) RETURN j
        if "match (j:job {id:" in cypher_lower and "return j" in cypher_lower:
            job_id = params.get("id")
            if job_id in self.jobs:
                return [{"j": self.jobs[job_id]}]
            return []
        
        # SET j. (UPDATE JOB)
        if "match (j:job {id:" in cypher_lower and "set j." in cypher_lower:
            job_id = params.get("id")
            if job_id in self.jobs:
                job = self.jobs[job_id]
                if params.get("title"):
                    job["title"] = params["title"]
                if params.get("description"):
                    job["description"] = params["description"]
                if params.get("company"):
                    job["company"] = params["company"]
                if params.get("salary"):
                    job["salary"] = params["salary"]
                return [{"id": job["id"], "title": job["title"]}]
            return []
        
        # DETACH DELETE j
        if "detach delete j" in cypher_lower and "match (j:job" in cypher_lower:
            job_id = params.get("id")
            if job_id in self.jobs:
                del self.jobs[job_id]
            return [{"id": job_id}]
        
        # MATCH (s:Skill) RETURN...
        if "match (s:skill)" in cypher_lower and "return" in cypher_lower:
            result = []
            limit = params.get("limit", 50)
            for i, (name, skill) in enumerate(self.skills.items()):
                if i >= limit:
                    break
                result.append({"id": name, "name": skill["name"]})
            return result
        
        # CREATE (c:Candidate {...})
        if "create (c:candidate" in cypher_lower:
            cand_id = str(uuid4())
            candidate = {
                "id": cand_id,
                "name": params.get("name", ""),
                "email": params.get("email", ""),
                "phone": params.get("phone", "")
            }
            self.candidates[cand_id] = candidate
            return [{"id": cand_id, "name": candidate["name"]}]
        
        # CREATE (j:Job {...})
        if "create (j:job" in cypher_lower:
            job_id = str(uuid4())
            job = {
                "id": job_id,
                "title": params.get("title", ""),
                "description": params.get("description", ""),
                "company": params.get("company", ""),
                "salary": params.get("salary", "")
            }
            self.jobs[job_id] = job
            return [{"id": job_id, "title": job["title"]}]
        
        # MERGE (s:Skill {name: ...})
        if "merge (s:skill" in cypher_lower:
            skill_name = params.get("skill_name", params.get("name", ""))
            if skill_name not in self.skills:
                self.skills[skill_name] = {"name": skill_name}
            return [{"name": skill_name}]
        
        # CREATE (c)-[:APPLIED_TO]->(j)
        if "applied_to" in cypher_lower and "create" in cypher_lower:
            cand_id = params.get("candidate_id")
            job_id = params.get("job_id")
            if cand_id in self.candidates and job_id in self.jobs:
                self.relations.append({"type": "APPLIED_TO", "from": cand_id, "to": job_id})
                return [{"candidate": self.candidates[cand_id].get("name"), "job": self.jobs[job_id].get("title")}]
            return []
        
        # MATCH (c)-[:APPLIED_TO]->(j:Job {id: ...})
        if "applied_to" in cypher_lower and "match (c" in cypher_lower:
            job_id = params.get("job_id")
            result = []
            for rel in self.relations:
                if rel["type"] == "APPLIED_TO" and rel["to"] == job_id:
                    cand_id = rel["from"]
                    if cand_id in self.candidates:
                        cand = self.candidates[cand_id]
                        result.append({"id": cand["id"], "name": cand["name"], "email": cand["email"]})
            return result
        
        # MATCH (c {id: ...})-[:APPLIED_TO]->(j) for candidate applications
        if "applied_to" in cypher_lower and "candidate {id:" in cypher_lower:
            cand_id = params.get("candidate_id")
            result = []
            for rel in self.relations:
                if rel["type"] == "APPLIED_TO" and rel["from"] == cand_id:
                    job_id = rel["to"]
                    if job_id in self.jobs:
                        job = self.jobs[job_id]
                        result.append({"id": job["id"], "title": job["title"], "company": job["company"]})
            return result
        
        # MATCH (c)-[:HAS_SKILL]->(s)
        if "has_skill" in cypher_lower:
            cand_id = params.get("candidate_id")
            result = []
            for rel in self.relations:
                if rel["type"] == "HAS_SKILL" and rel["from"] == cand_id:
                    skill_name = rel["to"]
                    if skill_name in self.skills:
                        result.append({"name": self.skills[skill_name]["name"]})
            return result
        
        # CREATE (c)-[:HAS_SKILL]->(s)
        if "has_skill" in cypher_lower and "create" in cypher_lower:
            cand_id = params.get("candidate_id")
            skill_name = params.get("skill_name")
            if cand_id in self.candidates:
                self.relations.append({"type": "HAS_SKILL", "from": cand_id, "to": skill_name})
                return [{"candidate": self.candidates[cand_id].get("name"), "skill": skill_name}]
            return []
        
        # RETURN 1 AS ok (health check)
        if "return 1" in cypher_lower:
            return [{"ok": 1}]
        
        # Default
        return []


    def create_user(self, username, email, password, role="user"):
        user_id = str(uuid4())
        pw_hash = generate_password_hash(password)
        self.users[user_id] = {
            "id": user_id, 
            "username": username, 
            "email": email, 
            "password_hash": pw_hash, 
            "role": role
        }
        if role == "user":
            cand_id = str(uuid4())
            self.candidates[cand_id] = {
                "id": cand_id, "name": username, "email": email
            }
        return User(user_id, username, email, pw_hash, role)

    def close(self):
        pass


class Neo4jDriver:
    def __init__(self, uri, user, password):
        try:
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
            self._database = os.getenv("NEO4J_DATABASE", "neo4j")
            self._init_default_users()
        except Exception as e:
            print(f"Erreur lors de la création du driver Neo4j : {e}")
            print("Basculement vers le mode mock/développement")
            self._driver = None
            self._database = None
            self._mock = True
    
    def _init_default_users(self):
        # Check if users exist/Seed specific users
        if not self._driver: return
        db_name = self._database or "neo4j"
        try:
             with self._driver.session(database=db_name) as session:
                # Seed Admin
                pw_admin = generate_password_hash("admin123")
                session.run("""
                    MERGE (u:User {email: 'admin@gmail.com'})
                    ON CREATE SET u.id = randomUUID(), u.username = 'admin', u.password_hash = $pw, u.role = 'admin'
                    ON MATCH SET u.role = 'admin'
                """, pw=pw_admin)

                # Seed Recruiter User nodes from Company.recruiter_email
                companies = list(session.run("""
                    MATCH (comp:Company)
                    WHERE comp.recruiter_email IS NOT NULL AND comp.recruiter_email <> ''
                    RETURN comp.recruiter_name AS rname, comp.recruiter_email AS remail,
                           COALESCE(comp.company_name, comp.name) AS cname
                """))
                for row in companies:
                    remail = row["remail"]
                    rname  = row["rname"] or remail.split("@")[0]
                    cname  = row["cname"] or "company"
                    # Generate personalized password: First part of email capitalized + 2026
                    base_name = remail.split("@")[0].split(".")[0].capitalize()
                    personal_pw = f"{base_name}2026"
                    pw_hash = generate_password_hash(personal_pw)
                    
                    session.run("""
                        MERGE (u:User {email: $email})
                        ON CREATE SET u.id = randomUUID(), u.username = $username,
                                      u.password_hash = $pw, u.role = 'recruiter',
                                      u.password_hint = $hint
                        ON MATCH SET u.role = 'recruiter',
                                     u.password_hash = $pw,
                                     u.password_hint = $hint
                    """, email=remail, username=rname, pw=pw_hash, hint=personal_pw)
                    print(f"[INIT] Recruiter user seeded for: {remail} (password: {personal_pw})")

                # Seed Candidate User nodes from Candidate nodes in Neo4j
                candidates = list(session.run("""
                    MATCH (c:Candidate)
                    WHERE c.email IS NOT NULL AND c.email <> ''
                    RETURN COALESCE(c.full_name, c.name) AS cname,
                           c.email AS cemail
                    LIMIT 200
                """))
                print(f"[INIT] Generating unique passwords for {len(candidates)} candidates. This may take a few seconds...")
                seeded_count = 0
                for row in candidates:
                    cemail = row["cemail"]
                    cname  = row["cname"] or cemail.split("@")[0]
                    if not cemail or "@" not in cemail:
                        continue
                    
                    base_name = cemail.split("@")[0].split(".")[0].capitalize()
                    personal_pw = f"{base_name}2026"
                    pw_hash = generate_password_hash(personal_pw)
                    
                    session.run("""
                        MERGE (u:User {email: $email})
                        ON CREATE SET u.id = randomUUID(), u.username = $username,
                                      u.password_hash = $pw, u.role = 'user',
                                      u.password_hint = $hint
                        ON MATCH SET u.role = 'user',
                                     u.password_hash = $pw,
                                     u.password_hint = $hint
                    """, email=cemail, username=cname, pw=pw_hash, hint=personal_pw)
                    seeded_count += 1
                print(f"[INIT] {seeded_count} candidate users seeded with unique passwords.")

        except Exception as e:
            print(f"Error initializing users in Neo4j (db: {db_name}): {e}")


    def get_user(self, user_id):
        if not self._driver: return None
        with self._driver.session() as session:
            # Use elementId for stable identification
            res = session.run("MATCH (u:User) WHERE elementId(u) = $id RETURN u", id=user_id).single()
            if res:
                u = res["u"]
                return User(u.element_id, u["username"], u.get("email"), u["password_hash"], u.get("role", "user"))
        return None

    def get_user_by_username(self, username):
        if not self._driver: return None
        with self._driver.session() as session:
            res = session.run("MATCH (u:User {username: $username}) RETURN u", username=username).single()
            if res:
                u = res["u"]
                return User(u.element_id, u["username"], u.get("email"), u["password_hash"], u.get("role", "user"))
        return None

    def get_user_by_email(self, email):
        if not self._driver: return None
        with self._driver.session() as session:
            # Allow login by email OR username (User nodes)
            query = "MATCH (u:User) WHERE u.email = $identifier OR u.username = $identifier RETURN u"
            res = session.run(query, identifier=email).single()
            if res:
                u = res["u"]
                return User(u.element_id, u["username"], u.get("email"), u["password_hash"], u.get("role", "user"))
            
            # If not found, check Company.recruiter_email (recruiter login via company data)
            comp_res = session.run("""
                MATCH (comp:Company)
                WHERE comp.recruiter_email = $email
                RETURN comp.recruiter_name AS rname, comp.recruiter_email AS remail, comp.name AS cname
                LIMIT 1
            """, email=email).single()
            if comp_res:
                remail = comp_res["remail"]
                rname = comp_res["rname"] or remail.split("@")[0]
                cname = comp_res["cname"] or "company"
                # Auto-create User node for this recruiter on first login attempt
                default_pw = generate_password_hash(cname.lower().replace(" ", "") + "2024")
                u_res = session.run("""
                    MERGE (u:User {email: $email})
                    ON CREATE SET u.id = randomUUID(), u.username = $username,
                                  u.password_hash = $pw, u.role = 'recruiter'
                    ON MATCH SET u.role = 'recruiter'
                    RETURN u
                """, email=remail, username=rname, pw=default_pw).single()
                if u_res:
                    u = u_res["u"]
                    return User(u.element_id, u["username"], u.get("email"), u["password_hash"], u.get("role", "recruiter"))

            # If not found, check Candidate node (candidate login via CV data)
            cand_res = session.run("""
                MATCH (c:Candidate)
                WHERE c.email = $email
                RETURN COALESCE(c.full_name, c.name) AS cname, c.password AS cpass
                LIMIT 1
            """, email=email).single()
            if cand_res:
                cname = cand_res["cname"] or email.split("@")[0]
                cpass = cand_res["cpass"]
                
                if not cpass:
                    base_name = email.split("@")[0].split(".")[0].capitalize()
                    cpass = f"{base_name}2026"
                
                pw_hash = cpass if str(cpass).startswith("pbkdf2:") else generate_password_hash(str(cpass))
                    
                u_res = session.run("""
                    MERGE (u:User {email: $email})
                    ON CREATE SET u.id = randomUUID(), u.username = $username,
                                  u.password_hash = $pw, u.role = 'user'
                    ON MATCH SET u.role = 'user'
                    RETURN u
                """, email=email, username=cname, pw=pw_hash).single()
                if u_res:
                    u = u_res["u"]
                    return User(u.element_id, u["username"], u.get("email"), u["password_hash"], u.get("role", "user"))
                    
        return None

    def close(self):
        if self._driver:
            self._driver.close()

    def run_query(self, cypher, parameters=None):
        if not self._driver:
            raise RuntimeError("Driver Neo4j non initialisé")
        
        # Determine if this is a write operation
        is_write = any(kw in cypher.upper() for kw in ['CREATE', 'SET', 'DELETE', 'MERGE', 'REMOVE'])
        
        try:
            # Use explicit transaction for writes to ensure commit
            if self._database and self._database != "":
                session = self._driver.session(database=self._database)
            else:
                session = self._driver.session()
            
            try:
                print(f"[CYPHER] Running: {cypher[:100]}...")
                if is_write:
                    # Explicit transaction with manual commit to guarantee persistence
                    tx = session.begin_transaction()
                    try:
                        records = list(tx.run(cypher, parameters or {}))
                        data = [record.data() for record in records]
                        tx.commit()  # Explicit commit — do NOT rely on context manager
                        print(f"[CYPHER] Write committed. Result Count: {len(data)}")
                        return data
                    except Exception:
                        tx.rollback()
                        raise
                else:
                    # For read operations, use simple run
                    records = list(session.run(cypher, parameters or {}))
                    data = [record.data() for record in records]
                    print(f"[CYPHER] Result Count: {len(data)}")
                    return data
            finally:
                session.close()
        except Exception as e:
            print(f"Neo4j query error: {e}")
            raise


    def create_user(self, username, email, password, role="user"):
        """Créer un utilisateur et le noeud Candidate associé"""
        if not self._driver: return None
        
        pw_hash = generate_password_hash(password)
        
        try:
            with self._driver.session() as session:
                # 1. Check if exists
                check = session.run("MATCH (u:User) WHERE u.email = $email OR u.username = $username RETURN u", 
                                    email=email, username=username).single()
                if check:
                    print(f"[REGISTER] User {email} already exists")
                    return None
                
                # 2. Create User & Candidate in transaction
                with session.begin_transaction() as tx:
                    # Create User Node
                    user_cypher = """
                    CREATE (u:User {
                        id: randomUUID(),
                        username: $username,
                        email: $email,
                        password_hash: $pw,
                        role: $role,
                        created_at: timestamp()
                    })
                    RETURN u
                    """
                    u_res = tx.run(user_cypher, username=username, email=email, pw=pw_hash, role=role).single()
                    
                    # If role is user, Create Candidate Node
                    if role == "user":
                        cand_cypher = """
                        CREATE (c:Candidate {
                            id: randomUUID(),
                            cv_id: randomUUID(),
                            full_name: $username,
                            name: $username, 
                            email: $email,
                            created_at: timestamp()
                        })
                        """
                        tx.run(cand_cypher, username=username, email=email)
                        
                    if u_res:
                        u = u_res["u"]
                        # Adapt return to User object
                        uid = u.get("id") or u.element_id
                        return User(uid, u["username"], u.get("email"), u["password_hash"], u["role"])
                        
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
        return None

    def get_market_trends(self):
        """Récupérer les tendances du marché (Top Skills & Hubs)"""
        if not self._driver: return {}
        
        try:
            with self._driver.session() as session:
                # 1. Top Skills (Supply: Most Common Skills in Candidates)
                cypher_skills = """
                MATCH (s:Skill)<-[:HAS_SKILL]-(c:Candidate)
                RETURN s.name as skill, count(c) as count
                ORDER BY count DESC LIMIT 8
                """
                
                # 2. Hub Skills (Demand/Centrality: Skills connecting Candidates to Companies/Jobs)
                # (Company)-[:POSTED]->(Job)<-[:APPLIED_TO]-(Candidate)-[:HAS_SKILL]->(s:Skill)
                cypher_hubs = """
                MATCH (comp:Company)-[:POSTED]->(j:Job)<-[:APPLIED_TO]-(c:Candidate)-[:HAS_SKILL]->(s:Skill)
                RETURN s.name as skill, count(DISTINCT comp) as companies, count(DISTINCT j) as jobs
                ORDER BY companies DESC, jobs DESC LIMIT 8
                """
                
                # Execute
                skills_res = session.run(cypher_skills)
                hubs_res = session.run(cypher_hubs)
                
                return {
                    "top_skills": [r.data() for r in skills_res],
                    "hubs": [r.data() for r in hubs_res]
                }
        except Exception as e:
            print(f"Error fetching market trends: {e}")
            return {"top_skills": [], "hubs": []}


_driver_instance = None

def init_driver():
    global _driver_instance
    if _driver_instance is not None:
        return _driver_instance
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j")
    mode = os.getenv("DB_MODE", "neo4j").lower()
    
    # Si mode mock ou si Neo4j n'est pas accessible
    if mode == "mock":
        print("[INFO] Mode MOCK activé par configuration")
        _driver_instance = MockDriver()
    else:
        # DO NOT CATCH EXCEPTION - FAIL LOUDLY if connection fails
        try:
            _driver_instance = Neo4jDriver(uri, user, password)
            # Tester la connexion
            _driver_instance.run_query("RETURN 1 AS ok")
            print(f"[INFO] Connexion Neo4j réussie sur {uri}")
        except Exception as e:
            print(f"[CRITICAL ERROR] Failed to connect to Neo4j: {e}")
            raise e
            # _driver_instance = MockDriver()
    
    return _driver_instance


def get_driver():
    return _driver_instance


def close_driver():
    """Fermer le driver - appelé à l'arrêt de l'app"""
    global _driver_instance
    if _driver_instance:
        try:
            _driver_instance.close()
        except:
            pass
        # Ne pas mettre à None ici, le garder accessible
        # _driver_instance = None
