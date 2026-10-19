"""Import data/*.csv vào Neo4j (chạy: py import_data.py). Có thể chạy lại nhiều lần (MERGE)."""
import csv
import os
import time

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
DATA_DIR = "data"
BATCH = 2000

CONSTRAINTS = [
    "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (n:User) REQUIRE n.userId IS UNIQUE",
    "CREATE CONSTRAINT movie_id IF NOT EXISTS FOR (n:Movie) REQUIRE n.movieId IS UNIQUE",
    "CREATE CONSTRAINT genre_id IF NOT EXISTS FOR (n:Genre) REQUIRE n.genreId IS UNIQUE",
    "CREATE CONSTRAINT comment_id IF NOT EXISTS FOR (n:Comment) REQUIRE n.commentId IS UNIQUE",
]
INDEXES = [
    "CREATE INDEX user_email IF NOT EXISTS FOR (n:User) ON (n.email)",
    "CREATE INDEX movie_title IF NOT EXISTS FOR (n:Movie) ON (n.title)",
    "CREATE INDEX comment_user IF NOT EXISTS FOR (n:Comment) ON (n.userId)",
]


JOBS = [
    ("users.csv", {"userId": int, "age": int}, """
        UNWIND $rows AS r
        MERGE (n:User {userId: r.userId})
        SET n.name = r.name, n.email = r.email, n.age = r.age, n.city = r.city,
            n.password = r.password, n.createdAt = r.createdAt"""),
    ("movies.csv", {"movieId": int, "year": int, "duration": int}, """
        UNWIND $rows AS r
        MERGE (n:Movie {movieId: r.movieId})
        SET n.title = r.title, n.year = r.year, n.duration = r.duration"""),
    ("genres.csv", {"genreId": int}, """
        UNWIND $rows AS r
        MERGE (n:Genre {genreId: r.genreId})
        SET n.name = r.name"""),
    ("movie_genres.csv", {"movieId": int, "genreId": int}, """
        UNWIND $rows AS r
        MATCH (m:Movie {movieId: r.movieId}), (g:Genre {genreId: r.genreId})
        MERGE (m)-[:HAS_GENRE]->(g)"""),
    ("ratings.csv", {"userId": int, "movieId": int, "rating": int}, """
        UNWIND $rows AS r
        MATCH (u:User {userId: r.userId}), (m:Movie {movieId: r.movieId})
        MERGE (u)-[x:RATED]->(m)
        SET x.rating = r.rating, x.ratedAt = r.ratedAt"""),
    ("watched.csv", {"userId": int, "movieId": int}, """
        UNWIND $rows AS r
        MATCH (u:User {userId: r.userId}), (m:Movie {movieId: r.movieId})
        MERGE (u)-[x:WATCHED]->(m)
        SET x.watchedAt = r.watchedAt"""),
    ("friends.csv", {"userId": int, "friendId": int}, """
        UNWIND $rows AS r
        MATCH (a:User {userId: r.userId}), (b:User {userId: r.friendId})
        MERGE (a)-[x:FRIEND]->(b)
        SET x.since = r.since"""),
    ("comments.csv", {"commentId": int, "userId": int, "movieId": int}, """
        UNWIND $rows AS r
        MATCH (m:Movie {movieId: r.movieId})
        MERGE (c:Comment {commentId: r.commentId})
        SET c.userId = r.userId, c.content = r.content, c.createdAt = r.createdAt
        MERGE (c)-[:ABOUT]->(m)"""),
]


def read_csv(name, conv):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, fn in conv.items():
            r[k] = fn(r[k])
    return rows


def main():
    t0 = time.time()
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    with driver, driver.session(database=DATABASE) as session:
        for q in CONSTRAINTS + INDEXES:
            session.run(q)
        for name, conv, cypher in JOBS:
            rows = read_csv(name, conv)
            for i in range(0, len(rows), BATCH):
                session.run(cypher, rows=rows[i:i + BATCH]).consume()
            print(f"  {name:<18} {len(rows):>7} dòng  ✓")
    print(f"Import xong trong {time.time() - t0:.1f}s. Chạy: py verify_data.py")


if __name__ == "__main__":
    main()