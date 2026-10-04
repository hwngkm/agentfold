---
name: project-audit
description: Audit định kỳ sức khoẻ toàn dự án, chỉ đọc — thiết kế còn khớp code, mọi bất biến còn lưới canh đỏ được, quy trình (claim bỏ dở, câu hỏi tồn, bàn giao chưa nhận), phụ thuộc có lỗ hổng, bí mật, test bị skip, tài liệu nói sai, chi phí — báo cáo xanh/vàng/đỏ theo từng mảng kèm bằng chứng và phát hiện có định tuyến. Dùng khi tới một mốc phát hành hoặc theo định kỳ (vd. cuối sprint), trước khi bàn giao dự án, khi nhận một dự án đang chạy, hoặc khi cảm thấy "mọi thứ xanh" nhưng không chắc.
---

# Audit dự án: CI xanh không có nghĩa là dự án khoẻ

CI chỉ kiểm điều đã được viết thành lưới canh. Audit tìm thứ **chưa** được viết: lưới đã mục, tài liệu đã cũ, quy trình
đã lệch. Audit **chỉ đọc** — không sửa gì trong lúc audit (như vai trò `supervisor`/`critic`); sửa là ticket sau.

## Chạy theo mảng (lệnh thật của template)

| Mảng | Kiểm | Lệnh / cách |
|---|---|---|
| **Cơ bản** | mọi kiểm của CI xanh trên máy | `python scripts/ci_local.py` |
| **Thiết kế ↔ code** | sơ đồ sinh, hợp đồng API, migration khớp model | `python scripts/generate_diagrams.py --check` · `python scripts/export_openapi.py --check` · `check_migration_matches_models.py` (Postgres) |
| | ADR `Accepted` còn đúng với code? | đọc từng ADR, tìm code trái (`grep` theo quyết định) |
| | sơ đồ người vẽ còn đúng? (lưới không kiểm) | đối chiếu `HAND-DRAWN` với code/hạ tầng hiện tại (skill `diagram-roadmap`) |
| **Lưới canh còn sống** | mỗi bất biến trỏ test tồn tại | `python -m pytest tests/guards/test_invariants_registry.py -q` |
| | lưới vẫn đỏ được | chọn ngẫu nhiên 3 lưới, phá tạm điều chúng bảo vệ, thấy đỏ, khôi phục (skill `guard-net`) |
| | test bị tắt | `grep -rnE "pytest.mark.skip\|xfail\|test.skip\|retries:" tests web/e2e web/playwright.config.ts` |
| **Quy trình** | claim quá hạn, ticket `ready` không ai làm, câu hỏi mở lâu, bàn giao chưa nhận | `python -m tools.agentctl board` |
| | commit ngoài phạm vi ticket, thông điệp sai | vai trò `supervisor` trên khoảng `<mốc audit trước>..HEAD` |
| **Phụ thuộc** | lỗ hổng đã biết | `pip-audit -r requirements.txt` · `cd web && npm audit --omit=dev` |
| | công cụ ghim quá cũ | so `requirements-dev.txt`, `package.json` với bản phát hành hiện tại |
| **Bí mật & dữ liệu** | file cấm, khoá trong cấu hình | `python scripts/check_structure.py` · `python -m pytest tests/guards/test_mcp_no_secrets.py -q` |
| **Bảo mật** | mô hình đe doạ còn đúng | skill `security-audit` (đầy đủ ở mốc lớn, rút gọn ở mốc nhỏ) |
| **Tài liệu** | đường dẫn chết, README hứa điều chưa làm | `python -m pytest tests/guards/test_doc_references.py -q`; đọc mục "Giới hạn" của README so với thực tế |
| **Yêu cầu** | yêu cầu "phải có" thiếu test | bảng truy vết của skill `design-tables` |
| **Chi phí** | phút CI, API, hạ tầng so ngân sách | skill `cost-guard` |

## Chấm

Mỗi mảng: 🟢 không phát hiện · 🟡 phát hiện không chặn phát hành · 🔴 chặn phát hành hoặc vi phạm bất biến. Mảng không
kiểm được (thiếu quyền, thiếu Postgres) ghi **"chưa kiểm"** — không ghi 🟢.

## Đầu ra

```markdown
# Audit <ngày> — mốc <tên> (<commit>)
| Mảng | Kết quả | Bằng chứng (lệnh + kết quả rút gọn) |
## Phát hiện
<khối `findings:` đúng định dạng của coordination/roles/critic.md — mỗi phát hiện có route>
## Không kiểm được và vì sao
## So với audit trước: đã đóng / còn mở / mới
```

Lưu bằng `python -m tools.agentctl new log --role Rn --title "Audit <mốc>"`; phát hiện 🔴 → `new incident` hoặc ticket.
Phát hiện lặp lại ở hai lần audit liên tiếp → đề xuất lưới canh để máy kiểm thay người.
