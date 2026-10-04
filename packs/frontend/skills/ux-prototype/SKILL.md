---
name: ux-prototype
description: Dựng bản mẫu nhanh, rẻ, vứt được để chốt luồng với người dùng thật hoặc chuyên gia TRƯỚC khi viết code thật — chọn độ trung thực vừa đủ, kịch bản thử với nhiệm vụ cụ thể, ghi quan sát, và chuyển kết luận thành ticket. Dùng khi luồng người dùng chưa rõ, khi chuẩn bị demo cho người duyệt/khách, khi có nhiều phương án giao diện cần chọn, hoặc trước một tính năng tốn nhiều công.
---

# Bản mẫu: trả lời một câu hỏi về người dùng, rồi vứt đi

Bản mẫu không phải phiên bản đầu của sản phẩm. Nó tồn tại để trả lời **một câu hỏi** ("bác sĩ có tìm được nút
duyệt trong 10 giây không?") với chi phí thấp nhất.

## 1. Viết câu hỏi trước

Ghi trong ticket: câu hỏi cần trả lời, ai sẽ thử (vai trò thật, không phải người trong nhóm), tiêu chí "đạt".
Không có câu hỏi → không làm bản mẫu, viết code thật với thiết kế đã chốt.

## 2. Độ trung thực vừa đủ

| Câu hỏi về | Bản mẫu |
|---|---|
| Thứ tự bước, thông tin nào cần ở đâu | khung dây (giấy, ảnh, HTML tĩnh) |
| Người dùng hiểu nội dung/nhãn không | HTML tĩnh với nội dung THẬT, không lorem ipsum |
| Cảm giác tương tác, tốc độ | trang Next.js riêng với dữ liệu giả cố định, không backend |

Đặt bản mẫu ngoài mã sản phẩm (nhánh riêng hoặc thư mục `prototypes/` không deploy); dữ liệu giả, không dữ liệu
thật của người dùng (R40.8).

## 3. Thử với người

- 3–5 người đúng vai trò thường đủ thấy vấn đề lớn nhất của một luồng; ghi rõ cỡ mẫu khi báo cáo, không quy ra
  phần trăm.
- Giao **nhiệm vụ** ("hãy duyệt đơn hàng của khách A"), không hướng dẫn từng bước, không hỏi "bạn thấy đẹp không".
- Ghi: chỗ dừng lại, chỗ bấm nhầm, câu hỏi họ đặt ra, thời gian hoàn thành. Quan sát thắng ý kiến.

## 4. Kết luận thành việc

Mỗi phát hiện → một dòng: *quan sát → mức độ → đề xuất*. Đề xuất được chấp nhận → ticket (`new ticket`) hoặc
cập nhật thiết kế (ADR nếu đổi thiết kế đã chốt). Ghi buổi thử thành `new log` kèm cỡ mẫu và giới hạn.

## Công cụ

Với bản mẫu HTML tương tác một file để trao đổi nhanh, plugin `playground` trong marketplace chính thức có thể dùng
được; bản mẫu nào cũng không đi vào nhánh `main` của sản phẩm.
Không có plugin: một file HTML tĩnh tự viết (không framework) làm được cùng việc.
