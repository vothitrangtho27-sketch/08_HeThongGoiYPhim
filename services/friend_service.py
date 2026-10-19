"""Quan hệ bạn bè (FRIEND xử lý vô hướng) và lời mời kết bạn (FRIEND_REQUEST: người gửi -> người nhận)."""
import redis_connection as rc
from neo4j_connection import run_query


def list_friends(user_id):
    """Danh sách bạn bè kèm độ hợp gu (%) tính từ chênh lệch điểm trên các phim cùng đánh giá."""
    return run_query("""
        MATCH (u:User {userId: $u})-[f:FRIEND]-(b:User)
        WITH u, b, min(f.since) AS ketBanTu
        OPTIONAL MATCH (u)-[a:RATED]->(m:Movie)<-[c:RATED]-(b)
        WITH b, ketBanTu, count(m) AS phimChung, avg(abs(a.rating - c.rating)) AS lechTB
        RETURN b.userId AS userId, b.name AS name, b.city AS city, ketBanTu, phimChung,
               CASE WHEN phimChung = 0 THEN null ELSE round(100 * (1 - lechTB / 4)) END AS hopGu
        ORDER BY name
    """, {"u": user_id})


def suggest_friends(user_id, limit=6):
    """Gợi ý kết bạn: bạn của bạn (chưa là bạn), xếp theo bạn chung + phim cùng đánh giá + cùng thành phố."""
    return run_query("""
        MATCH (u:User {userId: $u})-[:FRIEND]-(f:User)-[:FRIEND]-(c:User)
        WHERE c <> u AND NOT EXISTS { (u)-[:FRIEND]-(c) } AND NOT EXISTS { (u)-[:FRIEND_REQUEST]-(c) }
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
    """Tìm người dùng theo tên hoặc mã (loại trừ bản thân), xếp theo độ khớp, kèm số bạn chung."""
    kw = keyword.strip()
    uid = int(kw) if kw.isdigit() else -1
    return run_query("""
        MATCH (b:User)
        WHERE b.userId <> $u AND (toLower(b.name) CONTAINS toLower($k) OR b.userId = $uid)
        WITH b, CASE WHEN b.userId = $uid THEN 0
                     WHEN toLower(b.name) = toLower($k) THEN 1
                     WHEN toLower(b.name) STARTS WITH toLower($k) THEN 2
                     ELSE 3 END AS doKhop
        RETURN b.userId AS userId, b.name AS name, b.city AS city,
               EXISTS { (:User {userId: $u})-[:FRIEND]-(b) } AS isFriend,
               EXISTS { (:User {userId: $u})-[:FRIEND_REQUEST]->(b) } AS daGuiLoiMoi,
               EXISTS { (b)-[:FRIEND_REQUEST]->(:User {userId: $u}) } AS coLoiMoiDen,
               COUNT { (b)-[:FRIEND]-(x:User) WHERE EXISTS { (:User {userId: $u})-[:FRIEND]-(x) } } AS banChung
        ORDER BY doKhop, name
        LIMIT $limit
    """, {"u": user_id, "k": kw, "uid": uid, "limit": limit})


def send_request(user_id, target_id):
    """Gửi lời mời kết bạn. Bỏ qua nếu tự mời mình, đã là bạn hoặc đã có lời mời (theo cả hai chiều)."""
    rows = run_query("""
        MATCH (a:User {userId: $a}), (b:User {userId: $b})
        WHERE a <> b
          AND NOT EXISTS { (a)-[:FRIEND]-(b) }
          AND NOT EXISTS { (a)-[:FRIEND_REQUEST]-(b) }
        CREATE (a)-[:FRIEND_REQUEST {sentAt: toString(datetime())}]->(b)
        RETURN b.name AS name
    """, {"a": user_id, "b": int(target_id)})
    return bool(rows)


def incoming_requests(user_id):
    """Lời mời kết bạn gửi đến người dùng, kèm số bạn chung và số phim cùng đánh giá với người gửi."""
    return run_query("""
        MATCH (s:User)-[r:FRIEND_REQUEST]->(m:User {userId: $u})
        RETURN s.userId AS userId, s.name AS name, s.city AS city, r.sentAt AS sentAt,
               COUNT { (s)-[:FRIEND]-(x:User) WHERE EXISTS { (m)-[:FRIEND]-(x) } } AS banChung,
               COUNT { (s)-[:RATED]->(:Movie)<-[:RATED]-(m) } AS phimChung
        ORDER BY r.sentAt DESC
    """, {"u": user_id})


def outgoing_requests(user_id):
    """Lời mời mà người dùng đã gửi và đang chờ người kia trả lời."""
    return run_query("""
        MATCH (m:User {userId: $u})-[r:FRIEND_REQUEST]->(t:User)
        RETURN t.userId AS userId, t.name AS name, t.city AS city, r.sentAt AS sentAt
        ORDER BY r.sentAt DESC
    """, {"u": user_id})


def count_requests(user_id):
    """Số lời mời đang chờ người dùng trả lời (hiện ở thanh bên)."""
    rows = run_query("MATCH (:User)-[r:FRIEND_REQUEST]->(:User {userId: $u}) RETURN count(r) AS n", {"u": user_id})
    return rows[0]["n"] if rows else 0


def accept_request(user_id, sender_id):
    """Chấp nhận: xóa lời mời rồi tạo quan hệ FRIEND giữa người gửi và người nhận."""
    rows = run_query("""
        MATCH (s:User {userId: $s})-[r:FRIEND_REQUEST]->(m:User {userId: $m})
        DELETE r
        WITH s, m
        WHERE NOT EXISTS { (s)-[:FRIEND]-(m) }
        CREATE (s)-[:FRIEND {since: toString(date())}]->(m)
        RETURN s.name AS name
    """, {"s": int(sender_id), "m": user_id})
    rc.cache_delete_pattern(f"rec:{user_id}:*")
    rc.cache_delete_pattern(f"rec:{int(sender_id)}:*")
    return bool(rows)


def decline_request(user_id, sender_id):
    """Từ chối: chỉ xóa lời mời, không tạo quan hệ bạn bè."""
    run_query("MATCH (:User {userId: $s})-[r:FRIEND_REQUEST]->(:User {userId: $m}) DELETE r",
              {"s": int(sender_id), "m": user_id})


def cancel_request(user_id, target_id):
    """Hủy lời mời mình đã gửi."""
    decline_request(int(target_id), user_id)


def remove_friend(user_id, friend_id):
    run_query("MATCH (:User {userId: $a})-[f:FRIEND]-(:User {userId: $b}) DELETE f",
              {"a": user_id, "b": int(friend_id)})
    rc.cache_delete_pattern(f"rec:{user_id}:*")
