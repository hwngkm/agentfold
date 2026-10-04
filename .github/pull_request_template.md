## Ticket

`ABC-01` — docs/work/tickets/ABC-01.md

## Thay đổi

-

## Vì sao / tham chiếu thiết kế

- design_refs, ADR, câu hỏi đã được trả lời:

## Bằng chứng (lệnh đã chạy + kết quả rút gọn)

- [ ] `python scripts/ci_local.py` →
- [ ] `python -m tools.agentctl check-scope` →
- [ ] Test mới đã thấy ĐỎ trước khi có code:

## Phạm vi và điều phối

- [ ] Mọi file nằm trong `scope` của ticket (scope-guard kiểm)
- [ ] Làn độc quyền đã khai nếu chạm migration / phụ thuộc / hợp đồng API
- [ ] Không sửa, nới, xoá hay skip lưới canh hiện có (thêm mới thì được)
- [ ] Tài liệu và `contracts/openapi.json` cập nhật nếu đổi luồng hoặc API
- [ ] `.env.example` cập nhật nếu thêm biến môi trường
- [ ] Không bí mật, không dữ liệu định danh, không `print()` trong `src/`

## Câu hỏi mở / quyết định mới

-

## Bàn giao (nếu còn dở)

-
