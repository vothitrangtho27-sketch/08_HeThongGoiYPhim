# Hệ thống gợi ý phim

Hệ thống gợi ý phim dùng **Neo4j** (đồ thị) + **Redis** (cache) + **Streamlit** (giao diện).

## Yêu cầu
- Python 3.10+, **Neo4j 5.x** (cần cho cú pháp `COUNT { }` / `EXISTS { }`), Redis (không bắt buộc).

## Cài đặt
```bash
pip install -r requirements.txt
cp .env.example .env      # rồi sửa NEO4J_PASSWORD
```

## Quy mô dữ liệu
| Loại | Số lượng | | Loại | Số lượng |
|---|---|---|---|---|
| User | 10.000 | | Friend | 10.000 |
| Movie | 8.000 | | Comment | 10.000 |
| Genre | 2.000 | | Movie–Genre | 20.000 |
| Rating | 40.000 | | Watched | 20.000 |

Tổng: 30.000 node (User, Movie, Genre, Comment) và 100.000 relationship
(RATED, WATCHED, FRIEND, HAS_GENRE, ABOUT). Comment có 1 quan hệ `ABOUT` tới Movie, mã người viết lưu ở thuộc tính `userId`.

## Dữ liệu
```bash
python generate_data.py   # (tuỳ chọn) sinh lại CSV trong data/
python clear_db.py        # (tuỳ chọn) xoá database
python import_data.py     # import CSV vào Neo4j
python verify_data.py     # kiểm tra sau import
```

## Chạy ứng dụng
```bash
python -m streamlit run app.py
```
Tài khoản thử: `nguyenvana@gmail.com` / mật khẩu `123456` (User 1).
(Nếu mật khẩu khác, kiểm tra trong `generate_data.py`.)

## Redis
Redis không bắt buộc: nếu không chạy, ứng dụng bỏ qua cache và lấy dữ liệu trực tiếp từ Neo4j
(Redis tắt giữa chừng được phát hiện qua PING mỗi giây; sau khi bật lại, kết nối được thử lại sau 30 giây, không cần khởi động lại ứng dụng).

| Khóa | Kiểu | TTL | Dùng cho |
|---|---|---|---|
| `stats:overview` | String (JSON) | 120 s | Thống kê trang chủ |
| `genres:all` | String (JSON) | 3600 s | Danh mục thể loại |
| `rec:{userId}:{method}` | String (JSON) | 300 s | Kết quả gợi ý |
| `movie:{id}` | Hash | 300-360 s | Cache thông tin phim (chống Avalanche / Penetration / Breakdown) |
| `movie:{id}:views` | String | - | Bộ đếm lượt xem (INCR) |
| `movie:popular` | Sorted Set | - | Bảng xếp hạng phim xem nhiều |
| `user:{id}:recent` | List | 7 ngày | 10 phim xem gần nhất |
| `user:{id}:stats` | Hash | - | Số lượt xem / đánh giá |
| `user:{id}:login:count` | String | - | Số lần đăng nhập |
| `online:users` | Sorted Set | - | Người đang online (score = thời điểm hoạt động) |
| `friends:{id}` | Set | 300-360 s | Tập bạn bè (SINTER / SUNION / SDIFF) |

Chạy bản minh họa các lệnh Redis (chỉ cần Redis, không cần Neo4j):
- `python redis_demo.py`: gọi các hàm của chương trình trên **dữ liệu thật trong `data/`** (phim, lượt WATCHED, bạn bè của người dùng 1), thay Neo4j bằng việc đọc CSV. Nếu Redis đang có dữ liệu, script dừng lại và yêu cầu đặt `REDIS_DB=1`; cuối chương trình xóa các khóa nó tạo ra.
- `python redis_commands_demo.py`: gọi lệnh Redis trực tiếp (phim 1, người dùng 1, 91). **Script này xóa các khóa `movie:1`, `movie:popular`, `online:users`, `user:1:*`...**; nếu Redis đang chứa dữ liệu thật, đặt `REDIS_DB=1` trong `.env` trước khi chạy.

## Cấu trúc
- `app.py` giao diện · `config.py` cấu hình · `neo4j_connection.py`, `redis_connection.py` kết nối · `redis_demo.py` minh họa Redis
- `services/` xử lý nghiệp vụ: auth, movie, comment, history, friend, recommendation, profile, redis (`redis_service.py`)
- Các truy vấn Cypher nằm trong từng file của `services/` (gợi ý phim: `recommendation_service.py`)
