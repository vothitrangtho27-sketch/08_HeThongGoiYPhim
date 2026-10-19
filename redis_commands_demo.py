"""Minh họa dữ liệu, truy vấn và kết nối ứng dụng trên Redis.

CẢNH BÁO: phần "0. Dọn dữ liệu demo" xóa các khóa movie:1, movie:popular, online:users, user:1:*...
Nếu Redis đang chứa dữ liệu thật của ứng dụng, hãy đặt REDIS_DB=1 trong .env trước khi chạy.
"""
import json
import random
import time

import config
import redis_connection as rc

c = rc.get_client()
if c is None:
    raise SystemExit("Không kết nối được Redis (kiểm tra REDIS_HOST/PORT trong .env)")
print("Kết nối OK:", c.ping(), f"-> {config.REDIS_HOST}:{config.REDIS_PORT} db={config.REDIS_DB}")


def title(s):
    print(f"\n=== {s} ===")


# ---------- 0. Dọn dữ liệu demo ----------
for k in ["movie:1", "movie:1:views", "movie:popular", "user:1:recent", "user:1:stats",
          "user:1:login:count", "online:users", "friends:1", "friends:91",
          "rec:1:hybrid", "lock:movie:1", "movie:99999"]:
    c.delete(k)

# ---------- 1. String: bộ đếm ----------
title("String: INCR / GET")
c.incr("movie:1:views")
c.incr("movie:1:views")
c.incr("user:1:login:count")
print("movie:1:views =", c.get("movie:1:views"))
print("user:1:login:count =", c.get("user:1:login:count"))

# ---------- 2. Hash: cache thông tin phim, thống kê người dùng ----------
title("Hash: HSET / HGETALL / HINCRBY / TTL")
c.hset("movie:1", mapping={"title": "The Matrix", "year": 1999, "duration": 153,
                           "genres": json.dumps(["Action", "Sci-Fi"]),
                           "avgRating": 4.2, "ratingCount": 35})
c.expire("movie:1", config.CACHE_TTL + random.randint(0, 60))   # chống Avalanche
print(c.hgetall("movie:1"))
print("TTL movie:1 =", c.ttl("movie:1"), "giây")
c.hincrby("user:1:stats", "views", 1)
c.hincrby("user:1:stats", "ratings", 1)
print("user:1:stats =", c.hgetall("user:1:stats"))

# ---------- 3. List: 10 phim xem gần đây ----------
title("List: LPUSH / LREM / LTRIM / LRANGE")
for mid in [1114, 2262, 2247, 2262]:          # 2262 xem lại -> lên đầu, không trùng
    p = c.pipeline()
    p.lrem("user:1:recent", 0, str(mid))
    p.lpush("user:1:recent", str(mid))
    p.ltrim("user:1:recent", 0, 9)
    p.execute()
print("user:1:recent =", c.lrange("user:1:recent", 0, 4))

# ---------- 4. Sorted Set: xếp hạng phim, người dùng online ----------
title("Sorted Set: ZADD / ZINCRBY / ZREVRANGE / ZCARD")
c.zadd("movie:popular", {"1": 120, "2": 98, "3": 75})
c.zincrby("movie:popular", 1, "1")
print("Top phim:", c.zrevrange("movie:popular", 0, 2, withscores=True))

now = time.time()
c.zadd("online:users", {"1": now, "91": now - 10, "205": now - 900})  # 205 đã quá 5 phút
c.zremrangebyscore("online:users", 0, now - 300)                       # loại người không hoạt động
print("Đang online:", c.zcard("online:users"), "| score user 91:", c.zscore("online:users", "91"))

# ---------- 5. Set: bạn bè ----------
title("Set: SADD / SINTER / SUNION / SDIFF")
c.sadd("friends:1", 91, 141, 205)
c.sadd("friends:91", 1, 141, 300)
print("Bạn chung  :", c.sinter("friends:1", "friends:91"))
print("Hợp        :", c.sunion("friends:1", "friends:91"))
print("1 có, 91 không:", c.sdiff("friends:1", "friends:91"))
print("Số bạn của 1 :", c.scard("friends:1"))

# ---------- 6. Cache-aside cho kết quả gợi ý ----------
title("Cache-aside: get_or_set (rec:{id}:{method})")


def truy_van_neo4j():
    time.sleep(0.5)                            # giả lập Cypher chậm
    return [{"movieId": 7285, "title": "Inception"}]


for lan in (1, 2):
    t = time.perf_counter()
    kq, from_cache = rc.get_or_set("rec:1:hybrid", truy_van_neo4j, ttl=config.CACHE_TTL)
    print(f"Lần {lan}: {'HIT ' if from_cache else 'MISS'} {(time.perf_counter() - t) * 1000:.1f} ms -> {kq}")

# xóa cache khi dữ liệu đổi (SCAN + DEL)
rc.cache_delete_pattern("rec:1:*")
print("Sau khi xóa, rec:1:hybrid tồn tại?", bool(c.exists("rec:1:hybrid")))

# ---------- 7. Ba sự cố cache ----------
title("Avalanche / Penetration / Breakdown")
# Avalanche: TTL ngẫu nhiên để các key không hết hạn cùng lúc
print("TTL ngẫu nhiên:", [config.CACHE_TTL + random.randint(0, 60) for _ in range(5)])

# Penetration: phim không tồn tại -> lưu dấu null TTL ngắn, không hỏi lại DB
c.set("movie:99999", "__null__", ex=30)
print("movie:99999 =", c.get("movie:99999"), "| TTL =", c.ttl("movie:99999"))

# Breakdown: mutex, chỉ một tiến trình được dựng lại cache
print("Tiến trình A lấy khóa:", c.set("lock:movie:1", "1", nx=True, ex=5))   # True
print("Tiến trình B lấy khóa:", c.set("lock:movie:1", "1", nx=True, ex=5))   # None -> phải chờ
c.delete("lock:movie:1")

# ---------- 8. Pipeline: ghi nhận một lượt xem ----------
title("Pipeline: record_view")
p = c.pipeline()
p.incr("movie:1:views")
p.zincrby("movie:popular", 1, "1")
p.lpush("user:1:recent", "1")
p.ltrim("user:1:recent", 0, 9)
p.hincrby("user:1:stats", "views", 1)
kq = p.execute()
print("Kết quả 5 lệnh:", kq)

# ---------- 9. Kiểm tra kiểu và TTL của các key ----------
title("TYPE / TTL")
for k in ["movie:1", "movie:1:views", "movie:popular", "user:1:recent", "friends:1"]:
    print(f"{k:20} {c.type(k):6} TTL={c.ttl(k)}")

print("\nHoàn tất.")
