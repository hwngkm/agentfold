---
name: competitor-analysis
description: Phân tích đối thủ và phương án thay thế — gồm cả cách làm thủ công và giải pháp mã nguồn mở, so sánh tính năng/giá/đối tượng/điểm mạnh-yếu bằng bảng có nguồn và ngày truy cập, tìm khoảng trống thật, và tránh kết luận từ trang quảng cáo. Dùng khi định vị một sản phẩm/tính năng, khi viết PRD hay đề xuất, khi quyết định tự làm hay dùng giải pháp có sẵn, hoặc khi cần biết sản phẩm khác đã giải bài toán tương tự thế nào.
---

# Phân tích đối thủ: so với cái người dùng đang dùng thật, không chỉ với công ty cùng ngành

## 1. Ai là "đối thủ"

1. **Cách người dùng đang làm hôm nay** (giấy, Excel, Zalo nhóm, quy trình thủ công) — thường là đối thủ mạnh nhất.
2. Sản phẩm thương mại cùng việc (trong nước, quốc tế).
3. Mã nguồn mở / mô hình mở làm được phần lõi (skill `repo-research`, `model-hub-research` của pack `research`).
4. Tính năng nằm trong một sản phẩm lớn hơn mà khách đã dùng (HIS/EMR, bộ văn phòng…).

## 2. Thu thập — mỗi ô có nguồn và ngày

| Đối thủ | Đối tượng | Việc chính | Tính năng then chốt | Giá (công khai?) | Triển khai / dữ liệu ở đâu | Điểm mạnh | Điểm yếu | Nguồn + ngày |
|---|---|---|---|---|---|---|---|---|

- Nguồn mạnh: dùng thử thật, tài liệu kỹ thuật, bảng giá, đánh giá của người dùng thật, hồ sơ thầu công khai.
- Nguồn yếu: trang quảng cáo, thông cáo báo chí — ghi là "tự công bố".
- Không đăng ký dùng thử bằng danh tính giả; không lấy dữ liệu sau đăng nhập trái điều khoản.

## 3. Phân tích

- **Ma trận tính năng** chỉ cho những tính năng quyết định việc mua (từ phỏng vấn — skill `market-research`), không liệt
  kê mọi thứ.
- **Khoảng trống**: nhu cầu có bằng chứng mà không ai đáp ứng tốt — kèm lý do có thể họ cố ý bỏ (khó, không lời, pháp lý).
- **Điều phải bằng**: thứ mọi đối thủ đều có và khách coi là mặc định.
- **Tự làm hay dùng sẵn**: nếu mã nguồn mở/sản phẩm có sẵn giải được 80% → so chi phí tích hợp + bảo trì với tự làm (ghi DEC).

## 4. Trung thực

Không hạ đối thủ bằng thông tin cũ (ghi ngày); không khẳng định "không ai làm X" khi chỉ tìm 15 phút — ghi đã tìm ở đâu,
bằng truy vấn gì. Kết quả đi vào PRD (`docs/design/PRD.md` — vùng bảo vệ, đề xuất qua PR) và sổ rủi ro.

Không có plugin `product-management`: dùng bảng ở mục 2 trong repo; tìm sản phẩm/mã nguồn mở bằng tìm kiếm web và
`python -m scripts.research github ...`.
