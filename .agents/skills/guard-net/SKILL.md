---
name: guard-net
description: Biến một quyết định thiết kế hoặc bài học sự cố thành lưới canh chạy được trong tests/guards/ và đăng ký vào docs/design/invariants.yaml. Dùng khi vừa sửa xong một bug đáng nhớ, khi chốt một ràng buộc kiến trúc, khi review thấy "chỗ này ai đó sẽ phá lại", hoặc khi một lưới canh đỏ vì PR đổi cơ chế hợp lệ.
---

# Lưới canh: biến lời hứa thành test

Luật đầy đủ: `docs/rules/80-guard-nets.md`. Đây là **thủ tục thực hiện**, không lặp lại luật.

## Khi nào đáng làm một lưới canh

Làm khi trả lời được "hệ thống hứa gì?" bằng một câu, và câu đó **không phải** "hàm này trả đúng giá trị"
(đó là unit test). Ví dụ hứa: lõi tất định không bao giờ import SDK LLM · tài liệu kiến trúc không rời
hợp đồng · migration luôn một head · PR nháp không tốn phút CI.

Không làm khi: chỉ để tăng coverage · khoá một chi tiết cài đặt sắp đổi · chưa có ai từng phá nó và cũng
không thấy đường nào phá được.

## Thủ tục (không bỏ bước 3)

1. **Viết bất biến bằng một câu** — dạng *kết quả*, không dạng *cơ chế*. "Không module nào trong lõi tất
   định import SDK nhà cung cấp" ✅. "File `gateway.py` có dòng `from openai`" ❌ — câu sau chặn cả refactor
   hợp lệ (R80.3).

2. **Viết test trong `tests/guards/`** với docstring đủ ba phần bắt buộc (R80.2): **Vì sao** (sự cố thật,
   có ngày/số đo nếu có) · **Khoá gì** (bất biến, một câu) · **Sửa khi đỏ** (cách sửa đúng, và cách sửa
   SAI phải tránh).

3. 🔴 **Chứng minh nó đỏ — bắt buộc, không được bỏ.** Test chưa bao giờ đỏ không chứng minh gì; nó có thể
   đang xanh vì khẳng định rỗng.
   ```bash
   cp <file-nguon> /tmp/bak                    # sao lưu trước
   # sửa nguồn cho VI PHẠM đúng bất biến vừa viết
   python -m pytest tests/guards/test_<tên>.py -q   # PHẢI đỏ, và đỏ ĐÚNG ở test của bạn
   cp /tmp/bak <file-nguon>                    # khôi phục
   python -m pytest tests/guards/test_<tên>.py -q   # xanh lại
   ```
   Đỏ ở test khác, hoặc đỏ vì `ImportError`/lỗi cú pháp, **không tính** — sửa lại rồi thử lần nữa.

4. **Đăng ký vào `docs/design/invariants.yaml`** với `enforced_by` trỏ tới `đường/dẫn::tên_hàm_test`.
   `tests/guards/test_invariants_registry.py` đỏ nếu bất biến trỏ tới test không tồn tại, hoặc nếu có file
   lưới canh nào không được bất biến nào nhận (lưới không có lý do tồn tại thì gỡ).

5. **Chạy `python scripts/ci_local.py`** rồi mở PR. `tests/guards/` là vùng bảo vệ: thêm lưới mới thì được,
   sửa/xoá lưới cũ cần người duyệt.

## Khi một lưới đỏ mà PR của bạn hợp lệ

Đừng nới lưới để qua. Theo R80.3: đọc hàm sinh ra đầu ra thật (không suy từ tên test) → viết lại bất biến
kết quả cần giữ vĩnh viễn → viết lại lưới theo bất biến đó → **chứng minh lưới mới vẫn đỏ với đúng lỗi lưới
cũ bắt** → PR có người duyệt.

## Bẫy hay gặp

- **Khẳng định quá chặt hơn bất biến thật.** Ví dụ khoá "danh sách sắp theo độ dài" trong khi điều thật sự
  cần là "mẫu cụ thể luôn đứng sau mẫu rộng chứa nó" — cái sau đúng với cả cách sắp khác.
- **Lưới đọc chính đầu ra mình vừa sinh** trong cùng tiến trình ⇒ luôn xanh. Đọc file trên đĩa, hoặc đối
  chiếu với nguồn độc lập.
- **Mutation không đổi đầu ra** ⇒ bộ sinh/hàm kiểm đang trả hằng. Thêm một test nhỏ chứng minh đầu ra đổi
  khi nguồn đổi (xem `tests/guards/test_diagrams_dong_bo.py::test_bo_sinh_doc_nguon_that_khong_tra_van_ban_hang`).
