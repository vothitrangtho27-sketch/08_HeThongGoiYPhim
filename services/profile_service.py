"""Hồ sơ và thống kê hoạt động của người dùng."""
from neo4j_connection import run_query


def get_profile(user_id):
    rows = run_query("""
        MATCH (u:User {userId: $u})
        RETURN u.userId AS userId, u.name AS name, u.email AS email, u.age AS age,
               u.city AS city, u.createdAt AS createdAt,
               COUNT { (u)-[:WATCHED]->() } AS watched,
               COUNT { (u)-[:RATED]->() } AS rated,
               COUNT { MATCH (c:Comment) WHERE c.userId = u.userId } AS comments,
               COUNT { (u)-[:FRIEND]-() } AS friends
    """, {"u": user_id})
    if not rows:
        return None
    p = rows[0]
    avg = run_query("MATCH (:User {userId: $u})-[r:RATED]->() RETURN round(avg(r.rating), 2) AS a", {"u": user_id})
    p["avgRating"] = avg[0]["a"] if avg and avg[0]["a"] is not None else 0
    p["topGenres"] = run_query("""
        MATCH (:User {userId: $u})-[r:RATED]->(:Movie)-[:HAS_GENRE]->(g:Genre)
        WHERE r.rating >= 4
        RETURN g.name AS genre, count(*) AS n ORDER BY n DESC LIMIT 3
    """, {"u": user_id})
    return p
