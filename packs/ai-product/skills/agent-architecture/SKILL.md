---
name: agent-architecture
description: Thiết kế phần AI của một sản phẩm — chọn mức tự chủ thấp nhất đủ dùng (hàm tất định, một lời gọi mô hình, chuỗi bước cố định, agent có công cụ), đặt ranh giới giữa mô hình và code, giới hạn vòng lặp, ngân sách và điểm dừng, và cách kiểm từng phần riêng. Dùng khi bắt đầu một tính năng AI mới, khi định chuyển một luồng sang "agent", khi agent chạy lan man hoặc tốn kém, hoặc khi viết ADR cho kiến trúc AI.
---

# Kiến trúc AI: tự chủ ít nhất có thể, ranh giới rõ nhất có thể

Ranh giới sẵn có của template (`contracts/boundaries.yaml`, R20.14–R20.19): `src/domain` tất định không gọi mô hình;
SDK nhà cung cấp chỉ trong `src/llm`; `src/agents` điều phối; mô hình **chọn**, code **tính** (INV-005).

## 1. Thang tự chủ — chọn bậc thấp nhất giải được bài toán

| Bậc | Hình dạng | Khi đủ |
|---|---|---|
| 0 | Hàm tất định / quy tắc | đầu vào có cấu trúc, quy tắc biết trước |
| 1 | Một lời gọi mô hình, structured output | phân loại, trích xuất, chọn từ danh mục (mẫu: `src/agents/quote_agent.py`) |
| 2 | Chuỗi bước cố định, mỗi bước một lời gọi | các bước biết trước, cần kiểm giữa chừng |
| 3 | Agent có công cụ, tự chọn bước | số bước/thứ tự thật sự không biết trước |

Lên một bậc phải có lý do đo được (bậc dưới thất bại ở ca nào) — ghi vào ADR (skill `adr`). Bậc 3 khó kiểm, khó
đoán chi phí, khó giải thích cho người duyệt.

## 2. Ranh giới mô hình ↔ code

- Mô hình trả **lựa chọn** (id, nhãn, đoạn trích) qua schema hẹp `extra="forbid"` (skill `prompt-io`); mọi con số
  nghiệp vụ code tính từ dữ liệu có nguồn.
- Dữ liệu ngoài vào prompt qua `sanitize_untrusted` + `fence`; văn bản ra ngoài qua `assert_no_egress`
  (`src/llm/safety.py`).
- Mọi hành động của agent khai trong `src/agents/actions.py` theo mức rủi ro; HIGH qua `require_approval`
  (skill `human-in-the-loop`).

## 3. Giới hạn cứng (bậc 2–3)

- Trần số bước/lời gọi mỗi yêu cầu, trần token đầu ra, timeout mỗi lời gọi và toàn yêu cầu (R20.16).
- Hết trần → dừng với lỗi rõ ràng và trạng thái dở dang lưu được, không lặp vô hạn, không âm thầm trả kết quả nửa vời.
- Ngân sách chi phí mỗi yêu cầu, đo từ `usage` thật (skill `token-economics`).

## 4. Kiểm được từng phần

- Gateway giả lập (`ScriptedGateway` trong `src/llm/gateway.py`) để test luồng mà không gọi mô hình thật.
- Mỗi bước có đầu vào/đầu ra kiểu rõ → test riêng; agent bậc 3 thì lưu toàn bộ quỹ đạo (lời gọi, công cụ, kết
  quả) để đọc lại khi sai.
- Chất lượng đo bằng eval có golden set (skill `eval-harness`), không bằng vài lần thử tay.

## Đầu ra

ADR ngắn: bậc tự chủ đã chọn và vì sao bậc thấp hơn không đủ · sơ đồ luồng (skill `diagram`) · danh sách hành
động + mức rủi ro · giới hạn cứng · cách đo chất lượng.
