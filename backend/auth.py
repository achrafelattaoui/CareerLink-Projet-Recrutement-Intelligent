from flask import Blueprint, request, jsonify, redirect
from flask_login import login_user, logout_user, login_required, current_user
from db import get_driver
from werkzeug.security import generate_password_hash
import uuid
import os
from datetime import datetime, timedelta

bp = Blueprint("auth", __name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")


# ═══════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════
@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password")
    role     = data.get("role", "user")

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400

    print(f"[AUTH] Login attempt for: {email} (role: {role})")
    driver = get_driver()
    user = driver.get_user_by_email(email)

    if user:
        print(f"[AUTH] User found: {user.username} role={user.role}")
        if user.check_password(password):
            print("[AUTH] Password OK")
            if user.role != role:
                print(f"[AUTH] Role mismatch: expected {role}, got {user.role}")
                return jsonify({"error": f"Accès refusé. Vous n'êtes pas un {role}."}), 403

            login_user(user)
            return jsonify({
                "success": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": getattr(user, 'email', email),
                    "role": user.role
                }
            })
        else:
            print("[AUTH] Password FAILED")
    else:
        print("[AUTH] User not found")

    return jsonify({"error": "Email ou mot de passe incorrect"}), 401


# ═══════════════════════════════════════════════════════════════
# LOGOUT
# ═══════════════════════════════════════════════════════════════
@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"success": True})


# ═══════════════════════════════════════════════════════════════
# ME
# ═══════════════════════════════════════════════════════════════
@bp.route("/me", methods=["GET"])
def me():
    if current_user.is_authenticated:
        driver = get_driver()
        email = None
        try:
            res = driver.run_query(
                "MATCH (u:User) WHERE elementId(u) = $eid RETURN u.email AS email",
                {"eid": current_user.id}
            )
            if res:
                email = res[0].get("email")
        except Exception:
            pass
        return jsonify({"authenticated": True, "user": {
            "id": current_user.id,
            "username": current_user.username,
            "role": current_user.role,
            "email": email
        }})
    return jsonify({"authenticated": False}), 401


# ═══════════════════════════════════════════════════════════════
# ME/COMPANY (recruteur)
# ═══════════════════════════════════════════════════════════════
@bp.route("/me/company", methods=["GET"])
@login_required
def me_company():
    """Retourne l'entreprise associée au recruteur connecté via Company.recruiter_email"""
    if current_user.role != 'recruiter':
        return jsonify({"error": "Not a recruiter"}), 403
    driver = get_driver()
    try:
        user_res = driver.run_query(
            "MATCH (u:User) WHERE elementId(u) = $eid RETURN u.email AS email",
            {"eid": current_user.id}
        )
        if not user_res or not user_res[0].get("email"):
            return jsonify({"error": "Email not found"}), 404
        recruiter_email = user_res[0]["email"]

        comp_res = driver.run_query(
            """
            MATCH (comp:Company)
            WHERE comp.recruiter_email = $email
            RETURN COALESCE(comp.company_name, comp.name) AS company_name,
                   toString(COALESCE(comp.company_id, comp.id, elementId(comp))) AS company_id,
                   comp.recruiter_name AS recruiter_name,
                   comp.recruiter_email AS recruiter_email
            LIMIT 1
            """,
            {"email": recruiter_email}
        )
        if not comp_res:
            return jsonify({"company": None, "recruiter_email": recruiter_email}), 200
        return jsonify({"company": comp_res[0]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════
# REGISTER
# ═══════════════════════════════════════════════════════════════
@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    # ── Champs communs ──
    prenom       = (data.get("prenom") or "").strip()
    nom          = (data.get("nom") or "").strip()
    date_nais    = (data.get("date_naissance") or "").strip()
    email        = (data.get("email") or "").strip().lower()
    password     = data.get("password") or ""
    role         = data.get("role", "user")

    # ── Champs spécifiques ──
    company_name = (data.get("companyName") or "").strip()           # recruteur
    title        = (data.get("title") or "").strip()                 # candidat
    location     = (data.get("location") or "").strip()              # candidat

    # ── Validations ──
    if not prenom or not nom:
        return jsonify({"error": "Prénom et Nom sont requis"}), 400
    if not email or "@" not in email:
        return jsonify({"error": "Adresse email invalide"}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "Le mot de passe doit contenir au moins 6 caractères"}), 400
    if role == "recruiter" and not company_name:
        return jsonify({"error": "Le nom de l'entreprise est requis pour un recruteur"}), 400
    if role == "user" and (not title or not location):
        return jsonify({"error": "Poste actuel et Localisation sont requis"}), 400

    # ── Vérifier que l'email n'est pas déjà utilisé ──
    driver = get_driver()
    try:
        existing = driver.get_user_by_email(email)
        if existing:
            return jsonify({"error": "Cette adresse email est déjà utilisée"}), 409
    except Exception:
        pass

    # ── Construire nom complet ──
    full_name = f"{prenom} {nom}"
    pw_hash = generate_password_hash(password)

    try:
        if role == "user":
            driver.run_query("""
                CREATE (u:User {
                    id: randomUUID(),
                    username: $username,
                    email: $email,
                    password_hash: $pw,
                    role: $role,
                    prenom: $prenom,
                    date_naissance: $date_naissance,
                    created_at: timestamp()
                })
                WITH u
                CREATE (c:Candidate {
                    id: randomUUID(),
                    cv_id: randomUUID(),
                    user_id: elementId(u),
                    full_name: $username,
                    name: $username,
                    email: $email,
                    date_naissance: $date_naissance,
                    current_title: $title,
                    location: $location,
                    created_at: timestamp()
                })
            """, {
                "username": full_name,
                "email": email,
                "pw": pw_hash,
                "role": role,
                "prenom": prenom,
                "date_naissance": date_nais,
                "title": title,
                "location": location
            })
        elif role == "recruiter":
            driver.run_query("""
                CREATE (u:User {
                    id: randomUUID(),
                    username: $username,
                    email: $email,
                    password_hash: $pw,
                    role: $role,
                    prenom: $prenom,
                    date_naissance: $date_naissance,
                    created_at: timestamp()
                })
                MERGE (c:Company {company_name: $company_name})
                ON CREATE SET c.company_id = randomUUID(),
                              c.recruiter_name = $username,
                              c.recruiter_email = $email,
                              c.created_at = timestamp()
                ON MATCH SET  c.recruiter_name = $username,
                              c.recruiter_email = $email
            """, {
                "username": full_name,
                "email": email,
                "pw": pw_hash,
                "role": role,
                "prenom": prenom,
                "date_naissance": date_nais,
                "company_name": company_name
            })
            
        return jsonify({
            "success": True,
            "message": "Compte créé avec succès ! Vous pouvez maintenant vous connecter."
        })

    except Exception as e:
        print(f"[AUTH] Erreur création compte Neo4j : {e}")
        return jsonify({"error": "Erreur interne Neo4j"}), 500



# ═══════════════════════════════════════════════════════════════
# SET-PASSWORD
# ═══════════════════════════════════════════════════════════════
@bp.route("/set-password", methods=["POST"])
@login_required
def set_password():
    """Allow a logged-in recruiter to set/change their password."""
    data = request.get_json()
    new_password = data.get("password")
    if not new_password or len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    driver = get_driver()
    new_hash = generate_password_hash(new_password)
    try:
        driver.run_query(
            "MATCH (u:User) WHERE u.email = $email SET u.password_hash = $pw",
            {"email": current_user.id if '@' in current_user.id else None,
             "pw": new_hash}
        )
        driver.run_query(
            "MATCH (u:User) WHERE elementId(u) = $eid SET u.password_hash = $pw",
            {"eid": current_user.id, "pw": new_hash}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"success": True, "message": "Password updated successfully"})
