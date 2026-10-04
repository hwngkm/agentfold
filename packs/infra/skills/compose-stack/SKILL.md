---
name: compose-stack
description: Dựng hoặc sửa môi trường nhiều dịch vụ bằng Docker Compose cho dev, test và staging — CSDL riêng không bao giờ trỏ vào production, health check và thứ tự khởi động, volume dữ liệu tách khỏi mã, profile cho dịch vụ tuỳ chọn. Dùng khi thêm dịch vụ (CSDL, hàng đợi, vector DB, worker) vào môi trường cục bộ, khi `docker compose up` lỗi hoặc dịch vụ khởi động sai thứ tự, hoặc khi cần môi trường staging trên một máy.
---

# Docker Compose: một lệnh dựng lại được cả môi trường, và không bao giờ chạm production

Mẫu: `docker-compose.yml` (db Postgres 16 + backend + web). Mật khẩu trong đó được đặt tên
`local-only-not-a-secret` có chủ ý — chỉ dùng cho môi trường cục bộ.

## Thêm một dịch vụ

1. Image ghim tag cụ thể (`postgres:16-alpine`, không `latest`).
2. `healthcheck` cho mọi dịch vụ có trạng thái sẵn sàng; dịch vụ phụ thuộc dùng
   `depends_on: {db: {condition: service_healthy}}` — `depends_on` trơn chỉ chờ container KHỞI ĐỘNG, không chờ sẵn sàng.
3. Dữ liệu vào **volume có tên** (`db-data:`), không bind-mount thư mục trong repo (dễ lọt vào git; quyền file lệch
   trên Windows).
4. Dịch vụ chỉ cần đôi khi (worker cập nhật, công cụ quản trị) đặt dưới `profiles: [ten]` — `docker compose up`
   mặc định không bật chúng.
5. Chỉ publish cổng khi máy chủ cần gọi vào; giữa các dịch vụ dùng tên dịch vụ (`db:5432`).

## Bí mật và môi trường

- Giá trị thật đặt trong `.env` (đã gitignore), compose đọc bằng `${TEN_BIEN}`; mẫu ở `.env.example`.
- Không bao giờ để `DATABASE_URL` trong compose trỏ tới CSDL production — kể cả "để thử nhanh".

## Lệnh

```bash
docker compose up --build -d          # dựng + chạy nền
docker compose ps                     # cột STATUS phải "healthy"
docker compose logs -f backend        # đọc log một dịch vụ
docker compose --profile <ten> up -d <dich-vu>   # bật dịch vụ tuỳ chọn
docker compose down                   # dừng, GIỮ volume
docker compose down -v                # dừng và XOÁ volume — mất dữ liệu cục bộ, hỏi trước khi chạy
```

## Bẫy

| Bẫy | Sửa |
|---|---|
| Backend đổ "connection refused" lúc khởi động | thiếu `condition: service_healthy` |
| Đổi mã không có hiệu lực | quên `--build`, hoặc image cũ cùng tag |
| Ổ đĩa đầy dần | `docker system df`; dọn image/volume cũ có chủ đích (`docker image prune`) |
| Windows: Docker Desktop chiếm RAM/ổ C | giới hạn RAM WSL (`.wslconfig`), chuyển thư mục dữ liệu Docker sang ổ khác |
