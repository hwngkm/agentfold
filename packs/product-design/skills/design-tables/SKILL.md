---
name: design-tables
description: Lập các bảng cấu trúc thiết kế mà sơ đồ không diễn đạt đủ — bảng yêu cầu có truy vết tới test, ma trận quyền vai trò × hành động, bảng chuyển trạng thái, danh mục lỗi, bảng tích hợp ngoài, sổ rủi ro — dạng Markdown trong repo để review và kiểm bằng máy được. Dùng khi chốt yêu cầu cho một bản phát hành, khi thiết kế phân quyền hay quy trình duyệt, khi thực thể có vòng đời, khi cần chứng minh mọi yêu cầu đều có test, hoặc khi chuẩn bị review thiết kế.
---

# Bảng thiết kế: thứ cần ĐỦ và KHÔNG MÂU THUẪN thì viết thành bảng

> Các dòng trong bảng dưới đây là ví dụ minh hoạ theo miền mẫu "báo giá" của template — thay bằng nghiệp vụ thật.

Sơ đồ cho thấy hình dạng; bảng cho thấy **đủ hay thiếu**. Ma trận quyền 6 vai trò × 15 hành động vẽ thành sơ đồ thì
không ai kiểm được ô trống. Bảng lưu trong `docs/design/` (vùng bảo vệ `design` — đổi qua PR có duyệt); bảng nào cũng
có cột trỏ tới nơi kiểm chứng.

## 1. Bảng yêu cầu có truy vết

| Mã | Yêu cầu (đo được) | Ưu tiên | Nguồn (PRD/người) | Thiết kế | Ticket | Test chứng minh |
|---|---|---|---|---|---|---|
| YC-03 | Báo giá chưa duyệt không gửi được cho khách | phải có | PRD §2 | máy trạng thái `quote` | API-04 | `tests/unit/test_quotes_api.py::test_chua_duyet_khong_gui` |

Cột "Test chứng minh" trống ở yêu cầu "phải có" = chưa xong. Đây là đầu vào cho skill `test-strategy`.

## 2. Ma trận quyền (vai trò × hành động)

| Hành động | Mức rủi ro | khách | nhân viên | người duyệt | quản trị |
|---|---|---|---|---|---|
| xem báo giá của mình | LOW | ✅ | ✅ | ✅ | ✅ |
| duyệt báo giá | HIGH | ❌ | ❌ | ✅ | ❌ |

Mỗi hành động khớp một mục trong `src/agents/actions.py` (mức rủi ro, `requires_role`). Mỗi ô ❌ của hành động HIGH là
một ca test bị từ chối. Ô bỏ trống không được phép — "chưa quyết" ghi rõ và mở câu hỏi (`new question`).

## 3. Bảng chuyển trạng thái

| Từ | Sự kiện | Đến | Ai được làm | Điều kiện | Tác dụng phụ |
|---|---|---|---|---|---|
| draft | gửi duyệt | pending_review | nhân viên | đủ dòng, mọi giá có nguồn | ghi audit |
| pending_review | duyệt | approved | người duyệt | — | ghi audit, cho phép gửi |
| pending_review | từ chối | draft | người duyệt | lý do bắt buộc | ghi audit, báo người tạo |

Cặp (trạng thái, sự kiện) không có trong bảng = **bị cấm** và phải có test chứng minh bị chặn. Bảng đi kèm sơ đồ
`stateDiagram-v2` (skill `diagram-roadmap`).

## 4. Danh mục lỗi

| Mã lỗi | HTTP | Khi nào | Thử lại được? | Thông điệp cho người dùng |
|---|---|---|---|---|
| `QUOTE_NOT_APPROVED` | 409 | gửi báo giá chưa duyệt | không | "Báo giá cần được duyệt trước khi gửi." |

Khớp `src/api/errors.py` và OpenAPI (skill `api-contract`).

## 5. Bảng tích hợp ngoài

| Hệ thống | Hướng | Dữ liệu gửi đi | Nhạy cảm | Xác thực | Timeout / thử lại | Khi hệ thống ngoài sập |
|---|---|---|---|---|---|---|

Mọi dòng có dữ liệu "cao" phải xuất hiện trong DFD có biên tin cậy và qua egress guard (R60).

## 6. Sổ rủi ro

| Rủi ro | Khả năng | Tác hại | Giảm bằng | Lưới canh / test | Chủ |
|---|---|---|---|---|---|

Rủi ro "cao × cao" mà cột lưới canh trống → đề xuất lưới (skill `guard-net`). Đầu vào cho skill `critical-debate` và
`project-audit` (pack `review-audit`).

## Kiểm bằng máy (khi bảng ổn định)

Bảng Markdown đọc được bằng script: lưới canh kiểm mọi hành động trong ma trận quyền có trong `actions.py`, mọi yêu cầu
"phải có" có test tồn tại, mọi trạng thái trong bảng có trong CHECK của cột `status`. Viết lưới khi bảng đã qua một
vòng duyệt — trước đó bảng còn đổi nhiều.
