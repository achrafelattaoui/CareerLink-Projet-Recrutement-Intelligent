import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "neo4j")

try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        res = session.run("""
        MATCH (u:User {email: 'testeur.candidat@test.com'})
        MATCH (c:Candidate {email: 'testeur.candidat@test.com'})
        RETURN u.email, elementId(u), c.email, c.user_id, c.current_title, c.location
        """)
        for r in res:
            print("User Email:", r["u.email"])
            print("User elementId:", r["elementId(u)"])
            print("Candidate Email:", r["c.email"])
            print("Candidate user_id:", r["c.user_id"])
            print("Candidate Title:", r["c.current_title"])
            print("Candidate Location:", r["c.location"])
            print("MATCH:", r["elementId(u)"] == r["c.user_id"])
except Exception as e:
    print(f"Error: {e}")
