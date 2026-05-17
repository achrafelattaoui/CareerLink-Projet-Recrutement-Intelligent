import os
import random
from dotenv import load_dotenv
from db import get_driver, init_driver

# Load .env
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def seed_full():
    print("🚀 Starting Full Data Seeding...")
    init_driver()
    driver = get_driver()
    
    if not driver:
        print("❌ DB Connection Failed.")
        return

    # 1. Clear DB (Optional, but ensures clean state for debugging)
    print("🧹 Clearing Database...")
    driver.run_query("MATCH (n) DETACH DELETE n")

    # 2. Create Companies
    print("🏢 Creating Companies...")
    companies = ['TechCorp', 'DataViz', 'WebAgency', 'HealthPlus', 'EduTech']
    sectors = ['Tech', 'Data', 'Web', 'Santé', 'Education']
    
    for i, name in enumerate(companies):
        driver.run_query("""
            CREATE (c:Company {
                id: randomUUID(),
                company_name: $name,
                sector: $sector,
                location: 'Paris'
            })
        """, {'name': name, 'sector': sectors[i]})

    # 3. Create Jobs
    print("💼 Creating Jobs...")
    titles = ['Développeur Python', 'Data Analyst', 'Devops Engineer', 'Product Manager', 'UX Designer']
    locations = ['Paris', 'Lyon', 'Remote', 'Bordeaux', 'Toulouse']
    
    for _ in range(20):
        c_name = random.choice(companies)
        driver.run_query("""
            MATCH (c:Company {company_name: $c_name})
            CREATE (j:Job {
                id: randomUUID(),
                title: $title,
                company: $c_name,
                location: $loc,
                salary_min: $sal,
                created_at: datetime()
            })
            MERGE (c)-[:POSTED]->(j)
        """, {
            'c_name': c_name,
            'title': random.choice(titles),
            'loc': random.choice(locations),
            'sal': random.randint(30000, 70000)
        })

    # 4. Create Skills
    print("⚡ Creating Skills...")
    skills = ['Python', 'SQL', 'React', 'Java', 'Docker', 'AWS']
    for s in skills:
        driver.run_query("MERGE (s:Skill {name: $name, skill_name: $name})", {'name': s})

    # 5. Create Candidates & Link Skills
    print("👥 Creating Candidates...")
    for i in range(15):
        driver.run_query("""
            CREATE (c:Candidate {
                id: randomUUID(),
                name: 'Candidate ' + $i,
                email: 'cand' + $i + '@test.com'
            })
            WITH c
            MATCH (s:Skill)
            WITH c, s ORDER BY rand() LIMIT 2
            MERGE (c)-[:HAS_SKILL]->(s)
        """, {'i': str(i)})

    print("✅ Seeding Complete!")

if __name__ == "__main__":
    seed_full()
