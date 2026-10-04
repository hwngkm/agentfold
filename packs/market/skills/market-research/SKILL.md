---
name: market-research
description: Nghiên cứu thị trường cho một sản phẩm hoặc tính năng một cách trung thực — câu hỏi kinh doanh rõ, phân khúc và người dùng mục tiêu, quy mô thị trường ước tính từ dưới lên có nguồn, tín hiệu nhu cầu thật (phỏng vấn, hành vi, sẵn lòng trả tiền), và tách rõ dữ kiện có nguồn, ước tính và giả định. Dùng khi đánh giá ý tưởng sản phẩm mới, khi viết phần thị trường cho PRD hay đề xuất đầu tư/tài trợ, khi chọn phân khúc để bắt đầu, hoặc khi một con số thị trường cần được kiểm.
---

# Nghiên cứu thị trường: con số có nguồn, ước tính có cách tính, giả định có cách kiểm

Luật nền: R40.5 (ước tính phải trung thực), R40.6 (số liệu công bố phải có nguồn sơ cấp), R40.11 (không tự chấm).

## 1. Câu hỏi trước, số liệu sau

Viết 1–3 câu hỏi quyết định được: "Phòng khám tư ở Việt Nam có trả tiền cho công cụ X không, mức nào?" — không phải
"thị trường AI y tế lớn cỡ nào". Mỗi phần dưới đây phải giúp trả lời câu hỏi đó.

## 2. Phân khúc và người dùng

| Phân khúc | Ai dùng / ai trả tiền | Việc họ cần làm | Đang giải quyết bằng gì | Đau ở đâu | Bằng chứng |
|---|---|---|---|---|---|

Người dùng ≠ người trả tiền ≠ người quyết định mua — ghi cả ba. Cột "Bằng chứng" là phỏng vấn, quan sát, dữ liệu hành vi,
không phải cảm nhận của nhóm.

## 3. Quy mô — tính từ dưới lên

```
Số đơn vị mục tiêu (nguồn: thống kê chính thức, năm) × tỷ lệ có nhu cầu (nguồn hoặc giả định ghi rõ)
  × mức chi trả/năm (nguồn: phỏng vấn n=?, bảng giá đối thủ) = quy mô ước tính, kèm khoảng thấp–cao
```

- Báo cáo thị trường "toàn cầu X tỷ USD" là tín hiệu thứ cấp; chỉ dùng khi đọc được phương pháp, và ghi là thứ cấp.
- Mỗi tham số trong phép nhân ghi: nguồn + năm, hoặc nhãn **giả định** + cách kiểm. Kết quả luôn là khoảng, không là
  một con số tròn.

## 4. Tín hiệu nhu cầu thật (mạnh → yếu)

Đã trả tiền / ký ý định mua > dùng thử lặp lại > đăng ký chờ có cam kết > phỏng vấn mô tả nỗi đau cụ thể kèm cách đang
xoay xở > "nghe hay đấy". Ghi cỡ mẫu; 5 cuộc phỏng vấn cho thấy vấn đề có thật, không cho thấy tỷ lệ trên toàn thị trường.

## 5. Nguồn

- Thống kê nhà nước, báo cáo ngành có phương pháp, báo cáo tài chính công ty niêm yết, bảng giá công khai của đối thủ
  (ghi ngày truy cập), dữ liệu tìm kiếm/xu hướng (tín hiệu tương đối).
- Không gửi dữ liệu khách hàng, kế hoạch nội bộ hay dữ liệu người dùng vào công cụ tìm kiếm/AI bên ngoài.

## Đầu ra

Bản tóm tắt 1–2 trang: câu hỏi → trả lời ngắn + mức chắc chắn · bảng phân khúc · phép tính quy mô có nguồn từng tham số
· tín hiệu nhu cầu kèm cỡ mẫu · giả định then chốt + cách kiểm rẻ nhất (đưa vào skill `critical-debate` nếu sắp quyết
lớn). Đối thủ: skill `competitor-analysis`.

Không có plugin `product-management`: toàn bộ thủ tục trên chạy bằng tìm kiếm web thường + bảng trong repo.
