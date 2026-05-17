#!/usr/bin/env python3
"""
Script de test des endpoints principaux de l'API
"""
import requests
import json
from time import sleep

BASE_URL = "http://localhost:5000"

def test_endpoint(method, endpoint, data=None, description=""):
    """Helper pour tester un endpoint"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            resp = requests.get(url, timeout=5)
        elif method.upper() == "POST":
            resp = requests.post(url, json=data, timeout=5)
        elif method.upper() == "PUT":
            resp = requests.put(url, json=data, timeout=5)
        elif method.upper() == "DELETE":
            resp = requests.delete(url, timeout=5)
        else:
            return False, f"Méthode inconnue: {method}"
        
        status = "✓ OK" if resp.status_code < 400 else f"✗ {resp.status_code}"
        print(f"{status:8} {method:6} {endpoint:40} {description}")
        
        if resp.status_code >= 400:
            print(f"         Réponse: {resp.text[:100]}")
            return False, resp.text
        
        return True, resp.json()
    except Exception as e:
        print(f"✗ ERROR  {method:6} {endpoint:40} {str(e)[:50]}")
        return False, str(e)

def main():
    print("=" * 100)
    print("TEST DES ENDPOINTS API")
    print("=" * 100)
    print()
    
    # Health check
    print("1. Health Check")
    print("-" * 100)
    success, result = test_endpoint("GET", "/health", description="Vérifier connexion BDD")
    if success:
        print(f"   Réponse: {json.dumps(result, indent=2)[:200]}")
    print()
    
    # Candidates
    print("2. Candidats")
    print("-" * 100)
    success, result = test_endpoint("GET", "/candidates", description="Lister les candidats")
    if success:
        count = result.get("count", 0)
        print(f"   Total: {count} candidats")
        if count > 0:
            print(f"   Sample: {json.dumps(result.get('candidates', [])[:1], indent=2)[:200]}")
    print()
    
    # Add candidate
    print("3. Ajouter un candidat")
    print("-" * 100)
    new_cand = {
        "name": "Alice Test",
        "email": "alice.test@example.com",
        "phone": "+33612345678"
    }
    success, result = test_endpoint("POST", "/candidates/add", data=new_cand, description="Créer candidat")
    cand_id = None
    if success:
        cand_id = result.get("data", {}).get("id")
        print(f"   Réponse: {json.dumps(result, indent=2)[:200]}")
    print()
    
    # Jobs
    print("4. Offres d'emploi")
    print("-" * 100)
    success, result = test_endpoint("GET", "/jobs", description="Lister les offres")
    if success:
        count = result.get("count", 0)
        print(f"   Total: {count} offres")
        if count > 0:
            print(f"   Sample: {json.dumps(result.get('jobs', [])[:1], indent=2)[:200]}")
    print()
    
    # Add job
    print("5. Ajouter une offre d'emploi")
    print("-" * 100)
    new_job = {
        "title": "Développeur Python Test",
        "company": "TestCorp",
        "description": "Une offre de test",
        "salary": "50000"
    }
    success, result = test_endpoint("POST", "/jobs/add", data=new_job, description="Créer offre")
    job_id = None
    if success:
        job_id = result.get("data", {}).get("id")
        print(f"   Réponse: {json.dumps(result, indent=2)[:200]}")
    print()
    
    # Skills
    print("6. Compétences")
    print("-" * 100)
    success, result = test_endpoint("GET", "/skills", description="Lister les compétences")
    if success:
        count = result.get("count", 0)
        print(f"   Total: {count} compétences")
    print()
    
    # Add skill
    print("7. Ajouter une compétence")
    print("-" * 100)
    success, result = test_endpoint("POST", "/skills/add", data={"name": "Python"}, description="Créer compétence")
    print()
    
    # Test relation: add skill to candidate
    if cand_id:
        print("8. Ajouter compétence à candidat")
        print("-" * 100)
        success, result = test_endpoint(
            "POST",
            f"/candidate/{cand_id}/skills/add",
            data={"skill_name": "Python"},
            description=f"Lier {cand_id[:8]}... à Python"
        )
        print()
    
    # Test relation: apply to job
    if cand_id and job_id:
        print("9. Candidat postule à une offre")
        print("-" * 100)
        success, result = test_endpoint(
            "POST",
            "/apply",
            data={"candidate_id": cand_id, "job_id": job_id},
            description=f"Postuler à {job_id[:8]}..."
        )
        print()
    
    # Get applicants for job
    if job_id:
        print("10. Candidats ayant postulé à une offre")
        print("-" * 100)
        success, result = test_endpoint("GET", f"/job/{job_id}/candidates", description=f"Lister postulants")
        if success:
            print(f"    Réponse: {json.dumps(result, indent=2)[:200]}")
        print()
    
    # Search
    print("11. Recherche")
    print("-" * 100)
    success, result = test_endpoint("GET", "/search?q=Python&type=all", description="Rechercher 'Python'")
    if success:
        print(f"    Résultats: {json.dumps(result.get('results', {}), indent=2)[:200]}")
    print()
    
    print("=" * 100)
    print("TEST TERMINÉ")
    print("=" * 100)

if __name__ == "__main__":
    main()
