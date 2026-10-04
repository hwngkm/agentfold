---
name: observability
description: Làm cho backend tự kể được chuyện gì đang xảy ra — log có cấu trúc với trace id xuyên request, phân loại lỗi có thể thử lại hay không, chỉ số tối thiểu (tỷ lệ lỗi, độ trễ theo phân vị), audit cho hành động quan trọng, và không để dữ liệu nhạy cảm lọt vào log. Dùng khi thêm endpoint hay tác vụ nền, khi lỗi production không truy được nguyên nhân từ log, khi thêm lời gọi dịch vụ ngoài, hoặc trước khi đưa tính năng lên production.
---

# Quan sát được: mỗi lỗi production phải truy được từ log trong vài phút

## 1. Log có cấu trúc

- Dùng `logging.getLogger(__name__)` (như `src/api/errors.py`); không `print` trong `src/` (vai trò reviewer bắt).
- Mỗi dòng log là một sự kiện có tên + trường: `logger.info("quote_created", extra={"quote_id": ..., "trace_id": ...})`.
  Ở production xuất JSON để tìm theo trường được.
- Mức log có nghĩa: `ERROR` = cần người xem; `WARNING` = bất thường tự hồi phục; `INFO` = sự kiện nghiệp vụ;
  `DEBUG` tắt ở production.

## 2. Trace id xuyên request

Nhận `X-Request-ID` từ client/proxy nếu có, không có thì sinh; gắn vào mọi log của request đó, trả lại trong
header response và trong thân lỗi. Người dùng báo lỗi kèm mã đó → tìm ra toàn bộ chuỗi sự kiện. Bản ghi audit
đã có cột `trace_id` (`src/db/models/audit.py`) — điền nó.

## 3. Phân loại lỗi

| Loại | Ví dụ | Xử lý |
|---|---|---|
| Lỗi người gọi | dữ liệu sai, thiếu quyền | 4xx, không log ERROR |
| Tạm thời, thử lại được | timeout dịch vụ ngoài, CSDL mất kết nối | thử lại có giới hạn + backoff; 503 kèm "thử lại được" |
| Lỗi hệ thống | bug, cấu hình sai | 500, log ERROR kèm trace id, KHÔNG lộ chi tiết cho client |

Mọi lời gọi ra ngoài có timeout. Không `except Exception: pass` — nuốt lỗi im lặng là thứ khó truy nhất.

## 4. Chỉ số tối thiểu

Theo từng endpoint/tác vụ: số request, tỷ lệ lỗi, độ trễ P50/P95/P99 tính từ mẫu thô (skill `latency-slo` nếu pack
`ai-llm` bật). Health: `/health` (sống) và `/health/ready` (phụ thuộc sẵn sàng) tách nhau.

## 5. Audit

Hành động thay đổi dữ liệu quan trọng hoặc rủi ro cao (INV-006): ghi ai (vai trò), làm gì, trên đối tượng nào, kết
quả, trace id — vào bảng audit, không chỉ vào log (log có thể bị xoay vòng mất).

## 6. Không lọt dữ liệu nhạy cảm

Không log: mật khẩu, token, khoá API, nội dung đầy đủ của prompt chứa dữ liệu người dùng, mã định danh gốc (R40.8).
Log mã đối tượng nội bộ thay vì nội dung. Kiểm bằng test: gọi endpoint với dữ liệu giả có dấu hiệu nhận biết, rồi
assert dấu hiệu đó không xuất hiện trong `caplog`.
