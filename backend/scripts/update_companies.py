import csv
import sys
import os
from dotenv import load_dotenv

os.environ['DB_MODE'] = 'neo4j'

# Load env variables from backend directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(backend_dir, '.env'))

sys.path.append(backend_dir)
from db import init_driver

def update_companies(csv_path):
    driver = init_driver()
    if not driver:
        print("Erreur: Impossible de se connecter à Neo4j.")
        return

    try:
        with open(csv_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            count = 0
            for row in reader:
                # Build properties dictionary from row
                props = {
                    "company_id": row.get("company_id", ""),
                    "company_name": row.get("company_name", ""),
                    "sector": row.get("sector", ""),
                    "recruiter_name": row.get("recruiter_name", ""),
                    "recruiter_email": row.get("recruiter_email", ""),
                    "location": row.get("location", ""),
                    "company_size": row.get("company_size", ""),
                    "founded_year": row.get("founded_year", ""),
                    "description": row.get("description", ""),
                    "industry_keywords": row.get("industry_keywords", ""),
                    "website": row.get("website", "")
                }
                
                # Make sure company_name exists, skip if not
                if not props["company_name"]:
                    continue

                cypher = """
                MERGE (c:Company {company_name: $props.company_name})
                SET c.company_id = $props.company_id,
                    c.name = $props.company_name,
                    c.sector = $props.sector,
                    c.recruiter_name = $props.recruiter_name,
                    c.recruiter_email = $props.recruiter_email,
                    c.location = $props.location,
                    c.company_size = $props.company_size,
                    c.founded_year = CASE WHEN $props.founded_year = '' THEN null ELSE toInteger($props.founded_year) END,
                    c.description = $props.description,
                    c.industry_keywords = $props.industry_keywords,
                    c.website = $props.website,
                    c.updated_at = timestamp()
                """
                
                try:
                    driver.run_query(cypher, {"props": props})
                    count += 1
                    if count % 50 == 0:
                        print(f"{count} entreprises mises à jour...")
                except Exception as node_err:
                    print(f"Erreur l'insertion de l'entreprise {props['company_name']}: {node_err}")

            print(f"Terminé ! {count} nœuds Company ont été mis à jour avec les recruteurs et autres détails.")

            # Trigger auto-seeding of users for these newly updated companies
            print("Auto-seeding des comptes recruteurs dans la collection User...")
            try:
                driver._init_default_users()
                print("Création de comptes recruteurs réussie.")
            except Exception as seed_err:
                print(f"Erreur lors de la création des users: {seed_err}")

    except Exception as e:
        print(f"Erreur d'accès ou lecture du CSV: {e}")

if __name__ == "__main__":
    target_csv = r"C:\Users\USER\.Neo4jDesktop2\Data\dbmss\dbms-6bfcd9af-5cec-473b-8d28-db29f0ccaac1\import\companies_500_multi_cities_long_description.csv"
    print(f"Lecture du CSV: {target_csv}")
    update_companies(target_csv)
