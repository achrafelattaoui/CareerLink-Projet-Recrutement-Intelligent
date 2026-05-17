from neo4j import GraphDatabase
import os
import random
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))

def seed_relations():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session() as session:
        print("1. Seeding Candidate Skills...")
        # Get Candidates and Skills
        cands = session.run("MATCH (c:Candidate) RETURN elementId(c) as id").value()
        skills = session.run("MATCH (s:Skill) RETURN elementId(s) as id").value()
        
        if not cands: print("No candidates found!"); return
        if not skills: print("No skills found!"); return

        # Link random skills to candidates (batching for speed)
        # We'll just link 500 candidates to random skills to ensure chart data
        target_cands = random.sample(cands, min(len(cands), 500))
        
        for cid in target_cands:
            my_skills = random.sample(skills, k=min(len(skills), 3))
            session.run("""
                MATCH (c:Candidate), (s:Skill)
                WHERE elementId(c) = $cid AND elementId(s) IN $sids
                MERGE (c)-[:HAS_SKILL]->(s)
            """, cid=cid, sids=my_skills)
        print(f"Linked {len(target_cands)} candidates to skills.")

        print("2. Ensuring Job-Company Links...")
        # Link orphan jobs to random companies
        res = session.run("""
            MATCH (j:Job) WHERE NOT (()-[:POSTED]->(j))
            WITH j
            MATCH (c:Company) 
            WITH j, c ORDER BY rand() LIMIT 1
            MERGE (c)-[:POSTED]->(j)
            RETURN count(j) as updated
        """)
        print(f"Linked orphan jobs: {res.single()['updated']}")

    driver.close()

if __name__ == "__main__":
    seed_relations()
