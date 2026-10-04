# DEPLOY — Render (backend) · Vercel (frontend) · PostgreSQL

> Owner: **R3**. Mọi bẫy dưới đây đã xảy ra thật khi vận hành; mỗi cái có cách phòng.

## 1. Kiến trúc triển khai

```
git push main ──► GitHub Actions (5 job) ──check qua──► Render: Docker backend (/health)
                                          └─check qua──► Vercel: Next.js (Deployment Checks)
backend ──► PostgreSQL (Supabase hoặc Postgres tự quản) — Alembic là nguồn schema duy nhất
```

Deploy **chỉ** xảy ra sau khi đủ năm check của `.github/workflows/ci.yml` xanh trên commit đó.

## 2. Biến môi trường

| Biến | Nơi đặt | Ghi chú |
|---|---|---|
| `APP_ENV=production` | Render | bật cổng cấu hình production |
| `DATABASE_URL` | Render (`sync: false`) | `postgresql+psycopg2://...`; Supabase: dùng **Session Pooler** (IPv4) — host kết nối trực tiếp chỉ có IPv6, mạng không route IPv6 sẽ báo "could not translate host name" |
| `JWT_SECRET` | Render (`sync: false`) | ≥ 32 ký tự; thiếu/mặc định thì dịch vụ KHÔNG lên (cố ý) |
| `CORS_ORIGINS` | Render | domain Vercel production, phân tách dấu phẩy |
| `CORS_ORIGIN_REGEX` | Render | chỉ khi cần preview; neo `^https://<dự-án>-[a-z0-9]+-<team>\.vercel\.app$` |
| `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY` | Render (`sync: false` cho khoá) | khoá không bao giờ tới frontend |
| `NEXT_PUBLIC_API_BASE_URL` | Vercel — **cả Production, Preview, Development** | gốc API không kèm `/api/v1`; thiếu thì bản dựng đổ (cố ý) |

## 3. Render (backend)

1. New → Blueprint → chọn repo → Render đọc `render.yaml`.
2. Điền các biến `sync: false`.
3. **Settings → Auto-Deploy → "After CI Checks Pass".** Trường `autoDeployTrigger: checksPass` trong blueprint chỉ
   áp cho dịch vụ mới dựng; dịch vụ có sẵn giữ thiết lập dashboard. Bật TRƯỚC khi `main` có CI chạy được thì
   backend không bao giờ deploy.
4. Container chạy `alembic upgrade head` rồi mới khởi động API — phù hợp gói một instance. Nhiều instance: tách
   migration thành bước release riêng (ADR).
5. Gói miễn phí ngủ sau ~15 phút không có request, cold start ~50 giây: frontend phải hiện trạng thái "đang khởi
   động"; trước buổi demo gọi `/health` để làm ấm.

## 4. Vercel (frontend)

1. Import repo, **Root Directory = `web`**.
2. Đặt `NEXT_PUBLIC_API_BASE_URL` cho cả ba môi trường (đã gặp: Production xanh, Preview đỏ
   liên tục vì biến chỉ đặt cho Production).
3. **Settings → Build and Deployment → Deployment Checks → GitHub**, chọn đủ: `guards`, `test`, `migration-postgres`,
   `docker-build`, `web`. Đổi tên job ở CI phải đổi ở đây cùng lúc (lưới canh nhắc).
4. `web/vercel.json` tắt deploy cho nhánh sổ claim `agent-claims`.

## 5. CSDL

- Alembic là nguồn schema duy nhất: không dùng migration của nền tảng song song, không tạo bảng bằng tay.
- CSDL production **không** dùng chung với máy phát triển. Nếu buộc phải dùng chung trong giai đoạn đầu: script
  ghi dữ liệu mặc định chạy thử, in host đích, cần `--apply`; test trỏ URL vào cổng chết (`tests/conftest.py`).
- Sao lưu trước mọi migration có `ALTER`/`DROP` trên dữ liệu thật; sao lưu không vào git.
- Hai head migration: `alembic merge`. **Không `alembic stamp`.**

## 6. Merge và deploy

- Merge bằng nút Merge của GitHub (merge commit/squash/rebase đều tạo commit mới). **Không** fast-forward thủ công
  vào `main`: commit từng nằm trên PR nháp mang sẵn check `skipped` — Render tính là QUA.
- Deploy tay ("Deploy latest commit") không chờ CI — chỉ dùng cho commit đã xanh. "Deploy a specific commit" TẮT
  auto-deploy của dịch vụ; dùng xong phải bật lại "After CI Checks Pass".

## 7. Quay lui

| Tình huống | Làm |
|---|---|
| Bản mới lỗi, schema không đổi | Render/Vercel → Rollback về deploy trước, rồi revert commit qua PR |
| Bản mới có migration | revert qua PR có migration đảo ngược (`downgrade` đã viết và đã thử); khôi phục sao lưu nếu mất dữ liệu |
| Lộ bí mật | thu hồi/xoay khoá NGAY trên nhà cung cấp → cập nhật biến trên Render/Vercel → rồi mới dọn repo |
| Dịch vụ cũ vẫn chạy ở tài khoản khác | cắt quyền CSDL của nó (đổi mật khẩu CSDL) — đã từng phải làm vậy |

## 8. Kiểm sau deploy

```bash
curl -fsS https://<backend>/health            # {"status":"ok","env":"production"}
curl -fsS https://<backend>/health/ready      # {"status":"ready"} — CSDL kết nối được
```

Mở frontend production, xác nhận trang gọi đúng backend (tab Network), không lỗi CORS.

## 9. Runner CI tự host (khi phút GitHub hết hoặc repo private)

Mọi job trong `ci.yml` chạy trên `${{ vars.CI_RUNNER || 'ubuntu-latest' }}`: không đặt biến thì dùng máy GitHub
(tốn phút), đặt biến thì dùng runner có nhãn đó. Đổi runner **không cần commit**.

**Dấu hiệu cần runner tự host:** job đỏ trong 2–3 giây, danh sách bước rỗng, annotation ghi *"job was not
started because recent account payments have failed or your spending limit needs to be increased"*. Đó là hạ
tầng, không phải mã — đọc annotation trước khi đọc code.

**Runner cấp repo không dùng chung được giữa hai repo cá nhân.** Muốn một máy phục vụ nhiều repo: cài thêm
một **instance** riêng cho mỗi repo (thư mục riêng, tên riêng, nhãn riêng) — hoặc chuyển các repo vào một
organization và đăng ký runner cấp org.

```bash
# 1. Token đăng ký (sống 1 giờ) — chạy trên máy có gh đăng nhập quyền admin repo:
gh api -X POST repos/<chủ>/<repo>/actions/runners/registration-token --jq .token

# 2. Trên máy runner, thư mục RIÊNG cho repo này (đã có instance khác thì chép bản cài, BỎ các file
#    .runner .credentials .credentials_rsaparams .service .env .path _work _diag của instance cũ):
./config.sh --unattended --url https://github.com/<chủ>/<repo> --token <TOKEN> \
  --name <tên-duy-nhất> --labels <nhãn-riêng> --work _work
sudo ./svc.sh install <user> && sudo ./svc.sh start

# 3. Trỏ CI sang runner — không cần commit:
gh variable set CI_RUNNER --body <nhãn-riêng> -R <chủ>/<repo>

# 4. Kiểm từ phía GitHub, rồi chạy lại một lượt:
gh api repos/<chủ>/<repo>/actions/runners --jq '.runners[] | {name, status, labels: [.labels[].name]}'
gh run rerun <run-id> -R <chủ>/<repo>
```

⚠️ **Nhiều instance trên cùng một máy phải chia chung trần tài nguyên**, không mỗi cái một trần. Với systemd:
drop-in `Slice=<slice-chung>` cho mọi unit runner (và docker/containerd) — nếu không, hai lượt CI song song có
thể bóp cạn RAM của máy chủ. Ví dụ cấu hình: `ci.slice` với `MemoryHigh=3G`/`MemoryMax=5G` sau khi đo thấy trần
cũ đẩy RAM khả dụng của máy chủ xuống rất thấp.

Runner trên máy cá nhân: máy tắt thì job **xếp hàng** tới khi máy bật (quá 24 giờ thì đỏ). Bật máy trước khi
bấm "Ready for review" hay merge.
