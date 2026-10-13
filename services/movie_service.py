"""Quản lý phim: danh sách, tìm kiếm, chi tiết, đánh giá."""
import redis_connection as rc
from neo4j_connection import run_query

_CARD = """
    OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
    WITH m, collect(DISTINCT g.name) AS genres
    OPTIONAL MATCH (m)<-[r:RATED]-(:User)
    RETURN m.movieId AS movieId, m.title AS title, m.year AS year, m.duration AS duration,
           genres, round(coalesce(avg(r.rating), 0), 2) AS avgRating, count(r) AS ratingCount
"""


def stats():
    def load():
        return run_query("""
            MATCH (m:Movie) WITH count(m) AS movies
            MATCH (u:User)  WITH movies, count(u) AS users
            MATCH (g:Genre) WITH movies, users, count(g) AS genres
            MATCH ()-[r:RATED]->() RETURN movies, users, genres, count(r) AS ratings
        """)[0]
    return rc.get_or_set("stats:overview", load, ttl=120)[0]


def list_genres():
    return rc.get_or_set("genres:all", lambda: run_query(
        "MATCH (g:Genre) OPTIONAL MATCH (g)<-[:HAS_GENRE]-(m:Movie) "
        "RETURN g.genreId AS genreId, g.name AS name, count(m) AS n ORDER BY n DESC, name"), ttl=3600)[0]


def count_movies(genre=None):
    if genre:
        q = "MATCH (m:Movie)-[:HAS_GENRE]->(:Genre {name: $g}) RETURN count(DISTINCT m) AS c"
    else:
        q = "MATCH (m:Movie) RETURN count(m) AS c"
    return run_query(q, {"g": genre})[0]["c"]


def list_movies(page=1, size=10, genre=None):
    skip = (page - 1) * size
    if genre:
        head = "MATCH (m:Movie)-[:HAS_GENRE]->(:Genre {name: $g}) WITH DISTINCT m ORDER BY m.title SKIP $skip LIMIT $size"
    else:
        head = "MATCH (m:Movie) WITH m ORDER BY m.title SKIP $skip LIMIT $size"
    return run_query(head + _CARD + " ORDER BY title", {"g": genre, "skip": skip, "size": size})


def search_movies(keyword, limit=30):
    return run_query(
        "MATCH (m:Movie) WHERE toLower(m.title) CONTAINS toLower($k) WITH m ORDER BY m.title LIMIT $limit"
        + _CARD + " ORDER BY title", {"k": keyword.strip(), "limit": limit})


def get_movie(movie_id):
    rows = run_query("MATCH (m:Movie {movieId: $id})" + _CARD, {"id": int(movie_id)})
    return rows[0] if rows else None


def get_user_rating(user_id, movie_id):
    rows = run_query("MATCH (:User {userId: $u})-[r:RATED]->(:Movie {movieId: $m}) RETURN r.rating AS rating",
                     {"u": user_id, "m": int(movie_id)})
    return rows[0]["rating"] if rows else None


def rate_movie(user_id, movie_id, rating):
    """Đánh giá phim (1-5). Tự ghi nhận đã xem. Xóa cache gợi ý của người dùng."""
    run_query("""
        MATCH (u:User {userId: $u}), (m:Movie {movieId: $m})
        MERGE (u)-[r:RATED]->(m) SET r.rating = $rating, r.ratedAt = toString(date())
        MERGE (u)-[w:WATCHED]->(m) ON CREATE SET w.watchedAt = toString(date())
    """, {"u": user_id, "m": int(movie_id), "rating": int(rating)})
    rc.cache_delete_pattern(f"rec:{user_id}:*")
    rc.cache_delete("stats:overview")
