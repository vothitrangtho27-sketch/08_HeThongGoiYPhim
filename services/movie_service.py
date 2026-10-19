"""Quản lý phim: danh sách, tìm kiếm, chi tiết, phim tương tự, đánh giá.

Mỗi hàm dùng một kỹ thuật Cypher khác nhau (CALL subquery, pattern comprehension,
UNION, COUNT subquery, điểm Bayes, độ tương tự Jaccard...) và đều chạy trực tiếp trên Neo4j.
Redis chỉ cache lại kết quả của các thống kê tổng quan.
"""
import redis_connection as rc
from neo4j_connection import run_query

# Điểm Bayes: kéo điểm của phim ít lượt đánh giá về điểm trung bình chung (3.9) để xếp hạng công bằng.
_SORTS = {
    "title": "m.title",
    "popular": "ratingCount DESC, m.title",
    "top": "score DESC, ratingCount DESC, m.title",
}
SORT_LABELS = {"title": "Tên A → Z", "popular": "Nhiều đánh giá nhất", "top": "Điểm cao nhất (có trọng số)"}

def stats():
    """Thống kê tổng quan: mỗi con số tính trong một CALL subquery riêng."""
    def load():
        return run_query("""
            CALL { MATCH (m:Movie) RETURN count(m) AS movies }
            CALL { MATCH (u:User) RETURN count(u) AS users }
            CALL { MATCH (g:Genre) RETURN count(g) AS genres }
            CALL { MATCH ()-[r:RATED]->() RETURN count(r) AS ratings, round(avg(r.rating), 2) AS avgRating }
            RETURN movies, users, genres, ratings, avgRating
        """)[0]
    return rc.get_or_set("stats:overview", load, ttl=120)[0]


def list_genres():
    return rc.get_or_set("genres:all", lambda: run_query("""
        MATCH (g:Genre)
        RETURN g.genreId AS genreId, g.name AS name, COUNT { (g)<-[:HAS_GENRE]-(:Movie) } AS n
        ORDER BY n DESC, name
    """), ttl=3600)[0]


def list_movies(page=1, size=10, genre=None, sort="title"):
    """Danh sách phim phân trang, có lọc thể loại và 3 kiểu sắp xếp."""
    where = "WHERE EXISTS { (m)-[:HAS_GENRE]->(:Genre {name: $g}) }" if genre else ""
    q = """
        MATCH (m:Movie) @WHERE@
        WITH m, [(m)<-[r:RATED]-(:User) | r.rating] AS rs
        WITH m, size(rs) AS ratingCount,
             CASE WHEN size(rs) = 0 THEN 0.0 ELSE reduce(t = 0.0, x IN rs | t + x) / size(rs) END AS avgRating
        WITH m, ratingCount, avgRating, (ratingCount * avgRating + 3 * 3.9) / (ratingCount + 3) AS score
        ORDER BY @ORDER@
        SKIP $skip LIMIT $size
        RETURN m.movieId AS movieId, m.title AS title, m.year AS year, m.duration AS duration,
               [(m)-[:HAS_GENRE]->(g:Genre) | g.name] AS genres,
               round(avgRating, 2) AS avgRating, ratingCount
    """.replace("@WHERE@", where).replace("@ORDER@", _SORTS.get(sort, _SORTS["title"]))
    return run_query(q, {"g": genre, "skip": (page - 1) * size, "size": size})


def search_movies(keyword, limit=30):
    """Tìm theo tên (ưu tiên cao nhất), năm phát hành hoặc thể loại; gộp kết quả bằng UNION."""
    return run_query("""
        CALL {
            MATCH (m:Movie) WHERE toLower(m.title) CONTAINS toLower($k) RETURN m, 3 AS w
            UNION
            MATCH (m:Movie) WHERE toString(m.year) = $k RETURN m, 2 AS w
            UNION
            MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre) WHERE toLower(g.name) CONTAINS toLower($k) RETURN m, 1 AS w
        }
        WITH m, max(w) AS relevance
        ORDER BY relevance DESC, m.title
        LIMIT $limit
        OPTIONAL MATCH (m)<-[r:RATED]-(:User)
        WITH m, relevance, count(r) AS ratingCount, avg(r.rating) AS diemTB
        RETURN m.movieId AS movieId, m.title AS title, m.year AS year, m.duration AS duration,
               [(m)-[:HAS_GENRE]->(g:Genre) | g.name] AS genres,
               round(coalesce(diemTB, 0), 2) AS avgRating, ratingCount
        ORDER BY relevance DESC, title
    """, {"k": keyword.strip(), "limit": limit})


def get_movie(movie_id, user_id):
    """Chi tiết phim + điểm của người dùng + trạng thái đã xem, gói trong MỘT truy vấn."""
    rows = run_query("""
        MATCH (m:Movie {movieId: $id})
        CALL {
            WITH m
            MATCH (m)-[:HAS_GENRE]->(g:Genre)
            RETURN collect(g.name) AS genres
        }
        CALL {
            WITH m
            OPTIONAL MATCH (m)<-[r:RATED]-(:User)
            RETURN count(r) AS ratingCount, coalesce(round(avg(r.rating), 2), 0) AS avgRating
        }
        OPTIONAL MATCH (:User {userId: $u})-[mine:RATED]->(m)
        RETURN m.movieId AS movieId, m.title AS title, m.year AS year, m.duration AS duration,
               genres, avgRating, ratingCount, mine.rating AS myRating,
               EXISTS { (:User {userId: $u})-[:WATCHED]->(m) } AS daXem
    """, {"id": int(movie_id), "u": user_id})
    return rows[0] if rows else None


def get_related_movies(movie_id, limit=5):
    """Phim tương tự: độ giống thể loại (Jaccard) + số người cùng chấm >= 4 sao cho cả hai phim."""
    return run_query("""
        MATCH (m:Movie {movieId: $id})-[:HAS_GENRE]->(g:Genre)<-[:HAS_GENRE]-(o:Movie)
        WHERE o <> m
        WITH m, o, count(g) AS chung
        WITH m, o,
             toFloat(chung) / (COUNT { (m)-[:HAS_GENRE]->() } + COUNT { (o)-[:HAS_GENRE]->() } - chung) AS jaccard,
             COUNT { MATCH (m)<-[a:RATED]-(:User)-[b:RATED]->(o) WHERE a.rating >= 4 AND b.rating >= 4 } AS nguoiCungThich
        OPTIONAL MATCH (o)<-[r:RATED]-(:User)
        WITH o, jaccard, nguoiCungThich, count(r) AS ratingCount, avg(r.rating) AS diemTB
        RETURN o.movieId AS movieId, o.title AS title, o.year AS year,
               [(o)-[:HAS_GENRE]->(x:Genre) | x.name] AS genres,
               round(coalesce(diemTB, 0), 2) AS avgRating, ratingCount,
               round(jaccard, 2) AS doTuongTu, nguoiCungThich
        ORDER BY jaccard + 0.25 * nguoiCungThich DESC, avgRating DESC, title
        LIMIT $limit
    """, {"id": int(movie_id), "limit": limit})


def rate_movie(user_id, movie_id, rating):
    """Đánh giá phim (1-5), tự ghi nhận đã xem và trả về điểm trung bình mới của phim."""
    rows = run_query("""
        MATCH (u:User {userId: $u}), (m:Movie {movieId: $m})
        MERGE (u)-[r:RATED]->(m)
        SET r.rating = $rating, r.ratedAt = toString(date())
        MERGE (u)-[w:WATCHED]->(m)
          ON CREATE SET w.watchedAt = toString(date()), w.soLanXem = 1
        WITH m
        MATCH (m)<-[x:RATED]-(:User)
        RETURN count(x) AS ratingCount, round(avg(x.rating), 2) AS avgRating
    """, {"u": user_id, "m": int(movie_id), "rating": int(rating)})
    rc.cache_delete_pattern(f"rec:{user_id}:*")
    rc.cache_delete("stats:overview")
    return rows[0] if rows else None
