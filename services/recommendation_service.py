"""Gợi ý phim: 4 phương pháp, mỗi phương pháp một truy vấn Cypher riêng chạy trên Neo4j.
Kết quả được cache trên Redis theo từng người dùng và từng phương pháp."""
import config
import redis_connection as rc
from neo4j_connection import run_timed

METHODS = {
    "similar": "Người dùng tương đồng",
    "friends": "Bạn bè",
    "genre": "Thể loại yêu thích",
    "hybrid": "Điểm tổng hợp",
}

# 1. Người dùng tương đồng: người chấm >= 4 sao cho ít nhất 2 phim giống bạn -> lấy phim họ thích.
_SIMILAR = """
MATCH (u:User {userId: $userId})-[r1:RATED]->(m:Movie)<-[r2:RATED]-(s:User)
WHERE s <> u AND r1.rating >= 4 AND r2.rating >= 4
WITH u, s, count(m) AS soPhimChung
WHERE soPhimChung >= 2
MATCH (s)-[r3:RATED]->(c:Movie)
WHERE r3.rating >= 4
  AND NOT (u)-[:RATED]->(c)
  AND NOT (u)-[:WATCHED]->(c)
RETURN c.movieId AS maPhim, c.title AS tenPhim,
       count(DISTINCT s) AS soNguoiTuongDongUngHo
ORDER BY soNguoiTuongDongUngHo DESC, tenPhim
LIMIT 10
"""

# 2. Bạn bè: duyệt đồ thị tối đa 2 bước trên quan hệ FRIEND.
_FRIENDS = """
MATCH (u:User {userId: $userId})-[:FRIEND*1..2]-(f:User)
WHERE f <> u
WITH DISTINCT u, f
MATCH (f)-[r:RATED]->(m:Movie)
WHERE r.rating >= 4
  AND NOT (u)-[:RATED]->(m)
  AND NOT (u)-[:WATCHED]->(m)
RETURN m.movieId AS maPhim, m.title AS tenPhim,
       count(DISTINCT f) AS soBanUngHo,
       round(avg(r.rating), 2) AS diemTBTuBanBe
ORDER BY soBanUngHo DESC, diemTBTuBanBe DESC, tenPhim
LIMIT 10
"""

# 3. Thể loại yêu thích: lấy 3 thể loại bạn chấm cao nhiều nhất, rồi tìm phim chưa xem thuộc các thể loại đó.
_GENRE = """
MATCH (u:User {userId: $userId})-[r:RATED]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
WHERE r.rating >= 4
WITH u, g, count(DISTINCT m) AS soPhimYeuThich
ORDER BY soPhimYeuThich DESC, g.name
LIMIT 3
WITH u, collect(g) AS theLoaiYeuThich
MATCH (c:Movie)-[:HAS_GENRE]->(g2:Genre)
WHERE g2 IN theLoaiYeuThich
  AND NOT (u)-[:RATED]->(c)
  AND NOT (u)-[:WATCHED]->(c)
WITH c, collect(DISTINCT g2.name) AS theLoaiPhuHop
OPTIONAL MATCH (c)<-[r2:RATED]-(:User)
WITH c, theLoaiPhuHop, count(r2) AS soLuotDanhGia, coalesce(avg(r2.rating), 0) AS diemTB
RETURN c.movieId AS maPhim, c.title AS tenPhim, theLoaiPhuHop,
       soLuotDanhGia, round(diemTB, 2) AS diemTB
ORDER BY size(theLoaiPhuHop) DESC, diemTB DESC, soLuotDanhGia DESC
LIMIT 10
"""

# 4. Điểm tổng hợp: ghép 3 yếu tố bằng các CALL subquery độc lập rồi chấm điểm
#    diemTongHop = 0.5 * người tương đồng + 0.3 * điểm TB + 0.2 * số thể loại hợp gu.
_HYBRID = """
MATCH (u:User {userId: $userId})
CALL {
    WITH u
    MATCH (u)-[r:RATED]->(:Movie)-[:HAS_GENRE]->(g:Genre)
    WHERE r.rating >= 4
    RETURN collect(DISTINCT g) AS theLoaiYeuThich
}
CALL {
    WITH u
    MATCH (u)-[a:RATED]->(:Movie)<-[b:RATED]-(s:User)
    WHERE s <> u AND a.rating >= 4 AND b.rating >= 4
    WITH s, count(*) AS chung
    WHERE chung >= 2
    RETURN collect(s) AS nguoiTuongDong
}
UNWIND nguoiTuongDong AS s
MATCH (s)-[r3:RATED]->(c:Movie)
WHERE r3.rating >= 4 AND NOT EXISTS { (u)-[:RATED|WATCHED]->(c) }
WITH c, theLoaiYeuThich, count(DISTINCT s) AS soNguoiTuongDong
WITH c, soNguoiTuongDong,
     COUNT { (c)-[:HAS_GENRE]->(g:Genre) WHERE g IN theLoaiYeuThich } AS soTheLoaiLienQuan,
     [(c)<-[x:RATED]-(:User) | x.rating] AS rs
WITH c, soNguoiTuongDong, soTheLoaiLienQuan, reduce(t = 0.0, v IN rs | t + v) / size(rs) AS diemTB
RETURN c.movieId AS maPhim, c.title AS tenPhim,
       soNguoiTuongDong, round(diemTB, 2) AS diemTB, soTheLoaiLienQuan,
       round(0.5 * soNguoiTuongDong + 0.3 * diemTB + 0.2 * soTheLoaiLienQuan, 3) AS diemTongHop
ORDER BY diemTongHop DESC, tenPhim
LIMIT 10
"""

_QUERIES = {"similar": _SIMILAR, "friends": _FRIENDS, "genre": _GENRE, "hybrid": _HYBRID}


def recommend(user_id, method="hybrid", use_cache=True):
    """Trả (danh sách phim, elapsed_ms, from_cache)."""
    key = f"rec:{user_id}:{method}"
    if use_cache:
        cached = rc.cache_get(key)
        if cached is not None:
            return cached, 0.0, True
    rows, ms = run_timed(_QUERIES[method], {"userId": int(user_id)})
    for r in rows:  # chuẩn hoá khoá để giao diện dùng chung
        r["movieId"] = r.pop("maPhim", None)
        r["title"] = r.pop("tenPhim", None)
    if use_cache:
        rc.cache_set(key, rows, config.CACHE_TTL)
    return rows, ms, False


def invalidate(user_id):
    rc.cache_delete_pattern(f"rec:{user_id}:*")
