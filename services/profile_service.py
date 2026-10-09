"""Hồ sơ và thống kê hoạt động của người dùng."""
from neo4j_connection import run_query


def get_profile(user_id):
    rows = run_query("""
        MATCH (u:User {userId: $u})
        WITH u, [(u)-[r:RATED]->(:Movie) | r.rating] AS rs
        RETURN u.userId AS userId, u.name AS name, u.email AS email, u.age AS age,
               u.city AS city, u.createdAt AS createdAt,
               COUNT { (u)-[:WATCHED]->() } AS watched,
               size(rs) AS rated,
               COUNT { MATCH (c:Comment) WHERE c.userId = u.userId } AS comments,
               COUNT { (u)-[:FRIEND]-() } AS friends,
               CASE WHEN size(rs) = 0 THEN 0 ELSE round(reduce(t = 0.0, x IN rs | t + x) / size(rs), 2) END AS avgRating
    """, {"u": user_id})
    if not rows:
        return None
    p = rows[0]
    p["topGenres"] = run_query("""
        MATCH (:User {userId: $u})-[r:RATED]->(:Movie)-[:HAS_GENRE]->(g:Genre)
        WHERE r.rating >= 4
        RETURN g.name AS genre, count(*) AS n, round(avg(r.rating), 2) AS diemTB
        ORDER BY n DESC, genre LIMIT 3
    """, {"u": user_id})
    return p
