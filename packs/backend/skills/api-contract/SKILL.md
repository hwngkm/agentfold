---
name: api-contract
description: Đổi API mà không phá bên gọi — thêm/sửa endpoint theo hợp đồng contracts/openapi.json, phân biệt thay đổi tương thích và phá vỡ, sinh lại bản chụp trong làn độc quyền api-contract, cập nhật client frontend cùng lúc. Dùng khi thêm hoặc sửa endpoint, đổi schema request/response, đổi mã lỗi, hoặc khi frontend và backend lệch nhau về trường dữ liệu.
---

# Hợp đồng API: bản chụp là luật, đổi nó là quyết định có chủ ý

`contracts/openapi.json` là thứ backend và frontend cùng dựa vào. CI chạy `python scripts/export_openapi.py --check`
(lưới `tests/guards/test_openapi_contract.py`): ứng dụng lệch bản chụp là đỏ. File nằm trong làn độc quyền
`api-contract` — ticket đổi API phải khai `exclusive: [api-contract]`.

## Thủ tục

1. **Phân loại thay đổi** trước khi viết code:

   | Tương thích (an toàn) | Phá vỡ (cần kế hoạch) |
   |---|---|
   | thêm endpoint mới | xoá/đổi tên endpoint hoặc trường |
   | thêm trường **tuỳ chọn** vào request | thêm trường **bắt buộc** vào request |
   | thêm trường vào response | đổi kiểu trường, đổi nghĩa giá trị |
   | thêm mã lỗi mới cho tình huống mới | đổi mã trạng thái của tình huống cũ |

2. **Viết test trước** cho hành vi endpoint (`tests/unit/`, dùng `TestClient`): ca hợp lệ, ca biên, ca không đủ quyền.
3. **Thêm route** = thêm file trong `src/api/routes/` (tự khám phá, không sửa file đăng ký tập trung). Schema
   Pydantic hẹp: `extra="forbid"` cho request; response không lộ trường nội bộ.
4. **Sinh lại bản chụp:** `python scripts/export_openapi.py` → ĐỌC `git diff contracts/openapi.json`. Diff phải đúng
   bằng thay đổi định làm; có thay đổi ngoài ý muốn thì dừng tìm nguyên nhân.
5. **Frontend cùng PR** (hoặc PR nối ngay sau, ghi trong ticket): module tài nguyên trong `web/src/lib/api/`, không
   đoán trường không có trong hợp đồng (web/AGENTS.md luật 3).

## Thay đổi phá vỡ

Thêm bản mới bên cạnh bản cũ (trường mới / endpoint `v2`), chuyển bên gọi sang, đánh dấu bản cũ `deprecated`
trong OpenAPI, gỡ ở ticket sau khi không còn ai gọi. Không đổi nghĩa một trường đang có người dùng.

## Lỗi

Lỗi trả về theo một khuôn (`src/api/errors.py`): mã máy đọc được + thông điệp cho người; không lộ stack trace,
câu SQL hay chi tiết driver (INV-007). Lỗi 5xx do hạ tầng tạm thời thì nói rõ có thể thử lại.

## Kiểm trước khi báo xong

`python scripts/export_openapi.py --check` · `python -m pytest tests/unit -q` · `cd web && npm run build`.
