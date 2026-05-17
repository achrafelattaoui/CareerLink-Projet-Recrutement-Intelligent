
import os
import json
import random
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "neo4j")
database = os.getenv("NEO4J_DATABASE", "neo4j")

print(f"Connecting to {uri} (db: {database})...")

def seed_data(tx):
    print("Seeding synthetic employment history...")
    # Get some candidates with INTERNAL ID
    result = tx.run("MATCH (c:Candidate) RETURN id(c) as internal_id, c.full_name as name LIMIT 50")
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
             {"title": "Data Scientist", "duration": "2 ans", "company": "AI Lab"},
             {"title": "Lead Data Scientist", "duration": "2 ans", "company": "AI Lab"}
        ]
    ]
    
    count = 0
    for cand in candidates:
        if random.random() > 0.1: # Seed 90%
            history = random.choice(paths)
            hist_str = json.dumps(history)
            tx.run("""
                MATCH (c:Candidate) 
                WHERE id(c) = $id
                SET c.employment_history = $history
            """, id=cand['internal_id'], history=hist_str)
            count += 1
            
    print(f"Seeded history for {count} candidates.")

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session(database=database) as session:
        # Check using READ transaction
        result = session.run("""
            MATCH (c:Candidate) 
            WHERE c.employment_history IS NOT NULL 
            RETURN count(c) as count
        """)
        count = result.single()["count"]
        print(f"Current Candidates with history: {count}")
        
        if count < 10:
            # explicit write transaction
            with session.begin_transaction() as tx:
                seed_data(tx)
                tx.commit()
            print("Transaction committed.")
            
            # Verify
            result = session.run("MATCH (c:Candidate) WHERE c.employment_history IS NOT NULL RETURN count(c) as count")
            print(f"Verified count after seeding: {result.single()['count']}")
        else:
            print("Enough history exists.")

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'driver' in locals():
        driver.close()
