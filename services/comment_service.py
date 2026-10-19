"""Bình luận phim: (Comment {userId})-[:ABOUT]->(Movie). Mã người viết lưu trong node Comment."""
from neo4j_connection import run_query


def add_comment(user_id, movie_id, content):
    """Thêm bình luận; từ chối nếu người dùng đã gửi đúng nội dung này cho phim (chống trùng)."""
    content = content.strip()
    if not content:
        return False
    rows = run_query("""
        MATCH (u:User {userId: $u}), (m:Movie {movieId: $m})
        WHERE NOT EXISTS { MATCH (d:Comment {userId: $u, content: $content})-[:ABOUT]->(m) }
        CALL {
            MATCH (x:Comment)
            RETURN coalesce(max(x.commentId), 0) + 1 AS newId
        }
        CREATE (c:Comment {commentId: newId, userId: u.userId, content: $content, createdAt: toString(date())})
        CREATE (c)-[:ABOUT]->(m)
        RETURN c.commentId AS commentId
    """, {"u": user_id, "m": int(movie_id), "content": content})
    return bool(rows)


def get_comments(movie_id, limit=20):
    return run_query("""
        MATCH (c:Comment)-[:ABOUT]->(:Movie {movieId: $m})
        MATCH (u:User {userId: c.userId})
        OPTIONAL MATCH (u)-[r:RATED]->(:Movie {movieId: $m})
        RETURN c.commentId AS commentId, u.userId AS userId, u.name AS name,
               c.content AS content, c.createdAt AS createdAt, r.rating AS rating
        ORDER BY c.createdAt DESC, c.commentId DESC LIMIT $limit
    """, {"m": int(movie_id), "limit": limit})
