from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
import json

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))

def simulate_analytics():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session() as session:
        print("\n--- 1. CANDIDATES BY SKILL ---")
        q1 = """
        MATCH (c:Candidate)-[:HAS_SKILL]->(s:Skill)
        RETURN s.skill_name as label, count(c) as count
        ORDER BY count DESC LIMIT 5
        """
        res1 = session.run(q1).data()
        print(json.dumps(res1, indent=2))

        print("\n--- 2. GEO DISTRIBUTION ---")
        q2 = """
        MATCH (j:Job)
        RETURN j.location as label, count(j) as count
        ORDER BY count DESC LIMIT 5
        """
        res2 = session.run(q2).data()
        print(json.dumps(res2, indent=2))

        print("\n--- 3. JOB EVOLUTION ---")
        q3 = """
        MATCH (j:Job)
        WITH j, 
             CASE 
                WHEN toString(j.created_at) CONTAINS '-' THEN date(j.created_at) 
                ELSE date(datetime({epochMillis: toInteger(j.created_at)})) 
             END as d
        RETURN toString(d.month) + '/' + toString(d.year) as label, 
               d.year as year, d.month as month, count(j) as count
        ORDER BY year, month LIMIT 5
        """
        try:
             res3 = session.run(q3).data()
             print(json.dumps(res3, indent=2))
        except Exception as e:
             print(f"Error Q3: {e}")

    driver.close()

if __name__ == "__main__":
    simulate_analytics()
