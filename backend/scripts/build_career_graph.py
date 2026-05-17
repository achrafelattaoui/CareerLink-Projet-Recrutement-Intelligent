
import os
import json
import re
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

uri = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "neo4j")

def normalize_title(title):
    if not title: return "Unknown"
    # Basic normalization: lowercase, remove special chars, trim
    t = title.lower().strip()
    return re.sub(r'[^a-z0-9\s]', '', t)

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        print("Cleaning old Career Graph...")
        session.run("MATCH (n:CareerStep) DETACH DELETE n")
        
        print("Building new Career Graph...")
        # Fetch all histories
        result = session.run("MATCH (c:Candidate) WHERE c.employment_history IS NOT NULL RETURN c.id, c.employment_history")
        
        count_nodes = 0
        count_rels = 0
        
        for record in result:
            hist_str = record["c.employment_history"]
            # print(f"DEBUG: Found history string: {hist_str[:50]}...")
            try:
                history = json.loads(hist_str)
            except Exception as e:
                print(f"DEBUG: JSON load error: {e}")
                continue
                
            if not isinstance(history, list) or len(history) < 2:
                # print(f"DEBUG: History is not list or too short: {type(history)}")
                continue
            
            # Sort likely by time? The seed data is ordered chronologically.
            # Assuming history list is ordered: [Job 1, Job 2, Job 3 (current)]
            print(f"DEBUG: Processing history with {len(history)} items", flush=True)
            
            for i in range(len(history) - 1):
                current_job = history[i]
                next_job = history[i+1]
                
                curr_title = current_job.get("title")
                next_title = next_job.get("title")
                
                if not curr_title or not next_title: continue
                
                # Cypher to merge nodes and relationships
                # We store both display title (first one seen) and normalized for matching
                cypher = """
                MERGE (s1:CareerStep {normalized_title: $norm1})
                ON CREATE SET s1.title = $title1
                
                MERGE (s2:CareerStep {normalized_title: $norm2})
                ON CREATE SET s2.title = $title2
                
                MERGE (s1)-[r:LEADS_TO]->(s2)
                ON CREATE SET r.count = 1
                ON MATCH SET r.count = r.count + 1
                """
                
                session.run(cypher, 
                            norm1=normalize_title(curr_title), title1=curr_title,
                            norm2=normalize_title(next_title), title2=next_title)
                
                count_rels += 1

        print(f"Graph built. Processed connections: {count_rels}")
        
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'driver' in locals():
        driver.close()
