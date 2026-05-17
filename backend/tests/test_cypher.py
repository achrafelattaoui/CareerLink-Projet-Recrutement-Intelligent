from db import init_driver, get_driver
import traceback
import os
from dotenv import load_dotenv

# Appeler load_dotenv() AVANT init_driver()
load_dotenv()

def test_queries():
    init_driver()
    driver = get_driver()
    
    if hasattr(driver, '_mock') and driver._mock:
        print("!!! DRIVER IS IN MOCK MODE !!! Checking .env...")
        print(f"NEO4J_URI: {os.getenv('NEO4J_URI')}")
        return

    queries = {
        "Candidates": """
            MATCH (c:Candidate)
            RETURN DISTINCT toString(COALESCE(c.cv_id, c.id)) as id, 
                   COALESCE(c.full_name, c.name, 'Unknown') as name,
                   c.email as email, c.phone as phone,
                   c.current_title as current_title,
                   c.location as location
            ORDER BY name ASC
            LIMIT 100
        """,
        "Jobs": """
            MATCH (j:Job) 
            RETURN DISTINCT toString(COALESCE(j.job_id, j.id)) as id, j.title as title, 
                   j.company_name_text as company, j.location as location,
                   toString(j.created_at) as created_at
            ORDER BY j.created_at DESC
            LIMIT 100
        """,
        "Companies": """
            MATCH (c:Company) 
            RETURN DISTINCT toString(COALESCE(c.company_id, c.id)) as id, 
                   COALESCE(c.company_name, c.name) as name,
                   c.location as location
            ORDER BY name ASC LIMIT 100
        """
    }
    
    for name, cypher in queries.items():
        print(f"--- Testing {name} ---")
        try:
            res = driver.run_query(cypher)
            print(f"Success: {len(res)} records")
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    test_queries()
