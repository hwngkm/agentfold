---
name: deploy-targets
description: Đưa backend, frontend hoặc bản demo lên một nền tảng cụ thể (Render, Vercel, Docker Compose trên VPS sau nginx, Hugging Face Spaces) — biến môi trường, health check, CSDL, tên miền, và cách quay lui cho từng nơi. Dùng khi lần đầu deploy một dịch vụ, khi chuyển nền tảng, khi thêm môi trường staging, hoặc khi deploy xong mà dịch vụ không lên.
---

# Nơi deploy: chọn theo việc, không theo thói quen

Mặc định của template: backend trên **Render** (`render.yaml`), frontend trên **Vercel** (`web/vercel.json`),
PostgreSQL quản lý (`docs/DEPLOY.md`). Các nơi khác dùng khi có lý do — ghi lý do thành DEC.

## Chọn nơi

| Nhu cầu | Nơi | Lưu ý chính |
|---|---|---|
| API + CSDL quản lý, ít vận hành | Render | `autoDeployTrigger: checksPass`; gói miễn phí ngủ khi rảnh (cold start) |
| Frontend Next.js | Vercel | Root Directory = `web`; `NEXT_PUBLIC_*` nhúng lúc build — đổi là phải build lại |
| Dữ liệu không được rời máy chủ tổ chức, hoặc cần GPU/RAM riêng | Docker Compose trên VPS + nginx | bạn tự lo TLS, sao lưu, cập nhật bảo mật |
| Demo công khai mô hình/ứng dụng AI | Hugging Face Spaces (Docker) | không cho dữ liệu thật; bí mật đặt trong Settings → Secrets |

## Thủ tục chung (mọi nơi)

1. **Biến môi trường:** liệt kê từ `.env.example`; bí mật đặt trên dashboard/kho bí mật, không trong git
   (`sync: false` trên Render). Cổng `src/core/production_gate.py` đổ khi thiếu — đọc thông điệp, đừng tắt cổng.
2. **Health check:** nền tảng trỏ `/health` (sống) — `/health/ready` cho kiểm sau deploy (CSDL kết nối được).
3. **CSDL:** migration chạy lúc khởi động (`alembic upgrade head` trong `CMD` của `Dockerfile`). Một bản chạy
   migration; nhiều bản song song thì tách bước migrate ra lệnh pre-deploy.
4. **Chờ CI** (skill `deploy-gate`) — áp cho mọi nơi tự deploy từ git.
5. **Kiểm sau deploy** theo `docs/DEPLOY.md` §8; ghi URL, commit, giờ vào nhật ký (`new log`).

## Docker Compose trên VPS

- Hai tệp: `docker-compose.yml` (dev) và một tệp deploy riêng chỉ chứa dịch vụ chạy production, image đã build
  sẵn theo tag commit — không `build:` trên máy chủ.
- nginx làm reverse proxy + TLS (Let's Encrypt); chỉ mở 80/443, CSDL không publish cổng ra ngoài.
- Script deploy: kéo image theo tag → `docker compose up -d` → chờ `/health` → không lên thì quay về tag trước.
  Viết test cho script (chạy được với `--dry-run`) trước khi tin nó.
- Sao lưu CSDL tự động và đã **thử khôi phục** ít nhất một lần.

## Hugging Face Spaces (Docker)

- `README.md` của Space có YAML đầu tệp với `sdk: docker` và `app_port` (cổng app lắng nghe).
- Bí mật: Space Settings → Secrets (đọc qua biến môi trường), không commit vào repo Space.
- Space công khai = ai cũng gọi được: giới hạn tốc độ, không chứa dữ liệu thật, ghi rõ "bản demo".

## Quay lui

Render/Vercel: Rollback trên dashboard. VPS: `docker compose up -d` với tag trước. Space: revert commit trên repo
Space. Có migration: xem skill `deploy-gate` — downgrade phải được thử trước.
