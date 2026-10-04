---
name: ui-component
description: Dựng hoặc sửa một component/màn hình React (Next.js) đủ trạng thái — đang tải, rỗng, lỗi có nút thử lại, không đủ quyền — dùng được bằng bàn phím và trình đọc màn hình, hiển thị nguyên văn số liệu backend kèm nguồn, kiểm ở các bề rộng màn hình thật. Dùng khi thêm màn hình hoặc component mới trong web/, khi sửa giao diện bị báo khó dùng, hoặc khi review một PR frontend.
---

# Component: đủ trạng thái, truy cập được, không tự tính nghiệp vụ

Luật bắt buộc: `web/AGENTS.md` và `docs/rules/30-frontend.md`. Skill này là thủ tục làm cho đúng các luật đó.

## 1. Trước khi viết

- Dữ liệu đến từ endpoint nào trong `contracts/openapi.json`? Chưa có → dừng, đề nghị endpoint (skill
  `api-contract`), không tự ghép từ endpoint khác hay tính trong TypeScript (R30.1).
- Gọi API qua module tài nguyên trong `web/src/lib/api/` (một tài nguyên một file); `http.ts` là làn độc quyền.

## 2. Bốn trạng thái + một

| Trạng thái | Hiển thị | Kiểm |
|---|---|---|
| Đang tải | khung chờ hoặc chữ "Đang tải…"; backend cold start thì nói "đang khởi động máy chủ" (R30.4) | giả lập mạng chậm |
| Rỗng | câu giải thích + hành động tiếp theo, không bảng trống | dữ liệu rỗng |
| Lỗi | thông điệp người đọc được + nút **Thử lại**; mã trace nếu backend trả | tắt backend |
| Không đủ quyền / hết phiên | nói rõ, dẫn tới đăng nhập | token hết hạn |
| Có dữ liệu | số liệu nguyên văn + nhãn nguồn, nhãn "ước tính" khi backend đánh dấu | dữ liệu thật mẫu |

## 3. Truy cập được (a11y)

- Phần tử tương tác là `<button>`/`<a>` thật, không `<div onClick>`; vùng bấm ≥ 44×44 px (đã đặt trong
  `globals.css`).
- Mọi ô nhập có `<label>`; lỗi form gắn với ô bằng `aria-describedby`.
- Đi hết luồng bằng Tab/Shift+Tab/Enter; focus nhìn thấy được; mở hộp thoại thì focus vào trong và trả lại khi đóng.
- Trạng thái (đã duyệt, lỗi) bằng chữ, không chỉ bằng màu (R30.5); tương phản đạt WCAG AA.

## 4. Responsive

Kiểm ở các bề rộng thật: ~360 px (điện thoại), ~768 px, ≥1280 px. Không cuộn ngang ở 360 px. Bảng dài trên điện
thoại → dạng thẻ hoặc cuộn trong vùng riêng có nhãn.

## 5. Kiểm

```bash
cd web && npm run lint && npm run build
```

Mở trang thật (hoặc qua MCP `playwright` của pack) đi qua cả năm trạng thái, chụp màn hình đính kèm PR. Luồng quan
trọng → thêm E2E (skill `e2e-browser` của pack `testing`).
Không có MCP: `cd web && npx playwright screenshot http://127.0.0.1:3000/<trang> trang.png` (thêm
`--viewport-size=360,800` cho điện thoại) hoặc chụp tay bằng DevTools.
