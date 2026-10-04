---
name: flaky-tests
description: Xử lý test chập chờn (lúc xanh lúc đỏ) như lỗi thật — tái hiện bằng chạy lặp, phân loại nguồn bất định (thời gian, thứ tự, đồng thời, mạng, dữ liệu chung), sửa nguồn chứ không bật retry hay skip. Dùng khi một test đỏ trên CI nhưng xanh khi chạy lại, khi CI đỏ ngẫu nhiên, hoặc khi ai đó đề xuất "chạy lại cho xanh".
---

# Test chập chờn: lỗi thật cho tới khi chứng minh khác

Một test lúc xanh lúc đỏ có hai khả năng, cả hai đều phải sửa: **code có điều kiện đua thật** (người dùng sẽ gặp),
hoặc **test bất định** (sẽ dạy cả đội lờ CI đỏ). Chạy lại tới khi xanh là giấu cả hai (R50.5).

## 1. Tái hiện bằng lặp

```bash
python -m pytest tests/unit/test_x.py::test_y -q --count=50 -x    # cần pytest-repeat; hoặc vòng for trong shell
for i in $(seq 1 50); do python -m pytest tests/unit/test_x.py::test_y -q -x || break; done
cd web && npx playwright test e2e/x.spec.ts --repeat-each=20
python -m pytest -p no:randomly tests/unit -q   # nếu dùng pytest-randomly: tắt để kiểm phụ thuộc thứ tự
```

Ghi tỷ lệ đỏ (vd. 3/50). Không tái hiện được sau ~50 lần cục bộ: so khác biệt môi trường với CI (múi giờ,
`TZ=UTC` mà `scripts/ci_local.py` ép, số CPU, phiên bản trình duyệt).

## 2. Phân loại nguồn

| Nguồn | Dấu hiệu | Sửa |
|---|---|---|
| Thời gian | đỏ quanh nửa đêm UTC, cuối tháng; `sleep` trong test | cố định đồng hồ; chờ theo trạng thái |
| Thứ tự | xanh khi chạy riêng, đỏ khi chạy cả bộ | mỗi test tự dựng/dọn dữ liệu; bỏ trạng thái toàn cục |
| Đồng thời | đỏ khi nhiều worker/luồng | khoá, giao dịch, hoặc test tuần tự có chủ ý |
| Mạng/dịch vụ ngoài | timeout lẻ tẻ | giả mạo ranh giới ngoài; test thật để job riêng |
| Dữ liệu chung | đỏ khi chạy song song với job khác | CSDL/thư mục riêng mỗi lần chạy (`tmp_path`) |
| Ngẫu nhiên | đỏ không quy luật | cố định seed, ghi seed vào thông điệp lỗi |
| Hệ điều hành | đỏ chỉ trên Windows/Linux | CRLF, đường dẫn, mã hoá — xem R50.11 |

## 3. Sửa và chứng minh

Sửa nguồn → chạy lặp lại đúng số lần đã tái hiện → 0 đỏ. Báo cáo: "trước 3/50, sau 0/200". Đỏ hiếm (vd. 1/200)
mà chưa sửa được: mở `new incident`, giữ test chạy (không skip), ghi giả thuyết và việc đã loại trừ.

## Cấm

`retries` > 0, `continue-on-error`, `@pytest.mark.flaky`, `test.skip` để CI xanh, tăng timeout mà không biết vì
sao chậm. Cả bốn đều bị lưới canh hoặc review chặn trong template.
