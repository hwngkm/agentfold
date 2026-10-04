"""agentctl — mặt phẳng điều phối cho nhiều AI agent (khác nhà cung cấp) cùng làm một repo.

Bốn việc, mỗi việc một module:

- `claims`  — sổ claim nguyên tử trên nhánh git mồ côi: ai đang giữ ticket/phạm vi nào.
- `scope`   — so thay đổi thật (diff) với phạm vi ticket đã được người duyệt trên nhánh gốc.
- `entries` — sinh nhật ký/quyết định/câu hỏi/sự cố thành từng file riêng (không file dùng chung).
- `board`   — bảng trạng thái suy ra từ ticket + claim + lịch sử `main` (không ai sửa tay).

Chạy: `python -m tools.agentctl --help`. Quy trình đầy đủ: `docs/rules/70-multi-agent-coordination.md`.
"""
