"""Minh họa dữ liệu, truy vấn và kết nối ứng dụng trên Redis bằng DỮ LIỆU THẬT trong thư mục data/ (không cần Neo4j).

Chạy:  python redis_demo.py

Script gọi đúng các hàm của redis_connection.py và services/redis_service.py. Chỉ phần truy vấn Neo4j được thay bằng
việc đọc các file CSV đã dùng để nhập vào Neo4j (movies, ratings, watched, friends, genres, movie_genres), nên các số liệu
(phim, điểm trung bình, lượt WATCHED, bạn bè của người dùng 1...) là dữ liệu của hệ thống.

An toàn: nếu Redis đang có dữ liệu, script dừng lại và yêu cầu dùng REDIS_DB khác (ví dụ REDIS_DB=1 trong .env).
Cuối chương trình script xóa mọi khóa mà nó tạo ra.
"""
import csv
import os
import time
from collections import Counter, defaultdict

import config
import redis_connection as rc
from services import redis_service as rs

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def read(name):
    with open(os.path.join(DATA, name + ".csv"), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- dữ liệu thật từ CSV
MOVIES = {int(r["movieId"]): r for r in read("movies")}
GENRE_NAME = {int(r["genreId"]): r["name"] for r in read("genres")}
MOVIE_GENRES = defaultdict(list)
for r in read("movie_genres"):
    MOVIE_GENRES[int(r["movieId"])].append(GENRE_NAME[int(r["genreId"])])
RATINGS = defaultdict(list)
for r in read("ratings"):
    RATINGS[int(r["movieId"])].append(int(r["rating"]))
WATCHED = read("watched")
WATCH_COUNT = Counter(int(r["movieId"]) for r in WATCHED)
FRIENDS = defaultdict(set)
for r in read("friends"):
    FRIENDS[int(r["userId"])].add(int(r["friendId"]))
    FRIENDS[int(r["friendId"])].add(int(r["userId"]))       # quan hệ FRIEND là vô hướng

U1 = 1                                                      # Nguyễn Văn A
U2 = next(int(r["friendId"]) for r in read("friends") if int(r["userId"]) == U1)   # một người bạn của U1
TOP = [m for m, _ in WATCH_COUNT.most_common(3)]            # 3 phim có nhiều lượt WATCHED nhất
M_NONE = 99999                                              # mã phim không tồn tại
neo4j_calls = {"n": 0}


def movie_loader(mid):
    def load():
        neo4j_calls["n"] += 1                               # đếm số lần "phải hỏi database gốc"
        m = MOVIES.get(mid)
        if not m:
            return None
        rt = RATINGS.get(mid, [])
        return {"title": m["title"], "year": int(m["year"]), "duration": int(m["duration"]),
                "genres": MOVIE_GENRES.get(mid, []), "avgRating": round(sum(rt) / len(rt), 2) if rt else None,
                "ratingCount": len(rt)}
    return load


def recent_ids(uid):                                        # lịch sử xem, mới nhất trước
    rows = sorted((r for r in WATCHED if int(r["userId"]) == uid), key=lambda r: r["watchedAt"], reverse=True)
    return [int(r["movieId"]) for r in rows]


def fake_run_query(query, params=None):                     # thay cho truy vấn WATCHED của warm_popular()
    return [{"id": m, "n": n} for m, n in WATCH_COUNT.most_common((params or {}).get("limit", 50))]


def title(text):
    print(f"\n=== {text} ===")


def name_of(mid):
    return MOVIES[int(mid)]["title"]


def main():
    # ---------- 1. Kết nối ----------
    title("1. Kết nối ứng dụng - Redis")
    c = rc.get_client()
    if c is None:
        print("Không kết nối được Redis. Hãy bật Redis (cổng 6379) hoặc kiểm tra file .env.")
        return
    print("host/port/db :", config.REDIS_HOST, config.REDIS_PORT, config.REDIS_DB)
    print("PING         :", c.ping())
    print("redis_version:", c.info("server")["redis_version"])
    if c.dbsize() and not os.getenv("DEMO_FORCE"):
        print(f"Database {config.REDIS_DB} đang có {c.dbsize()} khóa. Để không ảnh hưởng dữ liệu của ứng dụng, "
              "hãy đặt REDIS_DB=1 trong .env (hoặc đặt biến môi trường DEMO_FORCE=1 nếu chấp nhận).")
        return
    before = set(c.scan_iter())
    rs.run_query = fake_run_query                           # warm_popular() đọc số lượt WATCHED từ CSV
    print("Dữ liệu CSV  :", f"{len(MOVIES)} phim, {len(WATCHED)} lượt WATCHED, {sum(len(v) for v in RATINGS.values())} đánh giá")
    print("Người dùng   :", U1, "(bạn:", len(FRIENDS[U1]), ") và", U2, "(bạn:", len(FRIENDS[U2]), ")")

    # ---------- 2. String + TTL ----------
    title("2. String + TTL: cache JSON (rc.cache_set / cache_get)")
    rc.cache_set(f"rec:{U1}:hybrid", [{"movieId": TOP[0], "title": name_of(TOP[0])}], 300)
    print(f"GET rec:{U1}:hybrid ->", c.get(f"rec:{U1}:hybrid"))
    print(f"TTL rec:{U1}:hybrid ->", c.ttl(f"rec:{U1}:hybrid"), "giây")
    rc.cache_delete_pattern(f"rec:{U1}:*")
    print("sau cache_delete_pattern, EXISTS ->", c.exists(f"rec:{U1}:hybrid"))

    # ---------- 3. Hash + 3 sự cố cache ----------
    title("3. Hash: cache thông tin phim (movie_summary)")
    m1 = TOP[0]
    m, cached = rs.movie_summary(m1, movie_loader(m1))
    print(f"Lần 1 (cache miss): {m['title']} | from_cache = {cached}")
    m, cached = rs.movie_summary(m1, movie_loader(m1))
    print(f"Lần 2 (cache hit) : {m['title']} | from_cache = {cached}")
    print("Số lần phải truy vấn database gốc:", neo4j_calls["n"], "(chỉ 1 dù gọi 2 lần)")
    print(f"HGETALL movie:{m1} ->", c.hgetall(f"movie:{m1}"))
    print(f"TTL movie:{m1} ->", c.ttl(f"movie:{m1}"), "giây (300 + ngẫu nhiên 0-60: chống Avalanche)")
    before_calls = neo4j_calls["n"]
    print("Phim không tồn tại lần 1:", rs.movie_summary(M_NONE, movie_loader(M_NONE)))
    print("Phim không tồn tại lần 2:", rs.movie_summary(M_NONE, movie_loader(M_NONE)))
    print(f"GET movie:{M_NONE} -> {c.get(f'movie:{M_NONE}')!r}, TTL = {c.ttl(f'movie:{M_NONE}')} giây (chống Penetration)")
    print("Database gốc bị hỏi thêm:", neo4j_calls["n"] - before_calls, "lần (chỉ lần đầu)")
    lock = f"lock:movie:{TOP[1]}"
    print(f"SET {lock} NX EX 5 ->", c.set(lock, "1", nx=True, ex=5), "| tiến trình thứ hai ->", c.set(lock, "1", nx=True, ex=5),
          "(chống Breakdown)")
    c.delete(lock)

    # ---------- 4. Lượt xem: String, Sorted Set, List, Hash ----------
    title("4. Ghi nhận lượt xem (record_view): String, Sorted Set, List, Hash")
    a, b, d = TOP
    print("Bảng xếp hạng ban đầu nạp từ số lượt WATCHED thật:", [(x, WATCH_COUNT[x]) for x in TOP])
    print(f"Lịch sử xem thật của người dùng {U1} (mới nhất trước):", recent_ids(U1)[:5])
    for mid in (a, b, a, d, a, b):                          # 6 lượt xem
        rs.record_view(U1, mid, lambda: recent_ids(U1))
    rs.record_rating(U1)
    print(f"GET movie:{a}:views              ->", c.get(f"movie:{a}:views"))
    print("ZREVRANGE movie:popular 0 2 WITHSCORES ->", c.zrevrange("movie:popular", 0, 2, withscores=True))
    print(f"LRANGE user:{U1}:recent 0 4      ->", c.lrange(f"user:{U1}:recent", 0, 4))
    print(f"HGETALL user:{U1}:stats          ->", c.hgetall(f"user:{U1}:stats"))
    c.delete(f"user:{U1}:recent")
    print("Xóa List rồi dựng lại từ lịch sử xem thật:", rs.recent_movies(U1, 5, lambda: recent_ids(U1)))

    # ---------- 5. Đăng nhập, online ----------
    title("5. Bộ đếm đăng nhập và người online (String + Sorted Set)")
    rs.on_login(U1); rs.on_login(U1); rs.on_login(U2)
    print(f"GET user:{U1}:login:count ->", c.get(f"user:{U1}:login:count"))
    print(f"ZSCORE online:users {U2} ->", c.zscore("online:users", str(U2)))
    print("count_online() ->", rs.count_online())
    print(f"online_friends({U1}, bạn của {U1}) ->", sorted(rs.online_friends(U1, sorted(FRIENDS[U1]))))
    rs.on_logout(U2)
    print(f"sau on_logout({U2}) ->", sorted(rs.online_friends(U1, sorted(FRIENDS[U1]))))

    # ---------- 6. Set: bạn bè ----------
    title("6. Set: tập bạn bè và phép toán tập hợp")
    # U3: người có nhiều bạn chung nhất với U1 trong dữ liệu thật (không phải bạn của U1)
    U3 = max((u for u in FRIENDS if u != U1 and u not in FRIENDS[U1]),
             key=lambda u: (len(FRIENDS[U1] & FRIENDS[u]), -u))
    rs.cache_friend_set(U1, sorted(FRIENDS[U1]))
    rs.cache_friend_set(U3, sorted(FRIENDS[U3]))
    ops = rs.friend_set_ops(U1, U3, lambda u: sorted(FRIENDS[u]))
    print(f"SCARD friends:{U1} / friends:{U3} ->", ops["card_a"], "/", ops["card_b"])
    print(f"SINTER friends:{U1} friends:{U3} ->", ops["inter"], "# bạn chung")
    print(f"SUNION friends:{U1} friends:{U3} ->", len(ops["union"]), "người")
    print(f"SDIFF  friends:{U1} friends:{U3} ->", len(ops["diff"]), "người, 5 mã đầu:", ops["diff"][:5], "# chỉ người", U1, "có")

    # ---------- 7. Cache-aside: so sánh MISS và HIT ----------
    title("7. Cache-aside (rc.get_or_set): so sánh MISS và HIT")

    def top_movies_from_csv():                              # tính lại từ file CSV, tốn thời gian thật
        cnt = Counter(int(r["movieId"]) for r in read("watched"))
        return [{"movieId": m_, "title": MOVIES[m_]["title"], "views": n} for m_, n in cnt.most_common(10)]

    for lan in (1, 2):
        t = time.perf_counter()
        kq, from_cache = rc.get_or_set("stats:top10", top_movies_from_csv, ttl=120)
        print(f"Lần {lan}: {'HIT ' if from_cache else 'MISS'} {(time.perf_counter() - t) * 1000:.2f} ms -> {len(kq)} phim, đầu tiên: {kq[0]['title']}")

    # ---------- 8. TYPE / TTL ----------
    title("8. TYPE / TTL của các khóa đã tạo")
    for k in sorted(set(c.scan_iter()) - before):
        print(f"{k:24} {c.type(k):7} TTL={c.ttl(k)}")

    # ---------- 9. Dọn dữ liệu demo ----------
    title("9. Dọn dữ liệu demo")
    created = list(set(c.scan_iter()) - before)
    if created:
        c.delete(*created)
    print("Đã xóa", len(created), "khóa do script tạo ra.")


if __name__ == "__main__":
    main()
