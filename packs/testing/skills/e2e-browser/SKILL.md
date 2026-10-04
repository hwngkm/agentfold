---
name: e2e-browser
description: Viết và sửa test E2E giao diện bằng Playwright — chọn luồng đáng test, định vị phần tử theo vai trò/nhãn, chờ theo trạng thái thay vì theo giờ, dữ liệu test tự dọn, không retry che lỗi; dùng Playwright MCP để agent xem trình duyệt thật khi tái hiện lỗi. Dùng khi thêm hoặc sửa test trong web/e2e, khi E2E đỏ trên CI, khi cần tái hiện lỗi giao diện, hoặc trước khi tin một màn hình "chạy được" mà chưa ai bấm thử.
---

# E2E trên trình duyệt: ít, chắc, đọc được khi đỏ

Cấu hình gốc: `web/playwright.config.ts` — `retries: 0`, `workers: 1`, trace + ảnh chụp khi lỗi,
`reuseExistingServer: false`. Lưới canh `tests/guards/test_deploy_waits_for_ci.py` khoá `retries: 0`.

## 1. Chọn luồng

E2E chỉ cho **luồng người dùng xuyên nhiều tầng** mà test đơn vị/tích hợp không thấy: đăng nhập → làm việc chính
→ thấy kết quả. Một luồng quan trọng = một spec. Phép tính, nhánh lỗi chi tiết: test ở tầng dưới (skill
`test-strategy`).

## 2. Xem trước khi viết

Pack này bật MCP `playwright` (`npx @playwright/mcp@latest`, chạy cục bộ). Trước khi viết spec, cho agent mở
trang thật, bấm theo luồng, chụp màn hình — viết spec theo **cái đã thấy**, không theo cái đoán từ mã nguồn.
Không dùng MCP này với trang chứa dữ liệu thật của người dùng hay phiên đăng nhập production.
Không có MCP: `npx playwright codegen <url>` mở trình duyệt và ghi thao tác thành mã test;
`npx playwright screenshot <url> anh.png` để xem trang — cùng kết quả, không cần kết nối nào.

## 3. Định vị và chờ

- Định vị theo thứ người dùng thấy: `getByRole("button", { name: "Lưu" })`, `getByLabel`, `getByText`. Thiếu nhãn
  truy cập được thì đó là lỗi a11y của giao diện — sửa giao diện, đừng chuyển sang CSS selector.
- `data-testid` chỉ khi không có vai trò/nhãn hợp lý.
- **Không `waitForTimeout`.** Chờ theo trạng thái: `await expect(locator).toBeVisible()`,
  `await page.waitForResponse(...)`. Chờ theo giờ là nguồn chập chờn số một (skill `flaky-tests`).

## 4. Dữ liệu

- Mỗi spec tự tạo dữ liệu nó cần (qua API hoặc seed) và không phụ thuộc spec khác chạy trước.
- Không chạy E2E vào CSDL production. `docker compose up` dựng CSDL riêng (`docker-compose.yml`).
- Biến `NEXT_PUBLIC_*` nhúng lúc build/khởi động: đổi API URL thì build lại, không dùng server cũ.

## 5. Khi E2E đỏ trên CI

1. Tải artifact (trace, ảnh chụp, báo cáo HTML) của job `web`; mở trace: `npx playwright show-trace <file.zip>`.
2. Tái hiện cục bộ: `cd web && npx playwright test e2e/<spec>.spec.ts --headed`.
3. Đỏ thật → sửa code. Đỏ do test (chờ sai, định vị mơ hồ) → sửa test, ghi lý do. **Không** bật retry, không
   thêm `test.skip`, không chạy lại job tới khi xanh (R50.5).

## 6. Lệnh

```bash
cd web
npx playwright install chromium        # lần đầu mỗi máy
npm run build && npx playwright test   # như CI
npx playwright test --ui               # gỡ lỗi tương tác
```
