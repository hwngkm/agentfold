---
name: critical-debate
description: Tổ chức tranh luận phản biện có cấu trúc cho một quyết định quan trọng (kiến trúc, chọn công nghệ, phạm vi, kế hoạch, đổi mặc định) — một bên dựng lập luận bảo vệ mạnh nhất, một bên tấn công độc lập, trọng tài quyết theo bằng chứng chứ không theo độ tự tin; kèm pre-mortem và danh sách giả định có cách kiểm; kết quả thành DEC/ADR. Dùng khi sắp chốt một quyết định khó đảo ngược, khi cả nhóm (hoặc các agent) đồng ý quá nhanh, khi có hai phương án ngang nhau, hoặc khi cần phản biện cả dự án trước một mốc lớn.
---

# Tranh luận phản biện: tìm chỗ sai TRƯỚC khi cam kết

Mô hình ngôn ngữ — và người — có xu hướng đồng ý với đề xuất đang có trên bàn. Một agent được hỏi "đề xuất này ổn
không?" thường trả lời "ổn, với vài lưu ý". Cấu trúc dưới đây ép ra phản biện thật.

## Khi nào đáng làm

Quyết định **khó đảo ngược** (schema, nhà cung cấp, kiến trúc, cam kết với khách) hoặc **đắt nếu sai**. Quyết định dễ
đảo ngược, rẻ → làm, đo, sửa; đừng tranh luận.

## Vai trò

| Vai trò | Việc | Ai đóng |
|---|---|---|
| **Người bảo vệ** | dựng phiên bản MẠNH NHẤT của đề xuất (steelman), nêu bằng chứng ủng hộ | vai trò `architect`, hoặc tác giả đề xuất |
| **Người tấn công** | tìm cách đề xuất thất bại, phương án rẻ hơn bị bỏ qua, bất biến bị vi phạm, giả định ẩn | vai trò `red-team` (hoặc `critic`) — tốt nhất là agent của **nhà cung cấp khác** / phiên mới không có ngữ cảnh của bên bảo vệ |
| **Trọng tài** | xét từng điểm tấn công theo bằng chứng, quyết | **người** có quyền quyết theo `docs/GOVERNANCE.md`; agent chỉ được làm trọng tài sơ bộ |

## Thủ tục

1. **Mệnh đề** viết một câu có thể sai: "Dùng pgvector trong Postgres hiện có thay vì vector DB riêng cho 500 nghìn
   đoạn." Kèm tài liệu nền (PRD, ADR, số đo) giao cho CẢ HAI bên.
2. **Vòng 1 — viết độc lập, song song.** Bên tấn công không đọc lập luận bảo vệ trước khi viết (tránh bị neo).
   Bên tấn công phải nộp **ít nhất 5 kịch bản thất bại cụ thể**, hoặc chứng minh bằng bằng chứng vì sao không có.
3. **Pre-mortem** (cả hai bên): "Một năm sau, quyết định này bị coi là sai lầm. Chuyện gì đã xảy ra?" — liệt kê nguyên nhân.
4. **Vòng 2 — phản hồi một lần.** Mỗi bên đáp từng điểm của bên kia. Tối đa hai vòng: tranh luận dài hơn thường hội tụ
   về đồng thuận giả, không thêm thông tin.
5. **Trọng tài chấm từng điểm tấn công:** *bác bỏ (kèm bằng chứng)* / *chấp nhận — sửa đề xuất* / *chấp nhận — giữ
   rủi ro có lưới canh* / *chưa đủ bằng chứng — cần đo*. Không chấm theo bên nào viết hay hơn.

## Luật bằng chứng

- Mỗi khẳng định kèm bằng chứng: `đường/dẫn:dòng`, số đo + lệnh, nguồn tài liệu. Không có thì ghi **"giả định"**.
- **Danh sách giả định** là sản phẩm chính: mỗi giả định ghi cách kiểm rẻ nhất (đo trên mẫu, hỏi chuyên gia, đọc tài liệu).
  Giả định then chốt chưa kiểm → quyết định là "đo trước" (skill `experiment-design`), không phải "làm".
- Mức đảo ngược: ghi rõ cửa một chiều hay hai chiều, và chi phí quay lui.

## Đầu ra

```markdown
## Phản biện đã xét (đặt trong ADR/DEC)
- Mệnh đề: …
- Điểm tấn công → phán quyết → bằng chứng
- Giả định then chốt → cách kiểm → trạng thái
- Rủi ro giữ lại → lưới canh/test/ticket theo dõi (đưa vào sổ rủi ro của skill design-tables)
- Quyết định + mức đảo ngược + người quyết
```

## Chạy bằng agent

Một agent có thể đóng lần lượt hai vai, nhưng kém hơn: nó nhớ lập luận của chính nó. Tốt hơn: hai phiên/subagent tách
biệt (vai trò `architect` và `red-team` trong `coordination/roles/`), lý tưởng là hai nhà cung cấp khác nhau. Chạy nhiều
agent tốn token — chỉ dùng cho quyết định đủ lớn, và người dùng phải đồng ý trước.
