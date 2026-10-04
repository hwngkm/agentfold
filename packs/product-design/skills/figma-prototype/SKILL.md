---
name: figma-prototype
description: Áp dụng tư duy thiết kế với Figma và FigJam — hiểu người dùng, định nghĩa vấn đề, phác ý tưởng trên FigJam, dựng khung dây rồi bản mẫu tương tác dùng biến/thành phần, thử với người thật, và bàn giao sang code qua token và Code Connect bằng MCP Figma chính thức. Dùng khi thiết kế màn hình hay luồng mới, khi cần bản mẫu để chốt với người dùng/chuyên gia/khách trước khi viết code, khi chuyển thiết kế Figma thành component, hoặc khi giao diện code lệch thiết kế.
---

# Bản mẫu với Figma: thiết kế để HỌC, rồi mới thiết kế để LÀM

Đi kèm pack: plugin `figma@claude-plugins-official` (MCP `https://mcp.figma.com/mcp`, đăng nhập OAuth — không khoá
nào trong repo). Giới hạn: tài khoản Starter hoặc ghế View/Collab chỉ có 6 lượt gọi công cụ MCP mỗi tháng — đủ để
thử, không đủ để làm việc hằng ngày; ghế Dev/Full trên gói trả phí có giới hạn theo phút. Kiểm gói trước khi lập kế hoạch.

## 1. Năm bước, mỗi bước một sản phẩm trên Figma

| Bước | Làm gì | Sản phẩm | Xong khi |
|---|---|---|---|
| **Thấu hiểu** | phỏng vấn, quan sát người dùng thật (vai trò thật) | FigJam: ghi chú quan sát, bản đồ hành trình hiện tại | có trích dẫn nguyên văn, không phải phỏng đoán của nhóm |
| **Định nghĩa** | gom quan sát thành vấn đề | một câu "Làm sao để [người dùng] [làm được việc] khi [ràng buộc]" + tiêu chí thành công đo được | người duyệt đồng ý câu vấn đề |
| **Ý tưởng** | nhiều phương án thô, chọn 1–2 | FigJam: phác thảo, luồng màn hình (sơ đồ có thể dựng bằng công cụ `generate_diagram` của MCP) | phương án chọn có lý do ghi lại |
| **Bản mẫu** | khung dây → bản mẫu tương tác chỉ đủ cho nhiệm vụ cần thử | Figma: frame + prototype links, dùng component và biến (variables) | đi được trọn nhiệm vụ thử, nội dung thật (không lorem ipsum) |
| **Thử** | 3–5 người đúng vai trò làm nhiệm vụ trên bản mẫu | ghi quan sát vào FigJam + `new log` | phát hiện đã thành ticket hoặc đã quyết bỏ |

Câu hỏi cần trả lời, cách chọn độ trung thực, cách thử với người: skill `ux-prototype` (pack `frontend`). Skill này
thêm phần làm việc trên Figma.

## 2. Dựng trên Figma cho đúng ngay từ đầu

- **Biến (variables) cho màu, khoảng cách, cỡ chữ**, đặt tên theo tầng semantic giống code (`color/action`,
  `space/stack`) — để bàn giao ra token CSS khớp skill `design-system`.
- **Component có biến thể** cho trạng thái: mặc định, đang tải, rỗng, lỗi, không đủ quyền (giống bảng trạng thái của
  skill `ui-component`). Màn hình chỉ vẽ trạng thái "đẹp" là bản mẫu chưa xong.
- Auto layout để thấy hành vi ở các bề rộng (~360 px, ~768 px, ≥ 1280 px).
- Dữ liệu mẫu giả nhưng giống thật về độ dài và định dạng (tên dài, số lớn, chuỗi rỗng). **Không dữ liệu thật của người
  dùng/bệnh nhân** — Figma là dịch vụ ngoài (R40.8).
- Nhãn trạng thái bằng chữ, không chỉ màu; kiểm tương phản (R30.5).

## 3. Bàn giao sang code

1. Chọn frame trong Figma, nhờ agent đọc bằng MCP: `get_design_context` (cấu trúc + gợi ý code), `get_variable_defs`
   (biến đang dùng), `get_screenshot` (ảnh để so).
2. Ánh xạ biến Figma → token CSS trong `web/src/app/globals.css`; biến chưa có token → thêm token semantic, không viết
   giá trị thẳng vào component.
3. Code Connect (`add_code_connect_map`) nối component Figma với component React đã có — lần sinh code sau dùng lại
   component thật thay vì sinh mới.
4. Dựng component theo skill `ui-component`; so ảnh màn hình code với `get_screenshot` ở cùng bề rộng.
5. Dữ liệu/endpoint thiết kế cần mà chưa có trong `contracts/openapi.json` → đề nghị endpoint (skill `api-contract`),
   không bịa trường.

## 4. Lưu vết trong repo

Link file Figma/FigJam (không có quyền xem thì không ai review được — kiểm quyền chia sẻ) đặt trong ticket và trong tài
liệu thiết kế; quyết định thiết kế đáng kể → DEC; câu vấn đề + tiêu chí thành công + kết quả thử → `new log`. Figma là
nơi làm việc, **repo là nơi lưu quyết định**.

## Không có Figma

Cùng năm bước với giấy, HTML tĩnh, hoặc plugin `playground`; bàn giao token thì viết tay vào `globals.css` theo skill
`design-system`. Đừng để thiếu công cụ thành lý do bỏ bước thử với người.
