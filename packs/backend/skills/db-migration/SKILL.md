---
name: db-migration
description: Đổi schema CSDL an toàn — model và migration Alembic trong cùng PR, đọc lại file autogenerate, giữ đồ thị một head, kiểm model khớp migration trên PostgreSQL thật, downgrade đã thử, và đổi schema không khoá bảng lớn hay mất dữ liệu. Dùng khi thêm/sửa bảng hoặc cột, khi CI báo nhiều head hay lệch migration, khi migration đổ lúc deploy, hoặc khi cần đổi kiểu/tên cột đang có dữ liệu.
---

# Migration: schema chỉ đổi qua migration, và migration phải chạy trên Postgres thật

Bất biến INV-008: một head; schema chỉ đổi qua migration. Làn độc quyền `db-migrations` (`alembic/versions/`) —
ticket đổi schema khai `exclusive: [db-migrations]`, nên hai migration song song không thể xảy ra.

## Thủ tục

1. Sửa/thêm model trong `src/db/models/` (thêm bảng = thêm module, tự khám phá).
2. Sinh migration: `alembic revision --autogenerate -m "them cot x vao bang y"`.
3. **ĐỌC LẠI file sinh ra.** Autogenerate bỏ sót hoặc đoán sai: đổi tên cột (nó sinh drop + add = MẤT dữ liệu),
   ràng buộc CHECK, enum, index có điều kiện, kiểu tuỳ chỉnh. Sửa tay cho đúng ý.
4. Viết `downgrade()` thật, không để `pass`.
5. Chạy trên Postgres thật (compose có sẵn):
   ```bash
   docker compose up -d db
   alembic upgrade head && alembic downgrade -1 && alembic upgrade head
   python scripts/check_migration_matches_models.py --dsn postgresql+psycopg2://app:local-only-not-a-secret@localhost:5432/app
   python -m pytest tests/guards/test_migrations.py -q
   ```
6. CI job `migration-postgres` lặp lại bước 5; job `guards` kiểm một head.

## Đổi schema đang có dữ liệu (mở rộng → chuyển → thu hẹp)

Không đổi trực tiếp một cột đang dùng. Chia nhiều PR/deploy:

1. **Mở rộng:** thêm cột/bảng mới, cho phép NULL; code ghi cả hai nơi.
2. **Chuyển:** migration dữ liệu (theo lô nếu bảng lớn); code đọc nơi mới.
3. **Thu hẹp:** khi không còn ai đọc nơi cũ, migration gỡ cột cũ / đặt NOT NULL.

Bảng lớn: tạo index bằng `CREATE INDEX CONCURRENTLY` (trong Alembic cần `autocommit_block()`); tránh thêm cột NOT
NULL có default tính toán trên bảng lớn trong một bước.

## Nhiều head

Sinh ra do hai nhánh cùng thêm migration (không nên xảy ra nếu làn độc quyền được tôn trọng). Sửa:
`alembic merge -m "gop head" <rev1> <rev2>`, kiểm lại bước 5. **Không** `alembic stamp` để chữa head (R70.12).

## Dữ liệu seed

Seed nghiệp vụ không nằm trong migration schema; nếu buộc phải có, migration dữ liệu riêng, có `source`/`source_ref`
(R40.2) và chạy được nhiều lần không nhân bản dòng.
