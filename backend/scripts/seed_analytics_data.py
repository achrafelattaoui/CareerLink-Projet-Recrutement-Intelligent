import random
import os
from dotenv import load_dotenv
from db import get_driver, init_driver
from datetime import datetime, timedelta

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def seed_analytics():
    init_driver()
    driver = get_driver()
    
    # 1. Seed Sectors for Companies
    sectors = ['Tech', 'Finance', 'Santé', 'Distribution', 'Industrie', 'Conseil']
    print("Seeding Sectors...")
    driver.run_query("""
        MATCH (c:Company)
        WITH c, $sectors as sectors
        WITH c, sectors[toInteger(rand() * size(sectors))] as random_sector
        SET c.sector = random_sector
        RETURN count(c) as updated
    """, {"sectors": sectors})

    # 2. Seed Salaries for Jobs
    print("Seeding Salaries...")
    driver.run_query("""
        MATCH (j:Job)
        WITH j
        // Random salary between 28k and 80k
        WITH j, 28000 + toInteger(rand() * 52000) as random_salary
        SET j.salary_min = random_salary
        RETURN count(j) as updated
    """)

    # 3. Seed Evolution Dates (Spread over last 12 months)
    print("Seeding Dates...")
    # Neo4j has no easy random date function that is simple. 
    # Let's do it in Python loop to be safe and use parameters.
    
    # Get all job IDs
    jobs = driver.run_query("MATCH (j:Job) RETURN elementId(j) as id") 
    # Note: elementId might be new, use id(j) if older, or just match and update random chunk.
    # Safe robust way:
    
    cypher_date = """
        MATCH (j:Job)
        WITH j, timestamp() - toInteger(rand() * 31536000000) as random_time
        SET j.created_at = random_time
        RETURN count(j)
    """
    # 31536000000 ms = 1 year approx.
    driver.run_query(cypher_date)
    
    print("Analytics Data Seeded.")

if __name__ == "__main__":
    seed_analytics()
