---
name: deploy-gate
description: Giữ cổng "chỉ deploy commit đã qua CI" khi đổi CI, nền tảng deploy hoặc cách merge — chờ mọi check, không để check `skipped` thành đường tắt, merge bằng nút Merge, đường lùi đã thử. Dùng khi cấu hình deploy tự động mới, khi thêm/đổi tên job CI, khi deploy tay, khi một commit đỏ lỡ lên production, hoặc khi chuẩn bị quay lui.
---

# Cổng deploy: production chỉ nhận commit đã xanh

Tình huống gốc (đã xảy ra thật): một commit có test cổng duyệt ĐỎ vẫn lên production vì nền tảng deploy
không chờ CI. Cổng gồm ba phần, thiếu một là hở: **nền tảng chờ check** · **mọi check tồn tại ngay từ đầu** ·
**không có check `skipped` đi kèm commit lên main**.

## Kiểm cổng (chạy khi nghi ngờ hoặc sau mỗi thay đổi CI/deploy)

| Kiểm | Cách | Đúng khi |
|---|---|---|
| Render chờ CI | `render.yaml` có `autoDeployTrigger: checksPass` VÀ dashboard → Settings → Auto-Deploy = "After CI Checks Pass" | cả hai (trường blueprint chỉ áp cho dịch vụ mới) |
| Vercel chờ CI | Project → Settings → Deployment Checks chọn đủ job của `ci.yml` | danh sách khớp tên job hiện tại |
| Job không `needs` | `python -m pytest tests/guards/test_deploy_waits_for_ci.py -q` | xanh |
| Bảo vệ nhánh | `gh api repos/<chủ>/<repo>/branches/main/protection` | không trả 403/404 (403 = không có bảo vệ) |

## Merge

Merge bằng nút Merge của nền tảng (tạo commit mới). Không fast-forward tay vào `main`: commit từng nằm trên PR nháp
mang sẵn check `skipped`, nền tảng deploy tính là QUA (R50.8). Đẩy thẳng `main` cũng gặp đúng rủi ro này khi
commit đã có check `skipped` từ trước.

## Deploy tay

Chỉ cho commit **đã xanh** trên CI. Render "Deploy a specific commit" TẮT auto-deploy — bật lại
"After CI Checks Pass" ngay sau đó (`docs/DEPLOY.md` §6).

## Đường lùi — chuẩn bị TRƯỚC khi cần

- Bản không đổi schema: Rollback trên Render/Vercel, rồi revert qua PR.
- Bản có migration: `downgrade` phải được viết VÀ chạy thử (`alembic downgrade -1` trên CSDL thử) trước khi
  merge; mất dữ liệu thì khôi phục từ sao lưu (`docs/DEPLOY.md` §7).
- Thay đổi rủi ro cao: bật sau cờ tính năng để tắt được mà không deploy lại.

## Sau deploy

`curl -fsS https://<backend>/health` và `/health/ready`; mở frontend, xem tab Network gọi đúng backend, không lỗi
CORS (`docs/DEPLOY.md` §8). Commit đỏ đã lên production: quay lui trước, điều tra sau, ghi `new incident`
(skill `incident`).
