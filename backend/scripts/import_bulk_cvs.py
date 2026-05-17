import os
import re
import sys
import docx
from dotenv import load_dotenv

# Load env variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Add parent dir to path to import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import init_driver

def extract_text_from_docx(file_path):
    try:
        doc = docx.Document(file_path)
        return " ".join([p.text for p in doc.paragraphs])
    except Exception as e:
        print(f"Failed to read {file_path}: {e}")
        return ""

def process_resumes(directory):
    driver = init_driver()
    if not driver or getattr(driver, '_mock', False):
        print("Neo4j driver is not initialized or in mock mode.")
        return

    # fetch db skills
    query_all_skills = "MATCH (s:Skill) RETURN DISTINCT toLower(s.skill_name) as name"
    try:
        all_skills_records = driver.run_query(query_all_skills)
        db_skills = [r["name"] for r in all_skills_records if r.get("name")]
    except Exception as e:
        db_skills = []

    # fallback skills
    fallback_skills = ["python", "java", "sql", "react", "node", "javascript", "docker", "aws", "c++", "c#", "mongodb", "django", "html", "css", "spring", "agile", "scrum", "project management"]
    for s in fallback_skills:
        if s not in db_skills:
            db_skills.append(s)

    files = [f for f in os.listdir(directory) if f.endswith('.docx') or f.endswith('.doc')]
    print(f"Found {len(files)} resume files.")

    for filename in files:
        file_path = os.path.join(directory, filename)
        if filename.endswith('.docx'):
            text = extract_text_from_docx(file_path)
        else:
            print(f"Skipping {filename}, only .docx currently supported.")
            continue

        if not text:
            continue

        clean_text = re.sub(r'[^a-zA-Z0-9\+#]', ' ', text.lower())
        clean_text_norm = " ".join(clean_text.split())
        padded_text = f" {clean_text_norm} "

        detected_skills = []
        for skill in db_skills:
            skill_clean = re.sub(r'[^a-zA-Z0-9\+#]', ' ', skill.lower())
            skill_norm = " ".join(skill_clean.split())
            if f" {skill_norm} " in padded_text:
                detected_skills.append(skill)
        
        detected_skills = sorted(list(set(detected_skills)))
        
        # Get name from filename
        name = os.path.splitext(filename)[0].replace('_', ' ')
        
        cypher = """
        CREATE (c:Candidate {
            cv_id: randomUUID(),
            full_name: $name,
            name: $name,
            created_at: timestamp(),
            source: 'bulk_import'
        })
        WITH c
        UNWIND $skills AS skill_name
        MERGE (s:Skill {skill_name: skill_name})
        ON CREATE SET s.name = skill_name
        MERGE (c)-[:HAS_SKILL]->(s)
        """
        try:
            # Only run the query if skills are detected to avoid creating empty candidates
            # Or perhaps the user wants the candidate regardless
            # Using UNWIND on empty list will fail if we don't handle it
            if detected_skills:
                driver.run_query(cypher, {"name": name, "skills": detected_skills})
            else:
                empty_cypher = """
                CREATE (c:Candidate {
                    cv_id: randomUUID(),
                    full_name: $name,
                    name: $name,
                    created_at: timestamp(),
                    source: 'bulk_import'
                })
                """
                driver.run_query(empty_cypher, {"name": name})
            print(f"Imported {name} with {len(detected_skills)} skills.")
        except Exception as e:
            print(f"Failed to import {name}: {e}")

if __name__ == "__main__":
    directory = r"C:\Users\USER\Downloads\Resumes"
    process_resumes(directory)
