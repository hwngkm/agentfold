# RULE 80 — Lưới canh: thiết kế dạng chạy được

> Owner: **R1**. Lưới canh nằm ở `tests/guards/` (vùng bảo vệ: thêm được, sửa/xoá cần người duyệt).
> Mỗi lưới được một bất biến trong `docs/design/invariants.yaml` nhận — lưới không có lý do tồn tại thì bị gỡ.

## R80.1 — Lưới canh là gì

Một test khoá một QUYẾT ĐỊNH THIẾT KẾ hoặc một BÀI HỌC SỰ CỐ, để agent hay người không làm sai lặng lẽ được. Nó khác
unit test ở chỗ: unit test hỏi "hàm này đúng không", lưới canh hỏi "hệ thống còn giữ lời hứa không".

## R80.2 — Cấu trúc bắt buộc của docstring

1. **Vì sao** — sự cố thật hoặc rủi ro cụ thể (ngày, số đo nếu có).
2. **Khoá gì** — bất biến kết quả, một câu.
3. **Sửa khi đỏ** — cách sửa ĐÚNG, và cách sửa SAI phải tránh (vd. "không `alembic stamp`").

## R80.3 — Khoá kết quả, không khoá cơ chế

Lưới hỏi "có module nào import SDK LLM trong lõi tất định không" (kết quả), không hỏi "file X có dòng Y không"
(cơ chế). Lưới khoá kết quả không cản refactor hợp lý, mà vẫn đỏ khi ai đó vô tình phá lời hứa.

Khi một lưới đỏ vì PR đổi cơ chế một cách hợp lệ:

1. Đọc hàm sinh đầu ra thật để biết lưới thật sự canh gì — không suy từ tên test.
2. Viết ra bất biến kết quả cần giữ vĩnh viễn.
3. Viết lại lưới theo bất biến đó (thường mạnh hơn: phủ cả dữ liệu thêm sau).
4. **Chứng minh lưới mới vẫn đỏ** với đúng lỗi lưới cũ bắt (tái tạo hồi quy), rồi khôi phục.
5. PR có người duyệt (vùng bảo vệ) — không bao giờ nới lặng lẽ.

## R80.4 — Phải thấy đỏ trước khi tin

Lưới chưa từng đỏ không chứng minh gì. Sau khi viết: tạm phá cơ chế nó canh → chạy → xác nhận đỏ ĐÚNG chỗ với thông
điệp chỉ ra nguyên nhân → khôi phục → xanh. Lỗi đã gặp: spec e2e đếm nút khi trang còn đang tải nên "không có nút"
luôn đúng; regex `color:` khớp nhầm `border-color:`; lưới đọc đồ thị migration bằng hàm không nạp `env.py` nên xanh
cả khi `env.py` hỏng.

## R80.5 — Lưới cho chính lưới

Mỗi lưới quét file/dữ liệu kèm một khẳng định rằng nó THẬT SỰ quét được thứ gì đó (số file tối thiểu, một mẫu đã
biết phải bị bắt). Đường dẫn sai làm lưới xanh rỗng nghĩa — nguy hiểm hơn không có lưới, vì nó tạo cảm giác đã kiểm.

## R80.6 — Quét mã nguồn thì đọc bằng AST hoặc bỏ lời bình trước

Docstring mô tả lỗi hầu như luôn chứa đúng tên mà lưới tìm. Quét văn bản thô sinh báo động giả, người ta sẽ nới
lưới. Dùng `ast` cho Python; với văn bản khác, loại khối lệnh/lời bình trước khi quét.

## R80.7 — Báo đủ lỗi trong một lượt

Thông điệp lỗi của lưới liệt kê MỌI vi phạm và chỉ cách sửa. Lưới báo từng lỗi một buộc người sửa đẩy CI nhiều
lượt — đã có dự án mất sáu lượt CI liên tiếp cho sáu lỗi mà một lượt kiểm đủ đã thấy hết.

## R80.8 — Khi nào thêm lưới

- Sau mỗi sự cố: phần "Phòng ngừa" của file sự cố trỏ tới lưới mới.
- Khi một ADR được chấp nhận: quyết định có lưới kiểm chứng.
- Khi review thấy một lời hứa chỉ nằm trong tài liệu.
