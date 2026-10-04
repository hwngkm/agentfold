---
name: data-quality
description: Kiểm chất lượng một bộ dữ liệu trước khi dùng hoặc công bố — toàn vẹn (khoá trùng, tham chiếu gãy), đầy đủ (null theo cột), hợp lệ (miền giá trị, đơn vị, mã hoá), phân phối và trôi giữa hai lần nạp, và rút mẫu đọc bằng mắt đối chiếu nguồn. Dùng khi vừa nạp hoặc chuẩn hoá lại dữ liệu, trước khi phát hành một bản dữ liệu, khi số liệu báo cáo bất thường, hoặc khi nhận dữ liệu mới từ người khác.
---

# Chất lượng dữ liệu: đo bằng máy, rồi đọc bằng mắt

Không giả định file mới "đã sẵn sàng" (R40.3). Một bộ kiểm chỉ đếm sẽ cho qua 300 dòng câu mẫu lặp lại — luôn có
bước rút mẫu đọc nội dung (R40.11).

## 1. Kiểm bằng máy (chạy mỗi lần nạp)

| Nhóm | Kiểm | Ví dụ ngưỡng |
|---|---|---|
| Toàn vẹn | khoá chính trùng; khoá ngoại trỏ tới dòng không tồn tại | = 0 |
| Đầy đủ | tỷ lệ null theo cột; dòng thiếu `source`/`source_ref` | `source_ref` null = 0 |
| Hợp lệ | giá trị ngoài miền (âm, quá lớn), đơn vị lẫn lộn, mã hoá (UTF-8, không BOM, Unicode chuẩn hoá NFC) | theo miền |
| Trùng lặp mềm | cùng thực thể viết khác (`rau` / `rau củ`, hoa/thường, dấu) | báo cáo, người quyết |
| Phân phối | số dòng, min/max/phân vị theo cột số, tần suất giá trị phân loại | so với lần trước |

Viết thành script trả mã lỗi khác 0 khi vi phạm ngưỡng — chạy được trong CI nếu dữ liệu seed nằm trong repo.

## 2. Trôi giữa hai lần nạp

Lưu "dấu vân tay" mỗi lần (số dòng, phân phối chính, băm theo nguồn). Lần sau so: số dòng đổi bao nhiêu %, cột nào
đổi phân phối, nguồn nào biến mất. Thay đổi lớn mà không có lý do (nguồn cập nhật, đổi logic) là dấu hiệu lỗi
pipeline, không phải dữ liệu mới.

## 3. Rút mẫu đọc bằng mắt

- Rút **ngẫu nhiên có seed** 20–30 bản ghi (phân tầng theo nguồn/loại nếu có), đối chiếu từng bản với `source_ref`.
- Ghi: cỡ mẫu, số đúng, các lỗi gặp (loại lỗi + ví dụ). "29/30 đúng" là kết quả của mẫu, không phải tỷ lệ toàn bộ
  — nói kèm khoảng tin cậy khi mẫu nhỏ.
- Không dùng chính quy tắc trích xuất để chấm chính nó.

## 4. Báo cáo

Một mục trong ghi chú nghiên cứu hoặc nhật ký (`new log`): bản dữ liệu (mã phát hành), số đo phần 1–2, kết quả phần
3, vấn đề còn mở. Dữ liệu cần chuyên gia duyệt thì giữ trạng thái chờ duyệt — agent không tự duyệt thay.
