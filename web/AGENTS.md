# web/AGENTS.md — Luật bổ sung khi làm trong `web/`

> Luật chung vẫn là `../AGENTS.md` (đọc trước). File này chỉ THÊM luật riêng của frontend; nếu hai file
> mâu thuẫn, file gốc thắng và mâu thuẫn phải được báo. Chi tiết: `../docs/rules/30-frontend.md`.

1. **Giao diện không tính con số nghiệp vụ.** Chỉ hiển thị nguyên văn số backend trả về, kèm nhãn nguồn
   (`source`) và nhãn "ước tính" khi backend đánh dấu. Cần số mới ⇒ đề nghị endpoint, không tính trong TypeScript.
2. **Không gọi mô hình ngôn ngữ từ trình duyệt.** Mọi lời gọi LLM đi qua backend.
3. **Hợp đồng API là `../contracts/openapi.json`.** Không gọi endpoint không có trong đó; không đoán trường.
   Mỗi tài nguyên một module trong `src/lib/api/`; `src/lib/api/http.ts` là làn độc quyền `web-api-core`.
4. **Mọi màn hình có đủ trạng thái:** đang tải · rỗng · lỗi có nút thử lại · không đủ quyền.
5. **Nội dung chưa được người duyệt không được trông như đã duyệt** — trạng thái hiển thị bằng chữ, không
   chỉ bằng màu.
6. **Không lưu dữ liệu định danh/nhạy cảm trong `localStorage`/`sessionStorage`.**
7. **Biến `NEXT_PUBLIC_*` được nhúng lúc BUILD.** Thiếu `NEXT_PUBLIC_API_BASE_URL` trên Vercel thì bản dựng
   phải đổ (`next.config.ts` đã chặn) — đừng đổi `throw` thành cảnh báo.
8. **E2E không bật retry** (`playwright.config.ts` giữ `retries: 0`): chạy lại tới khi xanh là biến lỗi
   chập chờn thành lỗi vô hình. Đỏ thì đọc trace/ảnh chụp trước.
9. Trước khi báo xong: `npm run lint` và `npm run build` trong `web/`.
