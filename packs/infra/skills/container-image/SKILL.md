---
name: container-image
description: Viết hoặc sửa Dockerfile cho dịch vụ — build nhiều tầng, chạy bằng user không phải root, ghim phiên bản, image chỉ chứa mã chạy, health check, build tái lập được và kiểm bằng chạy thật. Dùng khi thêm dịch vụ mới cần container, khi image quá lớn hoặc build chậm, khi container chạy trên máy dev nhưng đổ trên nền tảng, hoặc khi thêm phụ thuộc hệ thống.
---

# Image container: nhỏ, không root, dựng lại được

Mẫu đã có: `Dockerfile` (backend, hai tầng, `appuser`, `HEALTHCHECK` gọi `/health`) và `web/Dockerfile`. Job CI
`docker-build` build image ở mỗi PR — image không build được thì CI đỏ trước khi tới nền tảng deploy.

## Thủ tục

1. **Tầng build và tầng chạy tách nhau.** Tầng build cài trình biên dịch/công cụ; tầng chạy chỉ chép kết quả
   (site-packages, `.next/standalone`). Không chép `tests/`, `docs/`, `tools/` vào tầng chạy.
2. **Ghim phiên bản:** image gốc theo tag cụ thể (`python:3.11-slim`, không `latest`); phụ thuộc theo lockfile.
3. **Thứ tự lớp theo tần suất đổi:** chép file phụ thuộc → cài → rồi mới chép mã nguồn, để đổi mã không cài lại
   phụ thuộc.
4. **Không root:** `useradd` + `USER`. Cài phụ thuộc vào chỗ user chạy đọc được (bài học trong `Dockerfile`:
   `--user` cài vào `/root`, thư mục 0700, user khác không đọc được).
5. **Không bí mật trong image:** không `COPY .env`, không `ARG` chứa khoá (giá trị `ARG` nằm lại trong lịch sử
   image). Bí mật vào lúc chạy qua biến môi trường. Kiểm `.dockerignore` loại `.env*`, `.git`, `data/`.
6. **Health check** gọi endpoint thật bằng công cụ có sẵn trong image (vd. Python `urllib`) — không cài `curl` chỉ
   để kiểm sức khoẻ.
7. **Cổng từ biến môi trường** (`${PORT:-8000}`): nhiều nền tảng tự đặt `PORT`.

## Kiểm bằng chạy thật

```bash
docker build -t app:dev .
docker run --rm -e APP_ENV=development -p 8000:8000 app:dev &   # hoặc docker compose up --build
curl -fsS http://127.0.0.1:8000/health
docker image ls app:dev                                         # ghi kích thước trước/sau khi tối ưu
docker run --rm app:dev id                                      # phải KHÔNG phải uid=0
```

## Bẫy

| Bẫy | Sửa |
|---|---|
| Chạy được trên máy, đổ trên nền tảng | so kiến trúc CPU (`--platform linux/amd64`), biến môi trường thiếu, cổng cứng |
| Image vài GB | thường do cache pip/npm, công cụ build ở tầng chạy, hoặc chép nhầm `data/` |
| Build lại toàn bộ mỗi lần | `COPY . .` đứng trước bước cài phụ thuộc |
| Cài thư viện hệ thống không ghim | ghim gói hoặc ghi rõ lý do không ghim |
