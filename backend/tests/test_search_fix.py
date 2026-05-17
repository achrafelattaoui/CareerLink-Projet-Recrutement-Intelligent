
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Load .env
load_dotenv()

uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "neo4j") # Defaulting to common defaults if env missing

print(f"Connecting to Neo4j at {uri}...")

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    print("Combined connectivity verified.")
except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)

def test_search(query_term):
    print(f"\n--- Testing search for: '{query_term}' ---")
    q_lower = query_term.lower()
    
    # Using the logic from routes.py (updated state)
    tokens = [t for t in q_lower.split() if t]
    
    cypher = """
    MATCH (j:Job)
    OPTIONAL MATCH (comp:Company)-[:POSTED]->(j)
    WITH j, comp, toLower(toString(coalesce(j.title, '')) + ' ' + 
                          toString(coalesce(j.company_name_text, '')) + ' ' + 
                          toString(coalesce(j.location, '')) + ' ' + 
                          toString(coalesce(comp.company_name, ''))) as searchable
    WHERE all(token IN $tokens WHERE searchable CONTAINS token)
    RETURN j.title as title, COALESCE(comp.company_name, j.company_name_text) as company
    LIMIT 5
    """
    
    with driver.session() as session:
        result = session.run(cypher, {"tokens": tokens})
        records = list(result)
        print(f"Found {len(records)} jobs.")
        for r in records:
            print(f" - {r['title']} ({r['company']})")

if __name__ == "__main__":
    test_search("Python")
    test_search("Dev Python") # Should fail if strict phrase match is used and order differs
    test_search("Marketing")
    driver.close()
