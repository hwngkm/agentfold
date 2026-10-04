---
name: diagram-roadmap
description: Biết sơ đồ nào cần thiết kế ở từng giai đoạn xây dựng sản phẩm (khám phá, yêu cầu, kiến trúc, thiết kế chi tiết, phần AI, triển khai, vận hành) — mỗi sơ đồ trả lời câu hỏi gì, cho ai đọc, vẽ bằng ký hiệu nào, lưu ở đâu, khi nào phải cập nhật, và bộ tối thiểu theo cỡ dự án. Dùng khi bắt đầu dự án hoặc một giai đoạn mới, khi lập kế hoạch tài liệu thiết kế, khi review thấy thiết kế thiếu hình dung, hoặc khi không biết nên vẽ gì cho một tính năng.
---

# Lộ trình sơ đồ: vẽ đúng sơ đồ, đúng lúc, cho đúng người đọc

Skill lõi `diagram` lo **cơ chế** (sơ đồ sinh từ nguồn, vùng `HAND-DRAWN` trong `docs/design/ARCHITECTURE.md`, lưới
canh). Skill này trả lời câu hỏi đi trước: **cần sơ đồ nào**. Nguyên tắc: một sơ đồ trả lời một câu hỏi của một nhóm
người đọc; không trả lời được câu hỏi nào thì không vẽ.

## Bản đồ theo giai đoạn

| Giai đoạn | Sơ đồ | Câu hỏi nó trả lời | Người đọc | Ký hiệu (Mermaid) |
|---|---|---|---|---|
| **Khám phá** | Bối cảnh hệ thống (C4 mức 1) | Hệ thống nằm giữa ai và hệ thống nào? Cái gì ở NGOÀI phạm vi? | mọi người, người tài trợ | `flowchart` + nhãn |
| | Hành trình người dùng (hiện tại → tương lai) | Người dùng đau ở bước nào? Ta cải thiện bước nào? | sản phẩm, thiết kế | `journey` hoặc FigJam |
| **Yêu cầu** | Luồng nghiệp vụ có làn vai trò (swimlane) | Ai làm gì, theo thứ tự nào, chỗ nào người duyệt? | chuyên gia miền, kiểm thử | `flowchart` có `subgraph` mỗi vai trò |
| | Bản đồ câu chuyện người dùng / use case | Bản phát hành đầu gồm những gì? | sản phẩm, kỹ thuật | bảng (skill `design-tables`) hoặc FigJam |
| **Kiến trúc** | Container (C4 mức 2) | Gồm những khối chạy được nào, nói chuyện qua giao thức gì? | kỹ thuật, vận hành | `flowchart` |
| | Lớp & ranh giới import | Code nào được gọi code nào? | kỹ thuật, agent | **sinh** từ `contracts/boundaries.yaml` |
| | Luồng dữ liệu có biên tin cậy (DFD) | Dữ liệu nhạy cảm đi đâu, qua biên tin cậy nào, ra dịch vụ ngoài nào? | bảo mật, pháp chế | `flowchart` có `subgraph` mỗi vùng tin cậy |
| **Thiết kế chi tiết** | ERD | Thực thể, quan hệ, khoá — dữ liệu có nguồn ở đâu? | backend, dữ liệu | `erDiagram` (skill `data-model`) |
| | Tuần tự (sequence) cho luồng găng | Thứ tự gọi, chỗ timeout/thử lại, chỗ người duyệt chen vào? | backend, kiểm thử | `sequenceDiagram` |
| | Máy trạng thái của thực thể có vòng đời | Trạng thái hợp lệ, chuyển nào được phép, ai được chuyển? | backend, frontend, chuyên gia | `stateDiagram-v2` + bảng chuyển trạng thái |
| | Luồng màn hình / sơ đồ trang | Người dùng đi qua những màn hình nào? | thiết kế, frontend | FigJam/Figma (skill `figma-prototype`) |
| | Hợp đồng API | Endpoint, schema | frontend, tích hợp | **sinh**: `contracts/openapi.json` |
| **Phần AI** (nếu có) | Pipeline dữ liệu → mô hình | Nạp → chia đoạn → nhúng → truy hồi → sinh → kiểm; đo ở bước nào? | AI, dữ liệu | `flowchart` |
| | Vòng lặp agent + công cụ + cổng người | Mô hình chọn gì, code tính gì, hành động nào cần duyệt, trần vòng lặp? | AI, bảo mật, chuyên gia | `sequenceDiagram` hoặc `flowchart` |
| **Triển khai** | Triển khai / hạ tầng | Môi trường nào chạy gì ở đâu; mạng; CSDL; bí mật lấy từ đâu? | vận hành | `flowchart` có `subgraph` mỗi môi trường |
| | Đường CI/CD | Commit đi qua những cổng nào tới production? | mọi người làm code | `flowchart` (từ `.github/workflows/ci.yml`, R50.7) |
| **Vận hành** | Luồng xử lý sự cố / leo thang | Ai được báo, sau bao lâu, quay lui thế nào? | trực vận hành | `flowchart` |
| | Ai sở hữu vùng nào | Ai duyệt thay đổi ở đâu? | mọi người | **sinh** từ `coordination/policy.yaml` |

## Bộ tối thiểu theo cỡ dự án (`complexity` trong `team-profile.yaml`)

- **lite (POC):** bối cảnh hệ thống · một luồng găng (tuần tự hoặc luồng) · ERD nếu có CSDL.
- **standard:** + container · máy trạng thái cho mỗi thực thể có duyệt · triển khai · pipeline AI / vòng lặp agent nếu có.
- **strict (dữ liệu nhạy cảm):** + DFD có biên tin cậy (đầu vào cho skill `security-audit`) · luồng sự cố · hành trình
  người dùng hiện tại/tương lai đã được chuyên gia miền xác nhận.

## Lưu ở đâu, nguồn sự thật là gì

- **Nguồn sự thật là Mermaid trong repo** (`docs/design/ARCHITECTURE.md` vùng `HAND-DRAWN`, hoặc
  `docs/design/diagrams/<ten>.md` cho sơ đồ chi tiết): diff được, review được, agent đọc được.
- FigJam/Figma dùng cho buổi làm việc với người (vẽ nhanh, cùng chỉnh). Chốt xong → chép lại thành Mermaid, ghi link
  FigJam bên dưới làm tham khảo. MCP Figma có công cụ `generate_diagram` để dựng sơ đồ FigJam từ mô tả.
Không có MCP Figma: viết Mermaid trực tiếp — GitHub và mọi trình xem Markdown hiện đại đều vẽ được.
- Sơ đồ suy ra được từ nguồn máy đọc (lớp, quyền sở hữu, API) thì **sinh**, không vẽ tay (skill `diagram`).

## Khi nào cập nhật

Cùng PR với thay đổi làm nó sai: thêm container/dịch vụ ngoài → bối cảnh + container + triển khai; thêm trạng thái →
máy trạng thái + bảng chuyển; thêm bảng → ERD; thêm luồng dữ liệu ra ngoài → DFD (và R60). Reviewer hỏi: "PR này làm
sai sơ đồ nào?" (R00.4 không tính năng ẩn).

## Kiểm một sơ đồ

Mỗi mũi tên có nhãn động từ · mỗi khối có tên đúng như trong code/hạ tầng · ghi ngày và giai đoạn · người đọc mục tiêu
trả lời được câu hỏi ở bảng trên chỉ bằng sơ đồ. Lưới canh chỉ kiểm sơ đồ **có mặt**, không kiểm **đúng** — nói rõ
giới hạn này khi báo cáo.
