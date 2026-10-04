---
id: EXM-01
title: Thêm endpoint xem báo giá nháp
state: ready
owner_role: R3
design_refs:
  - docs/design/ARCHITECTURE.md
  - docs/rules/10-domain-safety.md
depends_on: []
scope:
  allow:
    - src/api/routes/quotes.py
    - tests/unit/test_quotes_api.py
  exclusive: [api-contract]
  protected: []
acceptance:
  - "`GET /api/v1/quotes/{id}` trả báo giá nháp; mọi dòng tiền kèm `source` và `source_ref`"
  - "Người không có vai trò `reviewer` và không phải chủ báo giá nhận 404 (không lộ báo giá tồn tại)"
  - "`contracts/openapi.json` được cập nhật bằng `python scripts/export_openapi.py`"
  - "`make check` xanh; `python -m tools.agentctl check-scope` không vi phạm"
---
# EXM-01 — Thêm endpoint xem báo giá nháp

> Ticket MẪU để minh hoạ định dạng và bảng công việc. Dự án thật xoá hoặc thay bằng ticket của mình.

## Bối cảnh

Người duyệt cần xem báo giá nháp do agent sản phẩm (`src/agents/quote_agent.py`) tạo trước khi gửi
khách. Số tiền đã được lõi tất định tính (`src/domain/catalog/pricing.py`); endpoint chỉ đọc và trả về.

## Ngoài phạm vi

- Không tính lại hay làm tròn số tiền ở tầng API (RULE-1 miền mẫu: code miền tính, nơi khác chỉ hiển thị).
- Không thêm hành động gửi báo giá — đó là hành động HIGH, ticket riêng, cần cổng duyệt.

## Ghi chú cho người thực hiện

Ticket khai làn `api-contract` vì thêm endpoint làm đổi `contracts/openapi.json`. Nếu cần bảng mới
cho báo giá, DỪNG và mở câu hỏi: việc đó cần làn `db-migrations`, ticket này chưa được duyệt cho làn ấy.
