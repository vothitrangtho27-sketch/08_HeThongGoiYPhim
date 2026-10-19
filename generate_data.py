"""Sinh dữ liệu giả lập bằng Faker -> thư mục data/*.csv

Quy mô (đúng theo yêu cầu):
  User 10.000 | Movie 8.000 | Genre 2.000 | Rating 40.000 | Watched 20.000
  Friend 10.000 | Comment 10.000 | Movie-Genre 20.000
=> 30.000 nodes (User + Movie + Genre + Comment) và 100.000 relationships
   (RATED + WATCHED + FRIEND + HAS_GENRE + ABOUT).
Chạy: py generate_data.py
"""
import csv
import hashlib
import os
import random
from datetime import date, timedelta
from itertools import accumulate

from faker import Faker

SEED = 42
N_USERS = 10_000
N_MOVIES = 8_000
N_GENRES = 2_000
N_RATINGS = 40_000
N_WATCHED = 20_000
N_FRIENDS = 10_000
N_COMMENTS = 10_000          # mỗi user đúng 1 bình luận
N_MOVIE_GENRES = 20_000
DATA_DIR = "data"
DEFAULT_PASSWORD = "123456"

random.seed(SEED)
Faker.seed(SEED)
fake = Faker("vi_VN")

BASE_GENRES = ["Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary",
               "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery",
               "Romance", "Sci-Fi", "Thriller", "War", "Western"]
GID = {g: i + 1 for i, g in enumerate(BASE_GENRES)}

SEED_MOVIES = [  # phim thật để demo tìm kiếm (movieId 1..5)
    ("The Matrix", 1999, ["Action", "Sci-Fi"]),
    ("The Matrix Reloaded", 2003, ["Action", "Sci-Fi"]),
    ("Inception", 2010, ["Action", "Sci-Fi", "Thriller"]),
    ("Interstellar", 2014, ["Adventure", "Drama", "Sci-Fi"]),
    ("The Dark Knight", 2008, ["Action", "Crime", "Drama"]),
]
ADJ = ["Silent", "Broken", "Hidden", "Last", "Dark", "Golden", "Lost", "Crimson", "Eternal", "Wild",
       "Frozen", "Secret", "Burning", "Distant", "Fallen", "Hollow", "Iron", "Midnight", "Savage",
       "Silver", "Final", "Rising", "Shattered", "Endless", "Forgotten", "Electric", "Blind", "Rogue",
       "Neon", "Sacred", "Phantom", "Velvet", "Bitter", "Cosmic", "Lonely", "Rebel", "Stolen",
       "Twisted", "Wicked", "Gentle", "Restless", "Quiet", "Toxic", "Radiant", "Ancient", "Digital",
       "Hungry", "Faded", "Mighty", "Cruel"]
NOUN = ["Empire", "Shadow", "River", "Horizon", "Kingdom", "Storm", "Garden", "Memory", "Promise",
        "Frontier", "Legacy", "Mirror", "Voyage", "Echo", "Harvest", "Signal", "Fortress", "Dream",
        "Island", "Hunter", "Letter", "Bridge", "Throne", "Whisper", "Tide", "Citadel", "Rhythm",
        "Prophecy", "Outpost", "Carnival", "Labyrinth", "Paradise", "Witness", "Machine", "Avenue",
        "Reckoning", "Sanctuary", "Gambit", "Odyssey", "Eclipse", "Canyon", "Harbor", "Verdict",
        "Mission", "Rebellion", "Symphony", "Territory", "Mirage", "Fever", "Dynasty"]
CITIES = ["Hồ Chí Minh", "Hà Nội", "Đà Nẵng", "Cần Thơ", "Hải Phòng", "Huế", "Nha Trang",
          "Biên Hòa", "Vũng Tàu", "Đà Lạt", "Buôn Ma Thuột", "Quy Nhơn", "Thủ Dầu Một"]
PREFIXES = ("Anh ", "Chị ", "Ông ", "Bà ", "Cô ", "Bác ")
PHRASES = [
    "Phim hay, đáng xem!", "Cốt truyện cuốn hút từ đầu đến cuối.", "Diễn xuất rất tốt.",
    "Hơi dài nhưng kết thúc ổn.", "Hình ảnh và âm nhạc tuyệt vời.", "Không như mong đợi.",
    "Xem lần hai vẫn thấy hay.", "Phù hợp xem cùng gia đình.", "Kịch bản hơi dễ đoán.",
    "Một trong những phim hay nhất năm nay.", "Nhịp phim nhanh, rất giải trí.",
    "Nhân vật chính xây dựng chưa sâu.", "Great movie, highly recommended!",
    "Plot twist bất ngờ quá.", "Cảnh quay đẹp, đáng xem trên màn hình lớn.",
    "Phần đầu chậm nhưng càng về sau càng hay.", "Mình rất thích bộ phim này.",
]


def rand_date(start=date(2023, 1, 1), end=date(2026, 9, 30)):
    return start + timedelta(days=random.randint(0, (end - start).days))


def clamp(x, lo=1, hi=5):
    return max(lo, min(hi, x))


def write_csv(name, header, rows):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, name), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {name:<18} {len(rows):>7} dòng")
    return len(rows)


def make_titles(n):
    titles = [t for t, _, _ in SEED_MOVIES]
    used = set(titles)
    while len(titles) < n:
        a, b, c = random.choice(ADJ), random.choice(NOUN), random.choice(NOUN)
        t = random.choice([f"The {a} {b}", f"{a} {b}", f"{b} of {c}"])
        if t in used:
            t = f"{t} {random.choice(['II', 'III', 'IV', 'Reborn', 'Origins', 'Returns', 'Rising'])}"
        if t not in used:
            used.add(t)
            titles.append(t)
    return titles


def make_genre_names(n):
    """18 thể loại thật (id 1..18) + các thể loại con/kết hợp cho đủ n."""
    def gen():
        for a in ADJ:
            for g in BASE_GENRES:
                yield f"{a} {g}"
        for g1 in BASE_GENRES:
            for g2 in BASE_GENRES:
                if g1 != g2:
                    yield f"{g1}-{g2}"
        for a in ADJ:
            for g1 in BASE_GENRES[:4]:
                for g2 in BASE_GENRES[4:8]:
                    yield f"{a} {g1}-{g2}"
    extra = [x for x in dict.fromkeys(gen()) if x not in GID]
    random.shuffle(extra)
    return BASE_GENRES + extra[: n - len(BASE_GENRES)]


def main():
    print("Đang sinh dữ liệu...")
    uids = list(range(1, N_USERS + 1))
    mids = list(range(1, N_MOVIES + 1))
    gids = list(range(1, N_GENRES + 1))

    # ---------- genres: 18 thể loại thật có trọng số lớn ----------
    genre_names = make_genre_names(N_GENRES)
    genre_rows = [(i + 1, n) for i, n in enumerate(genre_names)]
    gw = [random.uniform(60, 140) if i < len(BASE_GENRES) else random.uniform(0.3, 1.0) for i in range(N_GENRES)]
    gcum = list(accumulate(gw))

    # ---------- movies + movie_genres (đúng N_MOVIE_GENRES dòng) ----------
    titles = make_titles(N_MOVIES)
    seed_map = {t: gs for t, _, gs in SEED_MOVIES}
    seed_year = {t: y for t, y, _ in SEED_MOVIES}
    k = {}
    for i, t in enumerate(titles, start=1):
        k[i] = len(seed_map[t]) if t in seed_map else random.choices([1, 2, 3, 4], [10, 40, 35, 15])[0]
    free = [i for i in mids if titles[i - 1] not in seed_map]
    diff = N_MOVIE_GENRES - sum(k.values())
    while diff != 0:
        i = random.choice(free)
        if diff > 0 and k[i] < 6:
            k[i] += 1; diff -= 1
        elif diff < 0 and k[i] > 1:
            k[i] -= 1; diff += 1
    forced = {}                       # mỗi thể loại xuất hiện ít nhất ở 1 phim
    order = free[:]
    random.shuffle(order)
    for g, i in zip(gids, order):
        forced[i] = g
    mg, movie_rows, mg_rows = {}, [], []
    for i, title in enumerate(titles, start=1):
        i = i
        if title in seed_map:
            gs = {GID[g] for g in seed_map[title]}
        else:
            gs = {forced[i]} if i in forced else set()
            while len(gs) < k[i]:
                gs.add(random.choices(gids, cum_weights=gcum)[0])
        mg[i] = gs
        movie_rows.append((i, title, seed_year.get(title, random.randint(1980, 2026)), random.randint(80, 180)))
        mg_rows += [(i, g) for g in sorted(gs)]

    # độ phổ biến phim (Zipf) -> nhiều người cùng xem 1 phim => đồ thị liên kết dày
    rank = mids[:]
    random.shuffle(rank)
    pop = {m: 1.0 / (rank[m - 1] ** 0.7) for m in mids}
    bias = {m: random.choice([-1, 0, 0, 0, 1]) for m in mids}
    all_cum = list(accumulate(pop[m] for m in mids))
    pool = {g: [] for g in gids}
    for m in mids:
        for g in mg[m]:
            pool[g].append(m)
    pool_cum = {g: list(accumulate(pop[m] for m in pool[g])) for g in gids}

    # ---------- users ----------
    pw = hashlib.sha256(DEFAULT_PASSWORD.encode()).hexdigest()
    user_rows, fav = [], {}
    for u in uids:
        if u == 1:
            name, email = "Nguyễn Văn A", "nguyenvana@gmail.com"
        else:
            name, email = fake.name(), f"user{u}@example.com"
            for p in PREFIXES:
                if name.startswith(p):
                    name = name[len(p):]
        s = set()
        want = random.choice([2, 3])
        while len(s) < want:
            s.add(random.choices(gids, cum_weights=gcum)[0])
        fav[u] = tuple(s)
        user_rows.append((u, name, email, random.randint(16, 60), random.choice(CITIES), pw,
                          rand_date(date(2022, 1, 1), date(2023, 1, 1))))

    # ---------- friends (đúng N_FRIENDS, mỗi user >= 1 bạn, User 1 có 25 bạn) ----------
    by_genre = {}
    for u in uids:
        for g in fav[u]:
            by_genre.setdefault(g, []).append(u)
    edges, deg = set(), {u: 0 for u in uids}

    def add_edge(a, b):
        if a == b:
            return False
        e = (min(a, b), max(a, b))
        if e in edges:
            return False
        edges.add(e); deg[a] += 1; deg[b] += 1
        return True

    def pick_friend(u):
        if random.random() < 0.6:
            return random.choice(by_genre[random.choice(fav[u])])
        return random.randint(1, N_USERS)

    while deg[1] < 25:
        add_edge(1, random.randint(2, N_USERS))
    for u in uids:
        while deg[u] == 0:
            add_edge(u, pick_friend(u))
    while len(edges) < N_FRIENDS:
        u = random.randint(2, N_USERS)
        add_edge(u, pick_friend(u))
    friend_rows = [(a, b, rand_date(date(2022, 1, 1), date(2025, 12, 31))) for a, b in sorted(edges)]

    adj = {}
    for a, b in edges:
        adj.setdefault(a, set()).add(b); adj.setdefault(b, set()).add(a)
    net = set(adj[1])
    for f in adj[1]:
        net |= adj[f]
    net.discard(1)

    # ---------- ratings (đúng N_RATINGS dòng) ----------
    rated = {u: {} for u in uids}
    rated_movies = set()
    total = 0

    def make_rating(u, m):
        if set(fav[u]) & mg[m]:
            r = random.choices([3, 4, 5], [1, 4, 5])[0]
        else:
            r = random.choices([1, 2, 3, 4, 5], [15, 25, 30, 20, 10])[0]
        return clamp(r + bias[m])

    def pick_movie(u):
        if random.random() < 0.7:
            g = random.choice(fav[u])
            return random.choices(pool[g], cum_weights=pool_cum[g])[0]
        return random.choices(mids, cum_weights=all_cum)[0]

    def add_rating(u, m, r=None):
        nonlocal total
        if m in rated[u]:
            return False
        rated[u][m] = (r if r else make_rating(u, m), rand_date())
        rated_movies.add(m)
        total += 1
        return True

    while len(rated[1]) < 40:                       # User 1: 40 đánh giá (demo)
        add_rating(1, pick_movie(1))
    u1_high = [m for m, (r, _) in rated[1].items() if r >= 4]
    # cài sẵn người cùng sở thích với User 1 (trong mạng bạn bè và ngoài mạng) để các câu 3,5,11,14,15 có kết quả
    in_net = random.sample(sorted(net), min(25, len(net)))
    outside = random.sample([u for u in uids if u != 1 and u not in net], 80)
    for u in in_net + outside:
        for m in random.sample(u1_high, min(len(u1_high), random.randint(2, 4))):
            add_rating(u, m, random.choice([4, 5, 5]))
    for u in uids:                                   # mỗi user >= 1 đánh giá
        while not rated[u]:
            add_rating(u, pick_movie(u))
    for m in mids:                                   # mỗi phim >= 1 đánh giá
        while m not in rated_movies:
            add_rating(random.randint(2, N_USERS), m)
    act = [0.0] + [random.lognormvariate(0, 0.9) for _ in range(N_USERS - 1)]
    ucum = list(accumulate(act))
    while total < N_RATINGS:                         # bổ sung cho đủ số lượng
        u = random.choices(uids, cum_weights=ucum)[0]
        add_rating(u, pick_movie(u))

    # ---------- watched (đúng N_WATCHED dòng) ----------
    watched = {u: {} for u in uids}
    wtotal = 0

    def add_watch(u, m, d=None):
        nonlocal wtotal
        if m in watched[u]:
            return False
        watched[u][m] = d or rand_date()
        wtotal += 1
        return True

    for m in random.sample(sorted(rated[1]), 15):    # User 1: 15 phim đã đánh giá + 5 phim chỉ xem
        add_watch(1, m, rated[1][m][1] - timedelta(days=random.randint(0, 10)))
    while len(watched[1]) < 20:
        m = random.choices(mids, cum_weights=all_cum)[0]
        if m not in rated[1]:
            add_watch(1, m)
    for u in uids[1:]:                               # mỗi user xem >= 1 phim (phim đã đánh giá)
        m = random.choice(list(rated[u]))
        add_watch(u, m, rated[u][m][1] - timedelta(days=random.randint(0, 10)))
    while wtotal < N_WATCHED:                        # phần còn lại: xem nhưng chưa đánh giá
        u = random.choices(uids, cum_weights=ucum)[0]
        m = pick_movie(u)
        if m not in rated[u]:
            add_watch(u, m)

    # ---------- comments (mỗi user đúng 1 bình luận, trên phim đã xem) ----------
    authors = uids[:]
    random.shuffle(authors)
    comment_rows = []
    for cid, u in enumerate(authors, start=1):
        m = random.choice(list(watched[u]))
        comment_rows.append((cid, u, m, random.choice(PHRASES), watched[u][m] + timedelta(days=random.randint(0, 15))))

    rating_rows = [(u, m, r, d) for u in rated for m, (r, d) in rated[u].items()]
    watched_rows = [(u, m, d) for u in watched for m, d in watched[u].items()]

    # ---------- ghi file ----------
    write_csv("users.csv", ["userId", "name", "email", "age", "city", "password", "createdAt"], user_rows)
    write_csv("movies.csv", ["movieId", "title", "year", "duration"], movie_rows)
    write_csv("genres.csv", ["genreId", "name"], genre_rows)
    n_mg = write_csv("movie_genres.csv", ["movieId", "genreId"], mg_rows)
    n_rate = write_csv("ratings.csv", ["userId", "movieId", "rating", "ratedAt"], rating_rows)
    n_watch = write_csv("watched.csv", ["userId", "movieId", "watchedAt"], watched_rows)
    n_friend = write_csv("friends.csv", ["userId", "friendId", "since"], friend_rows)
    n_cmt = write_csv("comments.csv", ["commentId", "userId", "movieId", "content", "createdAt"], comment_rows)

    nodes = N_USERS + N_MOVIES + N_GENRES + n_cmt
    rels = n_rate + n_watch + n_friend + n_mg + n_cmt     # Comment: 1 quan hệ ABOUT (userId lưu trong node)
    print(f"\nƯớc tính: {nodes:,} nodes, {rels:,} relationships")
    if not (10_000 <= nodes <= 30_000 and 50_000 <= rels <= 100_000):
        print("CẢNH BÁO: chưa đạt yêu cầu 10k-30k nodes / 50k-100k relationships.")
    print(f"Mật khẩu mặc định mọi user: {DEFAULT_PASSWORD} | User 1: nguyenvana@gmail.com")


if __name__ == "__main__":
    main()
