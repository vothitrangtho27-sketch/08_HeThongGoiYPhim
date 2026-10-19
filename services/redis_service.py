"""Redis nâng cao: sử dụng đủ các kiểu dữ liệu String, Hash, List, Set, Sorted Set
và xử lý 3 sự cố cache (Avalanche, Penetration, Breakdown).

Khóa sử dụng (theo cách đặt tên của bài giảng Redis):
  movie:{id}              Hash        cache thông tin phim (TTL ngẫu nhiên)
  lock:movie:{id}         String      khóa mutex khi dựng lại cache (SET NX EX)
  movie:{id}:views        String      bộ đếm lượt xem (INCR)
  movie:popular           Sorted Set  bảng xếp hạng phim xem nhiều (ZINCRBY / ZREVRANGE)
  user:{id}:recent        List        cache 10 phim xem gần đây (LPUSH / LTRIM / LRANGE), mất thì dựng lại từ Neo4j
  user:{id}:stats         Hash        thống kê hoạt động (HINCRBY)
  user:{id}:login:count   String      số lần đăng nhập (INCR)
  online:users            Sorted Set  người dùng đang online (score = thời điểm hoạt động cuối)
  friends:{id}            Set         tập mã bạn bè (SADD / SINTER / SUNION / SDIFF)
Nếu Redis không chạy, mọi hàm trả giá trị mặc định để ứng dụng vẫn hoạt động."""
import json
import random
import time

import config
import redis_connection as rc
from neo4j_connection import run_query

NULL_MARK = "__null__"      # đánh dấu "phim không tồn tại" (chống Cache Penetration)
NULL_TTL = 30               # TTL ngắn cho dấu null
RECENT_TTL = 7 * 24 * 3600  # giây: cache danh sách phim gần đây sống 7 ngày
ONLINE_WINDOW = 300         # giây: không hoạt động quá 5 phút thì coi như offline
LOCK_TTL = 5                # giây: thời gian giữ khóa mutex


def _r():
    return rc.get_client()


# ====================== Hash: cache thông tin phim ======================
def _encode_movie(m):
    return {"title": m.get("title") or "", "year": m.get("year") or "", "duration": m.get("duration") or "",
            "genres": json.dumps(m.get("genres") or [], ensure_ascii=False),
            "avgRating": m.get("avgRating") if m.get("avgRating") is not None else 0,
            "ratingCount": m.get("ratingCount") or 0}


def _decode_movie(movie_id, h):
    def num(v, cast):
        try:
            return cast(v)
        except (TypeError, ValueError):
            return None
    return {"movieId": int(movie_id), "title": h.get("title"), "year": num(h.get("year"), int),
            "duration": num(h.get("duration"), int), "genres": json.loads(h.get("genres") or "[]"),
            "avgRating": num(h.get("avgRating"), float), "ratingCount": num(h.get("ratingCount"), int) or 0}


def movie_summary(movie_id, loader):
    """Cache-aside kiểu Hash. Trả (dict | None, from_cache).
    - Avalanche: TTL = CACHE_TTL + số ngẫu nhiên 0-60 giây nên các key không hết hạn cùng lúc.
    - Penetration: phim không tồn tại -> lưu dấu null với TTL ngắn, không truy vấn Neo4j lặp lại.
    - Breakdown: dùng khóa mutex lock:movie:{id} (SET NX EX), chỉ một tiến trình dựng lại cache."""
    c = _r()
    if c is None:
        return loader(), False
    key = f"movie:{movie_id}"
    lock, got_lock = f"lock:{key}", False
    try:
        if c.type(key) == "string":                  # dấu null
            return None, True
        h = c.hgetall(key)
        if h:
            return _decode_movie(movie_id, h), True
        got_lock = bool(c.set(lock, "1", nx=True, ex=LOCK_TTL))
        if not got_lock:                             # tiến trình khác đang dựng cache: chờ tối đa 0,5 giây
            for _ in range(10):
                time.sleep(0.05)
                h = c.hgetall(key)
                if h:
                    return _decode_movie(movie_id, h), True
    except Exception:
        got_lock = False                             # lỗi Redis: bỏ qua cache
        return loader(), False
    try:
        m = loader()                                 # lỗi của Neo4j được báo ra ngoài, không gọi lặp lại
        try:
            if m is None:
                c.set(key, NULL_MARK, ex=NULL_TTL)
            else:
                c.hset(key, mapping=_encode_movie(m))
                c.expire(key, config.CACHE_TTL + random.randint(0, 60))
        except Exception:
            pass
        if m is not None:
            m = {"movieId": int(movie_id), **m}      # cùng dạng với dữ liệu đọc từ cache
        return m, False
    finally:
        if got_lock:
            try:
                c.delete(lock)
            except Exception:
                pass


def invalidate_movie(movie_id):
    c = _r()
    if c is not None:
        try:
            c.delete(f"movie:{movie_id}")
        except Exception:
            pass


# ====================== String / Hash / List / Sorted Set: hành vi xem phim ======================
def _rebuild_recent(c, user_id, loader):
    """Cache-aside cho List: nếu khóa user:{id}:recent không còn thì dựng lại từ Neo4j (RPUSH)."""
    key = f"user:{user_id}:recent"
    if loader is not None and not c.exists(key):
        ids = [str(i) for i in loader()][:10]
        if ids:
            c.rpush(key, *ids)
            c.expire(key, RECENT_TTL)


def record_view(user_id, movie_id, recent_loader=None):
    """Ghi nhận một lượt xem phim bằng 1 pipeline. Trả tổng lượt xem của phim (hoặc None)."""
    c = _r()
    if c is None:
        return None
    try:
        warm_popular()                                         # nạp bảng xếp hạng ban đầu trước khi cộng thêm
        _rebuild_recent(c, user_id, recent_loader)             # List đã hết hạn thì dựng lại trước khi thêm
        p = c.pipeline()
        p.incr(f"movie:{movie_id}:views")                      # String: bộ đếm
        p.zincrby("movie:popular", 1, str(movie_id))           # Sorted Set: bảng xếp hạng
        p.lrem(f"user:{user_id}:recent", 0, str(movie_id))     # List: bỏ bản trùng
        p.lpush(f"user:{user_id}:recent", str(movie_id))       # List: đưa lên đầu
        p.ltrim(f"user:{user_id}:recent", 0, 9)                # List: chỉ giữ 10 phim gần nhất
        p.expire(f"user:{user_id}:recent", RECENT_TTL)         # làm mới thời gian sống
        p.hincrby(f"user:{user_id}:stats", "views", 1)         # Hash: thống kê người dùng
        return p.execute()[0]
    except Exception:
        return None


def get_views(movie_id):
    c = _r()
    if c is None:
        return None
    try:
        v = c.get(f"movie:{movie_id}:views")
        return int(v) if v is not None else 0
    except Exception:
        return None


def record_rating(user_id):
    c = _r()
    if c is not None:
        try:
            c.hincrby(f"user:{user_id}:stats", "ratings", 1)
        except Exception:
            pass


def warm_popular(limit=50):
    """Pre-warming: nạp bảng xếp hạng ban đầu từ Neo4j (số lượt WATCHED); chỉ chạy một lần,
    đánh dấu bằng khóa movie:popular:warmed. Nếu truy vấn lỗi thì bỏ dấu để lần sau thử lại;
    ZADD NX chỉ thêm phim chưa có, không ghi đè điểm đã được cộng bằng ZINCRBY."""
    c = _r()
    if c is None:
        return 0
    try:
        if not c.set("movie:popular:warmed", "1", nx=True):
            return 0
    except Exception:
        return 0
    try:
        rows = run_query("""
            MATCH (:User)-[w:WATCHED]->(m:Movie)
            RETURN m.movieId AS id, count(w) AS n
            ORDER BY n DESC
            LIMIT $limit
        """, {"limit": limit})
        if rows:
            c.zadd("movie:popular", {str(r["id"]): r["n"] for r in rows}, nx=True)
        return len(rows)
    except Exception:
        try:
            c.delete("movie:popular:warmed")
        except Exception:
            pass
        return 0


def popular_movies(limit=5):
    """Top phim xem nhiều: [(movieId, lượt xem)]."""
    c = _r()
    if c is None:
        return []
    try:
        warm_popular()
        return [(int(m), int(s)) for m, s in c.zrevrange("movie:popular", 0, limit - 1, withscores=True)]
    except Exception:
        return []


def recent_movies(user_id, limit=5, loader=None):
    """Phim xem gần đây (List). Chưa có cache thì dựng từ loader() (lịch sử xem trong Neo4j)."""
    c = _r()
    if c is None:
        return [int(i) for i in loader()][:limit] if loader else []
    try:
        _rebuild_recent(c, user_id, loader)
        return [int(x) for x in c.lrange(f"user:{user_id}:recent", 0, limit - 1)]
    except Exception:
        return []


# ====================== đăng nhập, online ======================
def on_login(user_id):
    """INCR số lần đăng nhập và đánh dấu online. Trả số lần đăng nhập."""
    c = _r()
    if c is None:
        return None
    try:
        n = c.incr(f"user:{user_id}:login:count")
        c.zadd("online:users", {str(user_id): time.time()})
        return n
    except Exception:
        return None


def touch_online(user_id):
    c = _r()
    if c is not None:
        try:
            c.zadd("online:users", {str(user_id): time.time()})
        except Exception:
            pass


def on_logout(user_id):
    c = _r()
    if c is not None:
        try:
            c.zrem("online:users", str(user_id))
        except Exception:
            pass


def count_online():
    c = _r()
    if c is None:
        return None
    try:
        c.zremrangebyscore("online:users", 0, time.time() - ONLINE_WINDOW)
        return c.zcard("online:users")
    except Exception:
        return None


def login_count(user_id):
    c = _r()
    if c is None:
        return None
    try:
        v = c.get(f"user:{user_id}:login:count")
        return int(v) if v is not None else 0
    except Exception:
        return None


# ====================== Set: tập bạn bè ======================
def cache_friend_set(user_id, ids):
    """Lưu tập mã bạn bè vào Set friends:{id} (làm mới mỗi lần)."""
    c = _r()
    if c is None:
        return
    try:
        key = f"friends:{user_id}"
        p = c.pipeline()
        p.delete(key)
        if ids:
            p.sadd(key, *[str(i) for i in ids])
            p.expire(key, config.CACHE_TTL + random.randint(0, 60))
        p.execute()
    except Exception:
        pass


def invalidate_friends(*user_ids):
    c = _r()
    if c is not None:
        try:
            for u in user_ids:
                c.delete(f"friends:{u}")
        except Exception:
            pass


def online_friends(user_id, ids):
    """Trong tập bạn bè, những người đã hoạt động trong ONLINE_WINDOW giây gần đây (ZSCORE)."""
    c = _r()
    if c is None:
        return set()
    try:
        ids = list(ids)
        if not ids:
            return set()
        p = c.pipeline()
        for i in ids:
            p.zscore("online:users", str(i))        # gửi một lần cho cả danh sách bạn bè
        now = time.time()
        return {int(i) for i, sc in zip(ids, p.execute()) if sc is not None and now - sc <= ONLINE_WINDOW}
    except Exception:
        return set()


def friend_set_ops(a, b, loader):
    """SINTER / SUNION / SDIFF giữa tập bạn bè của hai người dùng. loader(userId) -> list mã bạn bè."""
    c = _r()
    if c is None:
        return None
    try:
        for u in (a, b):
            if not c.exists(f"friends:{u}"):
                cache_friend_set(u, loader(u))
        ka, kb = f"friends:{a}", f"friends:{b}"
        to_int = lambda s: sorted(int(x) for x in s)
        return {"inter": to_int(c.sinter(ka, kb)), "union": to_int(c.sunion(ka, kb)),
                "diff": to_int(c.sdiff(ka, kb)), "card_a": c.scard(ka), "card_b": c.scard(kb)}
    except Exception:
        return None
