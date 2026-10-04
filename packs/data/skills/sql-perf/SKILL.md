---
name: sql-perf
description: Làm truy vấn PostgreSQL nhanh bằng bằng chứng — đo truy vấn thật chậm, đọc EXPLAIN (ANALYZE, BUFFERS), đặt index theo mẫu truy vấn thật, bắt N+1 từ ORM, và xác nhận cải thiện bằng số đo trước/sau trên dữ liệu đủ lớn. Dùng khi một endpoint hay báo cáo chậm, khi thêm truy vấn mới trên bảng lớn, khi định thêm index, hoặc khi log cho thấy số câu SQL mỗi request tăng bất thường.
---

# Hiệu năng SQL: đo trước, sửa sau, đo lại

## 1. Tìm đúng truy vấn chậm

- Đo ở tầng request trước (độ trễ P95 theo endpoint — skill `observability`), rồi mới xuống SQL.
- Bật log câu SQL trong môi trường dev (SQLAlchemy `echo=True` hoặc logger `sqlalchemy.engine`) và đếm **số câu mỗi
  request**: số câu tăng theo số dòng trả về = N+1.
- Trên Postgres: extension `pg_stat_statements` cho biết truy vấn nào tốn tổng thời gian nhiều nhất.

## 2. Đọc kế hoạch thực thi

```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;   -- chạy thật; với câu ghi dữ liệu, bọc trong BEGIN; ... ROLLBACK;
```

Đọc tìm: `Seq Scan` trên bảng lớn với điều kiện lọc chọn lọc · số dòng ước lượng lệch xa số dòng thật (thống kê
cũ → `ANALYZE ten_bang`) · `Sort`/`Hash` tràn ra đĩa · vòng `Nested Loop` lặp nhiều lần.

Đo trên **PostgreSQL với dữ liệu cỡ gần thật** — SQLite và bảng 100 dòng cho kế hoạch khác hẳn production.
CLI `psql` (pack này kiểm trên PATH) là đường ngắn nhất.

## 3. Sửa theo thứ tự rẻ

1. **N+1:** tải kèm (`selectinload`/`joinedload` trong SQLAlchemy) hoặc một truy vấn gộp.
2. **Chỉ lấy cột cần**, phân trang bằng khoá (`WHERE id > :last ORDER BY id LIMIT n`) thay vì `OFFSET` lớn.
3. **Index theo truy vấn thật:** cột trong `WHERE`/`JOIN`/`ORDER BY`; index nhiều cột theo thứ tự lọc bằng → lọc
   khoảng → sắp xếp; index một phần (`WHERE trang_thai = 'cho_duyet'`) cho tập con hay truy vấn. Mỗi index làm
   chậm ghi và tốn chỗ — không thêm "cho chắc".
4. Index mới đi qua migration (skill `db-migration`), trên bảng lớn dùng `CREATE INDEX CONCURRENTLY`.

## 4. Chứng minh

Ghi trước/sau: thời gian thực thi trong `EXPLAIN ANALYZE` (chạy vài lần, bỏ lần đầu nguội cache), số câu SQL mỗi
request, P95 endpoint. Cải thiện nhỏ hơn dao động giữa các lần chạy thì chưa chứng minh được gì.
