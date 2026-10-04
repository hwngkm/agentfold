---
name: mcp-server
description: Đóng gói công cụ hoặc dữ liệu của dự án thành MCP server để agent (Claude Code, ứng dụng khác) dùng — chọn transport cục bộ hay HTTP từ xa, xác thực và phân quyền, mặc định chỉ đọc, không để bí mật trong cấu hình, và kiểm bằng một client thật trước khi phát hành. Dùng khi muốn cho agent truy cập hệ thống nội bộ, CSDL hay API của dự án, khi thiết kế MCP server mới, hoặc khi thêm server vào .mcp.json của dự án.
---

# MCP server: mở cửa cho agent, nhưng chỉ đúng cửa

Thiết kế từng công cụ trong server theo skill `tool-design`. Skill này lo phần **server**: transport, xác thực,
phạm vi, phát hành. Plugin `mcp-server-dev` (pack này gợi ý) có hướng dẫn chi tiết theo từng mô hình triển khai.
Không có plugin: đặc tả và SDK chính thức tại modelcontextprotocol.io đủ cho mọi bước dưới đây.

## 1. Chọn transport

| Tình huống | Transport | Lưu ý |
|---|---|---|
| Công cụ chạy trên máy người dùng, dữ liệu cục bộ | stdio (tiến trình con) | không mở cổng mạng; lệnh khởi chạy ghim phiên bản |
| Dịch vụ dùng chung cho nhiều người/agent | HTTP từ xa | bắt buộc xác thực; TLS; giới hạn tốc độ |

## 2. Phạm vi và quyền

- **Mặc định chỉ đọc.** Công cụ ghi thêm sau, từng cái, có lý do và mức rủi ro (R60.7: MCP tới CSDL/cloud mặc định
  chỉ đọc).
- Server tới CSDL dùng tài khoản CSDL riêng có quyền tối thiểu, không dùng tài khoản ứng dụng.
- Kết quả trả về không chứa bí mật, dữ liệu định danh vượt mức cần thiết (R40.8).

## 3. Xác thực và bí mật

- Server HTTP: token/OAuth; mỗi người/agent một danh tính để audit được.
- Cấu hình phía client trong `.mcp.json` (được commit) chỉ dùng `${TEN_BIEN}` — lưới `test_mcp_no_secrets.py` chặn
  khoá thô. Server dùng chung cả đội: khai trong `packs/registry.yaml` (`kind: mcp`, có `why`) để
  `scripts/packs.py` tự đồng bộ, không `claude mcp add` tay ở phạm vi project.

## 4. Kiểm trước khi phát hành

1. Test từng công cụ như hàm thường (không cần client).
2. Kết nối bằng client thật (Claude Code với server trong `.mcp.json`, hoặc công cụ kiểm tra MCP) — liệt kê được công
   cụ, gọi được từng cái, lỗi trả về đọc được.
3. Thử chèn lệnh: dữ liệu trả về chứa câu "bỏ qua hướng dẫn trước…" — client không được làm theo; server không được
   tự hành động theo nội dung dữ liệu.
4. Ghi phiên bản server; đổi tên/schema công cụ là thay đổi phá vỡ với client (như skill `api-contract`).

## 5. Vận hành

Log mỗi lời gọi (ai, công cụ nào, tham số đã che phần nhạy cảm, kết quả, thời gian) — skill `observability`.
Thu hồi được quyền một client mà không ảnh hưởng client khác.
