"""Quan hệ bạn bè (FRIEND được xử lý vô hướng)."""
import redis_connection as rc
from neo4j_connection import run_query


def list_friends(user_id):
    return run_query("""
        MATCH (:User {userId: $u})-[f:FRIEND]-(b:User)
        RETURN DISTINCT b.userId AS userId, b.name AS name, b.city AS city
        ORDER BY name
    """, {"u": user_id})


def suggest_friends(user_id, limit=6):
    """Gợi ý kết bạn: bạn của bạn (chưa là bạn), xếp theo bạn chung + phim cùng đánh giá + cùng thành phố."""
    return run_query("""
        MATCH (u:User {userId: $u})-[:FRIEND]-(f:User)-[:FRIEND]-(c:User)
        WHERE c <> u AND NOT EXISTS { (u)-[:FRIEND]-(c) }
        WITH u, c, count(DISTINCT f) AS banChung
        WITH u, c, banChung,
             COUNT { (u)-[:RATED]->(:Movie)<-[:RATED]-(c) } AS phimChung,
             (c.city = u.city) AS cungThanhPho
        RETURN c.userId AS userId, c.name AS name, c.city AS city, banChung, phimChung, cungThanhPho,
               banChung * 2 + phimChung + CASE WHEN cungThanhPho THEN 1 ELSE 0 END AS diem
        ORDER BY diem DESC, name
        LIMIT $limit
    """, {"u": user_id, "limit": limit})


def search_users(keyword, user_id, limit=10):
    """Tìm người dùng theo tên hoặc mã (loại trừ bản thân)."""
    kw = keyword.strip()
    uid = int(kw) if kw.isdigit() else -1
    return run_query("""
        MATCH (b:User)
        WHERE b.userId <> $u AND (toLower(b.name) CONTAINS toLower($k) OR b.userId = $uid)
        RETURN b.userId AS userId, b.name AS name, b.city AS city,
               EXISTS { (:User {userId: $u})-[:FRIEND]-(b) } AS isFriend
        ORDER BY name LIMIT $limit
    """, {"u": user_id, "k": kw, "uid": uid, "limit": limit})


def add_friend(user_id, friend_id):
    if user_id == friend_id:
        return False
    run_query("""
        MATCH (a:User {userId: $a}), (b:User {userId: $b})
        WHERE NOT (a)-[:FRIEND]-(b)
        CREATE (a)-[:FRIEND {since: toString(date())}]->(b)
    """, {"a": user_id, "b": int(friend_id)})
    rc.cache_delete_pattern(f"rec:{user_id}:*")
    return True


def remove_friend(user_id, friend_id):
    run_query("MATCH (:User {userId: $a})-[f:FRIEND]-(:User {userId: $b}) DELETE f",
              {"a": user_id, "b": int(friend_id)})
    rc.cache_delete_pattern(f"rec:{user_id}:*")
