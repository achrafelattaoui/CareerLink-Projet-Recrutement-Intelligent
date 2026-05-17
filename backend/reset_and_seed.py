from db import init_driver
import os
from dotenv import load_dotenv
import random

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def reset_and_seed():
    driver = init_driver()
    if not driver: return

    print("--- 1. Clearing PREVIOUS Test Jobs (keeping real ones if any) ---")
    # We delete jobs created by our previous seed scripts (identified by specific titles or just wipe all for this demo user)
    # For safety, let's delete jobs from our 'Test Companies'
    
    test_companies = ["Tech Corp", "DataFlow", "Bank IT", "StartUp Hub", "BigData Corp", "SecureNet", "Innovate", "MediCare", "Global Brands", "Creative Studio", "Tech Solutions"]
    
    query_clear = """
    MATCH (c:Company)-[:POSTED]->(j:Job)
    WHERE c.company_name IN $companies
    DETACH DELETE j
    """
    driver.run_query(query_clear, {"companies": test_companies})
    print("Cleared old test jobs.")

    print("--- 2. Seeding DIVERSE Jobs ---")
    
    jobs_data = [
        # TECH
        ("Full Stack Developer", "Tech Solutions", "Casablanca", ["java", "react", "sql"], 18000),
        ("Python Backend Engineer", "DataFlow", "Rabat", ["python", "django", "sql"], 16000),
        ("Java Tech Lead", "Bank IT", "Casablanca", ["java", "spring", "sql", "leadership"], 30000),
        
        # MARKETING
        ("Digital Marketing Manager", "Global Brands", "Casablanca", ["marketing", "seo", "communication", "social media"], 14000),
        ("SEO Specialist", "Global Brands", "Rabat", ["seo", "analytics", "marketing"], 11000),
        ("Content Creator", "Creative Studio", "Marrakech", ["writing", "social media", "design"], 9000),
        
        # DESIGN
        ("UI/UX Designer", "Creative Studio", "Casablanca", ["design", "figma", "usability"], 13000),
        ("Graphic Designer", "Global Brands", "Tangier", ["design", "photoshop", "illustrator"], 10000),
        
        # HR / FINANCE
        ("HR Manager", "MediCare", "Rabat", ["hr", "management", "recruitment"], 18000),
        ("Financial Analyst", "Bank IT", "Casablanca", ["finance", "excel", "accounting"], 14500),
         ("Accountant", "MediCare", "Fes", ["accounting", "excel", "finance"], 11000),
    ]
    
    for title, company, location, skills, salary in jobs_data:
        # Create Company (Enriched) & Job
        query = """
        MERGE (c:Company {company_name: $company})
        SET c.sector = CASE 
            WHEN $company IN ['Tech Corp', 'DataFlow', 'Bank IT', 'Tech Solutions'] THEN 'IT Services'
            WHEN $company IN ['Global Brands', 'Creative Studio'] THEN 'Marketing & Design'
            WHEN $company = 'MediCare' THEN 'Healthcare'
            ELSE 'General' END,
            c.description = 'Top company in ' + $location,
            c.website = 'https://' + toLower(replace($company, ' ', '')) + '.com'
            
        CREATE (j:Job {
            job_id: randomUUID(),
            title: $title,
            description: 'We are hiring a ' + $title + ' to join our team. Must master ' + $req_skills + '.',
            location: $location,
            salary_min: toString($salary),
            date_posted: date()
        })
        MERGE (c)-[:POSTED]->(j)
        WITH j
        UNWIND $skills as skill_name
        MERGE (s:Skill {skill_name: skill_name})
        MERGE (j)-[:REQUIRES]->(s)
        RETURN j.title
        """
        
        driver.run_query(query, {
            "title": title,
            "company": company,
            "location": location,
            "skills": skills,
            "req_skills": ", ".join(skills),
            "salary": salary
        })
        print(f"Added: {title} at {company}")
        
    driver.close()

if __name__ == "__main__":
    reset_and_seed()
