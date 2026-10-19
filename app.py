"""Hệ thống gợi ý phim - giao diện Streamlit. Chạy: streamlit run app.py"""
import pandas as pd
import streamlit as st

import config
import neo4j_connection as nc
import redis_connection as rc
from services import (auth_service, comment_service, friend_service, history_service,
                      movie_service, profile_service, recommendation_service, redis_service)

st.set_page_config(page_title=config.APP_TITLE, page_icon="🎬", layout="wide")

MENU = ["🏠 Trang chủ", "🎬 Danh sách phim", "🔍 Tìm kiếm", "⭐ Chi tiết phim", "🕘 Lịch sử xem",
        "👥 Bạn bè", "🎯 Gợi ý phim", "👤 Hồ sơ", "🚪 Đăng xuất"]
M_HOME, M_LIST, M_SEARCH, M_DETAIL, M_HIST, M_FRIEND, M_REC, M_PROFILE, M_LOGOUT = MENU
MENU_VISIBLE = [m for m in MENU if m != M_DETAIL]  # Chi tiết phim: chỉ mở khi bấm vào một bộ phim



CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');
:root {
    --pink: #E8336D; --pink-2: #FF6B9D; --plum: #2A0F2E; --plum-2: #4B1A47;
    --ink: #2D1B26; --muted: #8A6B7A; --line: #F6D3E0; --soft: #FFF0F5; --gold: #FFB020;
}
html, body, [class*="css"], [data-testid="stAppViewContainer"], .stMarkdown, button, input, textarea {
    font-family: 'Be Vietnam Pro', 'Segoe UI', sans-serif !important;}
#MainMenu, footer {visibility: hidden;}
[data-testid="stHeader"] {background: transparent;}
[data-testid="stAppViewContainer"] {
    background: radial-gradient(1200px 500px at 85% -10%, #FFD9E7 0%, transparent 60%),
                radial-gradient(900px 500px at -10% 110%, #FFE6F0 0%, transparent 60%), #FFF8FB;}
.block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1120px;}
h1, h2, h3 {color: var(--ink); letter-spacing: -.01em;}
h2, h3 {font-weight: 700 !important;}

/* ===== Sidebar ===== */
[data-testid="stSidebar"] {background: linear-gradient(185deg, var(--plum) 0%, var(--plum-2) 100%);
    min-width: 290px; max-width: 290px; transform: none !important; border-right: none;
    box-shadow: 6px 0 30px rgba(42,15,46,.25);}
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {display: none !important;}
[data-testid="stSidebar"] [role="radiogroup"] {gap: 3px;}
[data-testid="stSidebar"] [role="radiogroup"] label {width: 100%; padding: 11px 16px; border-radius: 14px;
    cursor: pointer; transition: all .18s ease; border: 1px solid transparent;}
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child,
[data-testid="stSidebar"] [role="radiogroup"] label > div:has(input) {display: none !important;}
[data-testid="stSidebar"] [role="radiogroup"] label p {color: #EBD3E4 !important; font-weight: 500; font-size: .95rem;}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {background: rgba(255,255,255,.09); transform: translateX(3px);}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: linear-gradient(90deg, var(--pink), var(--pink-2)); box-shadow: 0 6px 18px rgba(232,51,109,.45);}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {color: #fff !important; font-weight: 700;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"], [data-testid="stSidebar"] .stCaption {color: #CDB0C6 !important;}
.brand {display: flex; align-items: center; gap: 12px; font-size: 1.2rem; font-weight: 800; line-height: 1.15;
    color: #fff; padding: 6px 4px 14px; margin-bottom: 6px; border-bottom: 1px solid rgba(255,255,255,.12);}
.brand-ico {display: flex; align-items: center; justify-content: center; width: 46px; height: 46px; font-size: 1.5rem;
    border-radius: 14px; background: linear-gradient(135deg, var(--pink), var(--pink-2)); box-shadow: 0 6px 16px rgba(232,51,109,.5);}
.userbox {display: flex; align-items: center; gap: 12px; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.12);
    border-radius: 16px; padding: 10px 14px; margin: 10px 0 16px; color: #fff; font-size: .92rem;}
.userbox .muted {color: #CDB0C6;}
.notice {background: linear-gradient(90deg, rgba(255,107,157,.28), rgba(232,51,109,.22)); border: 1px solid rgba(255,255,255,.2);
    color: #fff; border-radius: 14px; padding: 9px 14px; margin: -6px 0 8px; font-size: .9rem;}
.avatar {width: 40px; height: 40px; min-width: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
    font-weight: 800; color: #fff; background: linear-gradient(135deg, #FF6B9D, #C2255C); box-shadow: 0 3px 10px rgba(0,0,0,.25);}
.avatar.big {width: 84px; height: 84px; min-width: 84px; font-size: 2.2rem;}

/* ===== Banner tiêu đề trang ===== */
.page-header {position: relative; overflow: hidden; color: #fff; border-radius: 22px; padding: 28px 34px; margin-bottom: 26px;
    background: linear-gradient(120deg, #C2255C 0%, #E8336D 45%, #FF8FB3 100%); box-shadow: 0 14px 34px rgba(232,51,109,.30);}
.page-header::before {content: ""; position: absolute; right: -50px; top: -70px; width: 240px; height: 240px; border-radius: 50%;
    background: rgba(255,255,255,.14);}
.page-header::after {content: ""; position: absolute; right: 110px; bottom: -90px; width: 190px; height: 190px; border-radius: 50%;
    background: rgba(255,255,255,.10);}
.page-header h1 {position: relative; z-index: 1; margin: 0; font-size: 1.85rem; font-weight: 800; color: #fff; padding: 0;}
.page-header p {position: relative; z-index: 1; margin: 6px 0 0; opacity: .94; font-size: 1rem;}

/* ===== Card ===== */
[data-testid="stVerticalBlockBorderWrapper"] {background: #fff; border: 1px solid var(--line) !important;
    border-radius: 18px !important; box-shadow: 0 2px 12px rgba(232,51,109,.07); transition: all .2s ease;}
[data-testid="stVerticalBlockBorderWrapper"]:hover {box-shadow: 0 10px 26px rgba(232,51,109,.16); transform: translateY(-2px);}
[data-testid="stMetric"] {background: #fff; border: 1px solid var(--line); border-radius: 18px; padding: 16px 20px;
    box-shadow: 0 2px 12px rgba(232,51,109,.07); border-left: 5px solid var(--pink);}
[data-testid="stMetricLabel"] p {color: var(--muted); font-weight: 600;}
[data-testid="stMetricValue"] {color: var(--pink); font-weight: 800;}
.poster {position: relative; width: 58px; height: 80px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
    color: #fff; font-size: 1.75rem; font-weight: 800; box-shadow: 0 6px 14px rgba(0,0,0,.18); text-shadow: 0 2px 6px rgba(0,0,0,.25);}
.poster::after {content: "▶"; position: absolute; bottom: 5px; right: 7px; font-size: .55rem; opacity: .75;}
.rank {display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 50%;
    font-weight: 800; color: #fff; background: linear-gradient(135deg, var(--pink), var(--pink-2)); box-shadow: 0 4px 12px rgba(232,51,109,.4);}
.rank.top1 {background: linear-gradient(135deg, #FFB020, #FF8A00);}
.rank.top2 {background: linear-gradient(135deg, #B0B8C4, #8793A3);}
.rank.top3 {background: linear-gradient(135deg, #D9934E, #B56A2A);}
.mtitle {font-size: 1.08rem; font-weight: 700; color: var(--ink); margin: 0 0 2px;}
.chip {display: inline-block; background: var(--soft); color: #B0245A; border: 1px solid var(--line); border-radius: 999px;
    padding: 2px 11px; font-size: .74rem; font-weight: 600; margin: 5px 5px 0 0;}
.badge {display: inline-block; background: #FFF4D6; color: #8A5A00; border-radius: 999px; padding: 3px 11px;
    font-size: .8rem; font-weight: 700; margin-top: 6px;}
.score {display: inline-block; background: linear-gradient(90deg, #FFF0F5, #FFE0EA); color: #B0245A; border-radius: 10px;
    padding: 3px 10px; font-size: .78rem; font-weight: 600; margin: 5px 5px 0 0;}
.muted {color: var(--muted); font-size: .84rem;}
.stars {display: inline-block; font-size: 1.35rem; line-height: 1; letter-spacing: 2px;}
.stars .on {color: #FFB020; text-shadow: 0 1px 2px rgba(255,160,0,.35);}
.stars .off {color: #E3E3E3;}
.detail-hero {display: flex; gap: 22px; align-items: center; background: #fff; border: 1px solid var(--line); border-radius: 22px;
    padding: 22px 26px; margin-bottom: 18px; box-shadow: 0 6px 20px rgba(232,51,109,.10);}
.detail-hero .poster {width: 96px; height: 134px; min-width: 96px; font-size: 3rem; border-radius: 16px;}
.detail-hero h2 {margin: 0 0 6px; font-size: 1.6rem;}
.profile-hero {display: flex; gap: 22px; align-items: center; background: #fff; border: 1px solid var(--line); border-radius: 22px;
    padding: 22px 26px; margin-bottom: 18px; box-shadow: 0 6px 20px rgba(232,51,109,.10);}
.profile-hero h2 {margin: 0 0 4px;}

/* ===== Nút & input ===== */
.stButton > button, .stFormSubmitButton > button {border-radius: 999px; border: 1.5px solid var(--pink-2); font-weight: 600;
    background: #fff; color: var(--pink); transition: all .16s ease; padding: .45rem 1.1rem;}
.stButton > button:hover {border-color: var(--pink); color: #fff; background: var(--pink); transform: translateY(-1px);
    box-shadow: 0 6px 14px rgba(232,51,109,.28);}
.stButton > button[kind^="primary"], .stFormSubmitButton > button[kind^="primary"],
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
    background: linear-gradient(90deg, #E8336D, #FF6B9D) !important; color: #fff !important; border: none !important;
    box-shadow: 0 6px 16px rgba(232,51,109,.35); padding: .6rem 1.2rem;}
[data-testid="stBaseButton-primary"] *, [data-testid="stBaseButton-primaryFormSubmit"] *, button[kind^="primary"] * {color: #fff !important;}
.stButton > button[kind^="primary"]:hover, .stFormSubmitButton > button[kind^="primary"]:hover,
[data-testid="stBaseButton-primaryFormSubmit"]:hover, [data-testid="stBaseButton-primary"]:hover {
    filter: brightness(1.07); transform: translateY(-1px); box-shadow: 0 10px 22px rgba(232,51,109,.42);}
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
    background: #fff !important; border: 1.5px solid #F3C6D6 !important; border-radius: 12px !important;}
[data-baseweb="input"] input, [data-baseweb="base-input"] input, textarea {background: transparent !important; color: var(--ink) !important;}
[data-baseweb="base-input"] {border: none !important;}
[data-testid="InputInstructions"] {display: none;}
input::placeholder, textarea::placeholder {color: #C9A3B3 !important;}
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within, [data-baseweb="textarea"]:focus-within {
    border-color: var(--pink) !important; box-shadow: 0 0 0 3px rgba(232,51,109,.15) !important;}
[data-testid="stTabs"] button[aria-selected="true"] {color: var(--pink); font-weight: 700;}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {background-color: var(--pink);}
[data-testid="stAlert"] {border-radius: 14px;}
[data-testid="stDataFrame"] {border-radius: 14px; overflow: hidden; border: 1px solid var(--line);}

/* ===== Đăng nhập ===== */
.auth-logo {width: 76px; height: 76px; margin: 28px auto 0; border-radius: 22px; display: flex; align-items: center;
    justify-content: center; font-size: 2.4rem; background: linear-gradient(135deg, #E8336D, #FF8FB3);
    box-shadow: 0 12px 28px rgba(232,51,109,.4);}
.auth-title {text-align: center; font-size: 2rem; font-weight: 800; margin: 14px 0 0;
    background: linear-gradient(90deg, #C2255C, #FF6B9D); -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
.auth-sub {text-align: center; color: var(--muted); margin-bottom: 20px; font-size: .95rem;}
</style>
"""


def header(title, sub=""):
    st.markdown(f'<div class="page-header"><h1>{title}</h1>' + (f"<p>{sub}</p>" if sub else "") + "</div>",
                unsafe_allow_html=True)


# ---------- tiện ích ----------
REC_LABELS = {
    "diemTongHop": "🎯 Điểm gợi ý: {}",
    "soNguoiTuongDongUngHo": "👥 {} người có gu giống bạn đã thích",
    "soNguoiTuongDong": "👥 {} người có gu giống bạn",
    "soBanUngHo": "🤝 {} bạn bè đã đánh giá cao",
    "diemTBTuBanBe": "⭐ Bạn bè chấm trung bình {}",
    "diemTB": "⭐ Điểm trung bình {}",
    "soLuotDanhGia": "💬 {} lượt đánh giá",
    "soTheLoaiLienQuan": "🏷️ {} thể loại hợp gu bạn",
}


def rec_extra(m):
    """Đổi các cột kết quả gợi ý thành nhãn dễ hiểu."""
    keys = [k for k in REC_LABELS if k in m and m[k] is not None]
    return [REC_LABELS[k].format(m[k]) for k in keys]


def on_nav():
    if st.session_state.get("nav"):
        st.session_state["page"] = st.session_state["nav"]


def go_movie(movie_id):
    st.session_state["selected_movie"] = int(movie_id)
    st.session_state["page"] = M_DETAIL


def go_profile(user_id):
    st.session_state["view_profile"] = int(user_id)
    st.session_state["page"] = M_PROFILE


def star_row(rating):
    """Hàng 5 sao: sao đã chấm màu vàng, phần còn lại màu xám."""
    n = int(round(rating or 0))
    n = max(0, min(5, n))
    return (f'<span class="stars" title="{n}/5 sao">'
            + '<span class="on">★</span>' * n + '<span class="off">★</span>' * (5 - n) + '</span>')


def stars(x):
    return "⭐" * int(round(x or 0)) if x else "Chưa có"


POSTER_COLORS = [("#C2255C", "#FF8FB3"), ("#7048E8", "#B197FC"), ("#1C7ED6", "#74C0FC"), ("#0CA678", "#63E6BE"),
                 ("#E8590C", "#FFA94D"), ("#AE3EC9", "#E599F7"), ("#D6336C", "#FFA8C5"), ("#364FC7", "#91A7FF")]


def poster_html(title, extra_class=""):
    t = (title or "?").lstrip("0123456789. ")
    letter = t[:1].upper() or "?"
    a, b = POSTER_COLORS[sum(map(ord, t)) % len(POSTER_COLORS)]
    return f'<div class="poster {extra_class}" style="background:linear-gradient(135deg,{a},{b})">{letter}</div>'


def movie_card(m, key, extra=None, rank=None):
    with st.container(border=True):
        if rank is not None:
            c_rank, c0, c1, c2 = st.columns([0.7, 0.9, 6, 1.6], vertical_alignment="center")
            cls = {1: "top1", 2: "top2", 3: "top3"}.get(rank, "")
            c_rank.markdown(f'<div class="rank {cls}">{rank}</div>', unsafe_allow_html=True)
        else:
            c0, c1, c2 = st.columns([0.9, 6, 1.6], vertical_alignment="center")
        c0.markdown(poster_html(m.get("title")), unsafe_allow_html=True)
        year = f" <span class='muted'>({m['year']})</span>" if m.get("year") else ""
        html = f'<p class="mtitle">{m["title"]}{year}</p>'
        html += "".join(f'<span class="chip">{g}</span>' for g in (m.get("genres") or []))
        if m.get("avgRating") is not None:
            html += f'<br><span class="badge">⭐ {m["avgRating"]}</span> <span class="muted">{m.get("ratingCount", 0)} lượt đánh giá</span>'
        if extra:
            if isinstance(extra, (list, tuple)):
                html += "<br>" + "".join(f'<span class="score">{e}</span>' for e in extra)
            else:
                html += f'<br><span class="muted">{extra}</span>'
        c1.markdown(html, unsafe_allow_html=True)
        c2.button("Xem chi tiết", key=f"{key}_{m['movieId']}", on_click=go_movie, args=(m["movieId"],), use_container_width=True)


# ---------- đăng nhập / đăng ký ----------
def page_auth():
    st.markdown("""<style>
    [data-testid="stVerticalBlockBorderWrapper"] {border-radius: 26px !important; box-shadow: 0 20px 50px rgba(232,51,109,.18) !important;
        transform: none !important; padding: 10px 14px 6px;}
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {
        box-shadow: none !important; border: none !important; padding: 0;}
    </style>""", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.5, 1])
    with mid:
        st.markdown('<div class="auth-logo">🎬</div><div class="auth-title">Hệ thống gợi ý phim</div>'
                    '<div class="auth-sub">Khám phá bộ phim tiếp theo dành riêng cho bạn</div>', unsafe_allow_html=True)
        with st.container(border=True):
            tab_login, tab_reg = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký"])
            with tab_login:
                with st.form("login", border=False):
                    email = st.text_input("Email", placeholder="ten@email.com")
                    pw = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu")
                    if st.form_submit_button("Đăng nhập", type="primary", use_container_width=True):
                        user = auth_service.login(email, pw)
                        if user:
                            st.session_state["user"] = user
                            st.session_state["page"] = M_HOME
                            redis_service.on_login(user["userId"])   # INCR số lần đăng nhập, ZADD online
                            st.rerun()
                        else:
                            st.error("Sai email hoặc mật khẩu.")
            with tab_reg:
                with st.form("register", border=False):
                    name = st.text_input("Họ và tên")
                    email = st.text_input("Email ", key="reg_email", placeholder="ten@email.com")
                    c1, c2 = st.columns(2)
                    age = c1.number_input("Tuổi", 10, 100, 20)
                    city = c2.text_input("Thành phố")
                    pw = st.text_input("Mật khẩu ", type="password", key="reg_pw")
                    if st.form_submit_button("Tạo tài khoản", type="primary", use_container_width=True):
                        ok, msg, _ = auth_service.register(name, email, pw, age, city)
                        (st.success if ok else st.error)(msg + (" Hãy chuyển sang tab Đăng nhập." if ok else ""))


# ---------- các trang ----------
def recent_ids(uid):
    """Nguồn dựng lại cache List: các phim đã xem gần nhất trong Neo4j."""
    return [h["movieId"] for h in history_service.get_history(uid, 10)]


def cached_movie(movie_id):
    """Thông tin phim lấy qua cache Redis kiểu Hash (cache-aside)."""
    m, _ = redis_service.movie_summary(movie_id, lambda: movie_service.get_movie(movie_id, -1))
    return m


def page_home(uid):
    user = st.session_state["user"]
    header("🏠 Trang chủ", f"Xin chào {user['name']}! Cùng khám phá phim hay hôm nay nhé 🍿")
    s = movie_service.stats()
    c = st.columns(4)
    c[0].metric("🎬 Phim", f"{s['movies']:,}")
    c[1].metric("👤 Người dùng", f"{s['users']:,}")
    c[2].metric("🏷️ Thể loại", f"{s['genres']:,}")
    c[3].metric("⭐ Đánh giá", f"{s['ratings']:,}")
    st.subheader("🔥 Gợi ý nhanh cho bạn")
    rows, ms, cached = recommendation_service.recommend(uid, "hybrid")
    st.caption("Lấy từ Redis cache" if cached else f"Truy vấn Neo4j: {ms:.0f} ms")
    if not rows:
        st.info("Chưa đủ dữ liệu để gợi ý. Hãy đánh giá thêm vài phim.")
    for i, m in enumerate(rows[:3], 1):
        movie_card(m, "home", rec_extra(m), rank=i)

    # --- dữ liệu lưu trên Redis: Sorted Set, List, Hash cache, bộ đếm ---
    online, logins = redis_service.count_online(), redis_service.login_count(uid)
    if online is not None:
        st.caption(f"🟢 {online} người đang online · Bạn đã đăng nhập {logins} lần (bộ đếm Redis)")
    top = redis_service.popular_movies(5)
    if top:
        st.subheader("🔥 Phim được xem nhiều nhất")
        st.caption("Bảng xếp hạng Redis Sorted Set (ZREVRANGE movie:popular)")
        for rank, (mid, views) in enumerate(top, 1):
            m = cached_movie(mid)
            if m:
                movie_card(m, "pop", [f"👁 {views} lượt xem"], rank=rank)
    recent = redis_service.recent_movies(uid, 5, lambda: recent_ids(uid))
    if recent:
        st.subheader("🕘 Bạn xem gần đây")
        st.caption("Cache Redis List (LPUSH + LTRIM giữ 10 phim; mất cache thì dựng lại từ lịch sử xem trong Neo4j)")
        for mid in recent:
            m = cached_movie(mid)
            if m:
                movie_card(m, "rcnt")


def page_list(uid):
    header("🎬 Danh sách phim", "Khám phá kho phim theo thể loại")
    genre_rows = movie_service.list_genres()
    genre_total = {g["name"]: g["n"] for g in genre_rows}
    genres = ["Tất cả"] + [g["name"] for g in genre_rows]
    c1, c2, c3 = st.columns([2, 2, 1])
    genre = c1.selectbox("Thể loại", genres)
    sort = c2.selectbox("Sắp xếp", list(movie_service.SORT_LABELS), format_func=movie_service.SORT_LABELS.get)
    g = None if genre == "Tất cả" else genre
    total = genre_total[g] if g else movie_service.stats()["movies"]
    pages = max(1, -(-total // config.PAGE_SIZE))
    page = c3.number_input(f"Trang (1-{pages})", 1, pages, 1)
    st.caption(f"{total:,} phim")
    for m in movie_service.list_movies(int(page), config.PAGE_SIZE, g, sort):
        movie_card(m, "list")


def page_search(uid):
    header("🔍 Tìm kiếm phim", "Tìm theo tên phim, năm phát hành hoặc thể loại")
    kw = st.text_input("Từ khóa", placeholder="Ví dụ: Matrix, 1999 hoặc Action")
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
    m = movie_service.get_movie(mid, uid)
    if not m:
        st.error("Không tìm thấy phim.")
        return
    seen = st.session_state.setdefault("viewed_movies", set())
    if mid not in seen:                                  # mỗi phiên chỉ tính một lượt xem cho mỗi phim
        views = redis_service.record_view(uid, mid, lambda: recent_ids(uid))
        seen.add(mid)
    else:
        views = redis_service.get_views(mid)
    view_txt = f" &nbsp;·&nbsp; 👁 {views} lượt xem" if views else ""
    chips = "".join(f'<span class="chip">{g}</span>' for g in m["genres"])
    st.markdown(f'<div class="detail-hero">{poster_html(m["title"])}<div><h2>{m["title"]}</h2>'
                f'<span class="muted">📅 {m["year"]} &nbsp;·&nbsp; ⏱️ {m["duration"]} phút{view_txt}</span><br>{chips}<br>'
                f'<span class="badge">⭐ {m["avgRating"]}</span> <span class="muted">{m["ratingCount"]} lượt đánh giá</span>'
                f'</div></div>', unsafe_allow_html=True)

    if st.button("✅ Đánh dấu đã xem"):
        n = history_service.mark_watched(uid, mid)
        st.success("Đã thêm vào lịch sử xem." if n == 1 else f"Bạn đã xem phim này {n} lần.")
    elif m.get("daXem"):
        st.caption("✔ Bạn đã xem phim này.")

    st.subheader("Đánh giá của bạn")
    mine = m.get("myRating")
    rating = st.radio("Chọn số sao", [1, 2, 3, 4, 5], index=(mine - 1) if mine else 4,
                      format_func=lambda x: "⭐" * x, horizontal=True)
    if st.button("Gửi đánh giá", type="primary"):
        res = movie_service.rate_movie(uid, mid, rating)
        redis_service.invalidate_movie(mid)              # điểm trung bình đã đổi: xóa Hash cache của phim
        redis_service.record_rating(uid)                 # HINCRBY user:{id}:stats ratings
        st.success("Đã lưu đánh giá." + (f" Điểm trung bình mới: {res['avgRating']} ({res['ratingCount']} lượt)." if res else ""))
        st.rerun()

    st.subheader("Bình luận")
    with st.form("cmt", clear_on_submit=True):
        text = st.text_area("Viết bình luận")
        if st.form_submit_button("Gửi bình luận") and comment_service.add_comment(uid, mid, text):
            st.rerun()
    for c in comment_service.get_comments(mid):
        with st.container(border=True):
            badge = star_row(c["rating"]) if c.get("rating") else '<span class="muted">Chưa chấm điểm</span>'
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px">'
                f'<div class="avatar">{(c["name"] or "?")[:1].upper()}</div>'
                f'<div><b>{c["name"]}</b> <span class="muted">· ID {c["userId"]} · {c["createdAt"]}</span><br>{badge}</div>'
                f'</div>', unsafe_allow_html=True)
            st.write(c["content"])

    related = movie_service.get_related_movies(mid)
    if related:
        st.subheader("🎞️ Phim tương tự")
        for r in related:
            movie_card(r, "rel", [f"🧬 Giống {int(r['doTuongTu'] * 100)}% về thể loại",
                                  f"👍 {r['nguoiCungThich']} người cùng thích cả hai"])


def page_history(uid):
    header("🕘 Lịch sử xem", "Những phim bạn đã xem")
    rows = history_service.get_history(uid)
    st.write(f"**Tổng phim đã xem:** {rows[0]['tongSoPhim'] if rows else 0}")
    with st.expander("📊 Thống kê xem phim theo tháng"):
        ms = history_service.monthly_stats(uid)
        if ms:
            st.dataframe(pd.DataFrame([{"Tháng": r["thang"], "Số phim": r["soPhim"], "Đã đánh giá": r["soDaDanhGia"],
                                        "Tổng thời lượng (giờ)": round((r["tongPhut"] or 0) / 60, 1),
                                        "Ví dụ": ", ".join(r["viDu"])} for r in ms]),
                         use_container_width=True, hide_index=True)
        else:
            st.caption("Chưa có dữ liệu.")
    for h in rows:
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"**{h['title']}** ({h['year']})")
            c1.caption(f"Xem ngày {h['watchedAt']} · Đánh giá của bạn: {stars(h['myRating'])}")
            c2.button("Xem", key=f"h_{h['movieId']}", on_click=go_movie, args=(h["movieId"],))


def page_friends(uid):
    header("👥 Bạn bè", "Quản lý mạng bạn bè của bạn")

    # --- lời mời kết bạn gửi đến: Chấp nhận / Từ chối ---
    incoming = friend_service.incoming_requests(uid)
    if incoming:
        st.subheader(f"📨 Lời mời kết bạn ({len(incoming)})")
        for r in incoming:
            with st.container(border=True):
                c0, c1, c2, c3 = st.columns([0.8, 4, 1.4, 1.2], vertical_alignment="center")
                c0.markdown(f'<div class="avatar">{(r["name"] or "?")[:1].upper()}</div>', unsafe_allow_html=True)
                c1.markdown(f"**{r['name']}** · ID {r['userId']} · {r['city']}  \n"
                            f"<span class='muted'>🤝 {r['banChung']} bạn chung · 🎬 {r['phimChung']} phim cùng đánh giá"
                            f" · gửi lúc {str(r['sentAt'])[:10]}</span>", unsafe_allow_html=True)
                if c2.button("✅ Chấp nhận", key=f"ra_{r['userId']}", type="primary", use_container_width=True):
                    friend_service.accept_request(uid, r["userId"])
                    redis_service.invalidate_friends(uid, r["userId"])
                    st.toast(f"Bạn và {r['name']} đã trở thành bạn bè.", icon="🎉")
                    st.rerun()
                if c3.button("Từ chối", key=f"rd_{r['userId']}", use_container_width=True):
                    friend_service.decline_request(uid, r["userId"])
                    st.rerun()

    # --- danh sách bạn bè ---
    friends = friend_service.list_friends(uid)
    fids = [f["userId"] for f in friends]
    redis_service.cache_friend_set(uid, fids)            # Redis Set friends:{id}
    online_ids = redis_service.online_friends(uid, fids)  # ZSCORE trên online:users
    st.subheader(f"Danh sách bạn bè ({len(friends)})")
    for f in friends:
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 1, 1])
            hop = (f"🎯 Hợp gu {int(f['hopGu'])}% ({f['phimChung']} phim chung)" if f.get("hopGu") is not None
                   else "🎯 Chưa có phim chung")
            dot = "🟢 " if f["userId"] in online_ids else ""
            c1.markdown(f"**{dot}{f['name']}**  \nUser ID: {f['userId']} · {f['city']}  \n"
                        f"<span class='muted'>{hop} · kết bạn từ {f['ketBanTu']}</span>", unsafe_allow_html=True)
            c2.button("Xem hồ sơ", key=f"fp_{f['userId']}", on_click=go_profile, args=(f["userId"],))
            if c3.button("❌ Xóa", key=f"fd_{f['userId']}"):
                friend_service.remove_friend(uid, f["userId"])
                redis_service.invalidate_friends(uid, f["userId"])
                st.rerun()

    # --- lời mời mình đã gửi ---
    outgoing = friend_service.outgoing_requests(uid)
    if outgoing:
        st.subheader(f"⏳ Lời mời đã gửi ({len(outgoing)})")
        for r in outgoing:
            c1, c2 = st.columns([5, 1.4], vertical_alignment="center")
            c1.markdown(f"**{r['name']}** (ID {r['userId']}) · {r['city']}  \n"
                        f"<span class='muted'>Đang chờ phản hồi · gửi lúc {str(r['sentAt'])[:10]}</span>", unsafe_allow_html=True)
            if c2.button("Hủy lời mời", key=f"rc_{r['userId']}", use_container_width=True):
                friend_service.cancel_request(uid, r["userId"])
                st.rerun()

    # --- gợi ý kết bạn ---
    st.subheader("✨ Có thể bạn quen")
    for u in friend_service.suggest_friends(uid):
        c1, c2 = st.columns([5, 1.4], vertical_alignment="center")
        c1.markdown(f"**{u['name']}** (ID {u['userId']}) · {u['city']}  \n"
                    f"<span class='muted'>🤝 {u['banChung']} bạn chung · 🎬 {u['phimChung']} phim cùng đánh giá"
                    f"{' · 📍 cùng thành phố' if u['cungThanhPho'] else ''}</span>", unsafe_allow_html=True)
        if c2.button("➕ Kết bạn", key=f"fs_{u['userId']}", use_container_width=True):
            friend_service.send_request(uid, u["userId"])
            st.toast(f"Đã gửi lời mời đến {u['name']}.", icon="📨")
            st.rerun()

    # --- tìm và gửi lời mời ---
    st.subheader("Thêm bạn")
    kw = st.text_input("Tìm theo tên hoặc User ID")
    if kw.strip():
        for u in friend_service.search_users(kw, uid):
            c1, c2 = st.columns([5, 1.4], vertical_alignment="center")
            c1.markdown(f"{u['name']} (ID {u['userId']}) · {u['city']} "
                        f"<span class='muted'>· 🤝 {u['banChung']} bạn chung</span>", unsafe_allow_html=True)
            if u["isFriend"]:
                c2.write("✔ Đã là bạn")
            elif u["daGuiLoiMoi"]:
                c2.write("⏳ Đã gửi lời mời")
            elif u["coLoiMoiDen"]:
                if c2.button("✅ Chấp nhận", key=f"sa_{u['userId']}", type="primary", use_container_width=True):
                    friend_service.accept_request(uid, u["userId"])
                    st.rerun()
            elif c2.button("➕ Kết bạn", key=f"fa_{u['userId']}", use_container_width=True):
                friend_service.send_request(uid, u["userId"])
                st.toast(f"Đã gửi lời mời đến {u['name']}.", icon="📨")
                st.rerun()


def page_rec(uid):
    header("🎯 Gợi ý phim", "Gợi ý cá nhân hóa dựa trên đồ thị Neo4j")
    labels = dict(recommendation_service.METHODS)
    method = st.radio("Phương pháp", list(labels), format_func=labels.get, horizontal=True, index=3)
    use_cache = st.toggle("Dùng Redis cache", value=True, disabled=not rc.is_available())
    if not rc.is_available():
        st.caption("⚠️ Redis không chạy: kết quả luôn lấy trực tiếp từ Neo4j.")
    rows, ms, cached = recommendation_service.recommend(uid, method, use_cache)
    st.caption("⚡ Lấy từ Redis cache" if cached else f"🗄️ Truy vấn Neo4j: {ms:.0f} ms")
    if not rows:
        st.info("Chưa có gợi ý phù hợp.")
    for i, m in enumerate(rows, 1):
        movie_card({"movieId": m["movieId"], "title": m["title"], "avgRating": None,
                    "genres": m.get("theLoaiPhuHop")}, "rec", rec_extra(m), rank=i)


def page_profile(uid):
    header("👤 Hồ sơ", "Thông tin và thống kê hoạt động")
    target = st.session_state.pop("view_profile", None) or uid
    p = profile_service.get_profile(target)
    if not p:
        st.error("Không tìm thấy người dùng.")
        return
    email = f"<br><span class='muted'>✉️ {p['email']}</span>" if target == uid else ""
    st.markdown(f'<div class="profile-hero"><div class="avatar big">{(p["name"] or "?")[:1].upper()}</div><div>'
                f'<h2>{p["name"]}</h2><span class="muted">User ID: {p["userId"]} · 📍 {p["city"]} · {p["age"]} tuổi</span>'
                f'{email}<br><span class="muted">Tham gia từ {p["createdAt"]}</span></div></div>', unsafe_allow_html=True)
    c = st.columns(5)
    c[0].metric("Đã xem", p["watched"])
    c[1].metric("Đánh giá", p["rated"])
    c[2].metric("Bình luận", p["comments"])
    c[3].metric("Bạn bè", p["friends"])
    c[4].metric("Điểm TB", p["avgRating"])
    if p["topGenres"]:
        st.markdown("**Thể loại yêu thích:**<br>" + "".join(f'<span class="chip">{g["genre"]} ({g["n"]})</span>' for g in p["topGenres"]),
                    unsafe_allow_html=True)


def page_logout():
    header("🚪 Đăng xuất", "Kết thúc phiên làm việc")
    st.warning("Bạn có chắc muốn đăng xuất?")
    c1, c2, _ = st.columns([1, 1, 4])
    if c1.button("Đăng xuất", type="primary"):
        redis_service.on_logout(st.session_state["user"]["userId"])   # ZREM online:users
        auth_service.logout(st.session_state)
        st.rerun()
    if c2.button("Hủy"):
        st.session_state["page"] = M_HOME
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
    redis_service.touch_online(uid)
    st.session_state.setdefault("page", M_HOME)
    page = st.session_state["page"]
    # đồng bộ menu bên trái với trang hiện tại (đang ở Chi tiết phim thì không mục nào được chọn)
    st.session_state["nav"] = page if page in MENU_VISIBLE else None
    with st.sidebar:
        st.markdown('<div class="brand"><span class="brand-ico">🎬</span><span>Hệ thống<br>gợi ý phim</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="userbox"><div class="avatar">{(st.session_state["user"]["name"] or "?")[:1].upper()}</div>'
                    f'<div><b>{st.session_state["user"]["name"]}</b><br><span class="muted">User ID: {uid}</span></div></div>', unsafe_allow_html=True)
        pending = friend_service.count_requests(uid)
        if pending:
            st.markdown(f'<div class="notice">📨 Bạn có <b>{pending}</b> lời mời kết bạn</div>', unsafe_allow_html=True)
            st.button("Xem lời mời", key="to_requests", on_click=lambda: st.session_state.update(page=M_FRIEND),
                      use_container_width=True)
        st.radio("Menu", MENU_VISIBLE, key="nav", index=None, label_visibility="collapsed", on_change=on_nav)
        st.caption("Redis: " + ("🟢 hoạt động" if rc.is_available() else "🔴 tắt"))
    pages = {M_HOME: page_home, M_LIST: page_list, M_SEARCH: page_search, M_DETAIL: page_detail,
             M_HIST: page_history, M_FRIEND: page_friends, M_REC: page_rec,
             M_PROFILE: page_profile}
    page_logout() if page == M_LOGOUT else pages[page](uid)


main()
