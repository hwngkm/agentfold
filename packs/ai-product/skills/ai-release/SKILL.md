---
name: ai-release
description: Đưa một tính năng AI từ bản thử lên production có kiểm soát — cổng eval chặn hồi quy trước khi merge, bật dần sau cờ tính năng, chế độ bóng (chạy nhưng không hiển thị) để so với hệ thống cũ, theo dõi chất lượng và chi phí sau phát hành, và nút tắt nhanh. Dùng khi chuẩn bị phát hành tính năng AI mới, khi đổi mô hình hoặc prompt của tính năng đang chạy, khi đổi nhà cung cấp mô hình, hoặc khi chất lượng AI trên production giảm.
---

# Phát hành tính năng AI: chất lượng không được kiểm bằng "thử vài câu thấy ổn"

Đổi mô hình, prompt, cách truy hồi hay nhà cung cấp là một **bản phát hành**, kể cả khi không đổi dòng code nào khác.

## 1. Trước khi merge

- Golden set + eval offline (skill `eval-harness`): điểm mới so với điểm hiện tại, kèm khoảng tin cậy; tập con nhỏ ổn
  định chạy trong CI cho PR chạm prompt/mô hình/pipeline, với ngưỡng lớn hơn sàn nhiễu.
- Ghi phiên bản: mô hình (đọc từ response, không từ cấu hình), prompt, bộ ca, grader. Điểm không có phiên bản thì
  không so được.
- Chi phí và độ trễ trên bộ ca (skill `token-economics`, `latency-slo`): tăng bao nhiêu so với bản đang chạy.

## 2. Bật dần

1. **Cờ tính năng** tắt mặc định; tắt/bật không cần deploy.
2. **Chế độ bóng** (nếu thay thế hệ thống đang có): chạy bản mới song song, ghi kết quả, không hiển thị; so với bản
   cũ trên dữ liệu thật đã khử định danh.
3. **Nội bộ / người duyệt** trước, rồi một phần nhỏ người dùng, rồi tăng dần — mỗi bậc có tiêu chí đi tiếp ghi sẵn.
4. Tính năng có hành động HIGH: cổng người duyệt luôn bật ở mọi bậc (skill `human-in-the-loop`).

## 3. Theo dõi sau phát hành

- Chất lượng: tỷ lệ người duyệt sửa/từ chối, phản hồi người dùng, tỷ lệ từ chối trả lời, lỗi parse đầu ra.
- Vận hành: lỗi gọi mô hình, timeout, chi phí mỗi yêu cầu, độ trễ P95.
- Trôi: phân bố đầu vào thay đổi (loại câu hỏi mới) → thêm ca vào golden set.
- Nhà cung cấp đổi mô hình phía sau cùng tên gọi → ghim phiên bản mô hình khi nhà cung cấp cho phép; kiểm trường
  `model` trong response.

## 4. Tắt nhanh

Nút tắt (cờ) đã thử trước khi bật; khi tắt, giao diện có đường thay thế (hệ thống cũ, hoặc thông báo rõ ràng), không
màn hình trắng. Sự cố chất lượng → tắt trước, điều tra sau, ghi `new incident`.

## Đầu ra

Ghi chú phát hành: phiên bản (mô hình, prompt, bộ ca), điểm eval trước/sau có khoảng tin cậy, chi phí/độ trễ trước/sau,
kế hoạch bật dần + tiêu chí mỗi bậc, cách tắt.
