"""Bình luận phim: (Comment {userId})-[:ABOUT]->(Movie). Mã người viết lưu trong node Comment."""
from neo4j_connection import run_query


def add_comment(user_id, movie_id, content):
    content = content.strip()
    if not content:
        return False
    run_query("""
        MATCH (u:User {userId: $u}), (m:Movie {movieId: $m})
        MATCH (x:Comment) WITH u, m, coalesce(max(x.commentId), 0) + 1 AS newId
        CREATE (c:Comment {commentId: newId, userId: u.userId, content: $content, createdAt: toString(date())})
        CREATE (c)-[:ABOUT]->(m)
    """, {"u": user_id, "m": int(movie_id), "content": content})
    return True


def get_comments(movie_id, limit=20):
    return run_query("""
        MATCH (c:Comment)-[:ABOUT]->(:Movie {movieId: $m})
        MATCH (u:User {userId: c.userId})
        RETURN c.commentId AS commentId, u.userId AS userId, u.name AS name,
               c.content AS content, c.createdAt AS createdAt
        ORDER BY c.createdAt DESC, c.commentId DESC LIMIT $limit
    """, {"m": int(movie_id), "limit": limit})
