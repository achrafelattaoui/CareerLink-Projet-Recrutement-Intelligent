
import os
import json
import random
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "neo4j")

def seed_data(session):
    print("Seeding synthetic employment history...")
    # Get some candidates
    result = session.run("MATCH (c:Candidate) RETURN c.id as id, c.full_name as name LIMIT 50")
    candidates = list(result)
    
    paths = [
        [
            {"title": "Stagiaire Développeur", "duration": "6 mois", "company": "StartUp A"},
            {"title": "Développeur Junior", "duration": "2 ans", "company": "StartUp A"},
            {"title": "Développeur Senior", "duration": "3 ans", "company": "BigCorp"}
        ],
        [
            {"title": "Help Desk", "duration": "1 an", "company": "IT Services"},
            {"title": "Administrateur Système", "duration": "3 ans", "company": "Bank"},
            {"title": "Ingénieur DevOps", "duration": "2 ans", "company": "Tech Giant"}
        ],
        [
            {"title": "Business Analyst Junior", "duration": "2 ans", "company": "Consulting"},
            {"title": "Product Owner", "duration": "3 ans", "company": "Product Co"}
        ],
        [
             {"title": "Data Analyst", "duration": "2 ans", "company": "DataCorp"},
             {"title": "Data Scientist", "duration": "2 ans", "company": "AI Lab"}
        ]
    ]
    
    count = 0
    for cand in candidates:
        if random.random() > 0.3: # Seed 70% of them
            history = random.choice(paths)
            # Serialize as JSON string for property
            hist_str = json.dumps(history)
            session.run("""
                MATCH (c:Candidate {id: $id}) 
                SET c.employment_history = $history
            """, id=cand['id'], history=hist_str)
            count += 1
            
    print(f"Seeded history for {count} candidates.")

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # Check Candidate_Cv
        result = session.run("""
            MATCH (cCv:Candidate_Cv) 
            WHERE cCv.employment_history IS NOT NULL 
            RETURN cCv.full_name, cCv.employment_history
            LIMIT 5
        """)
        records = list(result)
        
        if records:
            print(f"Found {len(records)} Candidate_Cv with history.")
        else:
            print("No Candidate_Cv history found.")

        # Check Candidate again
        result = session.run("""
            MATCH (c:Candidate) 
            WHERE c.employment_history IS NOT NULL 
            RETURN c.full_name
            LIMIT 1
        """)
        if not result.single():
            print("Still no Candidate history found. Initiating SEEDING...")
            seed_data(session)
        else:
            print("Candidate history exists (at least one node).")

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'driver' in locals():
        driver.close()
