---
name: bug-fix
description: Sửa lỗi theo ba bước tách bạch — đánh giá (tái hiện + nguyên nhân gốc), sửa (đúng nguyên nhân đã đánh giá, trong phạm vi), kiểm (chạy lại ĐÚNG triệu chứng ban đầu) — và kết thúc bằng báo cáo có kết luận verified, partial hoặc failed kèm bằng chứng. Dùng khi nhận một báo lỗi hay CI đỏ do lỗi thật, khi agent định sửa theo phỏng đoán, hoặc khi cần chứng minh một lỗi đã được sửa thật.
---

# Sửa lỗi: đánh giá → sửa → kiểm, và kết luận phải có bằng chứng

Gốc của quy trình: github/spec-kit (bug-fixing: "giữ chẩn đoán, sửa chữa và kiểm tra tách nhau, để agent sửa đúng
nguyên nhân đã đánh giá và kiểm triệu chứng ban đầu"). **Thiếu kiểm chứng không phải là sửa xong.**

## 0. Mở báo cáo

```bash
python -m tools.agentctl new bug --role Rn --title "Gửi form rỗng làm sập đăng nhập"
```

Tạo `docs/work/bugs/BUG-<ngày>-<slug>.md` với `verdict: pending`. `check-work` kiểm kết luận thuộc tập đóng và
`verified`/`partial` có `evidence`.

## 1. Đánh giá — CHƯA sửa gì

1. **Triệu chứng nguyên văn** (log, ảnh, lời người báo). Không diễn giải trước khi tái hiện.
2. **Tái hiện bằng test ĐỎ trên code hiện tại**, đỏ vì đúng triệu chứng này (skill `tdd-loop` bước 2). Không tái hiện được
   thì dừng: ghi đã thử gì, mở `new question` — đừng sửa theo phỏng đoán.
3. **Nguyên nhân gốc là một cơ chế**: "hàm X nhận chuỗi rỗng và chia cho độ dài", không phải "sơ suất". Bằng chứng: dòng
   code, log, và lần thử loại trừ giả thuyết khác (đổi một biến, xem kết quả đổi).
4. Ca đụng bất biến hoặc ngưỡng/nguồn nghiệp vụ: DỪNG — việc của người (`route: human-decision`).

## 2. Sửa — đúng nguyên nhân đã đánh giá

- Nhỏ nhất đủ để test tái hiện chuyển xanh; trong `scope.allow` của ticket. Muốn dọn chỗ khác: ghi lại, làm ticket riêng.
- Sửa lỗi lớp (cùng cơ chế ở chỗ khác) thì liệt kê các chỗ đó trong báo cáo, đừng lặng lẽ sửa lan.

## 3. Kiểm — trên ĐÚNG triệu chứng ban đầu

1. Test tái hiện từng đỏ nay xanh.
2. Chạy cả nhóm liên quan, rồi `python scripts/ci_local.py --fast` (cổng bằng chứng của Claude Code cũng chờ nó).
3. Nếu có thể, chạy lại đúng thao tác người báo (không chỉ test viết lại).

## 4. Kết luận (đổi `verdict`, điền `evidence`)

| Kết luận | Khi nào | `evidence` |
|---|---|---|
| `verified` | triệu chứng gốc hết, test tái hiện xanh, nhóm liên quan xanh | bắt buộc: lệnh + kết quả, ghi rõ "đã đỏ trước khi sửa" |
| `partial` | hết một phần, hoặc hết nhưng chưa kiểm được một ca (thiếu môi trường…) | bắt buộc; mục 5 ghi phần CHƯA hết |
| `failed` | sửa xong mà triệu chứng còn, hoặc không sửa được | không bắt buộc — thừa nhận thất bại là kết quả hợp lệ |
| `pending` | chưa tái hiện được / chưa kiểm | không |

## 5. Phòng ngừa

Lỗi đáng nhớ ⇒ lưới canh (skill `guard-net`, có bước chứng minh đỏ). Sự cố đã tới người dùng ⇒ thêm `new incident` (skill
`incident` của pack `ops`). Ghi đường dẫn test vào mục 6 của báo cáo.
