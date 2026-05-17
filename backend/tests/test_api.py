#!/usr/bin/env python3
"""
Script de test complet de l'API
Exécutez avec: python test_api.py
"""

import json
from dotenv import load_dotenv
from db import init_driver
from routes import bp
from flask import Flask

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_api():
    load_dotenv()
    app = Flask(__name__)
    app.register_blueprint(bp)
    driver = init_driver()
    
    with app.test_client() as client:
        # Health Check
        print_section("HEALTH CHECK")
        resp = client.get('/health')
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Get Candidates
        print_section("LISTER LES CANDIDATS")
        resp = client.get('/candidates')
        cands = resp.get_json().get('candidates', [])
        print(f"Status: {resp.status_code}")
        print(f"Candidats trouvés: {len(cands)}")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Add Candidate
        print_section("AJOUTER UN CANDIDAT")
        new_cand_data = {
            'name': 'Eva Dubois',
            'email': 'eva@example.com',
            'phone': '+33712345678'
        }
        resp = client.post('/candidates/add', json=new_cand_data)
        print(f"Status: {resp.status_code}")
        new_cand = resp.get_json()['data']
        new_cand_id = new_cand['id']
        print(f"Nouveau candidat créé: {new_cand['name']} (ID: {new_cand_id[:8]}...)")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Get Specific Candidate
        print_section("RÉCUPÉRER UN CANDIDAT SPÉCIFIQUE")
        resp = client.get(f'/candidate/{new_cand_id}')
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Update Candidate
        print_section("METTRE À JOUR UN CANDIDAT")
        update_data = {'phone': '0666437505'}
        resp = client.put(f'/candidate/{new_cand_id}', json=update_data)
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Get Jobs
        print_section("LISTER LES OFFRES")
        resp = client.get('/jobs')
        jobs = resp.get_json().get('jobs', [])
        print(f"Status: {resp.status_code}")
        print(f"Offres trouvées: {len(jobs)}")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Add Job
        print_section("AJOUTER UNE OFFRE")
        new_job_data = {
            'title': 'Data Scientist',
            'company': 'DataCorp',
            'description': 'Recherche data scientist expérimenté',
            'salary': '55000'
        }
        resp = client.post('/jobs/add', json=new_job_data)
        print(f"Status: {resp.status_code}")
        new_job = resp.get_json()['data']
        new_job_id = new_job['id']
        print(f"Nouvelle offre créée: {new_job['title']} (ID: {new_job_id[:8]}...)")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Add Skill
        print_section("AJOUTER UNE COMPÉTENCE")
        resp = client.post('/skills/add', json={'name': 'Machine Learning'})
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Add Skill to Candidate
        print_section("AJOUTER UNE COMPÉTENCE AU CANDIDAT")
        resp = client.post(f'/candidate/{new_cand_id}/skills/add', 
                          json={'skill_name': 'Machine Learning'})
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Get Candidate Skills
        print_section("RÉCUPÉRER LES COMPÉTENCES DU CANDIDAT")
        resp = client.get(f'/candidate/{new_cand_id}/skills')
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Apply to Job
        print_section("CANDIDAT POSTULE POUR UNE OFFRE")
        resp = client.post('/apply', json={
            'candidate_id': new_cand_id,
            'job_id': new_job_id
        })
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Get Candidate Applications
        print_section("RÉCUPÉRER LES POSTULATIONS DU CANDIDAT")
        resp = client.get(f'/candidate/{new_cand_id}/applications')
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Get Job Applicants
        print_section("RÉCUPÉRER LES CANDIDATS POUR UNE OFFRE")
        resp = client.get(f'/job/{new_job_id}/candidates')
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Search
        print_section("RECHERCHE (Terme: 'python')")
        resp = client.get('/search?q=python&type=all')
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.get_json(), indent=2))
        
        # List Skills
        print_section("LISTER TOUTES LES COMPÉTENCES")
        resp = client.get('/skills')
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Delete Job
        print_section("SUPPRIMER UNE OFFRE")
        resp = client.delete(f'/job/{new_job_id}')
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.get_json(), indent=2))
        
        # Delete Candidate
        print_section("SUPPRIMER UN CANDIDAT")
        resp = client.delete(f'/candidate/{new_cand_id}')
        print(f"Status: {resp.status_code}")
        print(json.dumps(resp.get_json(), indent=2))
        
        print_section("TESTS TERMINÉS ✓")

if __name__ == '__main__':
    test_api()
