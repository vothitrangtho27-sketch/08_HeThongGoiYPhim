"""Lịch sử xem phim."""
import redis_connection as rc
from neo4j_connection import run_query


def mark_watched(user_id, movie_id):
    """Đánh dấu đã xem; xem lại thì tăng bộ đếm số lần xem. Trả về số lần xem."""
    rows = run_query("""
        MATCH (u:User {userId: $u}), (m:Movie {movieId: $m})
        MERGE (u)-[w:WATCHED]->(m)
          ON CREATE SET w.watchedAt = toString(date()), w.soLanXem = 1
          ON MATCH SET w.soLanXem = coalesce(w.soLanXem, 1) + 1, w.xemLanCuoi = toString(date())
        RETURN w.soLanXem AS soLanXem
    """, {"u": user_id, "m": int(movie_id)})
    rc.cache_delete_pattern(f"rec:{user_id}:*")
    return rows[0]["soLanXem"] if rows else 1


def get_history(user_id, limit=50):
    """Danh sách phim đã xem; mỗi dòng kèm tổng số phim đã xem (tongSoPhim)."""
    return run_query("""
        MATCH (u:User {userId: $u})
        WITH u, COUNT { (u)-[:WATCHED]->(:Movie) } AS tongSoPhim
        MATCH (u)-[w:WATCHED]->(m:Movie)
        OPTIONAL MATCH (u)-[r:RATED]->(m)
        RETURN m.movieId AS movieId, m.title AS title, m.year AS year,
               w.watchedAt AS watchedAt, r.rating AS myRating, tongSoPhim
        ORDER BY w.watchedAt DESC, m.title
        LIMIT $limit
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
