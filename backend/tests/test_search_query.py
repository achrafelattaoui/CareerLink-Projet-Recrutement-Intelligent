"""Test script to verify search query filtering in Neo4j"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "achraf2004")
database = os.getenv("NEO4J_DATABASE", "neo4j")

driver = GraphDatabase.driver(uri, auth=(user, password))

def test_job_search(query_term):
    """Test job search with filtering"""
    q_lower = query_term.lower()
    
    # Count query
    cypher_count = """
    MATCH (j:Job)
    OPTIONAL MATCH (comp:Company)-[:POSTED]->(j)
    WHERE toLower(coalesce(j.title, '')) CONTAINS $q
       OR toLower(coalesce(j.company_name_text, '')) CONTAINS $q
       OR toLower(coalesce(comp.company_name, '')) CONTAINS $q
    RETURN count(j) as total
    """
    
    # Results query
    cypher_results = """
    MATCH (j:Job)
    OPTIONAL MATCH (comp:Company)-[:POSTED]->(j)
    WHERE toLower(coalesce(j.title, '')) CONTAINS $q
       OR toLower(coalesce(j.company_name_text, '')) CONTAINS $q
       OR toLower(coalesce(comp.company_name, '')) CONTAINS $q
    RETURN DISTINCT toString(COALESCE(j.job_id, j.id)) as id, j.title as title, 
           COALESCE(comp.company_name, j.company_name_text) as company, 
           j.salary_min as salary, j.location as location
    ORDER BY j.created_at DESC
    LIMIT 5
    """
    
    with driver.session(database=database) as session:
        # Get count
        count_result = session.run(cypher_count, {"q": q_lower})
        total = count_result.single()["total"]
        print(f"\n=== Search for '{query_term}' ===")
        print(f"Total jobs found: {total}")
        
        # Get sample results
        results = session.run(cypher_results, {"q": q_lower})
        print(f"\nFirst 5 results:")
        for i, record in enumerate(results, 1):
            print(f"{i}. {record['title']} - {record['company']}")

if __name__ == "__main__":
    # Test with "marketing"
    test_job_search("marketing")
    
    # Test with "sales"
    test_job_search("sales")
    
    # Test with empty string (should return all)
    test_job_search("")
    
    driver.close()
