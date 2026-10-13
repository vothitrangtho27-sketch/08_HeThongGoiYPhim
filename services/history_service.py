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


def count_history(user_id):
    return run_query("MATCH (:User {userId: $u})-[:WATCHED]->(m) RETURN count(m) AS c", {"u": user_id})[0]["c"]
