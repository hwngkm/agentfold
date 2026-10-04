# docs/work — Công việc: mỗi mục một file

Thư mục này thay cho các file dùng chung kiểu `DEVLOG.md`, `TICKETS.md`, bảng Excel theo dõi việc.
Trong thực tế, ba file loại đó bị sửa hàng trăm lần trong vài tuần bởi nhiều người và nhiều AI agent;
gần như mọi lần merge đều đụng nhau, và file Excel thì không merge được. Ở đây **mỗi mục là một file
riêng, tên duy nhất**, nên hai agent ghi cùng lúc tạo ra hai file — không có gì để xung đột.

| Loại | Thư mục | Tên file | Ai tạo | Sửa sau khi merge? |
|---|---|---|---|---|
| Ticket | `tickets/` | `ABC-01.md` | người lập kế hoạch (người hoặc agent `planner`) | chỉ khi có người duyệt — vùng bảo vệ `work-plan` |
| Nhật ký | `log/YYYY/MM/` | `YYYY-MM-DD-rN-slug.md` | người làm, cuối mỗi phiên | không — ghi sai thì thêm mục đính chính |
| Quyết định | `decisions/` | `DEC-YYYYMMDD-slug.md` | người ra quyết định kỹ thuật cục bộ | chỉ đổi `status: superseded` + trỏ sang quyết định mới |
| Câu hỏi | `questions/` | `Q-YYYYMMDD-slug.md` | agent/người gặp chỗ thiết kế không phủ | người được hỏi điền phần Trả lời |
| Sự cố | `incidents/` | `INC-YYYYMMDD-slug.md` | ai phát hiện, kể cả sự cố do mình gây ra | bổ sung phần Phòng ngừa khi có lưới canh mới |
| Báo cáo sửa lỗi | `bugs/` | `BUG-YYYYMMDD-slug.md` | người sửa lỗi (skill `bug-fix`) | điền kết luận `verified\|partial\|failed` + `evidence` |
| Thẩm định ý tưởng | `assessments/` | `ASM-YYYYMMDD-slug.md` | người thẩm định (skill `idea-assessment`) | điền `go\|clarify\|kill` + `evidence` |
| Kế hoạch | `plans/` | `PLAN-<ticket>.md` | agent, trước khi viết mã việc lớn | CHỈ người đổi `status: approved` (vùng bảo vệ `work-plan`) |
| Bàn giao | `handoffs/` | `HND-YYYYMMDD-slug.md` | agent dừng giữa chừng (hết hạn mức, hết phiên, đổi công cụ) | chỉ đổi `status`: `open` → `taken` → `closed` |

Tạo đúng khuôn bằng lệnh (khuôn nằm trong `tools/agentctl/entries.py`):

```bash
python -m tools.agentctl new log      --role R2 --title "Xong phần tính báo giá"
python -m tools.agentctl new decision --role R3 --title "Dùng hàng đợi trong Postgres thay Redis"
python -m tools.agentctl new question --role R2 --title "Làm tròn tiền theo dòng hay theo tổng?" --blocking EXM-01 --answer-by R1
python -m tools.agentctl new incident --role R3 --title "CI đỏ vì migration hai head"
python -m tools.agentctl new ticket   --role R1 --id EXM-02 --title "Gửi báo giá đã duyệt"
python -m tools.agentctl new handoff  --role R3 --title "Hết hạn mức giữa lúc làm API-02"   # git điền sẵn nhánh/commit/file dở
```

## Vì sao mã theo ngày + slug, không theo số thứ tự

"Lấy số tiếp theo" (DEC-299 → DEC-300) là một cuộc đua: hai agent cùng đọc 299 và cùng cấp 300.
`DEC-20260915-dung-hang-doi-postgres` không cần biết ai khác đang cấp mã gì. Ticket vẫn dùng mã
`ABC-01` vì ticket được tạo trong buổi lập kế hoạch, không phải song song — và bộ kiểm bắt trùng mã.

## Trạng thái KHÔNG ghi tay

Ticket chỉ có `proposed | ready | cancelled`. "Đang làm" đọc từ sổ claim, "đã xong" suy ra từ mã ticket
trong lịch sử `main`. Xem bảng: `python -m tools.agentctl board`. Nhờ vậy không agent nào phải sửa
ticket trong lúc làm, và bảng không bao giờ lệch sự thật.

## Câu hỏi là cách DỪNG ĐÚNG

Khi thiết kế, luật hoặc ticket không trả lời được một chỗ — nhất là ngưỡng nghiệp vụ, nguồn số liệu,
hay một thay đổi ngoài phạm vi — agent **không đoán**. Nó tạo file câu hỏi, dừng phần bị chặn, làm tiếp
phần không bị chặn, và nêu câu hỏi trong báo cáo cuối phiên. Quyết định đáng kể từ câu trả lời được
chuyển thành DEC (kỹ thuật cục bộ) hoặc ADR (đổi thiết kế, `docs/design/adr/`).
