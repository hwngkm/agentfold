# RULE 30 — Frontend

> Owner: **R4**. Tóm tắt cho agent: `web/AGENTS.md`.

## R30.1 — Giao diện không tính con số nghiệp vụ

Hiển thị nguyên văn số backend trả về, kèm nguồn và nhãn "ước tính" khi backend đánh dấu. Cần số mới ⇒ đề
nghị endpoint. Làm tròn/định dạng hiển thị thì được; cộng, nhân, quy đổi đơn vị nghiệp vụ thì không.

## R30.2 — Không gọi mô hình ngôn ngữ từ trình duyệt

Khoá API không bao giờ tới client; mọi lời gọi mô hình qua backend (nơi có egress guard và audit).

## R30.3 — Hợp đồng API là `contracts/openapi.json`

Mỗi tài nguyên một module trong `web/src/lib/api/` (không một file client khổng lồ mọi nhánh cùng sửa — một
file `api.ts` như vậy thành điểm nóng xung đột). `web/src/lib/api/http.ts` là làn độc quyền `web-api-core`.

## R30.4 — Đủ trạng thái cho mọi màn hình

Đang tải · rỗng · lỗi có nút thử lại · không đủ quyền · hết phiên. Backend trên gói miễn phí có cold start
~50 giây: giao diện phải nói "đang khởi động máy chủ", không để người dùng tưởng hỏng.

## R30.5 — Trạng thái duyệt không chỉ bằng màu

Nội dung chưa duyệt không được trông như đã duyệt; nhãn bằng chữ, đạt tương phản WCAG.

## R30.6 — Không lưu dữ liệu nhạy cảm phía client

Không dữ liệu định danh/sức khoẻ/tài chính trong `localStorage`/`sessionStorage`. Token theo cơ chế đã chốt ở ADR.

## R30.7 — Biến môi trường được nhúng lúc BUILD

`NEXT_PUBLIC_*` nằm cứng trong bản dựng. `web/next.config.ts` làm bản dựng Vercel ĐỔ khi thiếu
`NEXT_PUBLIC_API_BASE_URL` hoặc trỏ localhost — một dòng tài liệu là tấm biển, bản dựng đổ là bức tường.
Trên Vercel, biến đặt riêng cho Production/Preview/Development: đặt đủ cả ba.

## R30.8 — E2E

`retries: 0` (chạy lại tới khi xanh là biến lỗi chập chờn thành vô hình). Lưu trace + ảnh chụp khi đỏ; CI tải
lên artifact. Mỗi spec dựng dữ liệu riêng — không dùng chung tài khoản mẫu giữa các spec (chạy riêng xanh,
chạy chung đỏ). Thêm spec vào CI từng cái một.

## R30.9 — Truy cập được

Chữ ≥ 16px cho nội dung chính, vùng chạm ≥ 44×44px, điều hướng bàn phím, nhãn cho trình đọc màn hình, tôn
trọng `prefers-reduced-motion`.

## R30.10 — Kiểm trước khi báo xong

`npm run lint` và `npm run build` trong `web/`. `lint` không bắt mọi thứ `build` bắt (và ngược lại) — chạy cả hai.
