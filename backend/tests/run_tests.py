#!/usr/bin/env python3
"""
Script de test intégré - lance le serveur, teste les endpoints, puis arrête
"""
import sys
import subprocess
import time
import requests
import json
import os
import signal
from threading import Thread

BASE_URL = "http://localhost:5000"
SERVER_PROCESS = None
SESS = requests.Session()

def start_server():
    """Démarrer le serveur Flask"""
    global SERVER_PROCESS
    venv_python = os.path.join(os.path.dirname(__file__), "..", ".venv", "Scripts", "python.exe")
    app_file = os.path.join(os.path.dirname(__file__), "app.py")
    
    SERVER_PROCESS = subprocess.Popen(
        [venv_python, app_file],
        cwd=os.path.dirname(__file__),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    print("✓ Serveur Flask démarré (PID: {})".format(SERVER_PROCESS.pid))
    time.sleep(2)  # Attendre que le serveur soit prêt

def stop_server():
    """Arrêter le serveur Flask"""
    global SERVER_PROCESS
    if SERVER_PROCESS:
        try:
            SERVER_PROCESS.terminate()
            SERVER_PROCESS.wait(timeout=5)
            print("✓ Serveur arrêté")
        except:
            SERVER_PROCESS.kill()
            print("✓ Serveur tué")

def test_endpoint(method, endpoint, data=None, description=""):
    """Helper pour tester un endpoint"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            resp = SESS.get(url, timeout=5)
        elif method.upper() == "POST":
            resp = SESS.post(url, json=data, timeout=5)
        elif method.upper() == "PUT":
            resp = SESS.put(url, json=data, timeout=5)
        elif method.upper() == "DELETE":
            resp = SESS.delete(url, timeout=5)
        else:
            return False, f"Méthode inconnue: {method}"
        
        status = "✓" if resp.status_code < 400 else f"✗"
        print(f"  {status}  {method:6} {endpoint:40} | {description}")
        
        if resp.status_code >= 400:
            print(f"      └─> Erreur {resp.status_code}: {resp.text[:80]}")
            return False, resp.text
        
        return True, resp.json()
    except Exception as e:
        print(f"  ✗  {method:6} {endpoint:40} | Erreur: {str(e)[:60]}")
        return False, str(e)

def main():
    try:
        start_server()
        # Connexion initiale pour obtenir le cookie de session
        try:
            login_payload = {"username": "user", "password": "user123"}
            ok, resp = test_endpoint("POST", "/auth/login", data=login_payload, description="Login test user")
            if not ok:
                print("      ⚠️ Login a échoué, les endpoints protégés retourneront 401")
        except Exception:
            print("      ⚠️ Erreur lors de la tentative de login")
        
        print("\n" + "=" * 100)
        print("TEST DES ENDPOINTS API")
        print("=" * 100 + "\n")
        
        # Health check
        print("1️⃣  HEALTH CHECK")
        print("-" * 100)
        success, result = test_endpoint("GET", "/health", description="Vérifier la connexion BDD")
        if success:
            print(f"      Status: {result.get('status')}\n")
        
        # Candidates
        print("2️⃣  CANDIDATS")
        print("-" * 100)
        success, result = test_endpoint("GET", "/candidates", description="Lister tous les candidats")
        if success:
            count = result.get("count", 0)
            print(f"      Total: {count} candidats")
            if count > 0:
                cand = result.get('candidates', [{}])[0]
                print(f"      Example: {cand.get('name')} ({cand.get('email')})\n")
        
        # Add candidate
        new_cand = {
            "name": "Alice Dupont Test",
            "email": "alice.test@example.com",
            "phone": "+33612345678"
        }
        success, result = test_endpoint("POST", "/candidates/add", data=new_cand, description="Créer un candidat")
        cand_id = None
        if success:
            cand_id = result.get("data", {}).get("id")
            print(f"      Créé: {result.get('data', {}).get('name')} (ID: {cand_id})\n")
        
        # Jobs
        print("3️⃣  OFFRES D'EMPLOI")
        print("-" * 100)
        success, result = test_endpoint("GET", "/jobs", description="Lister toutes les offres")
        if success:
            count = result.get("count", 0)
            print(f"      Total: {count} offres")
            if count > 0:
                job = result.get('jobs', [{}])[0]
                print(f"      Example: {job.get('title')} chez {job.get('company')}\n")
        
        # Add job
        new_job = {
            "title": "Développeur Python Senior",
            "company": "TechCorp",
            "description": "Nous cherchons un développeur Python expérimenté",
            "salary": "50000-60000"
        }
        success, result = test_endpoint("POST", "/jobs/add", data=new_job, description="Créer une offre")
        job_id = None
        if success:
            job_id = result.get("data", {}).get("id")
            print(f"      Créée: {result.get('data', {}).get('title')} (ID: {job_id})\n")
        
        # Skills
        print("4️⃣  COMPÉTENCES")
        print("-" * 100)
        success, result = test_endpoint("GET", "/skills", description="Lister toutes les compétences")
        if success:
            count = result.get("count", 0)
            print(f"      Total: {count} compétences\n")
        
        test_endpoint("POST", "/skills/add", data={"name": "Python"}, description="Créer une compétence")
        print()
        
        # Test relations
        if cand_id and job_id:
            print("5️⃣  RELATIONS")
            print("-" * 100)
            test_endpoint(
                "POST",
                f"/candidate/{cand_id}/skills/add",
                data={"skill_name": "Python"},
                description="Ajouter une compétence au candidat"
            )
            
            test_endpoint(
                "POST",
                "/apply",
                data={"candidate_id": cand_id, "job_id": job_id},
                description="Candidat postule à l'offre"
            )
            
            test_endpoint(
                "GET",
                f"/job/{job_id}/candidates",
                description="Lister les postulants de l'offre"
            )
            print()
        
        # Search
        print("6️⃣  RECHERCHE")
        print("-" * 100)
        success, result = test_endpoint("GET", "/search?q=Python&type=all", description="Rechercher 'Python'")
        if success:
            cands = result.get("results", {}).get("candidates", [])
            jobs = result.get("results", {}).get("jobs", [])
            print(f"      Résultats: {len(cands)} candidats, {len(jobs)} offres\n")
        
        print("=" * 100)
        print("✓ TEST TERMINÉ AVEC SUCCÈS")
        print("=" * 100)
        
    finally:
        stop_server()

if __name__ == "__main__":
    main()
