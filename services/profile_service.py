"""Hồ sơ và thống kê hoạt động của người dùng."""
from neo4j_connection import run_query


def get_profile(user_id):
    """Một truy vấn duy nhất: thông tin, thống kê hoạt động và top 3 thể loại yêu thích."""
    rows = run_query("""
        MATCH (u:User {userId: $u})
        CALL {
            WITH u
            MATCH (u)-[r:RATED]->(:Movie)-[:HAS_GENRE]->(g:Genre)
            WHERE r.rating >= 4
            WITH g, count(*) AS n, avg(r.rating) AS diemTB
            ORDER BY n DESC, g.name
            LIMIT 3
            RETURN collect({genre: g.name, n: n, diemTB: round(diemTB, 2)}) AS topGenres
        }
        WITH u, topGenres, [(u)-[x:RATED]->(:Movie) | x.rating] AS rs
        RETURN u.userId AS userId, u.name AS name, u.email AS email, u.age AS age,
               u.city AS city, u.createdAt AS createdAt,
               COUNT { (u)-[:WATCHED]->() } AS watched,
               size(rs) AS rated,
               COUNT { MATCH (c:Comment) WHERE c.userId = u.userId } AS comments,
               COUNT { (u)-[:FRIEND]-() } AS friends,
               CASE WHEN size(rs) = 0 THEN 0 ELSE round(reduce(t = 0.0, v IN rs | t + v) / size(rs), 2) END AS avgRating,
               topGenres
    """, {"u": user_id})
    return rows[0] if rows else None
