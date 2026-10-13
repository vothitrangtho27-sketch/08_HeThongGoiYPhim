# movie-recommender-nosql

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
streamlit run app.py
```
Tài khoản thử: `nguyenvana@gmail.com` / mật khẩu `123456` (User 1).
(Nếu mật khẩu khác, kiểm tra trong `generate_data.py`.)

## Benchmark
```bash
python benchmark_neo4j.py 1 5   # userId=1, mỗi câu chạy 5 lần
```
Kết quả in ra màn hình và lưu vào `benchmark_result.csv`; có thêm so sánh Neo4j vs Redis cache.

## Cấu trúc
- `app.py` giao diện · `config.py` cấu hình · `neo4j_connection.py`, `redis_connection.py` kết nối
- `services/` xử lý nghiệp vụ: auth, movie, comment, history, friend, recommendation, profile, query
- `queries_15.cypher` 15 câu truy vấn (nguồn duy nhất, `query_service.py` đọc từ file này)
