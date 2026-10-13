"""Gợi ý phim (dùng các câu Cypher 11, 12, 13, 15) kết hợp Redis cache kết quả."""
import config
import redis_connection as rc
from services.query_service import load_queries, run_query_no

METHODS = {
    "similar": (11, "Người dùng tương đồng"),
    "friends": (12, "Bạn bè"),
    "genre": (13, "Thể loại yêu thích"),
    "hybrid": (15, "Điểm tổng hợp"),
}


def recommend(user_id, method="hybrid", use_cache=True):
    """Trả (danh sách phim, elapsed_ms, from_cache)."""
    n = METHODS[method][0]
    key = f"rec:{user_id}:{method}"
    if use_cache:
        cached = rc.cache_get(key)
        if cached is not None:
            return cached, 0.0, True
    rows, ms = run_query_no(n, user_id)
    for r in rows:  # chuẩn hoá khoá để giao diện dùng chung
        r["movieId"] = r.pop("maPhim", None)
        r["title"] = r.pop("tenPhim", None)
    if use_cache:
        rc.cache_set(key, rows, config.CACHE_TTL)
    return rows, ms, False


def invalidate(user_id):
    rc.cache_delete_pattern(f"rec:{user_id}:*")
