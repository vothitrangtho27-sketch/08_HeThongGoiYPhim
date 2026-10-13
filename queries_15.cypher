// 15 CÂU TRUY VẤN CYPHER - movie-recommender-nosql
// Schema: (User)-[:RATED{rating}]->(Movie), (User)-[:WATCHED]->(Movie),
//         (User)-[:FRIEND]->(User) (một chiều, truy vấn dùng vô hướng), (Movie)-[:HAS_GENRE]->(Genre)
// Các câu 1,2,3,5,11-15 dùng userId = 1; đổi số để thử người khác.

// ======== 👤 SINH VIÊN 1 – USER VÀ QUAN HỆ XÃ HỘI ========

// Câu 1. Danh sách bạn bè trực tiếp
MATCH (u:User {userId: 1})-[:FRIEND]-(f:User)
RETURN DISTINCT f.userId AS maNguoiDung, f.name AS hoTen
ORDER BY maNguoiDung;

// Câu 2. Bạn của bạn trong phạm vi 2 cấp
MATCH p = (u:User {userId: 1})-[:FRIEND*1..2]-(f:User)
WHERE f <> u
RETURN f.userId AS maNguoiDung, f.name AS hoTen, min(length(p)) AS capKetNoi
ORDER BY capKetNoi, maNguoiDung;

// Câu 3. Người dùng có sở thích phim tương đồng
MATCH (u:User {userId: 1})-[r1:RATED]->(m:Movie)<-[r2:RATED]-(o:User)
WHERE o <> u AND r1.rating >= 4 AND r2.rating >= 4
WITH o, count(m) AS soPhimChung
WHERE soPhimChung >= 2
RETURN o.userId AS maNguoiDung, o.name AS hoTen, soPhimChung
ORDER BY soPhimChung DESC, maNguoiDung;

// Câu 4. Thống kê mức độ hoạt động của người dùng
MATCH (u:User)
OPTIONAL MATCH (u)-[:RATED]->(m1:Movie)
WITH u, count(DISTINCT m1) AS soPhimDanhGia
OPTIONAL MATCH (u)-[:WATCHED]->(m2:Movie)
WITH u, soPhimDanhGia, count(DISTINCT m2) AS soPhimDaXem
RETURN u.userId AS maNguoiDung, u.name AS hoTen,
       soPhimDanhGia, soPhimDaXem,
       soPhimDanhGia + soPhimDaXem AS diemHoatDong
ORDER BY diemHoatDong DESC, maNguoiDung
LIMIT 20;

// Câu 5. Bạn bè (tối đa 2 cấp) có cùng sở thích phim
MATCH (u:User {userId: 1})-[:FRIEND*1..2]-(f:User)
WHERE f <> u
WITH DISTINCT u, f
MATCH (u)-[r1:RATED]->(m:Movie)<-[r2:RATED]-(f)
WHERE r1.rating >= 4 AND r2.rating >= 4
WITH f, collect(m.title) AS dsPhimChung, count(m) AS soPhimChung
WHERE soPhimChung >= 2
RETURN f.userId AS maNguoiDung, f.name AS hoTen, dsPhimChung, soPhimChung
ORDER BY soPhimChung DESC, maNguoiDung;

// ======== 👤 SINH VIÊN 2 – MOVIE, GENRE VÀ PHÂN TÍCH DỮ LIỆU ========

// Câu 6. Phim được nhiều người đánh giá cao
MATCH (:User)-[r:RATED]->(m:Movie)
WITH m,
     count(CASE WHEN r.rating >= 4 THEN 1 END) AS soNguoiDanhGiaCao,
     avg(r.rating) AS diemTB
WHERE soNguoiDanhGiaCao > 0
RETURN m.movieId AS maPhim, m.title AS tenPhim,
       soNguoiDanhGiaCao, round(diemTB, 2) AS diemTB
ORDER BY soNguoiDanhGiaCao DESC, diemTB DESC
LIMIT 20;

// Câu 7. Thể loại được yêu thích nhiều nhất
MATCH (g:Genre)<-[:HAS_GENRE]-(m:Movie)<-[r:RATED]-(:User)
RETURN g.genreId AS maTheLoai, g.name AS tenTheLoai,
       count(DISTINCT CASE WHEN r.rating >= 4 THEN m END) AS soPhimDuocYeuThich,
       count(r) AS tongLuotDanhGia,
       round(avg(r.rating), 2) AS diemTB
ORDER BY soPhimDuocYeuThich DESC, diemTB DESC;

// Câu 8. Phim thuộc từ 2 thể loại trở lên
MATCH (m:Movie)-[:HAS_GENRE]->(g:Genre)
WITH m, collect(g.name) AS dsTheLoai
WHERE size(dsTheLoai) >= 2
RETURN m.movieId AS maPhim, m.title AS tenPhim,
       dsTheLoai, size(dsTheLoai) AS soTheLoai
ORDER BY soTheLoai DESC, tenPhim;

// Câu 9. Phim đã xem nhưng chưa đánh giá
MATCH (u:User)-[:WATCHED]->(m:Movie)
WHERE NOT (u)-[:RATED]->(m)
RETURN m.movieId AS maPhim, m.title AS tenPhim,
       count(u) AS soNguoiXemChuaDanhGia
ORDER BY soNguoiXemChuaDanhGia DESC, tenPhim;

// Câu 10. Phim nhiều lượt xem nhưng điểm đánh giá thấp
MATCH (m:Movie)
WITH m, size([(m)<-[:WATCHED]-() | 1]) AS soLuotXem
WHERE soLuotXem >= 3
MATCH (m)<-[r:RATED]-(:User)
WITH m, soLuotXem, count(r) AS soLuotDanhGia, avg(r.rating) AS diemTB
WHERE soLuotDanhGia >= 2 AND diemTB < 3
RETURN m.movieId AS maPhim, m.title AS tenPhim,
       soLuotXem, soLuotDanhGia, round(diemTB, 2) AS diemTB
ORDER BY soLuotXem DESC, diemTB ASC;

// ======== 👤 SINH VIÊN 3 – TRUY VẤN GỢI Ý PHIM ========

// Câu 11. Gợi ý phim dựa trên người dùng tương đồng
MATCH (u:User {userId: 1})-[r1:RATED]->(m:Movie)<-[r2:RATED]-(s:User)
WHERE s <> u AND r1.rating >= 4 AND r2.rating >= 4
WITH u, s, count(m) AS soPhimChung
WHERE soPhimChung >= 2
MATCH (s)-[r3:RATED]->(c:Movie)
WHERE r3.rating >= 4
  AND NOT (u)-[:RATED]->(c)
  AND NOT (u)-[:WATCHED]->(c)
RETURN c.movieId AS maPhim, c.title AS tenPhim,
       count(DISTINCT s) AS soNguoiTuongDongUngHo
ORDER BY soNguoiTuongDongUngHo DESC, tenPhim
LIMIT 10;

// Câu 12. Gợi ý phim dựa trên bạn bè
MATCH (u:User {userId: 1})-[:FRIEND*1..2]-(f:User)
WHERE f <> u
WITH DISTINCT u, f
MATCH (f)-[r:RATED]->(m:Movie)
WHERE r.rating >= 4
  AND NOT (u)-[:RATED]->(m)
  AND NOT (u)-[:WATCHED]->(m)
RETURN m.movieId AS maPhim, m.title AS tenPhim,
       count(DISTINCT f) AS soBanUngHo,
       round(avg(r.rating), 2) AS diemTBTuBanBe
ORDER BY soBanUngHo DESC, diemTBTuBanBe DESC, tenPhim
LIMIT 10;

// Câu 13. Gợi ý phim theo thể loại yêu thích
MATCH (u:User {userId: 1})-[r:RATED]->(m:Movie)-[:HAS_GENRE]->(g:Genre)
WHERE r.rating >= 4
WITH u, g, count(DISTINCT m) AS soPhimYeuThich
ORDER BY soPhimYeuThich DESC, g.name
LIMIT 3
WITH u, collect(g) AS theLoaiYeuThich
MATCH (c:Movie)-[:HAS_GENRE]->(g2:Genre)
WHERE g2 IN theLoaiYeuThich
  AND NOT (u)-[:RATED]->(c)
  AND NOT (u)-[:WATCHED]->(c)
WITH c, collect(DISTINCT g2.name) AS theLoaiPhuHop
OPTIONAL MATCH (c)<-[r2:RATED]-(:User)
WITH c, theLoaiPhuHop, count(r2) AS soLuotDanhGia, coalesce(avg(r2.rating), 0) AS diemTB
RETURN c.movieId AS maPhim, c.title AS tenPhim, theLoaiPhuHop,
       soLuotDanhGia, round(diemTB, 2) AS diemTB
ORDER BY size(theLoaiPhuHop) DESC, diemTB DESC, soLuotDanhGia DESC
LIMIT 10;

// Câu 14. Người dùng tương đồng nhất với User 1
MATCH (u:User {userId: 1})-[r1:RATED]->(m:Movie)<-[r2:RATED]-(s:User)
WHERE s <> u AND r1.rating >= 4 AND r2.rating >= 4
WITH s, collect(m.title) AS dsPhimChung, count(m) AS soPhimChung
WHERE soPhimChung >= 2
MATCH (s)-[rs:RATED]->(:Movie)
RETURN s.userId AS maNguoiDung, s.name AS hoTen,
       dsPhimChung, soPhimChung,
       round(avg(rs.rating), 2) AS diemTBNguoiDung
ORDER BY soPhimChung DESC, diemTBNguoiDung DESC
LIMIT 10;

// Câu 15. Xếp hạng phim ứng viên bằng điểm tổng hợp
// Thể loại User 1 yêu thích (từng chấm >= 4 sao)
MATCH (u:User {userId: 1})-[r:RATED]->(:Movie)-[:HAS_GENRE]->(lg:Genre)
WHERE r.rating >= 4
WITH u, collect(DISTINCT lg) AS theLoaiYeuThich

// Người dùng tương đồng
MATCH (u)-[r1:RATED]->(m:Movie)<-[r2:RATED]-(s:User)
WHERE s <> u AND r1.rating >= 4 AND r2.rating >= 4
WITH u, theLoaiYeuThich, s, count(m) AS soPhimChung
WHERE soPhimChung >= 2

// Phim ứng viên chưa xem / chưa đánh giá
MATCH (s)-[r3:RATED]->(c:Movie)
WHERE r3.rating >= 4
  AND NOT (u)-[:RATED]->(c)
  AND NOT (u)-[:WATCHED]->(c)
WITH theLoaiYeuThich, c, count(DISTINCT s) AS soNguoiTuongDong

// Yếu tố 2: điểm trung bình của phim
MATCH (c)<-[r4:RATED]-(:User)
WITH theLoaiYeuThich, c, soNguoiTuongDong, avg(r4.rating) AS diemTB

// Yếu tố 3: số thể loại của phim trùng thể loại User 1 yêu thích
OPTIONAL MATCH (c)-[:HAS_GENRE]->(g:Genre)
WHERE g IN theLoaiYeuThich
WITH c, soNguoiTuongDong, diemTB, count(g) AS soTheLoaiLienQuan

RETURN c.movieId AS maPhim, c.title AS tenPhim,
       soNguoiTuongDong, round(diemTB, 2) AS diemTB, soTheLoaiLienQuan,
       round(0.5 * soNguoiTuongDong + 0.3 * diemTB + 0.2 * soTheLoaiLienQuan, 3) AS diemTongHop
ORDER BY diemTongHop DESC, tenPhim
LIMIT 10;

