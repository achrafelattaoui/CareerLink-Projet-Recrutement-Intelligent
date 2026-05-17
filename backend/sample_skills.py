from db import init_driver
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def sample_skills():
    driver = init_driver()
    if not driver: return
    
    print("--- Sampling Skill Names ---")
    # Get top 20 most frequent skills to see formatting
    query = """
    MATCH (s:Skill)
    RETURN s.skill_name, count(s) as c
    ORDER BY c DESC
    LIMIT 20
    """
    results = driver.run_query(query)
    for r in results:
        print(f"Skill: '{r['s.skill_name']}'")

    print("\n--- Checking 'Java' variations ---")
    query_java = """
    MATCH (s:Skill)
    WHERE toLower(s.skill_name) CONTAINS 'java'
    RETURN s.skill_name
    LIMIT 10
    """
    results = driver.run_query(query_java)
    for r in results:
        print(f"Java Variation: '{r['s.skill_name']}'")

    driver.close()

if __name__ == "__main__":
    sample_skills()
