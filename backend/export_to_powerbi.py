"""
Export Neo4j data to CSV files for Power BI Dashboard.
Run this script to generate the CSV files:
    python export_to_powerbi.py

Files generated in ./powerbi_exports/:
  - candidates.csv
  - jobs.csv
  - companies.csv
  - applications.csv
  - skills.csv
  - candidate_skills.csv
  - recruiter_stats.csv
"""

import os
import csv
from dotenv import load_dotenv
from db import init_driver, get_driver

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'powerbi_exports')
os.makedirs(OUTPUT_DIR, exist_ok=True)

def write_csv(filename, rows, fieldnames):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:  # BOM for Excel/PowerBI
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"[OK] {filename} — {len(rows)} rows written to {path}")


def export_candidates(driver):
    cypher = """
    MATCH (c)
    WHERE c:Candidate OR c:Candidate_Cv
    OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill)
    WITH c,
         COALESCE(c.full_name, c.name) as name,
         c.email as email,
         c.current_title as current_title,
         c.location as location,
         c.experience_level as experience_level,
         c.education as education,
         count(DISTINCT s) as skill_count
    RETURN
        toString(COALESCE(c.cv_id, c.id, elementId(c))) as id,
        name,
        email,
        current_title,
        location,
        experience_level,
        education,
        skill_count
    ORDER BY name
    """
    rows = driver.run_query(cypher) or []
    write_csv('candidates.csv', rows, [
        'id', 'name', 'email', 'current_title',
        'location', 'experience_level', 'education', 'skill_count'
    ])


def export_jobs(driver):
    cypher = """
    MATCH (j:Job)
    OPTIONAL MATCH (comp:Company)-[:POSTED]->(j)
    OPTIONAL MATCH (j)<-[:APPLIED_TO|TARGETS]-(c)
    WHERE (c:Candidate OR c:Candidate_Cv)
    WITH j, comp, count(DISTINCT c) as applicant_count
    RETURN
        toString(COALESCE(j.job_id, j.id, elementId(j))) as id,
        j.title as title,
        COALESCE(comp.company_name, j.company_name_text, 'N/A') as company,
        COALESCE(comp.sector, 'N/A') as sector,
        j.location as location,
        COALESCE(j.salary_min, j.salary, 'N/A') as salary,
        applicant_count,
        COALESCE(j.created_at, '') as created_at
    ORDER BY applicant_count DESC
    """
    rows = driver.run_query(cypher) or []
    write_csv('jobs.csv', rows, [
        'id', 'title', 'company', 'sector',
        'location', 'salary', 'applicant_count', 'created_at'
    ])


def export_companies(driver):
    cypher = """
    MATCH (comp:Company)
    OPTIONAL MATCH (comp)-[:POSTED]->(j:Job)
    OPTIONAL MATCH (comp)<-[:WORKED_AT|TARGETS]-(c)
    WHERE (c:Candidate OR c:Candidate_Cv)
    WITH comp,
         count(DISTINCT j) as job_count,
         count(DISTINCT c) as candidate_count
    RETURN
        toString(COALESCE(comp.company_id, elementId(comp))) as id,
        COALESCE(comp.company_name, 'N/A') as company_name,
        COALESCE(comp.sector, 'N/A') as sector,
        COALESCE(comp.location, 'N/A') as location,
        COALESCE(comp.size, 'N/A') as company_size,
        COALESCE(comp.recruiter_name, 'N/A') as recruiter_name,
        COALESCE(comp.recruiter_email, 'N/A') as recruiter_email,
        job_count,
        candidate_count
    ORDER BY company_name
    """
    rows = driver.run_query(cypher) or []
    write_csv('companies.csv', rows, [
        'id', 'company_name', 'sector', 'location',
        'company_size', 'recruiter_name', 'recruiter_email',
        'job_count', 'candidate_count'
    ])


def export_applications(driver):
    cypher = """
    MATCH (c)-[r:APPLIED_TO|TARGETS]->(j:Job)
    WHERE (c:Candidate OR c:Candidate_Cv)
    OPTIONAL MATCH (comp:Company)-[:POSTED]->(j)
    RETURN
        toString(COALESCE(c.cv_id, c.id, elementId(c))) as candidate_id,
        COALESCE(c.full_name, c.name, 'N/A') as candidate_name,
        toString(COALESCE(j.job_id, j.id, elementId(j))) as job_id,
        j.title as job_title,
        COALESCE(comp.company_name, 'N/A') as company_name,
        COALESCE(comp.sector, 'N/A') as sector,
        type(r) as relation_type,
        COALESCE(r.date, r.applied_at, '') as application_date
    ORDER BY company_name, job_title
    """
    rows = driver.run_query(cypher) or []
    write_csv('applications.csv', rows, [
        'candidate_id', 'candidate_name', 'job_id', 'job_title',
        'company_name', 'sector', 'relation_type', 'application_date'
    ])


def export_skills(driver):
    cypher = """
    MATCH (c)-[:HAS_SKILL]->(s:Skill)
    WHERE (c:Candidate OR c:Candidate_Cv)
    WITH
        toLower(COALESCE(s.skill_name, s.name, 'Unknown')) as skill_name,
        count(DISTINCT c) as candidate_count
    RETURN skill_name, candidate_count
    ORDER BY candidate_count DESC
    LIMIT 100
    """
    rows = driver.run_query(cypher) or []
    write_csv('skills.csv', rows, ['skill_name', 'candidate_count'])


def export_candidate_skills(driver):
    cypher = """
    MATCH (c)-[:HAS_SKILL]->(s:Skill)
    WHERE (c:Candidate OR c:Candidate_Cv)
    RETURN
        toString(COALESCE(c.cv_id, c.id, elementId(c))) as candidate_id,
        COALESCE(c.full_name, c.name, 'N/A') as candidate_name,
        toLower(COALESCE(s.skill_name, s.name, 'Unknown')) as skill_name
    ORDER BY candidate_name
    """
    rows = driver.run_query(cypher) or []
    write_csv('candidate_skills.csv', rows, [
        'candidate_id', 'candidate_name', 'skill_name'
    ])


def export_recruiter_stats(driver):
    cypher = """
    MATCH (comp:Company)
    WHERE comp.recruiter_email IS NOT NULL
    OPTIONAL MATCH (comp)-[:POSTED]->(j:Job)
    OPTIONAL MATCH (j)<-[:APPLIED_TO|TARGETS]-(c)
    WHERE (c:Candidate OR c:Candidate_Cv)
    WITH comp,
         count(DISTINCT j) as total_jobs,
         count(DISTINCT c) as total_applicants
    RETURN
        COALESCE(comp.company_name, 'N/A') as company_name,
        COALESCE(comp.recruiter_name, 'N/A') as recruiter_name,
        COALESCE(comp.recruiter_email, 'N/A') as recruiter_email,
        COALESCE(comp.sector, 'N/A') as sector,
        total_jobs,
        total_applicants,
        CASE WHEN total_jobs > 0 THEN round(toFloat(total_applicants) / total_jobs, 2) ELSE 0 END as avg_applicants_per_job
    ORDER BY total_applicants DESC
    """
    rows = driver.run_query(cypher) or []
    write_csv('recruiter_stats.csv', rows, [
        'company_name', 'recruiter_name', 'recruiter_email', 'sector',
        'total_jobs', 'total_applicants', 'avg_applicants_per_job'
    ])


def main():
    print("=" * 60)
    print("  Neo4j -> Power BI Export Script")
    print("=" * 60)
    init_driver()
    driver = get_driver()
    if not driver:
        print("[ERROR] Could not connect to Neo4j. Check your .env settings.")
        return

    print(f"\nExporting data to: {os.path.abspath(OUTPUT_DIR)}\n")

    try:
        export_candidates(driver)
        export_jobs(driver)
        export_companies(driver)
        export_applications(driver)
        export_skills(driver)
        export_candidate_skills(driver)
        export_recruiter_stats(driver)
    except Exception as e:
        import traceback
        print(f"[ERROR] {traceback.format_exc()}")

    print("\n" + "=" * 60)
    print("  Export complete! Open Power BI and import the CSV files.")
    print("  Folder: " + os.path.abspath(OUTPUT_DIR))
    print("=" * 60)


if __name__ == '__main__':
    main()
