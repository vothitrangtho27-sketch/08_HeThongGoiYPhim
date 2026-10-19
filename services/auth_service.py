"""Tài khoản người dùng: đăng ký, đăng nhập, kiểm tra thông tin."""
import hashlib
import re

from neo4j_connection import run_query


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def register(name, email, password, age, city):
    """Trả (ok, thông báo, user). Kiểm tra email trùng và tạo tài khoản trong CÙNG một truy vấn."""
    name, email, city = name.strip(), email.strip().lower(), city.strip()
    if not name or not email or not password:
        return False, "Vui lòng nhập đầy đủ họ tên, email và mật khẩu.", None
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return False, "Email không hợp lệ.", None
    if len(password) < 6:
        return False, "Mật khẩu tối thiểu 6 ký tự.", None
    rows = run_query("""
        OPTIONAL MATCH (e:User {email: $email})
        WITH e WHERE e IS NULL
        CALL {
            MATCH (m:User)
            RETURN coalesce(max(m.userId), 0) + 1 AS newId
        }
        CREATE (u:User {userId: newId, name: $name, email: $email, age: $age, city: $city,
                        password: $pw, createdAt: toString(date()), loginCount: 0})
        RETURN u.userId AS userId, u.name AS name, u.email AS email, u.age AS age, u.city AS city
    """, {"name": name, "email": email, "age": int(age), "city": city, "pw": hash_password(password)})
    if not rows:  # email đã tồn tại nên truy vấn không tạo gì
        return False, "Email đã được đăng ký.", None
    return True, "Tạo tài khoản thành công.", rows[0]


def login(email, password):
    """Trả user dict hoặc None. Đồng thời ghi nhận lần đăng nhập và thống kê hoạt động."""
    rows = run_query("""
        MATCH (u:User {email: $e, password: $pw})
        SET u.loginCount = coalesce(u.loginCount, 0) + 1, u.lastLoginAt = toString(datetime())
        RETURN u.userId AS userId, u.name AS name, u.email AS email, u.age AS age, u.city AS city,
               u.loginCount AS loginCount,
               COUNT { (u)-[:RATED]->(:Movie) } AS soDanhGia,
               COUNT { (u)-[:WATCHED]->(:Movie) } AS soDaXem
    """, {"e": email.strip().lower(), "pw": hash_password(password)})
    return rows[0] if rows else None


def logout(session_state):
    for k in list(session_state.keys()):
        del session_state[k]
