
import os
from dotenv import load_dotenv
from db import get_driver, init_driver

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

init_driver()
driver = get_driver()

jobs = [
    {
        "title": "Développeur Python",
        "company": "TechCorp", 
        "description": "Nous cherchons un expert Python avec des compétences en SQL et Data.",
        "location": "Paris",
        "salary": "50000"
    },
    {
        "title": "Data Analyst",
        "company": "DataViz", 
        "description": "Analyse de données, SQL, Python, Excel.",
        "location": "Lyon",
        "salary": "42000"
    },
    {
        "title": "Fullstack Java/React",
        "company": "WebAgency", 
        "description": "Développement web complet, Java Spring et React.",
        "location": "Remote",
        "salary": "55000"
    }
]

print("Seeding Jobs...")
if hasattr(driver, "_mock") and driver._mock:
    print("WARNING: Using Mock Driver (Seeding ignored/temporary)")
else:
    for job in jobs:
        cypher = """
        CREATE (j:Job {
            id: randomUUID(),
            title: $title,
            description: $description,
            company: $company,
            company_name_text: $company,
            location: $location,
            salary_min: $salary,
            created_at: datetime()
        })
        RETURN j.id as id
        """
        driver.run_query(cypher, job)
        print(f"Created job: {job['title']}")

print("Seeding Complete.")
