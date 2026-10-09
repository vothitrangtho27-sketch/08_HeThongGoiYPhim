"""Kiểm tra dữ liệu sau import """
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")


def q(session, cypher, **kw):
    return [r.data() for r in session.run(cypher, **kw)]


def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    checks = []
    with driver, driver.session(database=DATABASE) as s:
        print("NODE theo nhãn ")
        nodes = q(s, "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS c ORDER BY c DESC")
        for r in nodes:
            print(f"  {r['label']:<10} {r['c']:>8,}")
        total_nodes = sum(r["c"] for r in nodes)

        print("RELATIONSHIP theo loại ")
        rels = q(s, "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c ORDER BY c DESC")
        for r in rels:
            print(f"  {r['t']:<10} {r['c']:>8,}")
        total_rels = sum(r["c"] for r in rels)
        print(f"\nTỔNG: {total_nodes:,} nodes | {total_rels:,} relationships")

        print("\n Mức độ kết nối của User ")
        rows = q(s, """
            MATCH (u:User)
            RETURN u.userId AS id,
                   size([(u)-[:RATED]->() | 1])    AS rated,
                   size([(u)-[:WATCHED]->() | 1])  AS watched,
                   size([(u)-[:FRIEND]-() | 1]) AS friends""")
        cm = {r["id"]: r["c"] for r in q(s, "MATCH (c:Comment) RETURN c.userId AS id, count(*) AS c")}
        for r in rows:
            r["comments"] = cm.get(r["id"], 0)
        stats = {}
        for k in ("rated", "watched", "friends", "comments"):
            vals = [r[k] for r in rows]
            stats[k] = vals
            print(f"  {k:<9} min={min(vals):<4} avg={sum(vals) / len(vals):<6.1f} max={max(vals):<4} "
                  f"user có 0: {sum(v == 0 for v in vals)}")
        u1 = next((r for r in rows if r["id"] == 1), None)
        if u1:
            print(f"  User 1    rated={u1['rated']} watched={u1['watched']} "
                  f"friends={u1['friends']} comments={u1['comments']}")

        isolated = q(s, "MATCH (n) WHERE NOT (n)--() RETURN count(n) AS c")[0]["c"]
        no_genre = q(s, "MATCH (m:Movie) WHERE NOT (m)-[:HAS_GENRE]->() RETURN count(m) AS c")[0]["c"]
        no_rating = q(s, "MATCH (m:Movie) WHERE NOT ()-[:RATED]->(m) RETURN count(m) AS c")[0]["c"]
        bad_rating = q(s, "MATCH ()-[r:RATED]->() WHERE r.rating < 1 OR r.rating > 5 RETURN count(r) AS c")[0]["c"]
        print(f"\nNode cô lập: {isolated} | Phim không thể loại: {no_genre} | "
              f"Phim chưa ai đánh giá: {no_rating} | Rating ngoài 1-5: {bad_rating}")

        checks = [
            ("Nodes trong 10.000 - 30.000", 10_000 <= total_nodes <= 30_000),
            ("Relationships trong 50.000 - 100.000", 50_000 <= total_rels <= 100_000),
            ("Không có node cô lập", isolated == 0),
            ("Mọi User có đánh giá", min(stats["rated"]) > 0),
            ("Mọi User có bạn bè", min(stats["friends"]) > 0),
            ("Mọi User có bình luận", min(stats["comments"]) > 0),
            ("Mọi Phim có thể loại", no_genre == 0),
            ("Mọi Phim có đánh giá", no_rating == 0),
            ("Điểm đánh giá hợp lệ (1-5)", bad_rating == 0),
        ]
    print("\n KẾT QUẢ ")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")


if __name__ == "__main__":
    main()

