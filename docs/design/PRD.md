# PRD — Agentfold

> Vùng bảo vệ `design`. Đây là khung — dự án thật điền trong buổi khởi động, rồi mọi thay đổi phạm vi đi
> qua PR có người duyệt. Agent đọc file này để biết **cái gì không được làm** chứ không chỉ cái gì cần làm.

## 1. Vấn đề

Ai đang gặp khó khăn gì, đo bằng gì. Số liệu phải có nguồn — không có nguồn thì không đưa vào.

## 2. Người dùng và vai trò

| Vai trò trong sản phẩm | Làm được gì | Không bao giờ được thấy/làm |
|---|---|---|
| … | … | … |

## 3. Giải pháp và giá trị

Mô tả luồng chính trong 5–7 bước. Chỉ ra bước nào mô hình ngôn ngữ tham gia và bước nào con người duyệt.

## 4. Phạm vi

### 4.1 Tính năng trong phạm vi (ưu tiên P0 → P2)

| Mã | Tính năng | Ưu tiên | Tiêu chí thành công đo được |
|---|---|---|---|
| F-01 | … | P0 | … |

### 4.2 KHÔNG mục tiêu

Liệt kê rõ. Agent không được tự thêm những thứ này "cho đầy đủ", kể cả khi thấy hợp lý.

- …

## 5. Ràng buộc an toàn và pháp lý

Những gì hệ thống không được làm (vd. chẩn đoán, tư vấn tài chính cá nhân, quyết định thay người).
Mỗi ràng buộc quan trọng trở thành một bất biến trong `docs/design/invariants.yaml`.

## 6. Dữ liệu

Nguồn dữ liệu, giấy phép, dữ liệu nhạy cảm, dữ liệu nào được đưa vào prompt mô hình ngôn ngữ (mặc định: không
có dữ liệu định danh).

## 7. Chỉ số và đánh giá

Chỉ số chất lượng, an toàn, chi phí; bộ đánh giá nằm ở đâu; ngưỡng phát hành.

## 8. Mốc và rủi ro

| Mốc | Ngày | Điều kiện đạt |
|---|---|---|
| … | … | … |
