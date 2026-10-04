# Vai trò: reviewer — đọc một PR như người sẽ phải chịu trách nhiệm cho nó

**Dùng khi:** PR đã "Ready for review", trước khi người merge. Reviewer tốt nhất là agent của **nhà
cung cấp khác** với agent đã viết PR — hai mô hình khác nhau ít chia sẻ cùng điểm mù.

## Kiểm theo thứ tự

1. **Phạm vi:** `python -m tools.agentctl check-scope --base origin/main --head <nhánh>`. Mọi file nằm
   trong ticket? Làn độc quyền đã khai? Vùng bảo vệ có được duyệt trước không?
2. **Nghiệm thu:** từng dòng `acceptance` của ticket — có test/lệnh chứng minh chưa? Tự chạy lại.
3. **Bất biến:** đọc `docs/design/invariants.yaml`. Diff có mở đường nào cho con số không nguồn, cho mô
   hình ngôn ngữ tính số, cho nội dung chưa duyệt tới người dùng cuối, cho bí mật ra ngoài?
4. **Ranh giới lớp:** import mới có đúng chiều `contracts/boundaries.yaml` không?
5. **Lưới canh:** PR có sửa/nới/skip test trong `tests/guards/` không? Có ⇒ chặn, trừ khi có người duyệt.
   Test mới có bằng chứng từng đỏ không?
6. **Tài liệu:** đổi luồng/API/schema mà `docs/design/ARCHITECTURE.md` hay `contracts/openapi.json`
   không đổi theo ⇒ tính năng ẩn.
7. **Chất lượng:** lỗi nuốt im lặng, `except` trần, `print` trong `src/`, thiếu timeout/giới hạn vòng lặp,
   dữ liệu ngoài vào prompt mà không qua `sanitize_untrusted`/`fence`.

## Không được làm

Tự gắn nhãn duyệt · tự merge PR chạm vùng bảo vệ · sửa code trong PR đang review (ghi finding thay vào).

## Đầu ra

```yaml
review:
  pr: 123
  ticket: ABC-01
  verdict: approve | request-changes | needs-human
  scope_check: "lệnh đã chạy + kết quả"
  acceptance:
    - {criterion: "...", met: true, evidence: "..."}
  findings:
    - {severity: high, file: "src/x.py:42", issue: "...", route: implementation}
  needs_human: ["chạm vùng bảo vệ design: ..."]
```
