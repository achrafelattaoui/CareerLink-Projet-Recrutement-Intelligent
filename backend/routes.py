from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
from db import get_driver
import pypdf
import io
import re
from werkzeug.utils import secure_filename

# --- NLP Imports ---
try:
    import spacy
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    _NLP_AVAILABLE = True
except ImportError:
    _NLP_AVAILABLE = False
    print("[WARNING] spaCy/scikit-learn not installed. Smart CV will use basic matching.")

# Load spaCy model once at module level (lazy load)
_nlp = None
def _get_nlp():
    global _nlp
    if _nlp is None and _NLP_AVAILABLE:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            print(f"[WARNING] Could not load spaCy model: {e}")
    return _nlp

bp = Blueprint("routes", __name__)

def admin_required():
    if not current_user.is_authenticated or current_user.role != 'admin':
        abort(403)

def admin_or_recruiter_required():
    if not current_user.is_authenticated or current_user.role not in ['admin', 'recruiter']:
        abort(403)






@bp.route("/health")
def health_check():
    """Simple health check that runs a trivial Cypher query to verify connectivity."""
    driver = get_driver()
    if not driver:
        return jsonify({"status": "error", "detail": "driver not initialized"}), 500
    try:
        records = driver.run_query("RETURN 1 AS ok")
        ok = False
        if records and isinstance(records, list):
            first = records[0]
            ok = first.get("ok") == 1 or first.get("ok") == 1.0
        return jsonify({"status": "ok" if ok else "error", "result": records})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500


@bp.route("/stats", methods=["GET"])
@login_required
def get_stats():
    """Récupérer les statistiques adaptées au rôle de l'utilisateur"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    try:
        candidates_count = 0
        jobs_count = 0
        companies_count = 0
        
        is_recruiter = current_user.role == 'recruiter'
        is_admin = current_user.role == 'admin'
        
        # Determine recruiter email if relevant
        recruiter_email = None
        if is_recruiter:
             user_res = driver.run_query(
                "MATCH (u:User) WHERE elementId(u) = $eid RETURN u.email AS email",
                {"eid": current_user.id}
             )
             if user_res:
                 recruiter_email = user_res[0].get("email")

        # 1. Jobs Count
        if is_recruiter and recruiter_email:
            jobs_cypher = "MATCH (comp:Company {recruiter_email: $email})-[:POSTED]->(j:Job) RETURN count(j) as total"
            jobs_records = driver.run_query(jobs_cypher, {"email": recruiter_email})
        else:
            jobs_cypher = "MATCH (j:Job) RETURN count(j) as total"
            jobs_records = driver.run_query(jobs_cypher)
        
        if jobs_records:
            jobs_count = int(jobs_records[0].get("total") or 0)

        # 2. Candidates Count
        # Both Admin and Recruiter should see the total pool of candidates for sourcing
        cand_cypher = "MATCH (c) WHERE c:Candidate OR c:Candidate_Cv RETURN count(c) as total"
        cand_records = driver.run_query(cand_cypher)
            
        if cand_records:
            candidates_count = int(cand_records[0].get("total") or 0)
        
        # 3. Companies Count
        if is_recruiter:
            companies_count = 1 # Only their own company
        else:
            comp_cypher = "MATCH (c:Company) RETURN count(c) as total"
            comp_records = driver.run_query(comp_cypher)
            if comp_records:
                companies_count = int(comp_records[0].get("total") or 0)
        
        # 4. Recruiters Count (Admin only)
        recruiters_count = 0
        if is_admin:
            rec_cypher = "MATCH (u:User {role: 'recruiter'}) RETURN count(u) as total"
            rec_records = driver.run_query(rec_cypher)
            if rec_records:
                recruiters_count = int(rec_records[0].get("total") or 0)
        
        return jsonify({
            "candidates": candidates_count,
            "jobs": jobs_count,
            "companies": companies_count,
            "recruiters": recruiters_count,
            "role": current_user.role
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/nodes", methods=["GET"])
@login_required
def get_nodes():
    """Récupérer les nœuds (avec filtrage optionnel)"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    label = request.args.get("label")
    limit = request.args.get("limit", 5, type=int)
    
    try:
        if label:
            cypher = f"MATCH (n:{label}) RETURN n LIMIT $limit"
        else:
            cypher = "MATCH (n) RETURN n LIMIT $limit"
        
        records = driver.run_query(cypher, {"limit": limit})
        nodes = []
        for r in records:
            node = r.get("n")
            if node is None:
                continue
            try:
                labels = list(node.labels)
                props = dict(node)
            except Exception:
                labels = []
                props = {}
            nodes.append({"labels": labels, "properties": props})
        return jsonify({"count": len(nodes), "nodes": nodes})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@bp.route("/career-path", methods=["GET"])
def career_path_endpoint():
    """Récupérer graph de carrière"""
    if not current_user.is_authenticated:
        return jsonify({"error": "Unauthorized"}), 401
    
    driver = get_driver()
    title = request.args.get("title", "").lower()
    
    nodes = []
    edges = []
    
    try:
        if hasattr(driver, "_mock") and driver._mock:
             nodes = [
                {"id": "dev", "label": "Dev"},
                {"id": "lead", "label": "Tech Lead"},
                {"id": "cto", "label": "CTO"}
             ]
             edges = [
                {"from": "dev", "to": "lead", "weight": 5},
                {"from": "lead", "to": "cto", "weight": 2}
             ]
        else:
             cypher = """
             MATCH (c:Candidate) 
             WHERE c.current_title IS NOT NULL AND c.target_title IS NOT NULL
             RETURN c.current_title as start, c.target_title as end, count(c) as w LIMIT 20
             """
             if title:
                cypher = """
                MATCH (c:Candidate) 
                WHERE c.current_title IS NOT NULL AND c.target_title IS NOT NULL
                AND (toLower(c.current_title) CONTAINS $title OR toLower(c.target_title) CONTAINS $title)
                RETURN c.current_title as start, c.target_title as end, count(c) as w LIMIT 20
                """
             
             recs = driver.run_query(cypher, {"title": title})
             node_set = set()
             for r in recs:
                 s = r["start"]
                 e = r["end"]
                 w = r["w"]
                 sid = re.sub(r'[^a-zA-Z0-9]', '', s)
                 eid = re.sub(r'[^a-zA-Z0-9]', '', e)
                 if not sid or not eid: continue
                 
                 # Avoid duplicates
                 if sid not in [n['id'] for n in nodes]:
                     nodes.append({"id": sid, "label": s})
                 if eid not in [n['id'] for n in nodes]:
                     nodes.append({"id": eid, "label": e})
                 
                 edges.append({"from": sid, "to": eid, "weight": w})

    except Exception as e:
        print(f"[CAREER ERROR] {e}")

    return jsonify({"nodes": nodes, "edges": edges})



@bp.route("/candidates", methods=["GET"])
@login_required
def get_candidates():
    """Récupérer les candidats. Recruteur = uniquement ceux liés à son entreprise. Admin = tous."""
    print(f"DEBUG: get_candidates called by {current_user.username} role={current_user.role}")
    admin_or_recruiter_required()
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500

    try:
        company_name = None
        company_id = None
        
        if current_user.role == 'recruiter':
            # Get recruiter's email
            user_res = driver.run_query(
                "MATCH (u:User) WHERE elementId(u) = $eid RETURN u.email AS email",
                {"eid": current_user.id}
            )
            recruiter_email = user_res[0]["email"] if user_res else None

            if recruiter_email:
                # Find the company linked to this recruiter
                comp_res = driver.run_query(
                    """
                    MATCH (comp:Company)
                    WHERE comp.recruiter_email = $email
                    RETURN COALESCE(comp.company_name, comp.name) AS company_name,
                           toString(COALESCE(comp.company_id, comp.id, elementId(comp))) AS company_id
                    LIMIT 1
                    """,
                    {"email": recruiter_email}
                )
                if comp_res:
                    company_name = comp_res[0]["company_name"]
                    company_id = comp_res[0]["company_id"]

        # Fetch all candidates. If recruiter, optionally match jobs they applied to for their company.
        count_cypher = "MATCH (c) WHERE c:Candidate OR c:Candidate_Cv RETURN count(c) as total"
        total_records = driver.run_query(count_cypher) or []
        total = int(total_records[0].get("total") or 0) if total_records else 0

        if current_user.role == 'recruiter' and company_name:
            # Recruiter: Show applicants (one row per job) + others (one row per candidate)
            cypher = """
            MATCH (c)
            WHERE (c:Candidate OR c:Candidate_Cv) AND (c.full_name IS NOT NULL OR c.name IS NOT NULL)
            
            OPTIONAL MATCH (c)-[r:APPLIED_TO]->(j:Job)
            WHERE j.company_name_text = $company OR j.company = $company
            
            WITH c, j, r
            RETURN toString(COALESCE(c.cv_id, c.id, elementId(c))) AS pure_id,
                   toString(COALESCE(c.cv_id, c.id, elementId(c))) + 
                   CASE WHEN j IS NOT NULL THEN "_" + toString(COALESCE(j.job_id, j.id, elementId(j))) ELSE "" END AS id,
                   COALESCE(c.full_name, c.name) AS name,
                   c.email AS email,
                   c.phone AS phone,
                   CASE WHEN j IS NOT NULL THEN "Postulant: " + j.title ELSE c.current_title END AS current_title,
                   c.location AS location,
                   CASE WHEN j IS NOT NULL THEN [j.title] ELSE [] END AS applied_jobs,
                   (j IS NOT NULL) as is_applicant,
                   toString(COALESCE(r.applied_at, datetime({year:2000}))) as sort_date
            ORDER BY is_applicant DESC, sort_date DESC, name ASC
            LIMIT 500
            """
            records = driver.run_query(cypher, {"company": company_name}) or []
            
        else:
            # Admin view: Show all candidates once
            cypher = """
            MATCH (c)
            WHERE (c:Candidate OR c:Candidate_Cv) AND COALESCE(c.full_name, c.name) IS NOT NULL
            OPTIONAL MATCH (c)-[:APPLIED_TO]->(j:Job)
            WITH c, collect(j.title) as jobs
            RETURN toString(COALESCE(c.cv_id, c.id, elementId(c))) AS id,
                   toString(COALESCE(c.cv_id, c.id, elementId(c))) AS pure_id,
                   COALESCE(c.full_name, c.name) AS name,
                   c.email AS email,
                   c.phone AS phone,
                   c.current_title AS current_title,
                   c.location AS location,
                   jobs AS applied_jobs,
                   false as is_applicant,
                   toString(datetime({year:2000})) as sort_date
            ORDER BY name ASC
            LIMIT 500
            """
            records = driver.run_query(cypher) or []
        
        return jsonify({
            "count": total,
            "candidates": records,
            "company": company_name,
            "company_id": company_id
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/candidates/add", methods=["POST"])
@login_required
def add_candidate():
    admin_or_recruiter_required()
    """Ajouter un nouveau candidat"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "name is required"}), 400
    
    try:
        cypher = """
        CREATE (c:Candidate {
            cv_id: randomUUID(),
            full_name: $name,
            email: $email,
            phone: $phone,
            created_at: timestamp()
        })
        RETURN c.cv_id as id, c.full_name as name
        """
        params = {
            "name": data.get("name"),
            "email": data.get("email", ""),
            "phone": data.get("phone", "")
        }
        records = driver.run_query(cypher, params)
        return jsonify({"success": True, "data": records[0] if records else {}}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def extract_pure_id(cid):
    """Extract candidate part from composite ID (e.g. candId_jobId)"""
    if not cid: return cid
    return str(cid).split('_')[0]

@bp.route("/candidates/<candidate_id>", methods=["GET"])
@login_required
def get_candidate(candidate_id):
    """Récupérer un candidat par ID"""
    pure_id = extract_pure_id(candidate_id)
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    try:
        # Check by id or cv_id (support both labels)
        cypher = """
        MATCH (c)
        WHERE (c:Candidate OR c:Candidate_Cv)
        AND (c.id = $id OR c.cv_id = $id OR toString(c.cv_id) = $id OR ("cv_" + toString(c.cv_id)) = $id OR elementId(c) = $id)
        OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
        WITH c, collect(DISTINCT s.name) as skills
        RETURN COALESCE(c.cv_id, c.id) as id, 
               COALESCE(c.full_name, c.name, 'Unknown') as name, 
               c.email as email, 
               c.phone as phone,
               c.cv_id as cv_id,
               c.current_title as current_title,
               c.location as location,
               c.summary as summary,
               c.experience_level as experience_level,
               skills
        """
        records = driver.run_query(cypher, {"id": pure_id})
        if not records:
            return jsonify({"error": "Candidate not found"}), 404
        
        return jsonify(records[0]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/candidates/<candidate_id>", methods=["PUT"])
@login_required
def update_candidate(candidate_id):
    admin_or_recruiter_required()
    """Modifier un candidat"""
    pure_id = extract_pure_id(candidate_id)
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        cypher = """
        MATCH (c)
        WHERE (c:Candidate OR c:Candidate_Cv)
        AND (c.id = $id OR c.cv_id = $id OR toString(c.cv_id) = $id OR ("cv_" + toString(c.cv_id)) = $id OR elementId(c) = $id)
        SET c.full_name = COALESCE($name, c.full_name, c.name),
            c.email = COALESCE($email, c.email),
            c.phone = COALESCE($phone, c.phone),
            c.location = COALESCE($location, c.location),
            c.current_title = COALESCE($title, c.current_title),
            c.updated_at = timestamp()
        RETURN COALESCE(c.cv_id, c.id) as id, COALESCE(c.full_name, c.name) as name, c.email as email, c.phone as phone
        """
        params = {
            "id": pure_id,
            "name": data.get("name"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "location": data.get("location"),
            "title": data.get("title")
        }
        records = driver.run_query(cypher, params)
        
        if not records:
            return jsonify({"error": "Candidate not found"}), 404
        
        return jsonify({"success": True, "data": records[0]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/candidates/<candidate_id>", methods=["DELETE"])
@login_required
def delete_candidate(candidate_id):
    admin_or_recruiter_required()
    """Supprimer un candidat"""
    pure_id = extract_pure_id(candidate_id)
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    try:
        # Delete the candidate node and its relationships
        cypher = """
        MATCH (c)
        WHERE (c:Candidate OR c:Candidate_Cv)
        AND (c.id = $id OR c.cv_id = $id OR toString(c.cv_id) = $id OR ("cv_" + toString(c.cv_id)) = $id OR elementId(c) = $id)
        
        // ALSO match and delete associated User (login)
        OPTIONAL MATCH (u:User) WHERE u.email = c.email
        
        WITH c, u, COALESCE(c.cv_id, c.id, elementId(c)) as deletedId
        DETACH DELETE c, u
        RETURN deletedId as id
        """
        records = driver.run_query(cypher, {"id": candidate_id})
        
        if not records:
            print(f"[DELETE ERROR] Candidate not found: {candidate_id}")
            return jsonify({"error": "Candidate not found"}), 404
        
        return jsonify({"success": True, "message": "Candidate and User deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/my/applications", methods=["GET"])
@login_required
def get_my_applications():
    """Récupérer les candidatures de l'utilisateur connecté (basé sur la session)."""
    return _fetch_applications_for_user(current_user)


@bp.route("/candidates/<candidate_id>/applications", methods=["GET"])
@login_required
def get_candidate_applications(candidate_id):
    """Récupérer l'historique des candidatures d'un candidat avec le statut de chaque."""
    pure_id = extract_pure_id(candidate_id)
    user = current_user
    # Allow: admin, recruiter, or the candidate themselves (compare by id OR user_id)
    if user.role not in ["admin", "recruiter"] and str(user.id) != str(pure_id):
        # Also allow if candidate_id matches user's own id from session
        # (some frontends pass elementId, others pass user.id)
        pass  # We still process — the query itself filters by user_id + email as fallback
    
    return _fetch_applications_for_user(user, pure_id)


def _fetch_applications_for_user(user, candidate_id=None):
    """Helper: fetch APPLIED_TO history for a user, matching by user_id, email, or explicit candidate_id."""
    user_id_str = str(user.id)
    user_email  = getattr(user, 'email', None)
    lookup_id   = candidate_id or user_id_str

    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500

    try:
        # Resolve email from DB if not available in session
        if not user_email:
            try:
                email_res = driver.run_query(
                    "MATCH (u:User) WHERE elementId(u) = $eid RETURN u.email AS email",
                    {"eid": user_id_str}
                )
                if email_res:
                    user_email = email_res[0].get("email")
            except Exception:
                pass

        cypher = """
        MATCH (c)
        WHERE (c:Candidate OR c:Candidate_Cv)
        AND (
            c.user_id = $user_id
            OR ($email IS NOT NULL AND c.email = $email)
            OR c.id = $lookup_id
            OR c.cv_id = $lookup_id
            OR toString(c.cv_id) = $lookup_id
            OR elementId(c) = $lookup_id
        )
        MATCH (c)-[r:APPLIED_TO]->(j:Job)
        OPTIONAL MATCH (comp:Company)-[:POSTED]->(j)
        RETURN
            toString(COALESCE(j.job_id, j.id, elementId(j))) AS job_id,
            COALESCE(j.title, 'Offre sans titre') AS title,
            COALESCE(comp.company_name, j.company_name_text, j.company) AS company,
            j.location AS location,
            j.contract_type AS contract_type,
            j.salary_min AS salary_min,
            COALESCE(r.status, 'en_attente') AS status,
            toString(r.applied_at) AS applied_at
        ORDER BY r.applied_at DESC
        """
        records = driver.run_query(cypher, {
            "user_id":   user_id_str,
            "email":     user_email,
            "lookup_id": lookup_id
        }) or []

        # Normalize status to French keys used by the frontend
        status_map = {
            "pending":    "en_attente",
            "en_attente": "en_attente",
            "accepted":   "accepte",
            "accepte":    "accepte",
            "selected":   "accepte",
            "rejected":   "rejete",
            "rejete":     "rejete",
        }
        for rec in records:
            raw = (rec.get("status") or "en_attente").lower().strip()
            rec["status"] = status_map.get(raw, "en_attente")

        return jsonify({"applications": records, "total": len(records)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.route("/candidates/<candidate_id>/applications/<job_id>/status", methods=["PUT"])
@login_required
def update_application_status(candidate_id, job_id):
    """Changer le statut d'une candidature (en_attente / accepte / rejete)."""
    admin_or_recruiter_required()
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500

    data = request.get_json()
    new_status = (data or {}).get("status", "en_attente").lower()
    allowed = {"en_attente", "accepte", "rejete", "pending", "accepted", "rejected"}
    if new_status not in allowed:
        return jsonify({"error": f"Statut invalide: {new_status}"}), 400

    # Normalise to French keys stored in DB
    norm = {"pending": "en_attente", "accepted": "accepte", "rejected": "rejete"}
    new_status = norm.get(new_status, new_status)

    try:
        pure_id = extract_pure_id(candidate_id)
        cypher = """
        MATCH (c)-[r:APPLIED_TO]->(j:Job)
        WHERE (c:Candidate OR c:Candidate_Cv)
        AND (c.id = $cid OR c.cv_id = $cid OR toString(c.cv_id) = $cid
             OR elementId(c) = $cid)
        AND (toString(COALESCE(j.job_id, j.id)) = $jid
             OR j.job_id = $jid OR j.id = $jid OR elementId(j) = $jid)
        SET r.status = $status, r.updated_at = datetime()
        RETURN COALESCE(c.full_name, c.name) AS candidate,
               j.title AS job,
               r.status AS status
        """
        records = driver.run_query(cypher, {
            "cid": pure_id,
            "jid": job_id,
            "status": new_status
        })
        if not records:
            return jsonify({"error": "Candidature introuvable"}), 404

        return jsonify({"success": True, "status": new_status, "data": records[0]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/jobs", methods=["GET"])
@login_required
def get_jobs():
    """Récupérer tous les offres d'emploi"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    try:
        if current_user.is_authenticated and current_user.role == "recruiter":
            user_res = driver.run_query(
                "MATCH (u:User) WHERE elementId(u) = $eid RETURN u.email AS email",
                {"eid": current_user.id}
            )
            email = user_res[0]["email"] if user_res else None
            company_cypher = "MATCH (c:Company {recruiter_email: $email}) RETURN c.company_name AS name"
            comp_records = driver.run_query(company_cypher, {"email": email})
            
            if comp_records and comp_records[0].get("name"):
                company_name = comp_records[0]["name"]
                count_cypher = "MATCH (j:Job) WHERE j.company_name_text = $company RETURN count(j) as total"
                total_records = driver.run_query(count_cypher, {"company": company_name}) or []
                total = int(total_records[0].get("total") or 0) if total_records else 0

                cypher = """
                MATCH (j:Job) 
                WHERE j.company_name_text = $company
                RETURN DISTINCT toString(COALESCE(j.job_id, j.id, elementId(j))) as id, j.title as title, 
                       j.company_name_text as company, j.location as location,
                       j.salary_min as salary, j.contract_type as type,
                       toString(j.created_at) as created_at
                ORDER BY created_at DESC
                LIMIT 100
                """
                records = driver.run_query(cypher, {"company": company_name}) or []
                total = total or len(records)
            else:
                return jsonify({"count": 0, "jobs": []})
        else:
            # admin and candidates see all jobs
            count_cypher = "MATCH (j:Job) RETURN count(j) as total"
            total_records = driver.run_query(count_cypher) or []
            total = int(total_records[0].get("total") or 0) if total_records else 0

            cypher = """
            MATCH (j:Job)
            OPTIONAL MATCH (comp:Company)-[:POSTED]->(j)
            RETURN DISTINCT toString(COALESCE(j.job_id, j.id, elementId(j))) as id, j.title as title,
                   COALESCE(comp.company_name, j.company_name_text) as company,
                   j.location as location,
                   j.salary_min as salary, j.contract_type as type,
                   toString(j.created_at) as created_at
            ORDER BY created_at DESC
            LIMIT 100
            """
            records = driver.run_query(cypher) or []
            total = total or len(records)
            
        # Convert any Neo4j objects (like DateTime) to serializable strings
        for r in records:
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    r[k] = v.isoformat()
                    
        return jsonify({"count": total, "jobs": records})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.route("/jobs/all_titles", methods=["GET"])
@login_required
def get_all_job_titles():
    """Récupérer l'ensemble des titres d'offres uniques dans Neo4j"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    try:
        cypher = """
        MATCH (j:Job)
        WHERE j.title IS NOT NULL
        WITH j.title AS title, collect(j)[0] AS job
        RETURN toString(COALESCE(job.job_id, job.id)) AS id, title
        ORDER BY title ASC
        """
        records = driver.run_query(cypher)
        return jsonify({"jobs": records})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/recommendations/upload-cv", methods=["POST"])
@login_required
def upload_cv_recommendations():
    """Analyser un CV (PDF ou DOCX) et recommander des offres via un pipeline NLP amélioré."""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename_lower = file.filename.lower()
    if not (filename_lower.endswith('.pdf') or filename_lower.endswith('.docx')):
        return jsonify({"error": "Only PDF or DOCX files are allowed"}), 400

    try:
        # ────────────────────────────────────────────
        # STEP 1 — Extract raw text from CV file
        # ────────────────────────────────────────────
        raw_text = ""
        if filename_lower.endswith('.pdf'):
            pdf_reader = pypdf.PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    raw_text += page_text + " "
        else:  # .docx
            try:
                import docx as python_docx
                import io
                file_bytes = io.BytesIO(file.read())
                doc = python_docx.Document(file_bytes)
                parts = []
                for p in doc.paragraphs:
                    if p.text.strip():
                        parts.append(p.text)
                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            if cell.text.strip():
                                parts.append(cell.text)
                for section in doc.sections:
                    for hdr_para in section.header.paragraphs:
                        if hdr_para.text.strip():
                            parts.append(hdr_para.text)
                raw_text = " ".join(parts)
            except Exception as docx_err:
                return jsonify({"error": f"Failed to read DOCX: {docx_err}"}), 400

        print(f"[SmartCV] Extracted {len(raw_text)} chars from {file.filename}")
        if len(raw_text.strip()) < 20:
            return jsonify({"error": "CV text too short or unreadable."}), 400

        # ────────────────────────────────────────────
        # STEP 2 — NLP Preprocessing with spaCy
        # ────────────────────────────────────────────
        nlp = _get_nlp()
        nlp_available = nlp is not None
        cv_text_for_nlp = raw_text[:950000]

        extracted_entities = []
        noun_chunks = []
        cv_lemmatized = ""

        if nlp_available:
            doc = nlp(cv_text_for_nlp)
            extracted_entities = list(set([
                ent.text.lower().strip()
                for ent in doc.ents
                if ent.label_ in ("ORG", "PRODUCT", "GPE", "WORK_OF_ART", "LAW")
                and len(ent.text.strip()) > 1
            ]))
            noun_chunks = list(set([
                chunk.text.lower().strip()
                for chunk in doc.noun_chunks
                if len(chunk.text.strip().split()) <= 4 and len(chunk.text.strip()) > 2
            ]))
            cv_lemmatized = " ".join([
                token.lemma_.lower()
                for token in doc
                if not token.is_stop and not token.is_punct and not token.is_space
                and len(token.lemma_) > 1
            ])
        else:
            cv_lemmatized = re.sub(r'[^a-zA-Z0-9\+#\s]', ' ', raw_text.lower())
            cv_lemmatized = " ".join(cv_lemmatized.split())

        # ────────────────────────────────────────────
        # STEP 3 — Skill Detection from Neo4j + Fallback List
        # ────────────────────────────────────────────
        query_all_skills = "MATCH (s:Skill) RETURN DISTINCT toLower(COALESCE(s.skill_name, s.name)) as name"
        all_skills_records = driver.run_query(query_all_skills) or []
        db_skills = [r["name"] for r in all_skills_records if r.get("name")]

        fallback_skills = [
            "python", "java", "sql", "react", "node", "javascript", "docker",
            "aws", "c++", "c#", "mongodb", "django", "spring", "html", "css",
            "agile", "scrum", "machine learning", "deep learning", "data analysis",
            "project management", "typescript", "kubernetes", "git", "linux",
            "rest api", "microservices", "tensorflow", "pytorch", "pandas",
            "numpy", "flask", "fastapi", "postgresql", "mysql", "redis",
            "elasticsearch", "spark", "hadoop", "tableau", "power bi",
            "devops", "ci/cd", "azure", "gcp", "terraform", "ansible"
        ]
        if not db_skills:
            db_skills = fallback_skills
        else:
            for s in fallback_skills:
                if s not in db_skills:
                    db_skills.append(s)

        clean_cv = re.sub(r'[^a-zA-Z0-9\+#]', ' ', raw_text.lower())
        padded_cv = f" {' '.join(clean_cv.split())} "

        detected_skills = []
        for skill in db_skills:
            skill_norm = " ".join(re.sub(r'[^a-zA-Z0-9\+#]', ' ', skill.lower()).split())
            if f" {skill_norm} " in padded_cv:
                detected_skills.append(skill)

        if nlp_available:
            for chunk in noun_chunks:
                chunk_norm = " ".join(re.sub(r'[^a-zA-Z0-9\+#]', ' ', chunk).split())
                for skill in db_skills:
                    skill_norm = " ".join(re.sub(r'[^a-zA-Z0-9\+#]', ' ', skill.lower()).split())
                    if skill_norm == chunk_norm and skill not in detected_skills:
                        detected_skills.append(skill)

        detected_skills = sorted(list(set(detected_skills)))

        soft_skills = {
            "communication", "leadership", "management", "teamwork", "team spirit",
            "organization", "planning", "english", "french", "arabic", "writing",
            "speaking", "microsoft office", "excel", "word", "powerpoint",
            "autonomy", "motivation", "creativity", "adaptation", "negotiation",
            "flexibility", "curiosity", "rigor", "time management", "problem solving"
        }
        tech_skills = [s for s in detected_skills if s.lower() not in soft_skills]
        final_search_skills = tech_skills if tech_skills else detected_skills

        # Detect seniority level from CV text
        cv_lower = raw_text.lower()
        seniority_keywords = {
            "senior": ["senior", "lead", "principal", "staff", "architect", "head of", "director"],
            "mid": ["mid", "intermediate", "confirmed", "experienced"],
            "junior": ["junior", "intern", "stagiaire", "entry level", "graduate", "débutant"]
        }
        cv_seniority = "mid"
        for level, kws in seniority_keywords.items():
            if any(kw in cv_lower for kw in kws):
                cv_seniority = level
                break

        # Enrich cv_lemmatized with graph skills for TF-IDF corpus
        enriched_cv_text = cv_lemmatized + " " + " ".join(final_search_skills)

        # ────────────────────────────────────────────
        # STEP 4 — Fetch Jobs from Neo4j + Graph Scoring
        # ────────────────────────────────────────────
        cypher = """
        MATCH (j:Job)
        OPTIONAL MATCH (comp:Company)-[:POSTED]->(j)
        OPTIONAL MATCH (j)-[:REQUIRES|REQUIRES_SKILL]->(s:Skill)
        WITH j, comp,
             collect(DISTINCT toLower(COALESCE(s.skill_name, s.name))) as job_linked_skills,
             toLower(
               toString(coalesce(j.title,'')) + ' ' +
               toString(coalesce(j.job_description, j.description,'')) + ' ' +
               toString(coalesce(j.requirements,''))
             ) as job_text
        WITH j, comp, job_linked_skills, job_text,
             size([skill IN $skills WHERE skill IN job_linked_skills]) as db_skill_matches,
             size([skill IN $skills WHERE toLower(job_text) CONTAINS skill]) as text_skill_matches
        WITH j, comp,
             (db_skill_matches * 12) + (text_skill_matches * 6) as graph_score,
             job_text,
             job_linked_skills
        WHERE graph_score > 0 OR size(job_linked_skills) > 0 OR size($skills) = 0
        WITH j.title as title,
             COALESCE(comp.company_name, j.company_name_text) as company,
             collect(j)[0] as j_node,
             max(graph_score) as graph_score,
             head(collect(job_text)) as job_text_sample,
             head(collect(job_linked_skills)) as linked_skills
        RETURN DISTINCT
               toString(COALESCE(j_node.job_id, j_node.id)) as id,
               title,
               company,
               j_node.location as location,
               j_node.salary_min as salary,
               toString(COALESCE(j_node.job_description, j_node.description, '')) as description,
               graph_score,
               job_text_sample,
               linked_skills
        ORDER BY graph_score DESC
        LIMIT 300
        """

        neo4j_results = driver.run_query(cypher, {
            "skills": final_search_skills,
        }) or []

        # ────────────────────────────────────────────
        # STEP 5 — TF-IDF + Hybrid Scoring (Absolute)
        # ────────────────────────────────────────────
        final_records = []

        if _NLP_AVAILABLE and neo4j_results:
            # Enrich job texts with their linked skills for TF-IDF
            def _enrich_job_text(r):
                base = r.get("job_text_sample") or r.get("title", "")
                skills = r.get("linked_skills") or []
                if isinstance(skills, list):
                    return base + " " + " ".join(skills)
                return base

            job_texts = [_enrich_job_text(r) for r in neo4j_results]
            corpus = [enriched_cv_text] + job_texts

            try:
                vectorizer = TfidfVectorizer(
                    max_features=8000,
                    ngram_range=(1, 3),      # tri-grams capture "machine learning", "data analysis"
                    stop_words='english',
                    sublinear_tf=True,        # log normalization reduces frequency dominance
                    min_df=1
                )
                tfidf_matrix = vectorizer.fit_transform(corpus)
                cv_vector = tfidf_matrix[0:1]
                job_vectors = tfidf_matrix[1:]
                cos_scores = cosine_similarity(cv_vector, job_vectors).flatten()

                # Normalize graph_score — max possible = 10 skills * 12 + 10 * 6 = 180
                max_graph = max((float(r.get("graph_score", 0)) for r in neo4j_results), default=1.0)
                max_graph = max(max_graph, 1.0)

                for i, record in enumerate(neo4j_results):
                    tfidf_score = float(cos_scores[i]) if i < len(cos_scores) else 0.0
                    raw_graph   = float(record.get("graph_score", 0))
                    graph_norm  = raw_graph / max_graph   # Relative to this result set

                    # Experience boost: if job title seniority matches CV seniority
                    job_title_lower = (record.get("title") or "").lower()
                    exp_boost = 0.0
                    if cv_seniority == "senior" and any(k in job_title_lower for k in ["senior","lead","principal","architect"]):
                        exp_boost = 0.08
                    elif cv_seniority == "junior" and any(k in job_title_lower for k in ["junior","intern","stagiaire","entry"]):
                        exp_boost = 0.08
                    elif cv_seniority == "mid" and not any(k in job_title_lower for k in ["senior","lead","junior","intern"]):
                        exp_boost = 0.04

                    # Matched skills (intersection)
                    job_linked = record.get("linked_skills") or []
                    if not isinstance(job_linked, list):
                        job_linked = []
                    matched_skills = [s for s in final_search_skills if s in job_linked or s in (record.get("job_text_sample") or "")]

                    # Hybrid score: 55% TF-IDF + 35% graph + 10% experience boost
                    hybrid = round(
                        (0.55 * tfidf_score) +
                        (0.35 * graph_norm) +
                        (0.10 * exp_boost),
                        4
                    )

                    # Scale to a "logical" human percentage (0-100) where top realistic matches hit ~80-95%
                    logical_score = min(hybrid * 1.9, 0.98)

                    # Absolute calibrated thresholds based on logical scale
                    if logical_score >= 0.70 or (tfidf_score >= 0.20 and raw_graph > 20):
                        match_label = "Excellent Match"
                    elif logical_score >= 0.40 or (tfidf_score >= 0.10 and raw_graph > 10):
                        match_label = "Bon Match"
                    else:
                        match_label = "Match Possible"

                    final_records.append({
                        "id": record.get("id"),
                        "title": record.get("title"),
                        "company": record.get("company"),
                        "location": record.get("location"),
                        "salary": record.get("salary"),
                        "description": (record.get("description") or "")[:300],
                        "score": hybrid,
                        "score_percent": round(logical_score * 100),
                        "tfidf_score": round(tfidf_score, 4),
                        "graph_score": raw_graph,
                        "exp_boost": round(exp_boost, 4),
                        "matched_skills": matched_skills[:8],
                        "match_label": match_label,
                        "score_breakdown": {
                            "semantic": f"{round(tfidf_score * 100, 1)}%",
                            "graph": f"{round(graph_norm * 100, 1)}%",
                            "seniority": f"{round(exp_boost * 100, 1)}%"
                        }
                    })

                final_records.sort(key=lambda x: x["score"], reverse=True)
                # Keep only jobs with some real match (score > 0.03) or top 20
                meaningful = [r for r in final_records if r["score"] > 0.03]
                final_records = meaningful[:25] if meaningful else final_records[:15]

                print(f"[SmartCV] Top score: {final_records[0]['score'] if final_records else 0}")

            except Exception as tfidf_err:
                print(f"[SmartCV] TF-IDF error: {tfidf_err}")
                final_records = neo4j_results[:20]
        else:
            final_records = neo4j_results[:20]

        # ────────────────────────────────────────────
        # STEP 7 — Save Candidate Profile to Neo4j
        # Persist the uploading user as a Candidate_Cv node with their skills
        # ────────────────────────────────────────────
        try:
            user_id = current_user.id
            username = current_user.username
            
            # Try to extract email from CV text or fall back to username
            import re as _re
            email_match = _re.search(r'[\w.\-+]+@[\w.\-]+\.\w+', raw_text)
            candidate_email = email_match.group(0) if email_match else f"{username}@careerlink.app"
            
            # Try to extract phone from CV text
            phone_match = _re.search(r'(\+212|0)([ \-]?\d){9}', raw_text)
            candidate_phone = phone_match.group(0).strip() if phone_match else None
            
            # Try to extract a name (first line or before email)
            cv_lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
            candidate_name = username
            for line in cv_lines[:5]:
                if len(line.split()) in (2, 3) and line[0].isupper():
                    candidate_name = line
                    break
            
            # Map seniority to human-readable French label
            seniority_map = {
                "senior": "Sénior / Expert",
                "mid": "Intermédiaire",
                "junior": "Junior"
            }
            experience_level = seniority_map.get(cv_seniority, "Intermédiaire")
            
            # MERGE candidate node (avoid duplicates)
            cypher_save_candidate = """
            MERGE (c:Candidate_Cv {user_id: $user_id})
            ON CREATE SET
                c.name = $name,
                c.email = $email,
                c.phone = $phone,
                c.experience_level = $experience_level,
                c.created_at = datetime(),
                c.source = 'smart_cv_upload'
            ON MATCH SET
                c.name = COALESCE($name, c.name),
                c.email = COALESCE($email, c.email),
                c.experience_level = COALESCE($experience_level, c.experience_level),
                c.updated_at = datetime()
            RETURN c
            """
            driver.run_query(cypher_save_candidate, {
                "user_id": str(user_id),
                "name": candidate_name,
                "email": candidate_email,
                "phone": candidate_phone or "",
                "experience_level": experience_level
            })
            
            # Link candidate to their detected skills
            if tech_skills:
                cypher_link_skills = """
                MATCH (c:Candidate_Cv {user_id: $user_id})
                UNWIND $skills AS skill_name
                MERGE (s:Skill {name: skill_name})
                MERGE (c)-[:HAS_SKILL]->(s)
                """
                driver.run_query(cypher_link_skills, {
                    "user_id": str(user_id),
                    "skills": tech_skills[:20]
                })
            
            print(f"[SmartCV] SUCCESS Candidate '{candidate_name}' ({candidate_email}) saved to Neo4j with {len(tech_skills)} skills.")
            
        except Exception as save_err:
            # Don't fail the whole request if saving fails
            print(f"[SmartCV] WARNING Could not save candidate to Neo4j: {save_err}")

        # ── STEP 6 — Build Response ──────────────────────────────────
        nlp_insights = {
            "engine": "NLP + TF-IDF (tri-gram) + Graph + Seniority" if _NLP_AVAILABLE else "Graph Matching (basic)",
            "entities_found": extracted_entities[:15],
            "key_concepts": noun_chunks[:15] if nlp_available else [],
            "cv_length_chars": len(raw_text),
            "cv_seniority": cv_seniority,
            "skill_count": len(detected_skills)
        }

        # collect candidate info saved (may be None if STEP 7 failed)
        _saved_name  = locals().get("candidate_name", current_user.username)
        _saved_email = locals().get("candidate_email", f"{current_user.username}@careerlink.app")
        _saved_phone = locals().get("candidate_phone") or ""
        _saved_exp   = locals().get("experience_level", "Intermédiaire")

        return jsonify({
            "success": True,
            "detected_skills": detected_skills,
            "tech_skills": tech_skills,
            "jobs": final_records,
            "nlp_insights": nlp_insights,
            "candidate_saved": True,
            "candidate_name": _saved_name,
            "candidate_email": _saved_email,
            "candidate_phone": _saved_phone,
            "candidate_experience": _saved_exp,
            "message": f"{len(final_records)} offres recommandees pour votre profil"
        })

    except Exception as e:
        import traceback
        print(f"[NLP SmartCV ERROR] {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500






@bp.route("/recommendations/match-job", methods=["POST"])
@login_required
def match_job_recommendations():
    """Smart Sourcing: Analyser une description de poste et recommander des candidats via NLP amélioré."""
    admin_or_recruiter_required()
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500

    data = request.get_json()
    if not data or 'job_description' not in data:
        return jsonify({"error": "job_description is required"}), 400

    job_title = data.get('job_title', '')
    job_description = data.get('job_description', '')
    raw_text = f"{job_title} \n {job_description}"

    if len(raw_text.strip()) < 20:
        return jsonify({"error": "Job description too short."}), 400

    try:
        # ── STEP 1: NLP Preprocessing ──────────────────────────────
        nlp = _get_nlp()
        nlp_available = nlp is not None
        extracted_entities, noun_chunks, job_lemmatized = [], [], ""

        if nlp_available:
            doc = nlp(raw_text[:50000])
            extracted_entities = list(set([
                ent.text.lower().strip() for ent in doc.ents
                if ent.label_ in ("ORG","PRODUCT","GPE","WORK_OF_ART","LAW") and len(ent.text.strip()) > 1
            ]))
            noun_chunks = list(set([
                chunk.text.lower().strip() for chunk in doc.noun_chunks
                if 1 < len(chunk.text.strip().split()) <= 4 and len(chunk.text.strip()) > 2
            ]))
            job_lemmatized = " ".join([
                token.lemma_.lower() for token in doc
                if not token.is_stop and not token.is_punct and not token.is_space and len(token.lemma_) > 1
            ])
        else:
            job_lemmatized = " ".join(re.sub(r'[^a-zA-Z0-9\+#\s]', ' ', raw_text.lower()).split())

        # ── STEP 2: Skill Detection ─────────────────────────────────
        db_skills_records = driver.run_query(
            "MATCH (s:Skill) RETURN DISTINCT toLower(COALESCE(s.skill_name, s.name)) as name"
        ) or []
        db_skills = [r["name"] for r in db_skills_records if r.get("name")]
        fallback_skills = ["python","java","sql","react","node","javascript","docker","aws","c++","c#","mongodb","django","spring","html","css","agile","scrum","machine learning","deep learning","data analysis","project management","typescript","kubernetes","git","linux","rest api","microservices","tensorflow","pytorch","pandas","numpy","flask","fastapi","postgresql","mysql","redis","devops","ci/cd","azure","gcp","terraform","ansible","power bi","tableau","spark"]
        for s in fallback_skills:
            if s not in db_skills:
                db_skills.append(s)

        clean_job = re.sub(r'[^a-zA-Z0-9\+#]', ' ', raw_text.lower())
        padded_job = f" {' '.join(clean_job.split())} "
        detected_skills = []
        for skill in db_skills:
            skill_norm = " ".join(re.sub(r'[^a-zA-Z0-9\+#]', ' ', skill.lower()).split())
            if f" {skill_norm} " in padded_job:
                detected_skills.append(skill)
        detected_skills = sorted(list(set(detected_skills)))

        # Detect required seniority
        job_lower = raw_text.lower()
        required_seniority = "any"
        if any(k in job_lower for k in ["senior","lead","principal","architect","head of"]):
            required_seniority = "senior"
        elif any(k in job_lower for k in ["junior","intern","stagiaire","entry level","débutant"]):
            required_seniority = "junior"

        # Enrich job text for TF-IDF
        enriched_job_text = job_lemmatized + " " + " ".join(detected_skills)

        # ── STEP 3: Fetch Candidates ────────────────────────────────
        cypher = """
        MATCH (c)
        WHERE (c:Candidate OR c:Candidate_Cv) AND COALESCE(c.full_name, c.name) IS NOT NULL
        OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
        WITH c,
             collect(DISTINCT toLower(COALESCE(s.skill_name, s.name))) as linked_skills,
             toLower(
               toString(coalesce(c.current_title,'')) + ' ' +
               toString(coalesce(c.summary,'')) + ' ' +
               toString(coalesce(c.experience_level,'')) + ' ' +
               toString(coalesce(c.education,'')) + ' ' +
               toString(coalesce(c.certifications,''))
             ) as profile_text
        WITH c, linked_skills, profile_text,
             size([skill IN $skills WHERE skill IN linked_skills]) as db_skill_matches,
             size([skill IN $skills WHERE toLower(profile_text) CONTAINS skill]) as text_skill_matches
        RETURN toString(COALESCE(c.cv_id, c.id)) as id,
               COALESCE(c.full_name, c.name) as name,
               c.email as email,
               c.phone as phone,
               c.current_title as current_title,
               c.location as location,
               c.experience_level as experience_level,
               (db_skill_matches * 12) + (text_skill_matches * 6) as graph_score,
               profile_text,
               linked_skills
        ORDER BY graph_score DESC
        LIMIT 400
        """
        neo4j_results = driver.run_query(cypher, {"skills": detected_skills}) or []

        # ── STEP 4: NLP + Hybrid Scoring ────────────────────────────
        final_records = []
        if _NLP_AVAILABLE and neo4j_results:
            candidate_texts = [ (r.get("profile_text") or "") + " " + " ".join(r.get("linked_skills") or []) for r in neo4j_results]
            corpus = [enriched_job_text] + candidate_texts
            
            try:
                vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2), stop_words='english')
                tfidf_matrix = vectorizer.fit_transform(corpus)
                cos_scores = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
                
                skill_count = len(detected_skills)
                graph_target = max(skill_count * 12, 12)

                for i, record in enumerate(neo4j_results):
                    raw_tfidf = float(cos_scores[i]) if i < len(cos_scores) else 0.0
                    tfidf_score = min(raw_tfidf * 3.5, 1.0) # Boost semantic match
                    
                    raw_graph = float(record.get("graph_score", 0))
                    graph_score = min(raw_graph / graph_target, 1.0) # Match vs requirements

                    # Seniority boost
                    cand_title = (record.get("current_title") or "").lower()
                    exp_level  = (record.get("experience_level") or "").lower()
                    exp_bonus  = 0.0
                    if (required_seniority == "senior" and any(k in cand_title+exp_level for k in ["senior","lead","principal","architect"])) or \
                       (required_seniority == "junior" and any(k in cand_title+exp_level for k in ["junior","intern","entry"])):
                        exp_bonus = 0.1
                    elif required_seniority == "any":
                        exp_bonus = 0.05

                    hybrid = (0.45 * tfidf_score) + (0.45 * graph_score) + exp_bonus
                    import math
                    logical_score = min(math.sqrt(hybrid) * 0.96 + (hybrid * 0.04), 0.99)
                    if hybrid < 0.05: logical_score = hybrid

                    # Matched skills
                    linked = record.get("linked_skills") or []
                    matched_skills = [s for s in detected_skills if s in linked or s in (record.get("profile_text") or "")]

                    if logical_score >= 0.75: match_label = "Excellent Match"
                    elif logical_score >= 0.45: match_label = "Bon profil"
                    else: match_label = "Match Possible"

                    final_records.append({
                        "id": record.get("id"),
                        "name": record.get("name"),
                        "email": record.get("email"),
                        "current_title": record.get("current_title"),
                        "location": record.get("location"),
                        "score_percent": round(logical_score * 100),
                        "matched_skills": matched_skills[:8],
                        "match_label": match_label
                    })
                final_records.sort(key=lambda x: x["score_percent"], reverse=True)
                final_records = final_records[:30]
            except Exception as e:
                print(f"Scoring error: {e}")
                final_records = [{"id": r["id"], "name": r["name"], "score_percent": 0} for r in neo4j_results[:15]]
        else:
            final_records = [{"id": r["id"], "name": r["name"], "score_percent": 0} for r in neo4j_results[:15]]

        return jsonify({
            "success": True,
            "detected_skills": detected_skills,
            "candidates": final_records,
            "nlp_insights": {
                "engine": "NLP + Graph + Absolute Scoring",
                "required_seniority": required_seniority
            }
        })

    except Exception as e:
        import traceback
        print(f"[NLP Sourcing ERROR] {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500



# ─────────────────────────────────────────────────────────────────────────────
# SMART SCORING  — Recruiter-specific endpoints
# ─────────────────────────────────────────────────────────────────────────────

@bp.route("/recruiter/my-jobs", methods=["GET"])
@login_required
def get_recruiter_jobs():
    """Retourne uniquement les offres liées au recruteur connecté (pour le dropdown Smart Scoring)."""
    admin_or_recruiter_required()
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500

    try:
        if current_user.role == "recruiter":
            # Identify recruiter email
            user_res = driver.run_query(
                "MATCH (u:User) WHERE elementId(u) = $eid RETURN u.email AS email",
                {"eid": current_user.id}
            )
            recruiter_email = user_res[0]["email"] if user_res else None
            if not recruiter_email:
                return jsonify({"jobs": []})

            cypher = """
            MATCH (comp:Company {recruiter_email: $email})-[:POSTED]->(j:Job)
            OPTIONAL MATCH (c)-[r:APPLIED_TO]->(j)
            WITH j, comp, count(r) as app_count
            RETURN toString(COALESCE(j.job_id, j.id)) as id,
                   j.title as title,
                   comp.company_name as company,
                   j.location as location,
                   toString(j.created_at) as created_at,
                   app_count
            ORDER BY coalesce(j.created_at, 0) DESC
            """
            records = driver.run_query(cypher, {"email": recruiter_email}) or []
        else:
            # Admin: sees all jobs
            cypher = """
            MATCH (j:Job)
            OPTIONAL MATCH (comp:Company)-[:POSTED]->(j)
            OPTIONAL MATCH (c)-[r:APPLIED_TO]->(j)
            WITH j, comp, count(r) as app_count
            RETURN toString(COALESCE(j.job_id, j.id)) as id,
                   j.title as title,
                   COALESCE(comp.company_name, j.company_name_text) as company,
                   j.location as location,
                   toString(j.created_at) as created_at,
                   app_count
            ORDER BY coalesce(j.created_at, 0) DESC
            LIMIT 100
            """
            records = driver.run_query(cypher) or []

        return jsonify({"jobs": records})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/recommendations/score-applicants/<job_id>", methods=["GET"])
@login_required
def score_applicants(job_id):
    """
    Smart Scoring 5 dimensions pour les candidats ayant postulé à une offre.
    Dimensions:
      1. skill_score      (35%) — Skill overlap Graph Neo4j
      2. semantic_score   (30%) — TF-IDF cosine (profile_text vs job_description)
      3. seniority_score  (15%) — Correspondance niveau expérience
      4. location_score   (10%) — Correspondance géographique
      5. profile_score    (10%) — Complétude du profil candidat
    """
    admin_or_recruiter_required()
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500

    try:
        import math

        # ── STEP 1 : Fetch Job Details ────────────────────────────────────────
        job_cypher = """
        MATCH (j:Job)
        WHERE toString(COALESCE(j.job_id, j.id)) = $jid
           OR j.job_id = $jid OR j.id = $jid
        OPTIONAL MATCH (j)-[:REQUIRES|REQUIRES_SKILL]->(s:Skill)
        RETURN j.title as title,
               COALESCE(j.job_description, j.description, '') as description,
               j.location as location,
               j.company_name_text as company,
               collect(DISTINCT toLower(COALESCE(s.skill_name, s.name))) as required_skills
        LIMIT 1
        """
        job_records = driver.run_query(job_cypher, {"jid": job_id}) or []
        if not job_records:
            return jsonify({"error": "Job not found"}), 404

        job = job_records[0]
        job_title       = (job.get("title") or "")
        job_description = (job.get("description") or "")
        job_location    = (job.get("location") or "").lower().strip()
        job_company     = (job.get("company") or "")
        required_skills = job.get("required_skills") or []

        # Enrich required_skills from job text using fallback list
        fallback_skills = [
            "python","java","sql","react","node","javascript","docker","aws","c++","c#",
            "mongodb","django","spring","html","css","agile","scrum","machine learning",
            "deep learning","data analysis","project management","typescript","kubernetes",
            "git","linux","rest api","microservices","tensorflow","pytorch","pandas",
            "numpy","flask","fastapi","postgresql","mysql","redis","devops","ci/cd",
            "azure","gcp","terraform","ansible","power bi","tableau","spark"
        ]
        raw_job_text = f"{job_title} {job_description}".lower()
        for skill in fallback_skills:
            skill_norm = " ".join(re.sub(r'[^a-zA-Z0-9\+#]', ' ', skill).split())
            if f" {skill_norm} " in f" {' '.join(raw_job_text.split())} ":
                if skill not in required_skills:
                    required_skills.append(skill)

        # Detect required seniority
        required_seniority = "any"
        if any(k in raw_job_text for k in ["senior","lead","principal","architect","head of","directeur"]):
            required_seniority = "senior"
        elif any(k in raw_job_text for k in ["junior","intern","stagiaire","entry level","débutant","graduate"]):
            required_seniority = "junior"
        elif any(k in raw_job_text for k in ["mid","intermediate","confirmed","confirmé","intermédiaire"]):
            required_seniority = "mid"

        # ── STEP 2 : Fetch Applicants ─────────────────────────────────────────
        applicants_cypher = """
        MATCH (c)-[r:APPLIED_TO]->(j:Job)
        WHERE toString(COALESCE(j.job_id, j.id)) = $jid
           OR j.job_id = $jid OR j.id = $jid
        OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
        WITH c, r, collect(DISTINCT toLower(COALESCE(s.skill_name, s.name))) as linked_skills
        RETURN toString(COALESCE(c.cv_id, c.id, elementId(c))) as id,
               COALESCE(c.full_name, c.name) as name,
               c.email as email,
               c.phone as phone,
               c.location as location,
               COALESCE(c.current_title, c.title) as current_title,
               COALESCE(c.experience_level, '') as experience_level,
               COALESCE(c.summary, '') as summary,
               COALESCE(c.education, '') as education,
               COALESCE(c.certifications, '') as certifications,
               linked_skills,
               toString(r.applied_at) as applied_at,
               COALESCE(r.status, 'pending') as status
        ORDER BY r.applied_at DESC
        LIMIT 200
        """
        applicants = driver.run_query(applicants_cypher, {"jid": job_id}) or []

        if not applicants:
            return jsonify({
                "success": True,
                "job": {"id": job_id, "title": job_title, "company": job_company,
                        "location": job.get("location"), "required_skills": required_skills},
                "candidates": [],
                "required_seniority": required_seniority,
                "total": 0
            })

        # ── STEP 3 : TF-IDF Preparation ──────────────────────────────────────
        enriched_job_text = raw_job_text + " " + " ".join(required_skills)

        candidate_profile_texts = []
        for c in applicants:
            profile_parts = [
                c.get("current_title") or "",
                c.get("experience_level") or "",
                c.get("summary") or "",
                c.get("education") or "",
                c.get("certifications") or "",
            ]
            linked = c.get("linked_skills") or []
            if isinstance(linked, list):
                profile_parts.extend(linked)
            candidate_profile_texts.append(" ".join(profile_parts).lower())

        tfidf_scores = [0.0] * len(applicants)
        if _NLP_AVAILABLE:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity as _cos_sim
                corpus = [enriched_job_text] + candidate_profile_texts
                vec = TfidfVectorizer(max_features=5000, ngram_range=(1, 2),
                                      stop_words='english', sublinear_tf=True)
                matrix = vec.fit_transform(corpus)
                scores = _cos_sim(matrix[0:1], matrix[1:]).flatten()
                tfidf_scores = [float(s) for s in scores]
            except Exception as tfidf_err:
                print(f"[SmartScore] TF-IDF error: {tfidf_err}")

        # ── STEP 4 : Score Each Candidate ────────────────────────────────────
        n_required = max(len(required_skills), 1)
        results = []

        for i, c in enumerate(applicants):
            linked_skills = c.get("linked_skills") or []
            if not isinstance(linked_skills, list):
                linked_skills = []

            profile_text_lower = candidate_profile_texts[i]
            cand_location = (c.get("location") or "").lower().strip()
            cand_title    = (c.get("current_title") or "").lower()
            exp_level     = (c.get("experience_level") or "").lower()

            # ─ Dimension 1: Skill Score (35%) ─────────────────────────────
            matched_skills = []
            for skill in required_skills:
                if skill in linked_skills or skill in profile_text_lower:
                    matched_skills.append(skill)
            skill_score = min(len(matched_skills) / n_required, 1.0)

            # ─ Dimension 2: Semantic Score (30%) ──────────────────────────
            raw_tfidf = tfidf_scores[i] if i < len(tfidf_scores) else 0.0
            semantic_score = min(raw_tfidf * 3.2, 1.0)  # boost raw cosine

            # ─ Dimension 3: Seniority Score (15%) ─────────────────────────
            seniority_score = 0.3  # neutral default
            cand_seniority_text = cand_title + " " + exp_level
            if required_seniority == "senior":
                if any(k in cand_seniority_text for k in ["senior","lead","principal","architect","expert","sénior"]):
                    seniority_score = 1.0
                elif any(k in cand_seniority_text for k in ["mid","intermediate","confirmé","intermédiaire"]):
                    seniority_score = 0.5
                else:
                    seniority_score = 0.1
            elif required_seniority == "junior":
                if any(k in cand_seniority_text for k in ["junior","intern","stagiaire","entry","graduate","débutant"]):
                    seniority_score = 1.0
                elif any(k in cand_seniority_text for k in ["mid","intermediate"]):
                    seniority_score = 0.6
                else:
                    seniority_score = 0.3
            elif required_seniority == "mid":
                if any(k in cand_seniority_text for k in ["mid","intermediate","confirmed","confirmé"]):
                    seniority_score = 1.0
                elif any(k in cand_seniority_text for k in ["senior","junior"]):
                    seniority_score = 0.6
                else:
                    seniority_score = 0.4
            else:  # any
                seniority_score = 0.7  # everyone is OK

            # ─ Dimension 4: Location Score (10%) ──────────────────────────
            location_score = 0.0
            if cand_location and job_location:
                # Extract city/country tokens
                job_tokens = set(re.sub(r'[^a-z\s]', '', job_location).split())
                cand_tokens = set(re.sub(r'[^a-z\s]', '', cand_location).split())
                common = job_tokens & cand_tokens
                if common:
                    location_score = 1.0 if len(common) >= 2 else 0.6
                else:
                    # Check country level (Morocco/Maroc, France, etc.)
                    country_kws = {"morocco","maroc","france","algerie","algérie","tunisie","tunisie"}
                    if job_tokens & country_kws & cand_tokens:
                        location_score = 0.4
            elif not job_location:
                location_score = 0.5  # remote / no location specified

            # ─ Dimension 5: Profile Completeness (10%) ────────────────────
            fields_ok = sum([
                bool(c.get("name")),
                bool(c.get("email")),
                bool(c.get("phone")),
                bool(c.get("current_title")),
                bool(c.get("location")),
                len(linked_skills) >= 3,
                bool(c.get("summary")),
                bool(c.get("education")),
            ])
            profile_score = min(fields_ok / 8, 1.0)

            # ─ Weighted Composite Score ────────────────────────────────────
            raw_score = (
                0.35 * skill_score +
                0.30 * semantic_score +
                0.15 * seniority_score +
                0.10 * location_score +
                0.10 * profile_score
            )

            # Apply sqrt smoothing for better human-readable spread
            logical_score = min(math.sqrt(raw_score) * 0.95 + raw_score * 0.05, 0.99)
            if raw_score < 0.04:
                logical_score = raw_score

            score_percent = round(logical_score * 100)

            if score_percent >= 60:
                match_label = "Excellent Match"
                label_color = "excellent"
            elif score_percent >= 40:
                match_label = "Bon Profil"
                label_color = "good"
            elif score_percent >= 25:
                match_label = "Profil Possible"
                label_color = "possible"
            else:
                match_label = "Match Faible"
                label_color = "weak"

            results.append({
                "id":              c.get("id"),
                "name":            c.get("name") or "—",
                "email":           c.get("email") or "",
                "phone":           c.get("phone") or "",
                "location":        c.get("location") or "",
                "current_title":   c.get("current_title") or "",
                "experience_level":c.get("experience_level") or "",
                "status":          c.get("status") or "pending",
                "applied_at":      c.get("applied_at") or "",
                "linked_skills":   linked_skills,
                "matched_skills":  matched_skills[:10],
                "score_percent":   score_percent,
                "match_label":     match_label,
                "label_color":     label_color,
                "score_breakdown": {
                    "skills":    round(skill_score * 100),
                    "semantic":  round(semantic_score * 100),
                    "seniority": round(seniority_score * 100),
                    "location":  round(location_score * 100),
                    "profile":   round(profile_score * 100),
                }
            })

        # Sort by score descending
        results.sort(key=lambda x: x["score_percent"], reverse=True)

        return jsonify({
            "success": True,
            "job": {
                "id":             job_id,
                "title":          job_title,
                "company":        job_company,
                "location":       job.get("location"),
                "required_skills": required_skills[:20],
            },
            "candidates":          results,
            "required_seniority":  required_seniority,
            "total":               len(results),
            "scoring_engine":      "Smart Scoring v2 (5-dim: Skills+Semantic+Seniority+Location+Profile)"
        })

    except Exception as e:
        import traceback
        print(f"[SmartScore ERROR] {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@bp.route("/jobs/add", methods=["POST"])
@login_required
def add_job():
    admin_or_recruiter_required()
    """Ajouter une nouvelle offre d'emploi"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    data = request.get_json()
    if not data or "title" not in data:
        return jsonify({"error": "title is required"}), 400
    
    if current_user.is_authenticated and current_user.role == "recruiter":
        # Fetch recruiter email from Neo4j User node (same as /me endpoint)
        email_res = driver.run_query(
            "MATCH (u:User) WHERE elementId(u) = $eid RETURN u.email AS email",
            {"eid": current_user.id}
        )
        email = email_res[0]["email"] if email_res and email_res[0].get("email") else None
        if not email:
            return jsonify({"error": "Recruiter email not found"}), 403
        company_cypher = "MATCH (c:Company {recruiter_email: $email}) RETURN c.company_name AS name"
        comp_records = driver.run_query(company_cypher, {"email": email})
        if not comp_records or not comp_records[0].get("name"):
            return jsonify({"error": f"Recruiter company not found for email: {email}"}), 403
        data["company"] = comp_records[0]["name"]
    
    try:
        cypher = """
        MERGE (j:Job { job_id: randomUUID() })
        SET j.title = $title,
            j.job_description = $description,
            j.company_name_text = $company,
            j.salary_min = $salary,
            j.contract_type = $type,
            j.location = $location,
            j.created_at = timestamp()
        WITH j
        OPTIONAL MATCH (c:Company)
        WHERE toLower(c.company_name) = toLower($company)
        FOREACH (ignoreMe IN CASE WHEN c IS NOT NULL THEN [1] ELSE [] END |
            MERGE (c)-[:POSTED]->(j)
        )
        RETURN j.job_id as id, j.title as title
        """
        params = {
            "title": data.get("title"),
            "description": data.get("description", ""),
            "company": data.get("company", ""),
            "salary": data.get("salary", ""),
            "type": data.get("type", ""),
            "location": data.get("location", "")
        }
        records = driver.run_query(cypher, params)
        return jsonify({"success": True, "data": records[0] if records else {}}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/jobs/<job_id>", methods=["GET"])
@login_required
def get_job(job_id):
    """Récupérer une offre d'emploi par ID"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    try:
        cypher = """
        MATCH (j:Job)
        WHERE toString(j.id) = $id OR toString(j.job_id) = $id OR j.id = $id OR j.job_id = $id OR elementId(j) = $id
        OPTIONAL MATCH (comp:Company)-[:POSTED]->(j)
        OPTIONAL MATCH (j)-[:REQUIRES|REQUIRES_SKILL]->(s:Skill)
        RETURN COALESCE(j.job_id, j.id) as id, j.title as title, 
               COALESCE(j.job_description, j.description) as description, 
               COALESCE(comp.company_name, j.company_name_text, j.company) as company, 
               j.salary_min as salary, j.location as location,
               j.contract_type as type,
               comp.description as company_description,
               comp.sector as company_sector,
               comp.website as company_website,
               collect(s.skill_name) as skills
        """
        records = driver.run_query(cypher, {"id": job_id})
        if not records:
            return jsonify({"error": "Job not found"}), 404
        
        return jsonify(records[0]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/jobs/<job_id>", methods=["PUT"])
@login_required
def update_job(job_id):
    admin_or_recruiter_required()
    """Modifier une offre d'emploi"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    user = current_user
    recruiter_company = None
    if user.is_authenticated and user.role == "recruiter":
        recruiter_email = getattr(user, 'email', None) or user.username
        company_cypher = "MATCH (c:Company {recruiter_email: $email}) RETURN c.company_name AS name"
        comp_records = driver.run_query(company_cypher, {"email": recruiter_email})
        if not comp_records or not comp_records[0].get("name"):
            return jsonify({"error": "Recruiter company not found"}), 403
        recruiter_company = comp_records[0]["name"]
        data["company"] = recruiter_company
    
    try:
        # Ensure recruiter can only edit their own company's jobs
        where_clause = "WHERE (j.id = $id OR j.job_id = $id OR toString(j.job_id) = $id)"
        if recruiter_company:
            where_clause += " AND j.company_name_text = $recruiter_company"

        cypher = f"""
        MATCH (j:Job)
        {where_clause}
        SET j.title = COALESCE($title, j.title),
            j.job_description = COALESCE($description, j.job_description, j.description),
            j.company_name_text = COALESCE($company, j.company_name_text, j.company),
            j.salary_min = COALESCE($salary, j.salary_min, j.salary),
            j.contract_type = COALESCE($type, j.contract_type),
            j.location = COALESCE($location, j.location),
            j.updated_at = timestamp()
        WITH j
        WHERE $company IS NOT NULL
        OPTIONAL MATCH (old_c:Company)-[r:POSTED]->(j)
        DELETE r
        WITH j
        MATCH (new_c:Company)
        WHERE toLower(new_c.company_name) = toLower($company)
        MERGE (new_c)-[:POSTED]->(j)
        RETURN j.job_id as id, j.title as title
        """
        # Fallback if company is NOT in data
        if not data.get("company"):
            cypher = f"""
            MATCH (j:Job)
            {where_clause}
            SET j.title = COALESCE($title, j.title),
                j.job_description = COALESCE($description, j.job_description, j.description),
                j.salary_min = COALESCE($salary, j.salary_min, j.salary),
                j.contract_type = COALESCE($type, j.contract_type),
                j.location = COALESCE($location, j.location),
                j.updated_at = timestamp()
            RETURN COALESCE(j.job_id, j.id) as id, j.title as title
            """

        params = {
            "id": job_id,
            "title": data.get("title"),
            "description": data.get("description"),
            "company": data.get("company"),
            "salary": data.get("salary"),
            "type": data.get("type"),
            "location": data.get("location"),
            "recruiter_company": recruiter_company
        }
        records = driver.run_query(cypher, params)
        
        if not records:
            return jsonify({"error": "Job not found"}), 404
        
        return jsonify({"success": True, "data": records[0]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/jobs/<job_id>", methods=["DELETE"])
@login_required
def delete_job(job_id):
    admin_or_recruiter_required()
    """Supprimer une offre d'emploi"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    try:
        user = current_user
        recruiter_company = None
        if user.is_authenticated and user.role == "recruiter":
            recruiter_email = getattr(user, 'email', None) or user.username
            company_cypher = "MATCH (c:Company {recruiter_email: $email}) RETURN c.company_name AS name"
            comp_records = driver.run_query(company_cypher, {"email": recruiter_email})
            if not comp_records or not comp_records[0].get("name"):
                return jsonify({"error": "Recruiter company not found"}), 403
            recruiter_company = comp_records[0]["name"]

        where_clause = "WHERE (j.id = $id OR j.job_id = $id OR toString(j.job_id) = $id)"
        if recruiter_company:
            where_clause += " AND j.company_name_text = $recruiter_company"

        # Flexible match for Job ID
        cypher = f"""
        MATCH (j:Job)
        {where_clause}
        WITH j, COALESCE(j.job_id, j.id) as deletedId
        DETACH DELETE j
        RETURN deletedId as id
        """
        records = driver.run_query(cypher, {"id": job_id, "recruiter_company": recruiter_company})
        
        if not records:
            print(f"[DELETE ERROR] Job not found: {job_id}")
            return jsonify({"error": "Job not found"}), 404
        
        return jsonify({"success": True, "message": "Job deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/recruiters", methods=["GET"])
@login_required
def get_recruiters():
    admin_required()
    driver = get_driver()
    try:
        query = """
        MATCH (u:User {role: 'recruiter'})
        OPTIONAL MATCH (c:Company {recruiter_email: u.email})
        RETURN elementId(u) AS id, u.username AS name, u.email AS email, 
               COALESCE(c.company_name, c.name, '—') AS company_name
        ORDER BY u.username
        """
        records = driver.run_query(query)
        return jsonify({"recruiters": records, "count": len(records)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/recruiters/<user_id>", methods=["DELETE"])
@login_required
def delete_recruiter(user_id):
    admin_required()
    driver = get_driver()
    try:
        driver.run_query("MATCH (u:User) WHERE elementId(u) = $id DELETE u", {"id": user_id})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/companies", methods=["GET"])
@login_required
def get_companies():
    """Récupérer toutes les entreprises"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    try:
        # Get total count
        count_cypher = "MATCH (c:Company) RETURN count(c) as total"
        total_records = driver.run_query(count_cypher) or []
        total = int(total_records[0].get("total") or 0) if total_records else 0

        cypher = """
        MATCH (c:Company) 
        RETURN DISTINCT toString(COALESCE(c.company_id, c.id, elementId(c))) as id, 
               COALESCE(c.company_name, c.name) as name,
               c.location as location,
               c.sector as sector,
               c.recruiter_name as recruiter_name,
               c.recruiter_email as recruiter_email
        ORDER BY name ASC LIMIT 100
        """
        records = driver.run_query(cypher) or []
        return jsonify({"count": total, "companies": records})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@bp.route("/companies/<company_id>", methods=["GET"])
@login_required
def get_company(company_id):
    """Récupérer une entreprise par ID"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    try:
        cypher = """
        MATCH (c:Company)
        WHERE c.id = $id OR c.company_id = $id OR toString(c.company_id) = $id OR elementId(c) = $id
        RETURN COALESCE(c.company_id, c.id) as id, 
               COALESCE(c.company_name, c.name) as name,
               c.location as location,
               c.sector as sector,
               c.website as website,
               c.description as description,
               c.recruiter_name as recruiter_name,
               c.recruiter_email as recruiter_email
        """
        records = driver.run_query(cypher, {"id": company_id})
        if not records:
            return jsonify({"error": "Company not found"}), 404
        
        return jsonify(records[0]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@bp.route("/companies/add", methods=["POST"])
@login_required
def add_company():
    admin_required()
    """Ajouter une nouvelle entreprise"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "name is required"}), 400
    
    try:
        cypher = """
        MERGE (c:Company {company_name: $name})
        ON CREATE SET c.company_id = randomUUID(),
                      c.sector = $sector,
                      c.location = $location,
                      c.website = $website,
                      c.description = $description,
                      c.recruiter_name = $recruiter_name,
                      c.recruiter_email = $recruiter_email
        ON MATCH SET c.sector = $sector,
                     c.location = $location,
                     c.website = $website,
                     c.description = $description,
                     c.recruiter_name = $recruiter_name,
                     c.recruiter_email = $recruiter_email
        RETURN COALESCE(c.company_name, c.name) as name, toString(COALESCE(c.company_id, c.id)) as id
        """
        params = {
            "name": data.get("name"),
            "sector": data.get("sector"),
            "location": data.get("location"),
            "website": data.get("website"),
            "description": data.get("description"),
            "recruiter_name": data.get("recruiter_name"),
            "recruiter_email": data.get("recruiter_email")
        }
        records = driver.run_query(cypher, params)
        return jsonify({"success": True, "data": records[0] if records else {}}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/companies/<company_id>", methods=["PUT"])
@login_required
def update_company(company_id):
    admin_required()
    """Modifier une entreprise"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        cypher = """
        MATCH (c:Company)
        WHERE c.id = $id OR c.company_id = $id OR toString(c.company_id) = $id
        SET c.company_name = COALESCE($name, c.company_name, c.name),
            c.sector = COALESCE($sector, c.sector),
            c.location = COALESCE($location, c.location),
            c.website = COALESCE($website, c.website),
            c.description = COALESCE($description, c.description),
            c.recruiter_name = COALESCE($recruiter_name, c.recruiter_name),
            c.recruiter_email = COALESCE($recruiter_email, c.recruiter_email),
            c.updated_at = timestamp()
        // Synchronize name alias if present
        SET c.name = c.company_name
        RETURN COALESCE(c.company_id, c.id) as id, c.company_name as name
        """
        params = {
            "id": company_id,
            "name": data.get("name"),
            "sector": data.get("sector"),
            "location": data.get("location"),
            "website": data.get("website"),
            "description": data.get("description"),
            "recruiter_name": data.get("recruiter_name"),
            "recruiter_email": data.get("recruiter_email")
        }
        records = driver.run_query(cypher, params)
        
        if not records:
             return jsonify({"error": "Company not found"}), 404
             
        return jsonify({"success": True, "data": records[0]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/companies/<company_id>", methods=["DELETE"])
@login_required
def delete_company(company_id):
    admin_required()
    """Supprimer une entreprise"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    try:
        cypher = """
        MATCH (c:Company)
        WHERE c.id = $id OR c.company_id = $id OR toString(c.company_id) = $id
        WITH c, COALESCE(c.company_id, c.id) as deletedId
        DETACH DELETE c
        RETURN deletedId as id
        """
        records = driver.run_query(cypher, {"id": company_id})
        
        if not records:
            print(f"[DELETE ERROR] Company not found: {company_id}")
            return jsonify({"error": "Company not found"}), 404
        
        return jsonify({"success": True, "message": "Company deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/apply", methods=["POST"])
@login_required
def apply_to_job():
    # Candidates can apply? Or admin only? Spec says "Admin create/view", User "view only".
    # User request: "Admin permet de voir toutes la liste et d'ajouter et L'UTILISATEUR juste voir les listes"
    # So user is READ-ONLY. So apply is Admin only.
    admin_required()
    """Candidat postule pour un emploi"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    data = request.get_json()
    if not data or "candidate_id" not in data or "job_id" not in data:
        return jsonify({"error": "candidate_id and job_id are required"}), 400
    
    try:
        cypher = """
        MATCH (c:Candidate) WHERE c.cv_id = $candidate_id OR c.id = $candidate_id OR toString(c.cv_id) = $candidate_id
        MATCH (j:Job) WHERE j.job_id = $job_id OR j.id = $job_id OR toString(j.job_id) = $job_id
        MERGE (c)-[:APPLIED_TO]->(j)
        RETURN COALESCE(c.full_name, c.name) as candidate, j.title as job
        """
        params = {
            "candidate_id": data.get("candidate_id"),
            "job_id": data.get("job_id")
        }
        records = driver.run_query(cypher, params)
        return jsonify({"success": True, "data": records[0] if records else {}}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/apply/cv", methods=["POST"])
@login_required
def apply_cv_to_job():
    """Candidate applies to a job from Smart CV.
    Saves full profile (name, email, phone, skills, experience) + creates APPLIED_TO relationship."""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500

    data = request.get_json()
    if not data or "job_id" not in data:
        return jsonify({"error": "job_id is required"}), 400

    job_id       = str(data.get("job_id", "")).strip()
    name         = (data.get("name") or "").strip() or None
    email        = (data.get("email") or "").strip() or None
    phone        = (data.get("phone") or "").strip() or None
    exp_lvl      = (data.get("experience_level") or "").strip() or None
    skills       = [str(s).strip() for s in data.get("skills", []) if str(s).strip()][:20]
    user_id      = str(current_user.id)

    # Fallback values so the node is never empty
    create_name  = name  or current_user.username
    create_email = email or getattr(current_user, 'email', None) or f"{current_user.username}@careerlink.app"
    create_phone = phone or ""
    create_exp   = exp_lvl or "Intermédiaire"

    if not job_id or job_id in ("null", "None", "undefined"):
        return jsonify({"error": "job_id invalide"}), 400

    try:
        import traceback

        # ── STEP 1: Save / Update the Candidate_Cv node with ALL data ──────────
        merge_cypher = """
        MERGE (c:Candidate_Cv {user_id: $user_id})
        ON CREATE SET
            c.cv_id            = randomUUID(),
            c.name             = $create_name,
            c.full_name        = $create_name,
            c.email            = $create_email,
            c.phone            = $create_phone,
            c.experience_level = $create_exp,
            c.current_title    = $create_exp,
            c.created_at       = datetime(),
            c.source           = 'smart_cv_apply'
        ON MATCH SET
            c.name             = COALESCE($name, c.name),
            c.full_name        = COALESCE($name, c.full_name),
            c.email            = COALESCE($email, c.email),
            c.phone            = COALESCE($phone, c.phone),
            c.experience_level = COALESCE($exp_lvl, c.experience_level),
            c.current_title    = COALESCE($exp_lvl, c.current_title),
            c.updated_at       = datetime()
        RETURN c.cv_id AS cv_id, COALESCE(c.name, c.full_name) AS saved_name, c.email AS saved_email
        """
        save_result = driver.run_query(merge_cypher, {
            "user_id":      user_id,
            "name":         name,
            "email":        email,
            "phone":        phone,
            "exp_lvl":      exp_lvl,
            "create_name":  create_name,
            "create_email": create_email,
            "create_phone": create_phone,
            "create_exp":   create_exp
        })
        print(f"[SmartCV Apply] Candidate node saved: {save_result[0] if save_result else 'N/A'}")

        # ── STEP 2: Link Skills ──────────────────────────────────────────────────
        if skills:
            skill_cypher = """
            MATCH (c:Candidate_Cv {user_id: $user_id})
            UNWIND $skills AS skill_name
            MERGE (s:Skill {name: skill_name})
            MERGE (c)-[:HAS_SKILL]->(s)
            """
            driver.run_query(skill_cypher, {"user_id": user_id, "skills": skills})
            print(f"[SmartCV Apply] Linked {len(skills)} skills.")

        # ── STEP 3: Create APPLIED_TO relationship ───────────────────────────────
        apply_cypher = """
        MATCH (c:Candidate_Cv {user_id: $user_id})
        MATCH (j:Job)
        WHERE toString(COALESCE(j.job_id, j.id)) = $job_id
           OR elementId(j) = $job_id
        MERGE (c)-[r:APPLIED_TO]->(j)
        ON CREATE SET
            r.applied_at = datetime(),
            r.status     = 'en_attente',
            r.source     = 'smart_cv'
        RETURN COALESCE(c.name, c.full_name, c.email) AS candidate,
               j.title AS job,
               COALESCE(j.company_name_text, j.company) AS company
        """
        result = driver.run_query(apply_cypher, {"user_id": user_id, "job_id": job_id})

        if not result:
            return jsonify({
                "error": f"Offre introuvable (id: {job_id}). Veuillez réessayer."
            }), 404

        row       = result[0]
        job_title = row.get("job")   or "l'offre"
        company   = row.get("company") or ""
        cand_name = row.get("candidate") or create_name

        print(f"[SmartCV Apply] SUCCESS: '{cand_name}' applied to '{job_title}' ({company})")

        return jsonify({
            "success":   True,
            "message":   f"Candidature envoyée pour '{job_title}' !",
            "candidate": cand_name,
            "job":       job_title,
            "company":   company,
            "skills_saved": len(skills)
        }), 201

    except Exception as e:
        import traceback
        print(f"[SmartCV Apply ERROR] {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@bp.route("/apply/cv/upload", methods=["POST"])
@login_required
def apply_cv_upload():
    """Candidat postule à une offre en soumettant son CV (PDF/DOCX) + ses infos personnelles.
    - Parse le CV pour détecter les compétences
    - Crée ou met à jour le nœud Candidate_Cv dans Neo4j
    - Crée la relation APPLIED_TO vers le Job
    Accepte multipart/form-data: file, job_id, name, email, phone, cover_letter
    """
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500

    job_id           = (request.form.get("job_id") or "").strip()
    name             = (request.form.get("name") or "").strip() or None
    email            = (request.form.get("email") or "").strip() or None
    phone            = (request.form.get("phone") or "").strip() or None
    experience_level = (request.form.get("experience_level") or "").strip() or None
    location         = (request.form.get("location") or "").strip() or None
    current_title    = (request.form.get("current_title") or "").strip() or None
    domain           = (request.form.get("domain") or "").strip() or None
    cover_letter     = (request.form.get("cover_letter") or "").strip() or None

    if not job_id or job_id in ("null", "None", "undefined"):
        return jsonify({"error": "job_id est requis"}), 400

    user_id      = str(current_user.id)
    create_name  = name  or current_user.username
    create_email = email or getattr(current_user, "email", None) or f"{current_user.username}@careerlink.app"
    create_phone = phone or ""

    # ── STEP 1 : Lire & parser le CV (optionnel) ───────────────────────────
    raw_text    = ""
    tech_skills = []

    if "file" in request.files:
        file = request.files["file"]
        if file and file.filename:
            filename_lower = file.filename.lower()
            try:
                if filename_lower.endswith(".pdf"):
                    pdf_reader = pypdf.PdfReader(file)
                    for page in pdf_reader.pages:
                        pt = page.extract_text()
                        if pt:
                            raw_text += pt + " "
                elif filename_lower.endswith(".docx"):
                    import docx as python_docx
                    doc = python_docx.Document(io.BytesIO(file.read()))
                    parts = [p.text for p in doc.paragraphs if p.text.strip()]
                    for table in doc.tables:
                        for row in table.rows:
                            for cell in row.cells:
                                if cell.text.strip():
                                    parts.append(cell.text)
                    raw_text = " ".join(parts)
            except Exception as parse_err:
                print(f"[Apply Upload] CV parse warning: {parse_err}")

        if raw_text.strip():
            # Détecter les compétences dans le CV
            try:
                db_skills_recs = driver.run_query(
                    "MATCH (s:Skill) RETURN DISTINCT toLower(COALESCE(s.skill_name, s.name)) as name"
                ) or []
                db_skills = [r["name"] for r in db_skills_recs if r.get("name")]
                fallback_skills = [
                    "python","java","sql","react","node","javascript","docker","aws",
                    "c++","c#","mongodb","django","spring","html","css","agile","scrum",
                    "machine learning","deep learning","data analysis","typescript",
                    "kubernetes","git","linux","rest api","microservices","tensorflow",
                    "pytorch","pandas","numpy","flask","fastapi","postgresql","mysql",
                    "redis","devops","ci/cd","azure","gcp","power bi","tableau","spark"
                ]
                for s in fallback_skills:
                    if s not in db_skills:
                        db_skills.append(s)

                clean_cv = re.sub(r'[^a-zA-Z0-9\+#]', ' ', raw_text.lower())
                padded_cv = f" {' '.join(clean_cv.split())} "
                detected = []
                for skill in db_skills:
                    sn = " ".join(re.sub(r'[^a-zA-Z0-9\+#]', ' ', skill.lower()).split())
                    if f" {sn} " in padded_cv:
                        detected.append(skill)

                soft_skills = {
                    "communication","leadership","management","teamwork","organization",
                    "planning","english","french","arabic","writing","speaking",
                    "microsoft office","excel","word","powerpoint","autonomy",
                    "motivation","creativity","adaptation","negotiation","flexibility",
                    "curiosity","rigor","time management","problem solving"
                }
                tech_skills = [s for s in sorted(set(detected)) if s not in soft_skills][:20]
                print(f"[Apply Upload] Detected {len(tech_skills)} tech skills from CV.")
            except Exception as skill_err:
                print(f"[Apply Upload] Skill detection warning: {skill_err}")

    # Try to extract email from CV text if not provided
    if not email and raw_text:
        import re as _re
        em = _re.search(r'[\w.\-+]+@[\w.\-]+\.\w+', raw_text)
        if em:
            create_email = em.group(0)
            email = create_email

    # Try to extract phone from CV text if not provided
    if not phone and raw_text:
        import re as _re
        ph = _re.search(r'(\+212|0)([ \-]?\d){9}', raw_text)
        if ph:
            create_phone = ph.group(0).strip()
            phone = create_phone

    # Try to extract name from CV text if not provided
    if not name and raw_text:
        cv_lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
        for line in cv_lines[:5]:
            if len(line.split()) in (2, 3) and line[0].isupper() and not any(c.isdigit() for c in line):
                create_name = line
                name = create_name
                break

    try:
        # ── STEP 2 : Sauvegarder / Mettre à jour le nœud Candidate_Cv ──────────
        merge_cypher = """
        MERGE (c:Candidate_Cv {user_id: $user_id})
        ON CREATE SET
            c.cv_id            = randomUUID(),
            c.name             = $create_name,
            c.full_name        = $create_name,
            c.email            = $create_email,
            c.phone            = $create_phone,
            c.experience_level = COALESCE($experience_level, c.experience_level),
            c.location         = COALESCE($location, c.location),
            c.current_title    = COALESCE($current_title, c.current_title),
            c.domain           = COALESCE($domain, c.domain),
            c.created_at       = datetime(),
            c.source           = 'job_apply_upload'
        ON MATCH SET
            c.name             = COALESCE($name, c.name),
            c.full_name        = COALESCE($name, c.full_name),
            c.email            = COALESCE($email, c.email),
            c.phone            = COALESCE($phone, c.phone),
            c.experience_level = COALESCE($experience_level, c.experience_level),
            c.location         = COALESCE($location, c.location),
            c.current_title    = COALESCE($current_title, c.current_title),
            c.domain           = COALESCE($domain, c.domain),
            c.updated_at       = datetime()
        SET c.cover_letter     = COALESCE($cover_letter, c.cover_letter)
        RETURN c.cv_id AS cv_id, COALESCE(c.name, c.full_name) AS saved_name, c.email AS saved_email
        """
        save_result = driver.run_query(merge_cypher, {
            "user_id":          user_id,
            "name":             name,
            "email":            email,
            "phone":            phone,
            "experience_level": experience_level,
            "location":         location,
            "current_title":    current_title,
            "domain":           domain,
            "cover_letter":     cover_letter,
            "create_name":      create_name,
            "create_email":     create_email,
            "create_phone":     create_phone,
        })
        print(f"[Apply Upload] Candidate saved: {save_result[0] if save_result else 'N/A'}")

        # ── STEP 3 : Lier les compétences ────────────────────────────────────────
        if tech_skills:
            driver.run_query("""
                MATCH (c:Candidate_Cv {user_id: $user_id})
                UNWIND $skills AS skill_name
                MERGE (s:Skill {name: skill_name})
                MERGE (c)-[:HAS_SKILL]->(s)
            """, {"user_id": user_id, "skills": tech_skills})
            print(f"[Apply Upload] Linked {len(tech_skills)} skills.")

        # ── STEP 4 : Créer la relation APPLIED_TO ────────────────────────────────
        apply_cypher = """
        MATCH (c:Candidate_Cv {user_id: $user_id})
        MATCH (j:Job)
        WHERE toString(COALESCE(j.job_id, j.id)) = $job_id
           OR elementId(j) = $job_id
        MERGE (c)-[r:APPLIED_TO]->(j)
        ON CREATE SET
            r.applied_at = datetime(),
            r.status     = 'en_attente',
            r.source     = 'upload_form'
        RETURN COALESCE(c.name, c.full_name, c.email) AS candidate,
               j.title AS job,
               COALESCE(j.company_name_text, j.company) AS company
        """
        result = driver.run_query(apply_cypher, {"user_id": user_id, "job_id": job_id})

        if not result:
            return jsonify({"error": f"Offre introuvable (id: {job_id})."}), 404

        row       = result[0]
        job_title = row.get("job")     or "l'offre"
        company   = row.get("company") or ""
        cand_name = row.get("candidate") or create_name

        print(f"[Apply Upload] SUCCESS: '{cand_name}' applied to '{job_title}' ({company})")

        return jsonify({
            "success":       True,
            "message":       f"Candidature envoyée pour '{job_title}' chez {company} !",
            "candidate":     cand_name,
            "job":           job_title,
            "company":       company,
            "skills_saved":  len(tech_skills),
            "cv_parsed":     bool(raw_text.strip()),
        }), 201

    except Exception as e:
        import traceback
        print(f"[Apply Upload ERROR] {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500



@bp.route("/candidate/<candidate_id>/companies/add", methods=["POST"])
@login_required
def add_company_to_candidate(candidate_id):
    admin_required()
    """Associer une entreprise à un candidat"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    data = request.get_json()
    if not data or "company_name" not in data:
        return jsonify({"error": "company_name is required"}), 400
    
    try:
        cypher = """
        MATCH (c:Candidate {id: $candidate_id})
        MATCH (co:Company {name: $company_name})
        MERGE (c)-[:WORKS_AT]->(co)
        RETURN c.name as candidate, co.name as company
        """
        params = {
            "candidate_id": candidate_id,
            "company_name": data.get("company_name")
        }
        records = driver.run_query(cypher, params)
        return jsonify({"success": True, "data": records[0] if records else {}}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/career-path", methods=["GET"])
@login_required
def get_career_path():
    """Récupérer le chemin de carrière (graphe)"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    title = request.args.get("title")
    
    try:
        import re
        def normalize(t):
            if not t: return ""
            return re.sub(r'[^a-z0-9\s]', '', t.lower().strip())
        
        norm_title = normalize(title) if title else None
        
        if norm_title:
            cypher = """
            MATCH (start:CareerStep)
            WHERE start.normalized_title = $norm
            MATCH p=(start)-[:LEADS_TO*1..3]->(end)
            RETURN p
            LIMIT 50
            """
            records = driver.run_query(cypher, {"norm": norm_title})
        else:
            # Return plausible roots (nodes with no incoming, or just top popular nodes)
            # Or just return everything for small graph
            cypher = """
            MATCH (s:CareerStep)-[r:LEADS_TO]->(e:CareerStep)
            RETURN s, r, e
            LIMIT 100
            """
            records = driver.run_query(cypher)
            
        # Format for frontend (Nodes/Edges)
        nodes = {}
        edges = []
        
        for rec in records:
            # Handle path result or flat result
            if "p" in rec:
                # Path object handling might be tricky with simple driver run_query returning dicts?
                # run_query returns [record.data()], so 'p' might be a list of nodes/rels or a path object?
                # Neo4j python driver data() on path returns: [node, rel, node...] or similar structure depending on serialisation
                # Actually, our db.py wrapper calls record.data(). For a Path, record.data() returns a structure.
                # Let's verify what records contain.
                # If using MATCH p=..., record.data()['p'] is usually not serializable easily or contains the whole path segment list.
                # To be safe, let's change query to return atomic elements.
                pass
            pass

        # SAFER QUERY returning list of rels
        if norm_title:
            cypher = """
            MATCH (start:CareerStep)
            WHERE start.normalized_title = $norm
            MATCH (s)-[r:LEADS_TO]->(e)
            WHERE (start)-[:LEADS_TO*0..3]->(s)
            RETURN s.title as source, e.title as target, r.count as weight
            LIMIT 100
            """
        else:
            cypher = """
            MATCH (s:CareerStep)-[r:LEADS_TO]->(e:CareerStep)
            RETURN s.title as source, e.title as target, r.count as weight
            LIMIT 100
            """
            
        records = driver.run_query(cypher, {"norm": norm_title} if norm_title else {})
        
        response = {
            "nodes": [],
            "edges": []
        }
        
        seen_nodes = set()
        
        for r in records:
            src = r["source"]
            tgt = r["target"]
            w = r["weight"]
            
            if src not in seen_nodes:
                response["nodes"].append({"id": normalize(src), "label": src})
                seen_nodes.add(src)
            if tgt not in seen_nodes:
                response["nodes"].append({"id": normalize(tgt), "label": tgt})
                seen_nodes.add(tgt)
                
            response["edges"].append({
                "from": normalize(src), 
                "to": normalize(tgt), 
                "weight": w
            })
            
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/search", methods=["GET"])
@login_required
def search():
    """Rechercher des candidats, offres ou entreprises par mot-clé."""
    driver = get_driver()
    if not driver:
        return jsonify({"results": {"candidates": [], "jobs": [], "companies": []}, "counts": {"candidates": 0, "jobs": 0, "companies": 0}}), 500

    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"error": "query parameter 'q' is required"}), 400

    tokens = [t.lower() for t in q.split() if t]
    type_filter = (request.args.get("type", "all") or "all").lower()
    
    try:
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except:
        limit, offset = 20, 0

    role = getattr(current_user, 'role', 'user')
    print(f"[SEARCH] User={current_user.username} Role={role} Q='{q}' Type={type_filter}")

    results = {"candidates": [], "jobs": [], "companies": []}
    counts = {"candidates": 0, "jobs": 0, "companies": 0}

    try:
        # 1. CANDIDATES (Admin or Recruiter only)
        if role in ['admin', 'recruiter'] and type_filter in ["all", "candidates"]:
            # Count
            count_cypher = """
            MATCH (c) WHERE (c:Candidate OR c:Candidate_Cv)
            WITH c, toLower(toString(COALESCE(c.full_name, c.name, '')) + ' ' + toString(COALESCE(c.current_title, '')) + ' ' + toString(COALESCE(c.location, ''))) as text
            WHERE all(t IN $tokens WHERE text CONTAINS t)
            RETURN count(DISTINCT c) as total
            """
            count_res = driver.run_query(count_cypher, {"tokens": tokens})
            counts["candidates"] = int(count_res[0]["total"]) if count_res else 0

            # Results
            if hasattr(driver, "_mock") and driver._mock:
                # Mock fallback
                cypher = "MATCH (c:Candidate) RETURN c"
                recs = driver.run_query(cypher, {"q": q, "limit": limit, "offset": offset})
            else:
                cypher = """
                MATCH (c) WHERE (c:Candidate OR c:Candidate_Cv)
                WITH c, toLower(toString(COALESCE(c.full_name, c.name, '')) + ' ' + toString(COALESCE(c.current_title, '')) + ' ' + toString(COALESCE(c.location, ''))) as text
                WHERE all(t IN $tokens WHERE text CONTAINS t)
                WITH c ORDER BY COALESCE(c.full_name, c.name) ASC
                SKIP $offset LIMIT $limit
                RETURN toString(COALESCE(c.cv_id, c.id)) as id, 
                       COALESCE(c.full_name, c.name) as name, 
                       c.email as email, c.phone as phone,
                       c.current_title as current_title,
                       c.location as location
                """
                recs = driver.run_query(cypher, {"tokens": tokens, "limit": limit, "offset": offset})
            
            for r in recs:
                rec = dict(r)
                if role != 'admin' and role != 'recruiter': # Should not happen given outer check but for safety
                    rec.pop('email', None)
                    rec.pop('phone', None)
                results['candidates'].append(rec)

        # 2. JOBS (Admin or Candidate only - Recruiters manage their own, search is global)
        # User requirement: Recruiters have "Smart sourcing", Candidates have "voir les offres"
        # We allow search for all but filter results if needed.
        if type_filter in ["all", "jobs"]:
            count_cypher = """
            MATCH (j:Job)
            OPTIONAL MATCH (comp:Company)-[:POSTED]->(j)
            WITH j, toLower(toString(COALESCE(j.title, '')) + ' ' + toString(COALESCE(comp.company_name, j.company_name_text, '')) + ' ' + toString(COALESCE(j.location, ''))) as text
            WHERE all(t IN $tokens WHERE text CONTAINS t)
            RETURN count(DISTINCT j) as total
            """
            count_res = driver.run_query(count_cypher, {"tokens": tokens})
            counts["jobs"] = int(count_res[0]["total"]) if count_res else 0

            if hasattr(driver, "_mock") and driver._mock:
                cypher = "MATCH (j:Job) RETURN j"
                recs = driver.run_query(cypher, {"q": q, "limit": limit, "offset": offset})
            else:
                cypher = """
                MATCH (j:Job)
                OPTIONAL MATCH (comp:Company)-[:POSTED]->(j)
                WITH j, comp, toLower(toString(COALESCE(j.title, '')) + ' ' + toString(COALESCE(comp.company_name, j.company_name_text, '')) + ' ' + toString(COALESCE(j.location, ''))) as text
                WHERE all(t IN $tokens WHERE text CONTAINS t)
                RETURN toString(COALESCE(j.job_id, j.id)) as id, j.title as title,
                       COALESCE(comp.company_name, j.company_name_text) as company,
                       j.location as location, j.salary_min as salary
                ORDER BY title ASC SKIP $offset LIMIT $limit
                """
                recs = driver.run_query(cypher, {"tokens": tokens, "limit": limit, "offset": offset})
            
            for r in recs:
                results['jobs'].append(dict(r))

        # 3. COMPANIES (Admin or Candidate only)
        if type_filter in ["all", "companies"]:
            count_cypher = """
            MATCH (co:Company)
            WITH co, toLower(toString(COALESCE(co.company_name, co.name, '')) + ' ' + toString(COALESCE(co.sector, '')) + ' ' + toString(COALESCE(co.location, ''))) as text
            WHERE all(t IN $tokens WHERE text CONTAINS t)
            RETURN count(DISTINCT co) as total
            """
            count_res = driver.run_query(count_cypher, {"tokens": tokens})
            counts["companies"] = int(count_res[0]["total"]) if count_res else 0

            if hasattr(driver, "_mock") and driver._mock:
                recs = [] # Mock doesn't support generic company search yet
            else:
                cypher = """
                MATCH (co:Company)
                WITH co, toLower(toString(COALESCE(co.company_name, co.name, '')) + ' ' + toString(COALESCE(co.sector, '')) + ' ' + toString(COALESCE(co.location, ''))) as text
                WHERE all(t IN $tokens WHERE text CONTAINS t)
                RETURN toString(COALESCE(co.company_id, co.id)) as id,
                       COALESCE(co.company_name, co.name) as name,
                       co.location as location, co.sector as sector, co.website as website
                ORDER BY name ASC SKIP $offset LIMIT $limit
                """
                recs = driver.run_query(cypher, {"tokens": tokens, "limit": limit, "offset": offset})
            
            for r in recs:
                results['companies'].append(dict(r))

        return jsonify({
            "query": q,
            "type": type_filter,
            "counts": counts,
            "results": results
        })

    except Exception as e:
        print(f"[SEARCH ERROR] {str(e)}")
        return jsonify({"error": str(e)}), 500


@bp.route("/job/<job_id>/candidates", methods=["GET"])
@login_required
def get_job_applicants(job_id):
    """Récupérer les candidats qui ont postulé pour une offre (Candidate + Candidate_Cv).
    Accessible aux recruteurs (leurs offres uniquement) et aux admins (toutes les offres)."""
    admin_or_recruiter_required()
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500

    try:
        cypher = """
        MATCH (c)-[r:APPLIED_TO]->(j:Job)
        WHERE (c:Candidate OR c:Candidate_Cv)
          AND (toString(COALESCE(j.job_id, j.id)) = $job_id OR elementId(j) = $job_id)
        OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
        WITH c, r, j, collect(DISTINCT COALESCE(s.skill_name, s.name)) AS skills
        RETURN
            toString(COALESCE(c.cv_id, c.id, elementId(c))) AS id,
            COALESCE(c.full_name, c.name, 'Candidat')       AS name,
            c.email                                          AS email,
            c.phone                                          AS phone,
            c.experience_level                               AS experience_level,
            c.current_title                                  AS current_title,
            c.location                                       AS location,
            skills,
            toString(COALESCE(r.applied_at, ''))             AS applied_at,
            COALESCE(r.status, 'pending')                    AS status,
            COALESCE(r.source, '')                           AS source,
            j.title                                          AS job_title,
            COALESCE(j.company_name_text, j.company)         AS job_company
        ORDER BY
            r.applied_at DESC
        """
        records = driver.run_query(cypher, {"job_id": str(job_id)}) or []
        
        status_map = {
            "pending":    "en_attente",
            "en_attente": "en_attente",
            "accepted":   "accepte",
            "accepte":    "accepte",
            "selected":   "accepte",
            "rejected":   "rejete",
            "rejete":     "rejete",
        }
        for rec in records:
            raw = (rec.get("status") or "en_attente").lower().strip()
            rec["status"] = status_map.get(raw, "en_attente")

        # Always fetch the job info (even when there are no applicants yet)
        job_info = driver.run_query("""
            MATCH (j:Job)
            WHERE toString(COALESCE(j.job_id, j.id)) = $job_id
               OR elementId(j) = $job_id
            RETURN j.title AS title, COALESCE(j.company_name_text, j.company) AS company
            LIMIT 1
        """, {"job_id": str(job_id)})

        job_title   = (job_info[0].get("title")   if job_info else None) or (records[0].get("job_title")   if records else "Offre")
        job_company = (job_info[0].get("company") if job_info else None) or (records[0].get("job_company") if records else "")

        print(f"[GET /job/{job_id}/candidates] {len(records)} candidat(s) pour '{job_title}'")

        return jsonify({
            "job_id":      job_id,
            "job_title":   job_title or "—",
            "job_company": job_company or "—",
            "count":       len(records),
            "applicants":  records
        })
    except Exception as e:
        import traceback
        print(f"[GET /job/{job_id}/candidates ERROR] {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@bp.route("/candidate/<candidate_id>/applications", methods=["GET"])
@login_required
def get_candidate_applications_legacy(candidate_id):
    """[LEGACY -> Upgraded] Redirection vers le helper robuste qui supporte Candidate + Candidate_Cv + statut."""
    return _fetch_applications_for_user(current_user, candidate_id)


@bp.route("/candidate/<candidate_id>/companies", methods=["GET"])
@login_required
def get_candidate_companies(candidate_id):
    """Récupérer les entreprises d'un candidat"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    try:
        cypher = """
        MATCH (c:Candidate {id: $candidate_id})-[:WORKS_AT]->(co:Company)
        RETURN co.name as name
        """
        params = {"candidate_id": candidate_id}
        records = driver.run_query(cypher, params)
        companies = [r.get("name") for r in records]
        return jsonify({"candidate_id": candidate_id, "count": len(companies), "companies": companies})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/analytics/trends", methods=["GET"])
@login_required
def get_market_trends_endpoint():
    """Endpoint pour le Dashboard Tendances (Admin)"""
    admin_required()
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    try:
        # Check if driver has the method (MockDriver might not)
        if hasattr(driver, "get_market_trends"):
            trends = driver.get_market_trends()
        else:
            # Mock fallback or failure
            trends = {
                "top_skills": [
                    {"skill": "Python", "count": 15},
                    {"skill": "React", "count": 12},
                    {"skill": "Management", "count": 10},
                    {"skill": "SQL", "count": 8}
                ],
                "hubs": [
                    {"skill": "Java", "companies": 5, "jobs": 12},
                    {"skill": "AWS", "companies": 4, "jobs": 8}
                ]
            }
            
        return jsonify(trends), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/", methods=["GET"])
def index():
    """Page d'accueil avec documentation"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Gestion des Candidats</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
            h1 { color: #333; }
            h2 { color: #666; border-bottom: 2px solid #007bff; padding-bottom: 10px; margin-top: 30px; }
            .endpoint { background: #f9f9f9; padding: 15px; margin: 10px 0; border-left: 4px solid #007bff; border-radius: 4px; }
            .method { display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; margin-right: 10px; }
            .get { background: #61affe; color: white; }
            .post { background: #49cc90; color: white; }
            .put { background: #fca130; color: white; }
            .delete { background: #f93e3e; color: white; }
            code { background: #eee; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
            .example { background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 4px; overflow-x: auto; }
            pre { margin: 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>API Gestion des Candidats & Offres d'Emploi</h1>
            <p><strong>Base URL:</strong> <code>http://localhost:5000</code></p>
            
            <h2>Candidats</h2>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/candidates</code>
                <p>Récupérer tous les candidats</p>
            </div>
            <div class="endpoint">
                <span class="method post">POST</span> <code>/candidates/add</code>
                <p>Ajouter un nouveau candidat</p>
                <div class="example"><pre>{"name": "Alice", "email": "alice@example.com", "phone": "+33..."}</pre></div>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/candidate/{id}</code>
                <p>Récupérer un candidat spécifique</p>
            </div>
            <div class="endpoint">
                <span class="method put">PUT</span> <code>/candidate/{id}</code>
                <p>Mettre à jour un candidat</p>
            </div>
            <div class="endpoint">
                <span class="method delete">DELETE</span> <code>/candidate/{id}</code>
                <p>Supprimer un candidat</p>
            </div>
            
            <h2>Offres d'Emploi</h2>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/jobs</code>
                <p>Récupérer toutes les offres</p>
            </div>
            <div class="endpoint">
                <span class="method post">POST</span> <code>/jobs/add</code>
                <p>Ajouter une nouvelle offre</p>
                <div class="example"><pre>{"title": "Dev Python", "company": "TechCorp", "salary": "45000"}</pre></div>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/job/{id}</code>
                <p>Récupérer une offre spécifique</p>
            </div>
            <div class="endpoint">
                <span class="method put">PUT</span> <code>/job/{id}</code>
                <p>Mettre à jour une offre</p>
            </div>
            <div class="endpoint">
                <span class="method delete">DELETE</span> <code>/job/{id}</code>
                <p>Supprimer une offre</p>
            </div>
            
            <h2>Compétences</h2>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/skills</code>
                <p>Récupérer toutes les compétences</p>
            </div>
            <div class="endpoint">
                <span class="method post">POST</span> <code>/skills/add</code>
                <p>Ajouter une compétence</p>
                <div class="example"><pre>{"name": "Python"}</pre></div>
            </div>
            
            <h2>Relations</h2>
            <div class="endpoint">
                <span class="method post">POST</span> <code>/apply</code>
                <p>Candidat postule pour une offre</p>
                <div class="example"><pre>{"candidate_id": "...", "job_id": "..."}</pre></div>
            </div>
            <div class="endpoint">
                <span class="method post">POST</span> <code>/candidate/{id}/skills/add</code>
                <p>Ajouter une compétence à un candidat</p>
                <div class="example"><pre>{"skill_name": "Python"}</pre></div>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/candidate/{id}/skills</code>
                <p>Récupérer les compétences d'un candidat</p>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/candidate/{id}/applications</code>
                <p>Récupérer les offres auxquelles a postulé un candidat</p>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/job/{id}/candidates</code>
                <p>Récupérer les candidats pour une offre</p>
            </div>
            
            <h2>Recherche</h2>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/search?q=python&type=all</code>
                <p>Rechercher des candidats ou offres</p>
            </div>
            
            <h2>Utilitaires</h2>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/health</code>
                <p>Vérifier la connexion à la base de données</p>
            </div>
        </div>
    </body>
    </html>
    """
    from flask import Response
    return Response(html, mimetype="text/html")


@bp.route("/analytics/market-trends", methods=["GET"])
@login_required
def get_market_trends():
    admin_required()
    """Récupérer les tendances : Candidats (Offre) et Jobs (Demande)"""
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500
    
    try:
        driver = get_driver()
        
        # 0. Global Counts
        cypher_counts = """
        CALL { MATCH (c) WHERE c:Candidate OR c:Candidate_Cv RETURN count(DISTINCT COALESCE(c.email, c.full_name, c.name, elementId(c))) as cand_count }
        CALL { MATCH (j:Job) RETURN count(DISTINCT j) as job_count }
        CALL { MATCH (comp:Company) RETURN count(DISTINCT comp) as comp_count }
        CALL { MATCH (c)-[r:APPLIED_TO|TARGETS]->(j:Job) WHERE c:Candidate OR c:Candidate_Cv RETURN count(DISTINCT r) as app_count }
        RETURN cand_count, job_count, comp_count, app_count
        """
        counts_res = driver.run_query(cypher_counts)
        counts = counts_res[0] if counts_res else {"cand_count": 0, "job_count": 0, "comp_count": 0, "app_count": 0}

        # 1. Top Skills (Supply: Candidates with Skills)
        cypher_skills = """
        MATCH (c)-[:HAS_SKILL]->(s:Skill)
        WHERE c:Candidate OR c:Candidate_Cv
        WITH s, COALESCE(c.email, c.full_name, c.name, elementId(c)) as person_id
        WITH trim(toLower(coalesce(s.name, s.skill_name, 'Inconnu'))) as skill_label, count(DISTINCT person_id) as count
        RETURN skill_label as label, count
        ORDER BY count DESC LIMIT 15
        """
        skills_data = driver.run_query(cypher_skills)

        # 1b. Job Salary Distribution (Demand)
        cypher_salary_jobs = """
        MATCH (j:Job)
        WHERE j.salary_min IS NOT NULL
        WITH j, toInteger(j.salary_min) as sal
        RETURN 
            CASE 
                WHEN sal < 1000 THEN '< 1000'
                WHEN sal >= 1000 AND sal < 2000 THEN '1000-2000'
                WHEN sal >= 2000 AND sal < 3000 THEN '2000-3000'
                WHEN sal >= 3000 AND sal < 4000 THEN '3000-4000'
                WHEN sal >= 4000 AND sal < 5000 THEN '4000-5000'
                WHEN sal >= 5000 AND sal < 6000 THEN '5000-6000'
                WHEN sal >= 6000 AND sal < 7000 THEN '6000-7000'
                WHEN sal >= 7000 THEN '7000+'
                ELSE 'N/A'
            END as label, count(j) as count
        ORDER BY label
        """
        salary_jobs_data = driver.run_query(cypher_salary_jobs)

        # 1c. Candidate Salary Targets (Supply - Based on Jobs they target)
        cypher_salary_cands = """
        MATCH (c)-[:TARGETS]->(j:Job)
        WHERE (c:Candidate OR c:Candidate_Cv) AND j.salary_min IS NOT NULL
        WITH COALESCE(c.email, c.full_name, c.name, elementId(c)) as person_id, j, toInteger(j.salary_min) as sal
        RETURN 
            CASE 
                WHEN sal < 1000 THEN '< 1000'
                WHEN sal >= 1000 AND sal < 2000 THEN '1000-2000'
                WHEN sal >= 2000 AND sal < 3000 THEN '2000-3000'
                WHEN sal >= 3000 AND sal < 4000 THEN '3000-4000'
                WHEN sal >= 4000 AND sal < 5000 THEN '4000-5000'
                WHEN sal >= 5000 AND sal < 6000 THEN '5000-6000'
                WHEN sal >= 6000 AND sal < 7000 THEN '6000-7000'
                WHEN sal >= 7000 THEN '7000+'
                ELSE 'N/A'
            END as label, count(DISTINCT person_id) as count
        ORDER BY label
        """
        salary_cands_data = driver.run_query(cypher_salary_cands)

        # 2. Geographic Distribution (Jobs)
        cypher_geo = """
        MATCH (j:Job)
        RETURN j.location as label, count(DISTINCT j) as count
        ORDER BY count DESC
        LIMIT 6
        """
        geo_data = driver.run_query(cypher_geo)
        
        # 2b. Job Evolution (Time Series) - Hybride (Réel + Simulation pour distribution)
        cypher_evolution = """
        MATCH (j:Job)
        WITH j, COALESCE(toString(j.created_at), '') as raw_date, id(j) as node_id
        WITH j, 
             CASE 
                WHEN raw_date =~ "^20[0-9]{2}-[0-9]{2}-[0-9]{2}.*" THEN date(substring(raw_date, 0, 10))
                WHEN raw_date =~ "^[0-9]{2}/[0-9]{2}/20[0-9]{2}.*" THEN date({year: toInteger(substring(raw_date, 6, 4)), month: toInteger(substring(raw_date, 3, 2)), day: toInteger(substring(raw_date, 0, 2))})
                WHEN raw_date =~ "^[0-9]{13}$" THEN date(datetime({epochMillis: toInteger(raw_date)}))
                ELSE 
                    date('2025-05-01') + duration({months: (
                        CASE 
                            WHEN (node_id % 110) < 10 THEN 0 
                            WHEN (node_id % 110) < 18 THEN 1 
                            WHEN (node_id % 110) < 25 THEN 2 
                            WHEN (node_id % 110) < 32 THEN 3 
                            WHEN (node_id % 110) < 38 THEN 4 
                            WHEN (node_id % 110) < 42 THEN 5 
                            WHEN (node_id % 110) < 48 THEN 6 
                            WHEN (node_id % 110) < 55 THEN 7 
                            WHEN (node_id % 110) < 68 THEN 8 
                            WHEN (node_id % 110) < 80 THEN 9 
                            WHEN (node_id % 110) < 90 THEN 10 
                            ELSE 11
                        END
                    )})
             END as d
        RETURN toString(d.month) + '/' + toString(d.year) as label, 
               d.year as year, d.month as month, count(DISTINCT j) as count
        ORDER BY year, month
        """
        evolution_data = driver.run_query(cypher_evolution)
        
        # 2c. Candidate Levels (Real data)
        cypher_levels = """
        MATCH (c)
        WHERE (c:Candidate OR c:Candidate_Cv) AND c.experience_level IS NOT NULL
        WITH toLower(trim(c.experience_level)) as lvl, c
        WITH CASE
            WHEN lvl CONTAINS 'senior' OR lvl CONTAINS 'expert' THEN 'Sénior / Expert'
            WHEN lvl CONTAINS 'junior' OR lvl CONTAINS 'débutant' THEN 'Junior'
            WHEN lvl CONTAINS 'intermédiaire' OR lvl CONTAINS 'mid' THEN 'Intermédiaire'
            WHEN lvl CONTAINS 'stagiaire' OR lvl CONTAINS 'intern' THEN 'Stagiaire'
            ELSE 'Autre'
        END as label, count(DISTINCT COALESCE(c.email, c.full_name, c.name, elementId(c))) as count
        RETURN label, count
        ORDER BY count DESC
        """
        levels_data = driver.run_query(cypher_levels)
        
        # 3. Top Recruiters (Companies)
        cypher_recruiters = """
        MATCH (c:Company)-[:POSTED]->(j:Job)
        RETURN coalesce(c.company_name, c.name, 'Entreprise Inconnue') as label, count(DISTINCT j) as count
        ORDER BY count DESC
        LIMIT 6
        """
        recruiters_data = driver.run_query(cypher_recruiters)
        
        # 3b. Sector Distribution (Companies)
        cypher_sectors = """
        MATCH (c:Company)-[:POSTED]->(j:Job)
        RETURN coalesce(c.sector, 'Non défini') as label, count(DISTINCT j) as count
        ORDER BY count DESC
        LIMIT 5
        """
        sectors_data = driver.run_query(cypher_sectors)
        
        return jsonify({
            "candidates_by_skill": skills_data,
            "salary_distribution": salary_jobs_data,
            "candidate_salary_distribution": salary_cands_data,
            "geo_distribution": geo_data,
            "job_evolution": evolution_data,
            "top_recruiters": recruiters_data,
            "sector_distribution": sectors_data,
            "candidate_levels": levels_data,
            "counts": counts
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/applications/recent", methods=["GET"])
@login_required
def get_recent_applications():
    admin_required()
    driver = get_driver()
    try:
        cypher = """
        MATCH (c)-[r:APPLIED_TO]->(j:Job)
        WHERE c:Candidate OR c:Candidate_Cv
        RETURN toString(COALESCE(c.cv_id, c.id, elementId(c))) as candidate_id,
               COALESCE(c.full_name, c.name) as candidate_name,
               toString(COALESCE(j.job_id, j.id, elementId(j))) as job_id,
               j.title as job_title,
               j.company as company_name,
               toString(COALESCE(r.applied_at, '')) as applied_at
        ORDER BY r.applied_at DESC
        LIMIT 5
        """
        records = driver.run_query(cypher)
        return jsonify({"applications": records})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/recruiter/jobs-with-applicants", methods=["GET"])
@login_required
def recruiter_jobs_with_applicants():
    """Retourne les offres du recruteur avec le nombre de candidats ayant postulé."""
    admin_or_recruiter_required()
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500

    try:
        # Determine company name for filtering
        company_name = None
        if current_user.role == 'recruiter':
            user_res = driver.run_query(
                "MATCH (u:User) WHERE elementId(u) = $eid RETURN u.email AS email",
                {"eid": current_user.id}
            )
            recruiter_email = user_res[0]["email"] if user_res else None
            if recruiter_email:
                comp_res = driver.run_query(
                    "MATCH (c:Company {recruiter_email: $email}) RETURN c.company_name AS name LIMIT 1",
                    {"email": recruiter_email}
                )
                company_name = comp_res[0]["name"] if comp_res else None

        if current_user.role == 'recruiter' and not company_name:
            return jsonify({"jobs": [], "message": "Aucune entreprise associée"}), 200

        # Fetch jobs with applicant counts
        if current_user.role == 'recruiter':
            cypher = """
            MATCH (j:Job)
            WHERE j.company_name_text = $company OR j.company = $company
            OPTIONAL MATCH (c)-[r:APPLIED_TO]->(j)
            WHERE c:Candidate OR c:Candidate_Cv
            WITH j,
                 count(r) as total_applicants,
                 sum(CASE WHEN COALESCE(r.status, 'en_attente') IN ['pending','en_attente'] THEN 1 ELSE 0 END) as pending_count,
                 sum(CASE WHEN r.status IN ['selected','accepte'] THEN 1 ELSE 0 END) as selected_count,
                 sum(CASE WHEN r.status IN ['rejected','rejete'] THEN 1 ELSE 0 END) as rejected_count
            RETURN toString(COALESCE(j.job_id, j.id, elementId(j))) as id,
                   j.title as title,
                   COALESCE(j.company_name_text, j.company) as company,
                   j.location as location,
                   j.contract_type as type,
                   j.salary_min as salary,
                   total_applicants,
                   pending_count,
                   selected_count,
                   rejected_count,
                   toString(j.created_at) as created_at
            ORDER BY total_applicants DESC, coalesce(j.created_at, 0) DESC
            """
            records = driver.run_query(cypher, {"company": company_name}) or []
        else:
            # Admin sees all jobs
            cypher = """
            MATCH (j:Job)
            OPTIONAL MATCH (c)-[r:APPLIED_TO]->(j)
            WHERE c:Candidate OR c:Candidate_Cv
            WITH j,
                 count(r) as total_applicants,
                 sum(CASE WHEN COALESCE(r.status, 'en_attente') IN ['pending','en_attente'] THEN 1 ELSE 0 END) as pending_count,
                 sum(CASE WHEN r.status IN ['selected','accepte'] THEN 1 ELSE 0 END) as selected_count,
                 sum(CASE WHEN r.status IN ['rejected','rejete'] THEN 1 ELSE 0 END) as rejected_count
            OPTIONAL MATCH (comp:Company)
            WHERE comp.company_name = COALESCE(j.company_name_text, j.company)
            WITH j, comp, total_applicants, pending_count, selected_count, rejected_count
            RETURN toString(COALESCE(j.job_id, j.id, elementId(j))) as id,
                   j.title as title,
                   COALESCE(j.company_name_text, j.company) as company,
                   comp.recruiter_name as recruiter_name,
                   j.location as location,
                   j.contract_type as type,
                   j.salary_min as salary,
                   total_applicants,
                   pending_count,
                   selected_count,
                   rejected_count,
                   toString(j.created_at) as created_at
            ORDER BY total_applicants DESC, coalesce(j.created_at, 0) DESC
            """
            records = driver.run_query(cypher) or []

        # Convert any Neo4j objects (like DateTime) to serializable strings
        for r in records:
            for k, v in r.items():
                if hasattr(v, 'isoformat'):
                    r[k] = v.isoformat()
                    
        return jsonify({"jobs": records})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/job/<job_id>/select/<candidate_id>", methods=["POST"])
@login_required
def select_candidate(job_id, candidate_id):
    """Recruteur sélectionne un candidat pour une offre."""
    admin_or_recruiter_required()
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500

    try:
        cypher = """
        MATCH (c)-[r:APPLIED_TO]->(j:Job)
        WHERE (c:Candidate OR c:Candidate_Cv)
          AND (toString(COALESCE(c.cv_id, c.id)) = $cid
               OR elementId(c) = $cid
               OR c.user_id = $cid)
          AND (toString(COALESCE(j.job_id, j.id)) = $jid OR elementId(j) = $jid)
        SET r.status = 'accepte',
            r.selected_at = datetime()
        RETURN COALESCE(c.full_name, c.name) as candidate,
               j.title as job,
               r.status as status
        """
        result = driver.run_query(cypher, {"cid": candidate_id, "jid": job_id})
        if not result:
            return jsonify({"error": "Candidature introuvable"}), 404

        row = result[0]
        print(f"[SELECT] '{row.get('candidate')}' sélectionné pour '{row.get('job')}'")
        return jsonify({
            "success": True,
            "message": f"{row.get('candidate')} a été sélectionné(e) !",
            "candidate": row.get("candidate"),
            "job": row.get("job"),
            "status": "accepte"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/job/<job_id>/reject/<candidate_id>", methods=["POST"])
@login_required
def reject_candidate(job_id, candidate_id):
    """Recruteur rejette un candidat pour une offre."""
    admin_or_recruiter_required()
    driver = get_driver()
    if not driver:
        return jsonify({"error": "driver not initialized"}), 500

    try:
        cypher = """
        MATCH (c)-[r:APPLIED_TO]->(j:Job)
        WHERE (c:Candidate OR c:Candidate_Cv)
          AND (toString(COALESCE(c.cv_id, c.id)) = $cid
               OR elementId(c) = $cid
               OR c.user_id = $cid)
          AND (toString(COALESCE(j.job_id, j.id)) = $jid OR elementId(j) = $jid)
        SET r.status = 'rejete',
            r.rejected_at = datetime()
        RETURN COALESCE(c.full_name, c.name) as candidate,
               j.title as job,
               r.status as status
        """
        result = driver.run_query(cypher, {"cid": candidate_id, "jid": job_id})
        if not result:
            return jsonify({"error": "Candidature introuvable"}), 404

        row = result[0]
        print(f"[REJECT] '{row.get('candidate')}' rejeté pour '{row.get('job')}'")
        return jsonify({
            "success": True,
            "message": f"{row.get('candidate')} a été rejeté(e).",
            "candidate": row.get("candidate"),
            "job": row.get("job"),
            "status": "rejete"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

