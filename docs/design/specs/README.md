# docs/design/specs — đặc tả sống

Ticket có tiêu chí nghiệm thu, nhưng khi merge xong tiêu chí biến mất cùng ticket: hệ thống "đã hứa gì" nằm rải rác
trong lịch sử. Thư mục này giữ **lời hứa hiện hành** ở một nơi, mỗi lời hứa trỏ tới test chứng minh nó.
Ý tưởng mượn từ [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) (delta thêm/sửa/bỏ).

```
specs/<năng-lực>.md                     đặc tả hiện hành của một năng lực (vd. handoff, agent-log)
specs/changes/<MÃ-TICKET>-<năng-lực>.md delta đang chờ gộp
specs/changes/archive/<ngày>-….md       delta đã gộp (lịch sử, không sửa)
```

## Khuôn một yêu cầu

```markdown
### Requirement: <tên, duy nhất trong năng lực>
Hệ thống SHALL <điều kiểm được>.

#### Scenario: <tên>
- **WHEN** <điều kiện>
- **THEN** <kết quả quan sát được>
- **Test:** tests/duong/dan.py::ten_ham      (nhiều test: cách nhau dấu phẩy; chưa có: planned:TICKET-NN)
```

- **`SHALL`**: yêu cầu phải kiểm được. "Nên", "cố gắng", "hỗ trợ tốt" không phải yêu cầu.
- **Kịch bản**: mỗi yêu cầu ≥ 1; có WHEN và THEN (AND tuỳ chọn). Ca biên và ca lỗi cũng là kịch bản.
- **`Test:`**: tệp và hàm phải tồn tại (CI kiểm). `planned:TICKET-NN` = chưa có test, đã có ticket — lời hứa chưa được chứng
  minh phải thấy được, không giấu.

## Một thay đổi đi qua delta

1. Trong ticket đổi hành vi: tạo `changes/<MÃ-TICKET>-<năng-lực>.md` với các mục (bỏ mục không dùng):
   `## ADDED Requirements` (yêu cầu mới) · `## MODIFIED Requirements` (viết lại TRỌN yêu cầu cũ) · `## REMOVED Requirements`
   (chỉ dòng `### Requirement: <tên>`).
2. `python -m tools.agentctl spec check` — kiểm delta gộp thử được và kết quả hợp lệ (CI cũng chạy).
3. Sau khi merge: `python -m tools.agentctl spec archive <MÃ-TICKET>-<năng-lực>` gộp vào đặc tả chung và chuyển delta vào
   `archive/`. Kết quả không hợp lệ thì lệnh từ chối và không đụng tệp nào.

Thêm trùng, sửa hay bỏ yêu cầu không tồn tại đều bị từ chối — delta nói THÊM thì phải là thêm.

## Giới hạn nói thật

- Lưới canh kiểm yêu cầu **có test trỏ tới và test tồn tại**, không kiểm test đó **thật sự** chứng minh yêu cầu — việc
  đó là của review (`reviewer`) và skill `guard-net` (test phải từng đỏ).
- Đặc tả mô tả hành vi quan sát được, không thay ADR (vì sao chọn) hay `invariants.yaml` (điều không bao giờ được phá).
- `docs/design/` là vùng bảo vệ: sửa đặc tả hiện hành trực tiếp cần người duyệt; delta đi qua ticket có `protected: [design]`.
