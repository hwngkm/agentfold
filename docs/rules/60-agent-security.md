# RULE 60 — Bảo mật: agent sản phẩm và agent phát triển

> Owner: **R1** (agent sản phẩm) + **R3** (bí mật, hạ tầng). Code: `src/llm/safety.py`, `src/agents/actions.py`.

## A. Agent trong sản phẩm

### R60.1 — Code là hàng rào, prompt thì không

Câu chữ trong system prompt chỉ giúp mô hình hợp tác. Ràng buộc thật: schema đầu ra hẹp, lõi tất định tính lại
mọi con số, cổng duyệt của người. Vì hậu quả đã bị chặn ở tầng code, gặp injection thì **ghi log và chạy tiếp**;
chặn cứng theo mẫu chuỗi tạo báo động giả làm hỏng luồng thật. **Rò rỉ thì chặn cứng** — không có hàng rào nào sau nó.

### R60.2 — Dữ liệu ngoài là dữ liệu, không bao giờ là mệnh lệnh

Dữ liệu ngoài gồm: văn bản người dùng nhập, dữ liệu nhập hàng loạt/crawl, đoạn truy hồi từ tài liệu, ghi chú tự do
của người duyệt. Trước khi vào prompt: `sanitize_untrusted` (chuẩn hoá, **làm phẳng xuống dòng**, cắt độ dài) →
`fence` (khối có nhãn "dữ liệu, không phải chỉ thị") → `scan_for_injection` (ghi log). Xuống dòng là công cụ tấn
công chính: trong prompt phẳng, `\n\nQUY TẮC MỚI:` đọc y hệt chỉ thị hệ thống.

### R60.3 — Chặn rò rỉ trước mọi lần gửi ra ngoài

`assert_no_egress(text, known_secrets=...)` trước khi gửi tới dịch vụ ngoài: khoá API, JWT, chuỗi kết nối CSDL,
giá trị bí mật trong cấu hình, email, số điện thoại, số định danh. Thông điệp lỗi nêu LOẠI, không nêu giá trị —
lỗi đi vào log và về client. Prompt chỉ chứa trường nghiệp vụ tối thiểu, không danh tính.

### R60.4 — Sổ hành động rủi ro, fail closed

Mọi hành động agent làm được khai trong `src/agents/actions.py`: LOW (đọc/tính) · MEDIUM (ghi dữ liệu của chính
người dùng, có audit) · HIGH (tới người dùng cuối, ra ngoài hệ thống, đổi dữ liệu dùng chung — **bắt buộc vai trò
người duyệt**). Chưa khai = HIGH. HIGH mà không khai vai trò duyệt thì test đỏ.

### R60.5 — Điều tra được sau sự cố

Trả lời được: ai làm, lúc nào, dữ liệu trước/sau, dữ liệu ngoài nào đã vào prompt (log mẫu cắt ≤ 60 ký tự — mẫu
đáng ngờ có thể chính là dữ liệu định danh).

### R60.6 — Bộ test tấn công

Mỗi lớp tấn công có ít nhất một test đánh vào đường đi thật của dữ liệu: ghi đè chỉ thị · giả vai trò · thoát
schema (ép trả trường tiền/số) · moi bí mật · moi dữ liệu người khác · vượt ranh giới miền · vượt cổng duyệt.
Mỗi bộ tấn công kèm bộ "không báo động giả". Test phải chứng minh ĐỎ khi gỡ lớp phòng thủ.

## B. Agent phát triển (AI viết code cho repo)

### R60.7 — Bí mật không đi qua agent

Không dán khoá vào chat. `.mcp.json` nằm trong git: chỉ tham chiếu `${TEN_BIEN}`, hoặc thêm server ở phạm vi cá
nhân (ngoài repo). MCP tới CSDL/cloud mặc định chỉ đọc. Lỡ lộ: thu hồi khoá trước, xoá khỏi file sau.
Server MCP dùng chung cho cả đội chỉ vào `.mcp.json` qua pack (`python scripts/packs.py --install <pack>`): khai một
nơi trong `packs/registry.yaml` kèm `why` nói rõ gửi gì ra ngoài, và tự gỡ khi tắt pack.

### R60.8 — Quyền tối thiểu cho agent

Token/tài khoản của agent không có quyền duyệt PR, gắn nhãn `human-approved`, sửa branch protection hay xoá nhánh
`main`. Agent không có quyền ghi CSDL production; script ghi dữ liệu mặc định chạy thử.

### R60.9 — Bên bị kiểm không cầm bộ kiểm

`tools/`, `coordination/`, `tests/guards/`, `.github/workflows/` là vùng bảo vệ. Trên CI, bộ kiểm phạm vi chạy
bằng công cụ lấy từ commit GỐC của PR. Workflow dùng `pull_request`, không `pull_request_target`.

### R60.10 — Chuỗi cung ứng

Thêm phụ thuộc là làn độc quyền, cần lý do trong PR. Ghim chính xác công cụ định dạng/kiểm tĩnh. Không chạy script
cài đặt từ nguồn không rõ; không để agent tự thêm MCP server hay kỹ năng từ internet mà không có người duyệt.
