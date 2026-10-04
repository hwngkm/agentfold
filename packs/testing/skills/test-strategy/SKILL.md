---
name: test-strategy
description: Chọn đúng tầng test cho một thay đổi theo rủi ro (đơn vị, tích hợp, hợp đồng, E2E, lưới canh) thay vì chạy theo % coverage; mỗi bất biến có ít nhất một test đỏ được khi bị phá. Dùng khi lập kế hoạch test cho ticket mới, khi không biết nên viết test ở tầng nào, khi bộ test chậm hoặc vỡ vặt, hoặc khi review thấy "có test" mà không chắc test bảo vệ điều gì.
---

# Chiến lược test: test bảo vệ RỦI RO, không bảo vệ con số coverage

Câu hỏi đúng cho mỗi thay đổi không phải "đã đủ 80% chưa" mà là **"nếu cái này hỏng, test nào đỏ?"**. Không trả
lời được thì chưa có test, dù coverage bao nhiêu.

## 1. Liệt kê rủi ro TRƯỚC khi viết test

Với ticket đang làm, viết 3–7 dòng "nếu sai thì": *tính sai tiền*, *lộ dữ liệu người khác*, *migration hỏng trên
Postgres thật*, *nút bấm không làm gì*… Sắp theo **tác hại × khả năng**. Rủi ro nào nằm trong
`docs/design/invariants.yaml` thì test của nó là **lưới canh** (skill `guard-net`), không phải test thường.

## 2. Chọn tầng theo rủi ro

| Rủi ro nằm ở | Tầng | Trong template |
|---|---|---|
| Logic tất định (tính toán, quy tắc, chuyển trạng thái) | **Đơn vị** — nhanh, nhiều ca biên | `tests/unit/`, nhắm `src/domain/` |
| Chỗ nối hai thành phần (API ↔ CSDL, code ↔ SDK mô hình) | **Tích hợp** — thành phần thật hoặc giả mạo có kiểm | `tests/unit/test_api.py`, job `migration-postgres` |
| Hợp đồng giữa hai bên (backend ↔ frontend, làn ↔ làn) | **Hợp đồng** — so bản chụp/schema | `tests/guards/test_openapi_contract.py` |
| Luồng người dùng chạy qua nhiều tầng | **E2E** — ít, chỉ luồng quan trọng | `web/e2e/` (skill `e2e-browser`) |
| Thứ CẤM xảy ra (bất biến, cấu trúc repo, cổng deploy) | **Lưới canh** | `tests/guards/` |

Quy tắc kéo xuống: cái gì test được ở tầng thấp hơn thì test ở tầng thấp hơn. E2E chỉ cho **sự nối** mà tầng dưới
không thấy được — không dùng E2E để kiểm phép tính.

## 3. Mỗi test phải đỏ được

- Viết test → **thấy nó đỏ** (trước khi có code, hoặc gỡ tạm bản vá) → rồi mới xanh (skill `tdd-loop`).
- Test chưa từng đỏ có thể đang kiểm sai thứ: assert vào giá trị mock trả về, so một thứ với chính nó, hoặc
  không bao giờ chạy tới dòng assert.
- Với bộ kiểm (validator, guard): luôn có một ca **đầu vào hỏng thật** và xác nhận nó bị bắt (`test_bo_kiem_bat_...`).

## 4. Giả mạo (mock) ở đâu

- Mock **ranh giới ngoài** (mạng, đồng hồ, mô hình ngôn ngữ, dịch vụ trả tiền) — không mock code của chính mình.
- Ranh giới có hợp đồng thì giả mạo phải **kiểm được với bản thật** ít nhất ở một job (vd. migration chạy trên
  Postgres thật ở CI, không chỉ SQLite).
- Đồng hồ: cố định thời gian (`AGENTCTL_NOW`, tham số `moment`) — test phụ thuộc giờ thật sẽ đỏ lúc nửa đêm UTC.

## 5. Khi nào KHÔNG cần test mới

Đổi tài liệu, đổi tên biến trong phạm vi một hàm, đổi định dạng — không thêm test. Đổi hành vi mà không thêm/sửa
test nào là dấu hiệu thiếu, ghi vào PR vì sao.

## Đầu ra

Trong PR (mục "Bằng chứng" của `.github/pull_request_template.md`): bảng *rủi ro → test bảo vệ → đã thấy đỏ
(có/không)*. Rủi ro chưa có test thì ghi thẳng, không giấu.
