"""Xóa toàn bộ node + relationship trong Neo4j """
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
BATCH = 5000


def clear_db(session):
    total = 0
    while True:
        n = session.run(
            "MATCH (n) WITH n LIMIT $b DETACH DELETE n RETURN count(*) AS c", b=BATCH
        ).single()["c"]
        total += n
        if n == 0:
            return total


def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    with driver, driver.session(database=DATABASE) as session:
        print(f"Đã xóa {clear_db(session):,} node (kèm relationship).")


if __name__ == "__main__":
    main()