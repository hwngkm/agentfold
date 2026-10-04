---
name: train-eval
description: Huấn luyện và đánh giá mô hình ML/DL không tự lừa mình — chia tập theo đơn vị độc lập (người, tài liệu, thời gian), bắt rò rỉ nhãn và trùng lặp giữa tập, baseline tầm thường trước mô hình phức tạp, chỉ số đúng với mục tiêu, và tập kiểm tra chỉ chạm một lần. Dùng khi dựng pipeline huấn luyện mới, khi kết quả đánh giá tốt bất thường, khi chọn chỉ số đánh giá, hoặc khi mô hình tốt trên tập kiểm tra nhưng kém khi dùng thật.
---

# Huấn luyện và đánh giá: kết quả đẹp bất thường là lỗi cho tới khi chứng minh khác

## 1. Chia tập

- Chia theo **đơn vị độc lập**: cùng một bệnh nhân/người dùng/tài liệu/phiên chỉ nằm ở một tập. Chia theo dòng khi
  một người có nhiều dòng = rò rỉ.
- Dữ liệu có thời gian → chia theo thời gian (huấn luyện quá khứ, kiểm tra tương lai), như lúc dùng thật.
- Ba tập: train / val (chọn siêu tham số, dừng sớm) / test (báo cáo cuối, **chạm một lần**). Phân tầng theo nhãn khi
  lớp lệch.
- Ghi seed và danh sách id mỗi tập (skill `experiment-tracking`).

## 2. Bắt rò rỉ

- Trùng/lặp gần giữa tập: băm nội dung chuẩn hoá; với văn bản kiểm cả gần trùng (n-gram, embedding).
- Đặc trưng chứa đáp án: trường được điền SAU sự kiện cần dự đoán, mã ghi chú lộ nhãn, đường dẫn file chứa tên lớp.
- Tiền xử lý (chuẩn hoá, chọn đặc trưng, từ vựng) **fit trên train**, áp lên val/test — fit trên toàn bộ là rò rỉ.
- Với mô hình nền đã huấn luyện sẵn: bộ kiểm tra công khai có thể đã nằm trong dữ liệu huấn luyện của nó.

## 3. Baseline trước

Luôn có: lớp đa số / giá trị trung bình, quy tắc đơn giản hoặc mô hình tuyến tính, và hệ thống hiện tại nếu có. Mô
hình phức tạp không thắng baseline đơn giản một khoảng lớn hơn dao động giữa seed thì không đáng độ phức tạp.

## 4. Chỉ số

- Chọn theo cái giá của lỗi: bỏ sót tốn hơn → recall/độ nhạy; báo động giả tốn hơn → precision. Lớp lệch → không
  dùng accuracy một mình; báo PR-AUC, F1 theo lớp, ma trận nhầm lẫn.
- Mô hình cho xác suất mà người dùng tin theo → kiểm hiệu chỉnh (calibration).
- Báo theo nhóm con (nguồn, nhóm người dùng, độ dài đầu vào) — trung bình che nhóm hỏng.
- Báo khoảng tin cậy (bootstrap trên tập test) và độ lệch giữa ≥ 3 seed.

## 5. Đọc lỗi

Rút ngẫu nhiên các ca sai trên val, đọc từng ca, phân loại nguyên nhân (nhãn sai, thiếu dữ liệu loại đó, mô hình
yếu). Nhãn sai nhiều → sửa dữ liệu trước khi chỉnh mô hình.
