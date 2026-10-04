---
name: idea-assessment
description: Thẩm định một ý tưởng hay yêu cầu mới trước khi cam kết làm — thu thập bằng chứng nhu cầu, xác định giả định then chốt và cách rẻ nhất để kiểm, cân chi phí rủi ro, rồi kết luận go, clarify hoặc kill kèm lý do ghi lại. Dùng khi có ý tưởng tính năng hoặc sản phẩm chưa có ticket, khi yêu cầu mơ hồ hoặc tốn công, hoặc khi cả nhóm hào hứng nhưng chưa ai hỏi vì sao nên làm.
---

# Thẩm định ý tưởng: thu bằng chứng trước, cam kết sau

Gốc: github/spec-kit (idea assessment: intake → research → define → shape → decide, kết thúc bằng go / cần làm rõ /
dừng). Dừng có lý do ghi lại là một kết quả tốt — rẻ hơn nhiều so với làm xong mới biết không ai cần.

## 0. Mở báo cáo

```bash
python -m tools.agentctl new assessment --role Rn --title "Cho phép dùng offline"
```

Tạo `docs/work/assessments/ASM-<ngày>-<slug>.md` với `decision: pending`. `check-work` kiểm `decision` thuộc tập đóng và
`go`/`kill` có `evidence`.

## 1. Năm bước, mỗi bước một mục trong báo cáo

| Bước | Làm gì | Công cụ |
|---|---|---|
| **Tiếp nhận** | Viết lại ý tưởng một đoạn: ai được lợi, việc họ cần làm, đang làm bằng gì | — |
| **Nghiên cứu** | Bằng chứng nhu cầu thật; cái đã có sẵn (sản phẩm, mã nguồn mở, mô hình) | `market-research`, `competitor-analysis`, `repo-research`, `paper-search` (pack `market`, `research`) |
| **Định nghĩa** | Giả định then chốt (đúng thì đáng làm, sai thì không) + cách RẺ NHẤT kiểm từng cái | `experiment-design` |
| **Định hình** | Phạm vi nhỏ nhất đáng làm; chi phí, rủi ro, phụ thuộc, bất biến bị đụng | `critical-debate` nếu quyết định khó đảo ngược |
| **Quyết định** | Một trong ba kết luận dưới đây | — |

## 2. Kết luận (`decision`)

| Kết luận | Nghĩa | Bắt buộc |
|---|---|---|
| `go` | đáng làm với phạm vi nhỏ nhất đã nêu | `evidence` không rỗng; mục 5 nêu phạm vi → tạo ticket (`new ticket`) |
| `clarify` | chưa đủ bằng chứng để quyết | mục 5 nêu CÂU HỎI cụ thể và ai trả lời (`new question`) — không phải "cần nghiên cứu thêm" |
| `kill` | không nên làm | `evidence` không rỗng; lý do ghi lại để người sau khỏi thử lại |
| `pending` | chưa kết luận | — |

`go` không phải phê duyệt: chuyển thành ticket `proposed` rồi người duyệt đổi `ready` như mọi việc khác. Đặc tả hành vi
mong muốn (nếu có) ghi thành delta theo `docs/design/specs/README.md` khi làm ticket.

## 3. Trung thực

- "Mọi người đều muốn" không phải bằng chứng. Phỏng vấn ghi cỡ mẫu; không quy 5 người ra phần trăm.
- Tìm 15 phút chưa đủ để nói "chưa ai làm" — ghi đã tìm ở đâu, truy vấn gì.
- Không gửi kế hoạch nội bộ hay dữ liệu người dùng vào công cụ tìm kiếm/AI bên ngoài.
