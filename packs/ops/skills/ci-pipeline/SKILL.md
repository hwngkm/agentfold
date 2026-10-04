---
name: ci-pipeline
description: Thêm, sửa hoặc gỡ lỗi CI (GitHub Actions) mà không phá các cổng an toàn của template — job độc lập không `needs`, bỏ qua PR nháp, cache phụ thuộc, mỗi lệnh CI có bản phản chiếu trong scripts/ci_local.py, đọc log job đỏ trước khi chạy lại. Dùng khi thêm bước/job vào .github/workflows, khi CI đỏ mà cục bộ xanh, khi CI chậm hoặc tốn phút, hoặc khi đổi tên job.
---

# CI: nhanh, trung thực, phản chiếu được trên máy

Luật cấu trúc nằm ở đầu `.github/workflows/ci.yml` và R50.5–R50.7; lưới canh
`tests/guards/test_deploy_waits_for_ci.py` và `tests/guards/test_ci_local_mirror.py` khoá chúng. Skill này là
thủ tục để đổi CI mà không vi phạm.

## Thêm một bước kiểm

1. Thêm `run:` vào job phù hợp (`guards` cho kiểm tĩnh/lưới canh, `test` cho test ứng dụng, `web` cho frontend).
2. Thêm **đúng chuỗi lệnh đó** vào `CI_COMMANDS` trong `scripts/ci_local.py` (hoặc vào danh sách miễn, kèm lý do).
3. `python -m pytest tests/guards/test_ci_local_mirror.py -q` → xanh.
4. `python scripts/ci_local.py` → xanh trên máy TRƯỚC khi đẩy.

## Thêm một job

- Điều kiện `if:` duy nhất được phép: bỏ qua PR nháp (chép nguyên dòng `if:` của job khác).
- **Không `needs`.** Job cần kết quả job khác thì gộp bước vào một job, hoặc dùng artifact trong cùng job.
- `timeout-minutes` bắt buộc; `runs-on: ${{ vars.CI_RUNNER || 'ubuntu-latest' }}` để đổi runner không cần commit.
- Thêm tên job mới vào Vercel Deployment Checks (và Render chờ mọi check) — tên job là hợp đồng (R50.7).
- `permissions:` tối thiểu; mặc định workflow là `contents: read`.

## CI đỏ

1. `gh run list --branch <nhánh> --limit 5` → `gh run view <id> --log-failed`. ĐỌC log trước.
2. Cục bộ xanh mà CI đỏ: so ba thứ hay lệch — múi giờ (CI `TZ=UTC`), file chưa commit (`git status`), phiên bản
   công cụ (ruff/mypy được ghim trong `requirements-dev.txt`).
3. Lỗi hạ tầng (runner, mạng) → sửa hạ tầng hoặc chạy lại MỘT lần có ghi lý do. Lỗi code → sửa code.
   Không `continue-on-error`, không tắt bước.

## Nhanh và rẻ

- PR ở chế độ nháp trong lúc làm: mọi job bỏ qua (0 phút). "Ready for review" ⇒ CI chạy đủ một lần (R50.6).
- `concurrency` với `cancel-in-progress: true` đã có: đẩy liên tiếp thì lượt cũ bị huỷ.
- Cache phụ thuộc bằng tham số `cache:` của `actions/setup-python` / `actions/setup-node`, khoá theo lockfile.
- `paths-ignore` cho tài liệu đã có; đừng thêm `paths` lọc khiến thay đổi code bị bỏ qua.
- Hết phút GitHub: runner tự host theo `docs/DEPLOY.md` §9 — máy RIÊNG cho CI (R50.10).

## Sau khi sửa CI

Ghi vào PR: bước nào thêm/bớt, đã chạy `scripts/ci_local.py` (kết quả), đã cập nhật Deployment Checks chưa.
