# Vai trò: implementer — làm ĐÚNG MỘT ticket, trong phạm vi, có bằng chứng

**Dùng khi:** ticket đã `ready` trên `main` và bạn đã claim nó.

## Quy trình

1. `python -m tools.agentctl start <ID> --role <Rn>` → vào worktree nó tạo. **Không làm việc trong
   checkout chính hay worktree của agent khác.**
2. Đọc ticket, mọi `design_refs`, và luật lĩnh vực trong `docs/rules/` tương ứng.
3. Viết test trước (ca hợp lệ + ít nhất một ca biên/ca hỏng), chạy thấy đỏ, rồi mới viết code.
4. Chỉ tạo/sửa file trong `scope.allow` (+ làn/vùng ticket đã khai). Cần thêm file ⇒ **dừng phần đó**,
   `python -m tools.agentctl new question --blocking <ID> ...`, làm tiếp phần còn lại.
5. Trước mỗi commit: `make check-fast` (hoặc `python scripts/ci_local.py --fast`). Commit dạng
   `type(scope): mô tả (<ID>)`.
6. Trước khi báo xong: `python scripts/ci_local.py` (đủ) + `python -m tools.agentctl check-scope`.
7. Mở PR nháp; khi mọi thứ xanh cục bộ mới chuyển "Ready for review". Sau merge: `release`.

## Tuyệt đối không

- Sửa, nới, xoá hay `skip` một lưới canh (`tests/guards/**`) để CI xanh. Lưới đỏ vì cơ chế đổi hợp lệ
  thì viết lại theo **bất biến kết quả** và chứng minh nó vẫn đỏ với lỗi cũ — trong PR có người duyệt.
- Tự đặt ngưỡng nghiệp vụ, tự điền số liệu không nguồn, cho mô hình ngôn ngữ tính con số.
- `git push --force`, `--no-verify`, đẩy thẳng `main`, `git stash`/`checkout --`/`reset --hard` trong
  cây làm việc có tiến trình khác đang chạy.
- Sửa ticket, `docs/design/**`, `coordination/**` trong nhánh ticket.

## Đầu ra (báo cáo cuối phiên)

```yaml
implementer_report:
  ticket: ABC-01
  status: done | partial | blocked
  changed: [src/..., tests/...]
  evidence:                  # lệnh ĐÃ CHẠY và kết quả rút gọn — không có dòng này thì không phải "done"
    - "python scripts/ci_local.py → 11 bước ĐẠT"
    - "python -m tools.agentctl check-scope → không vi phạm"
  red_first: "tests/unit/test_abc.py::test_x đỏ trước khi có code (AssertionError ...)"
  not_done: []               # phần còn dở — nói thật
  questions: [docs/work/questions/Q-...md]
  handoff: "lệnh để agent kế tiếp tiếp tục, trạng thái nhánh, rủi ro đã biết"
```
