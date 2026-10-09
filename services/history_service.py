"""Lịch sử xem phim."""
import redis_connection as rc
from neo4j_connection import run_query


def mark_watched(user_id, movie_id):
    run_query("""
        MATCH (u:User {userId: $u}), (m:Movie {movieId: $m})
        MERGE (u)-[w:WATCHED]->(m) ON CREATE SET w.watchedAt = toString(date())
    """, {"u": user_id, "m": int(movie_id)})
    rc.cache_delete_pattern(f"rec:{user_id}:*")


def get_history(user_id, limit=50):
    return run_query("""
        MATCH (:User {userId: $u})-[w:WATCHED]->(m:Movie)
        OPTIONAL MATCH (:User {userId: $u})-[r:RATED]->(m)
        RETURN m.movieId AS movieId, m.title AS title, m.year AS year,
               w.watchedAt AS watchedAt, r.rating AS myRating
        ORDER BY w.watchedAt DESC, m.title LIMIT $limit
    """, {"u": user_id, "limit": limit})


def monthly_stats(user_id, months=12):
    """Thống kê phim đã xem theo tháng: số phim, số phim đã đánh giá, tổng thời lượng, ví dụ."""
    return run_query("""
        MATCH (u:User {userId: $u})-[w:WATCHED]->(m:Movie)
        WITH substring(w.watchedAt, 0, 7) AS thang, m, EXISTS { (u)-[:RATED]->(m) } AS daDanhGia
        RETURN thang,
               count(m) AS soPhim,
               sum(CASE WHEN daDanhGia THEN 1 ELSE 0 END) AS soDaDanhGia,
               sum(m.duration) AS tongPhut,
               collect(m.title)[..3] AS viDu
        ORDER BY thang DESC
        LIMIT $months
    """, {"u": user_id, "months": months})


def count_history(user_id):
    return run_query("MATCH (:User {userId: $u})-[:WATCHED]->(m) RETURN count(m) AS c", {"u": user_id})[0]["c"]
