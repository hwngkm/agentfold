---
id: ABC-01
title: Tên việc ngắn, bắt đầu bằng động từ
state: proposed          # proposed → ready (NGƯỜI duyệt đặt) · cancelled. `done` được suy ra, không ghi tay.
owner_role: R1           # vai trò CON NGƯỜI chịu trách nhiệm kết quả
design_refs:             # thiết kế mà việc này phải tuân theo — agent đọc trước khi làm
  - docs/design/ARCHITECTURE.md
depends_on: []           # ticket phải merge trước; claim bị chặn nếu chưa thấy trên main
scope:
  allow:                 # file được tạo/sửa. Hẹp nhất có thể — scope rộng thì không ai làm song song được.
    - src/api/routes/abc.py
    - tests/unit/test_abc.py
  exclusive: []          # tên làn độc quyền trong coordination/policy.yaml, vd. [db-migrations, api-contract]
  protected: []          # id vùng bảo vệ được DUYỆT TRƯỚC cho ticket này, vd. [design]
acceptance:              # tiêu chí kiểm được bằng lệnh/test — "xong" nghĩa là tất cả đều đúng
  - "`pytest tests/unit/test_abc.py` xanh, có ca hợp lệ và ca biên"
  - "`python -m tools.agentctl check-scope` không vi phạm"
---
# ABC-01 — Tên việc

> File bắt đầu bằng `_` không phải ticket thật (bộ kiểm bỏ qua). Tạo ticket mới:
> `python -m tools.agentctl new ticket --id ABC-01 --title "..." --role R1`

## Bối cảnh

Vì sao cần việc này; liên kết PRD/ADR/câu hỏi đã trả lời.

## Đặc tả (nếu ticket đổi hành vi quan sát được)

Ghi yêu cầu mới/đổi/bỏ vào `docs/design/specs/changes/<ID>-<năng-lực>.md` (mục `## ADDED|MODIFIED|REMOVED Requirements`,
mỗi yêu cầu có `SHALL` + kịch bản `WHEN/THEN` + `**Test:**`). `docs/design/` là vùng bảo vệ: khai `protected: [design]` (đừng
đưa đường dẫn vào `scope.allow` — bị từ chối nếu lấn vùng). Sau khi merge: `python -m tools.agentctl spec archive <ID>-<năng-lực>`. Chi tiết: `docs/design/specs/README.md`.

## Ngoài phạm vi

Điều người làm KHÔNG được làm trong ticket này (để agent không "tiện tay").

## Ghi chú cho người thực hiện

Bẫy đã biết, dữ liệu mẫu, người cần hỏi khi vướng.

## Cập nhật

(Người duyệt thêm MỘT mục có ngày mỗi lần đổi yêu cầu SAU khi ticket đã `ready`, thay vì sửa lặng lẽ phần
trên: `### DD/MM/YYYY — thay đổi gì, vì sao`. Agent đọc cả phần này — yêu cầu mới nhất ở đây thắng yêu cầu cũ
phía trên. Đổi `scope`/`acceptance` trong front matter vẫn cần duyệt như thường. Nguồn: một dự án thực tế, nơi task
dài ngày bị đổi tiêu chí giữa chừng và agent kế tiếp chỉ đọc bản đầu.)
