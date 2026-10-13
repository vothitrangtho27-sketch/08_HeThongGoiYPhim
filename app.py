"""Movie Recommender - giao diện Streamlit. Chạy: streamlit run app.py"""
import pandas as pd
import streamlit as st

import config
import neo4j_connection as nc
import redis_connection as rc
from services import (auth_service, comment_service, friend_service, history_service,
                      movie_service, profile_service, query_service, recommendation_service)

st.set_page_config(page_title=config.APP_TITLE, page_icon="🎬", layout="wide")

MENU = ["🏠 Trang chủ", "🎬 Danh sách phim", "🔍 Tìm kiếm", "⭐ Chi tiết phim", "🕘 Lịch sử xem",
        "👥 Bạn bè", "🎯 Gợi ý phim", "👤 Hồ sơ", "🧪 Truy vấn dữ liệu", "🚪 Đăng xuất"]
M_HOME, M_LIST, M_SEARCH, M_DETAIL, M_HIST, M_FRIEND, M_REC, M_PROFILE, M_QUERY, M_LOGOUT = MENU



CSS = """
<style>
#MainMenu, footer {visibility: hidden;}
[data-testid="stHeader"] {background: transparent;}
[data-testid="stAppViewContainer"] {background: linear-gradient(180deg,#FFF1F5 0%,#FFF8FA 100%);}
.block-container {padding-top: 2rem; max-width: 1100px;}

/* ===== Sidebar cố định ===== */
[data-testid="stSidebar"] {background: linear-gradient(180deg,#FFD6E4 0%,#FFE8F0 100%);
    border-right: 1px solid #F8BBD0; min-width: 280px; max-width: 280px; transform: none !important;}
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {display: none !important;}
[data-testid="stSidebar"] [role="radiogroup"] {gap: 4px;}
[data-testid="stSidebar"] [role="radiogroup"] label {width: 100%; padding: 10px 14px; border-radius: 12px;
    cursor: pointer; transition: all .15s; font-weight: 500;}
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {display: none;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {background: rgba(255,255,255,.65);}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(90deg,#D6336C,#F06595); box-shadow: 0 4px 12px rgba(214,51,108,.30);}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) * {color: #fff !important; font-weight: 600;}
.brand {font-size: 1.45rem; font-weight: 800; color: #B0245A; margin-bottom: 2px;}
.userbox {background: rgba(255,255,255,.75); border-radius: 14px; padding: 10px 14px; margin: 8px 0 14px;
    font-size: .9rem; color: #5a3a48;}

/* ===== Tiêu đề trang ===== */
.page-header {background: linear-gradient(120deg,#D6336C,#F783AC); color: #fff; border-radius: 18px;
    padding: 22px 28px; margin-bottom: 22px; box-shadow: 0 8px 24px rgba(214,51,108,.25);}
.page-header h1 {margin: 0; font-size: 1.7rem; color: #fff; padding: 0;}
.page-header p {margin: 4px 0 0; opacity: .92; font-size: .95rem;}

/* ===== Thẻ / card ===== */
[data-testid="stVerticalBlockBorderWrapper"] {background: #fff; border: 1px solid #FBD0DF !important;
    border-radius: 16px !important; box-shadow: 0 2px 10px rgba(214,51,108,.08); transition: box-shadow .2s;}
[data-testid="stVerticalBlockBorderWrapper"]:hover {box-shadow: 0 6px 18px rgba(214,51,108,.16);}
[data-testid="stMetric"] {background: #fff; border: 1px solid #FBD0DF; border-radius: 16px; padding: 14px 18px;
    box-shadow: 0 2px 10px rgba(214,51,108,.08);}
[data-testid="stMetricValue"] {color: #D6336C; font-weight: 800;}
.poster {width: 54px; height: 72px; border-radius: 10px; display: flex; align-items: center; justify-content: center;
    color: #fff; font-size: 1.6rem; font-weight: 800; background: linear-gradient(135deg,#D6336C,#FFA8C5);
    box-shadow: 0 4px 10px rgba(214,51,108,.3);}
.mtitle {font-size: 1.05rem; font-weight: 700; color: #3A2A33; margin: 0;}
.chip {display: inline-block; background: #FFE0EA; color: #B0245A; border-radius: 999px; padding: 2px 10px;
    font-size: .75rem; font-weight: 600; margin: 4px 4px 0 0;}
.badge {display: inline-block; background: #FFF3BF; color: #8a6d00; border-radius: 999px; padding: 2px 10px;
    font-size: .78rem; font-weight: 700; margin-top: 4px;}
.muted {color: #8d6e7a; font-size: .82rem;}

/* ===== Nút & input ===== */
.stButton > button, .stFormSubmitButton > button {border-radius: 999px; border: 1px solid #F06595;
    font-weight: 600; transition: all .15s;}
.stButton > button:hover {border-color: #D6336C; color: #D6336C; background: #FFF0F6;}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
    background: linear-gradient(90deg,#D6336C,#F06595); color: #fff; border: none;
    box-shadow: 0 4px 12px rgba(214,51,108,.3);}
.stButton > button[kind="primary"]:hover {color: #fff; filter: brightness(1.05);}
[data-baseweb="input"], [data-baseweb="select"] > div, textarea {border-radius: 12px !important;}
[data-testid="stTabs"] button[aria-selected="true"] {color: #D6336C; font-weight: 700;}
.auth-box {background: #fff; border-radius: 22px; padding: 10px 28px 24px; border: 1px solid #FBD0DF;
    box-shadow: 0 12px 36px rgba(214,51,108,.18);}
.auth-title {text-align: center; font-size: 2rem; font-weight: 800; color: #B0245A; margin: 30px 0 0;}
.auth-sub {text-align: center; color: #8d6e7a; margin-bottom: 18px;}
</style>
"""


def header(title, sub=""):
    st.markdown(f'<div class="page-header"><h1>{title}</h1>' + (f"<p>{sub}</p>" if sub else "") + "</div>",
                unsafe_allow_html=True)


# ---------- tiện ích ----------
def go_movie(movie_id):
    st.session_state["selected_movie"] = int(movie_id)
    st.session_state["menu"] = M_DETAIL


def go_profile(user_id):
    st.session_state["view_profile"] = int(user_id)
    st.session_state["menu"] = M_PROFILE


def stars(x):
    return "⭐" * int(round(x or 0)) if x else "Chưa có"


def movie_card(m, key, extra=None):
    with st.container(border=True):
        c0, c1, c2 = st.columns([0.8, 6, 1.5], vertical_alignment="center")
        letter = (m.get("title") or "?").lstrip("0123456789. ")[:1].upper() or "?"
        c0.markdown(f'<div class="poster">{letter}</div>', unsafe_allow_html=True)
        year = f" <span class='muted'>({m['year']})</span>" if m.get("year") else ""
        html = f'<p class="mtitle">{m["title"]}{year}</p>'
        html += "".join(f'<span class="chip">{g}</span>' for g in (m.get("genres") or []))
        if m.get("avgRating") is not None:
            html += f'<br><span class="badge">⭐ {m["avgRating"]}</span> <span class="muted">{m.get("ratingCount", 0)} lượt đánh giá</span>'
        if extra:
            html += f'<br><span class="muted">{extra}</span>'
        c1.markdown(html, unsafe_allow_html=True)
        c2.button("Xem chi tiết", key=f"{key}_{m['movieId']}", on_click=go_movie, args=(m["movieId"],))


# ---------- đăng nhập / đăng ký ----------
def page_auth():
    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        st.markdown('<div class="auth-title">🎬 Movie Recommender</div>'
                    '<div class="auth-sub">Hệ thống gợi ý phim trên Neo4j + Redis</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        tab_login, tab_reg = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký"])
        with tab_login:
            with st.form("login", border=False):
                email = st.text_input("Email")
                pw = st.text_input("Mật khẩu", type="password")
                if st.form_submit_button("Đăng nhập", type="primary", use_container_width=True):
                    user = auth_service.login(email, pw)
                    if user:
                        st.session_state["user"] = user
                        st.session_state["menu"] = M_HOME
                        st.rerun()
                    else:
                        st.error("Sai email hoặc mật khẩu.")
        with tab_reg:
            with st.form("register", border=False):
                name = st.text_input("Họ và tên")
                email = st.text_input("Email ", key="reg_email")
                c1, c2 = st.columns(2)
                age = c1.number_input("Tuổi", 10, 100, 20)
                city = c2.text_input("Thành phố")
                pw = st.text_input("Mật khẩu ", type="password", key="reg_pw")
                if st.form_submit_button("Tạo tài khoản", type="primary", use_container_width=True):
                    ok, msg, _ = auth_service.register(name, email, pw, age, city)
                    (st.success if ok else st.error)(msg + (" Hãy chuyển sang tab Đăng nhập." if ok else ""))
        st.markdown("</div>", unsafe_allow_html=True)


# ---------- các trang ----------
def page_home(uid):
    user = st.session_state["user"]
    header("🏠 Trang chủ", "Tổng quan hệ thống và gợi ý dành riêng cho bạn")
    st.write(f"Xin chào, **{user['name']}**!")
    s = movie_service.stats()
    c = st.columns(4)
    c[0].metric("🎬 Phim", f"{s['movies']:,}")
    c[1].metric("👤 Người dùng", f"{s['users']:,}")
    c[2].metric("🏷️ Thể loại", f"{s['genres']:,}")
    c[3].metric("⭐ Đánh giá", f"{s['ratings']:,}")
    st.subheader("Gợi ý nhanh cho bạn")
    rows, ms, cached = recommendation_service.recommend(uid, "hybrid")
    st.caption("Lấy từ Redis cache" if cached else f"Truy vấn Neo4j: {ms:.0f} ms")
    if not rows:
        st.info("Chưa đủ dữ liệu để gợi ý. Hãy đánh giá thêm vài phim.")
    for m in rows[:3]:
        movie_card(m, "home", f"Điểm gợi ý: {m.get('diemTongHop')}")


def page_list(uid):
    header("🎬 Danh sách phim", "Khám phá kho phim theo thể loại")
    genres = ["Tất cả"] + [g["name"] for g in movie_service.list_genres()]
    c1, c2 = st.columns([2, 1])
    genre = c1.selectbox("Thể loại", genres)
    g = None if genre == "Tất cả" else genre
    total = movie_service.count_movies(g)
    pages = max(1, -(-total // config.PAGE_SIZE))
    page = c2.number_input(f"Trang (1-{pages})", 1, pages, 1)
    st.caption(f"{total:,} phim")
    for m in movie_service.list_movies(int(page), config.PAGE_SIZE, g):
        movie_card(m, "list")


def page_search(uid):
    header("🔍 Tìm kiếm phim", "Tìm phim theo tên")
    kw = st.text_input("Nhập tên phim", placeholder="Ví dụ: Matrix")
    if st.button("Tìm kiếm", type="primary") or kw:
        if not kw.strip():
            st.warning("Hãy nhập từ khóa.")
            return
        res = movie_service.search_movies(kw)
        st.write(f"**Kết quả tìm kiếm:** {len(res)} phim")
        for m in res:
            movie_card(m, "search")


def page_detail(uid):
    header("⭐ Chi tiết phim", "Đánh giá, bình luận và đánh dấu đã xem")
    mid = st.session_state.get("selected_movie")
    if mid is None:
        mid = st.number_input("Nhập mã phim", 1, value=1)
    m = movie_service.get_movie(mid)
    if not m:
        st.error("Không tìm thấy phim.")
        return
    st.header(m["title"])
    st.write(f"**Năm:** {m['year']} · **Thời lượng:** {m['duration']} phút · **Thể loại:** {', '.join(m['genres'])}")
    st.write(f"**Điểm trung bình:** {m['avgRating']} ({m['ratingCount']} lượt)")

    if st.button("✅ Đánh dấu đã xem"):
        history_service.mark_watched(uid, mid)
        st.success("Đã thêm vào lịch sử xem.")

    st.subheader("Đánh giá của bạn")
    mine = movie_service.get_user_rating(uid, mid)
    rating = st.radio("Chọn số sao", [1, 2, 3, 4, 5], index=(mine - 1) if mine else 4,
                      format_func=lambda x: "⭐" * x, horizontal=True)
    if st.button("Gửi đánh giá", type="primary"):
        movie_service.rate_movie(uid, mid, rating)
        st.success("Đã lưu đánh giá.")
        st.rerun()

    st.subheader("Bình luận")
    with st.form("cmt", clear_on_submit=True):
        text = st.text_area("Viết bình luận")
        if st.form_submit_button("Gửi bình luận") and comment_service.add_comment(uid, mid, text):
            st.rerun()
    for c in comment_service.get_comments(mid):
        with st.container(border=True):
            st.markdown(f"**{c['name']}** · User ID: {c['userId']} · {c['createdAt']}")
            st.write(c["content"])


def page_history(uid):
    header("🕘 Lịch sử xem", "Những phim bạn đã xem")
    rows = history_service.get_history(uid)
    st.write(f"**Tổng phim đã xem:** {history_service.count_history(uid)}")
    for h in rows:
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"**{h['title']}** ({h['year']})")
            c1.caption(f"Xem ngày {h['watchedAt']} · Đánh giá của bạn: {stars(h['myRating'])}")
            c2.button("Xem", key=f"h_{h['movieId']}", on_click=go_movie, args=(h["movieId"],))


def page_friends(uid):
    header("👥 Bạn bè", "Quản lý mạng bạn bè của bạn")
    friends = friend_service.list_friends(uid)
    st.subheader(f"Danh sách bạn bè ({len(friends)})")
    for f in friends:
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.markdown(f"**{f['name']}**  \nUser ID: {f['userId']} · {f['city']}")
            c2.button("Xem hồ sơ", key=f"fp_{f['userId']}", on_click=go_profile, args=(f["userId"],))
            if c3.button("❌ Xóa", key=f"fd_{f['userId']}"):
                friend_service.remove_friend(uid, f["userId"])
                st.rerun()
    st.subheader("Thêm bạn")
    kw = st.text_input("Tìm theo tên hoặc User ID")
    if kw.strip():
        for u in friend_service.search_users(kw, uid):
            c1, c2 = st.columns([5, 1])
            c1.write(f"{u['name']} (ID {u['userId']}) · {u['city']}")
            if u["isFriend"]:
                c2.write("✔ Đã là bạn")
            elif c2.button("➕ Thêm", key=f"fa_{u['userId']}"):
                friend_service.add_friend(uid, u["userId"])
                st.rerun()


def page_rec(uid):
    header("🎯 Gợi ý phim", "Gợi ý cá nhân hóa từ đồ thị Neo4j")
    labels = {k: v[1] for k, v in recommendation_service.METHODS.items()}
    method = st.radio("Phương pháp", list(labels), format_func=labels.get, horizontal=True, index=3)
    use_cache = st.toggle("Dùng Redis cache", value=True, disabled=not rc.is_available())
    if not rc.is_available():
        st.caption("⚠️ Redis không chạy: kết quả luôn lấy trực tiếp từ Neo4j.")
    rows, ms, cached = recommendation_service.recommend(uid, method, use_cache)
    st.caption("⚡ Lấy từ Redis cache" if cached else f"🗄️ Truy vấn Neo4j: {ms:.0f} ms")
    if not rows:
        st.info("Chưa có gợi ý phù hợp.")
    skip = {"movieId", "title"}
    for i, m in enumerate(rows, 1):
        extra = " · ".join(f"{k}: {v}" for k, v in m.items() if k not in skip and not isinstance(v, list))
        movie_card({"movieId": m["movieId"], "title": f"{i}. {m['title']}", "avgRating": None}, "rec", extra)


def page_profile(uid):
    header("👤 Hồ sơ", "Thông tin và thống kê hoạt động")
    target = st.session_state.pop("view_profile", None) or uid
    p = profile_service.get_profile(target)
    if not p:
        st.error("Không tìm thấy người dùng.")
        return
    st.header(p["name"])
    st.write(f"User ID: {p['userId']} · {p['city']} · {p['age']} tuổi")
    if target == uid:
        st.write(f"Email: {p['email']}")
    st.caption(f"Tham gia từ {p['createdAt']}")
    c = st.columns(5)
    c[0].metric("Đã xem", p["watched"])
    c[1].metric("Đánh giá", p["rated"])
    c[2].metric("Bình luận", p["comments"])
    c[3].metric("Bạn bè", p["friends"])
    c[4].metric("Điểm TB", p["avgRating"])
    if p["topGenres"]:
        st.write("**Thể loại yêu thích:** " + ", ".join(f"{g['genre']} ({g['n']})" for g in p["topGenres"]))


def page_query(uid):
    header("🧪 Truy vấn dữ liệu", "15 câu truy vấn Cypher và thời gian thực thi")
    qs = query_service.load_queries()
    n = st.selectbox("Chọn câu truy vấn", sorted(qs), format_func=lambda i: f"Câu {i}. {qs[i]['title']}")
    user_id = st.number_input("userId (cho các câu có tham số)", 1, value=int(uid))
    with st.expander("Xem câu Cypher"):
        st.code(qs[n]["cypher"], language="cypher")
    if st.button("▶ Chạy truy vấn", type="primary"):
        rows, ms = query_service.run_query_no(n, user_id)
        st.success(f"{len(rows)} dòng · Thời gian thực hiện: {ms:.1f} ms")
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)


def page_logout():
    header("🚪 Đăng xuất", "Kết thúc phiên làm việc")
    st.warning("Bạn có chắc muốn đăng xuất?")
    c1, c2, _ = st.columns([1, 1, 4])
    if c1.button("Đăng xuất", type="primary"):
        auth_service.logout(st.session_state)
        st.rerun()
    if c2.button("Hủy"):
        st.session_state["menu"] = M_HOME
        st.rerun()


# ---------- main ----------
def main():
    st.markdown(CSS, unsafe_allow_html=True)
    if not nc.ping():
        st.error("Không kết nối được Neo4j. Kiểm tra Neo4j đang chạy và thông tin trong file .env.")
        st.stop()
    if "user" not in st.session_state:
        page_auth()
        return
    uid = st.session_state["user"]["userId"]
    st.session_state.setdefault("menu", M_HOME)
    with st.sidebar:
        st.markdown('<div class="brand">🎬 Movie Recommender</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="userbox">👤 <b>{st.session_state["user"]["name"]}</b><br>'
                    f'<span class="muted">User ID: {uid}</span></div>', unsafe_allow_html=True)
        st.radio("Menu", MENU, key="menu", label_visibility="collapsed")
        st.caption("Redis: " + ("🟢 hoạt động" if rc.is_available() else "🔴 tắt"))
    pages = {M_HOME: page_home, M_LIST: page_list, M_SEARCH: page_search, M_DETAIL: page_detail,
             M_HIST: page_history, M_FRIEND: page_friends, M_REC: page_rec,
             M_PROFILE: page_profile, M_QUERY: page_query}
    menu = st.session_state["menu"]
    page_logout() if menu == M_LOGOUT else pages[menu](uid)


main()
