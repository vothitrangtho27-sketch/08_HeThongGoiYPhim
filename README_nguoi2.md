# Người 2 – Phần dữ liệu

1. py -m pip install -r requirements.txt
// py clear_db.py
2. py generate_data.py
3. py import_data.py
4. py verify_data.py


  NEO4J_PASSWORD= 12345678


Schema: User, Movie, Genre, Comment
RATED{rating,ratedAt}, WATCHED{watchedAt}, FRIEND{since} (1 chiều, truy vấn không hướng),
HAS_GENRE, (Comment {userId})-[:ABOUT]->(Movie)
Mật khẩu mặc định mọi user: 123456 (SHA-256). User 1: nguyenvana@gmail.com
