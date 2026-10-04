---
name: human-in-the-loop
description: Đặt người vào đúng chỗ trong luồng AI — xác định hành động nào cần người duyệt theo mức rủi ro, thiết kế màn hình duyệt hiện đủ bằng chứng để quyết nhanh và đúng, ghi audit, xử lý khi người từ chối hoặc sửa, và đo xem người có thực sự đọc hay chỉ bấm duyệt. Dùng khi tính năng AI tạo ra nội dung tới người dùng cuối hoặc hành động không đảo ngược được, khi thêm hành động HIGH vào sổ hành động, hoặc khi thiết kế quy trình chuyên gia duyệt (y khoa, pháp lý, tài chính).
---

# Người trong vòng lặp: cổng duyệt chỉ có giá trị nếu người duyệt thấy đủ để quyết

Cơ chế có sẵn: `src/agents/actions.py` — hành động HIGH bắt buộc `requires_role`, `require_approval` ném
`ApprovalRequiredError`; hành động chưa khai = HIGH (INV-006). R10.4: người là cổng cuối.

## 1. Chỗ nào cần người

| Hành động | Mức | Người |
|---|---|---|
| Đọc, tính toán, gợi ý chỉ người dùng hiện tại thấy | LOW | không |
| Ghi dữ liệu của chính người dùng | MEDIUM | không, nhưng audit + hoàn tác được |
| Nội dung tới người dùng cuối/bệnh nhân/khách; gửi ra ngoài; đổi dữ liệu dùng chung; không đảo ngược được | HIGH | vai trò duyệt khai rõ |

Nghi ngờ thì xếp cao hơn (R00.2 fail closed). Nội dung chuyên môn (liều thuốc, tư vấn pháp lý) cần người có chuyên
môn đúng vai trò — agent không tự duyệt thay, kể cả khi nội dung đúng.

## 2. Màn hình duyệt

Người duyệt cần thấy trong MỘT màn hình:
- **Cái sẽ xảy ra** (nội dung sẽ gửi, thay đổi sẽ ghi) — nguyên văn, không tóm tắt.
- **Bằng chứng**: nguồn của từng con số/khẳng định, đoạn trích, quy tắc đã áp; phần mô hình tự sinh đánh dấu rõ.
- **Điểm bất định**: chỗ hệ thống không chắc, cảnh báo, giá trị gần ngưỡng.
- Hành động: Duyệt · Sửa rồi duyệt · Từ chối (bắt buộc lý do). Trạng thái hiển thị bằng chữ (R30.5).

## 3. Sau quyết định

- Ghi audit: ai (vai trò), quyết gì, lúc nào, phiên bản nội dung, lý do khi từ chối/sửa, trace id.
- Từ chối → không gửi; nội dung quay về trạng thái nháp hoặc huỷ; người tạo yêu cầu được báo.
- Sửa → lưu cả bản AI và bản người sửa: đó là dữ liệu quý nhất để cải thiện hệ thống (đưa vào golden set).

## 4. Đo xem cổng có thật

- Thời gian duyệt mỗi mục, tỷ lệ duyệt không sửa, tỷ lệ từ chối theo loại.
- Tỷ lệ duyệt gần 100% với thời gian vài giây/mục → người đang bấm cho qua; cổng chỉ còn hình thức. Báo người phụ
  trách, xem lại khối lượng và màn hình duyệt.
- Định kỳ chèn vài mục đã biết sai (có thông báo trước với nhóm) để kiểm cổng còn bắt được lỗi.

## Test

`require_approval` từ chối sai vai trò và hành động chưa khai (đã có `tests/unit/test_api.py`,
`tests/unit/test_llm_boundary.py`); thêm test cho mỗi hành động HIGH mới.
