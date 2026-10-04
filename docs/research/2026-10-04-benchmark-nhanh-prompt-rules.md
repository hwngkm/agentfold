# Benchmark nhánh `prompt-rules`

Ngày: 2026-10-04 · Vai trò: R3 · Trạng thái: **bước 1 và bước 2 (120 lượt) đã xong**.

## Đã làm (bước 1)

- Nhánh thứ ba `prompt-rules` ở cả hai nhiệm vụ: cùng mã và không có AGENTS.md/CLAUDE.md/ticket như `plain`, nhưng lời nhắc có thêm luật (phạm vi = danh sách tệp được sửa, chạy pytest, bàn giao `## Đã làm`/`## Còn dở`). `arm_prompt` dựng lời nhắc; nhánh cũ giữ nguyên.
- Mỗi dòng JSONL lưu `violating` (tên tệp vi phạm); `--summarize` thêm bảng tệp bị sửa ngoài phạm vi, nhiều nhất trước (dòng cũ chưa có trường này vẫn đọc được).
- Cờ `--arms` để chạy riêng nhánh mới.
- Kiểm: 7 test mới đã thấy ĐỎ trước khi có mã, rồi xanh; `--check`: oracle đạt, null trượt ở cả ba nhánh.

## Mẫu đo chi phí (6 lượt thật, nhánh prompt-rules, 1 lượt/mô hình/nhiệm vụ)

| Mô hình | Chi phí 2 lượt | CI xanh | Phạm vi sạch | Bàn giao |
|---|---|---|---|---|
| deepseek/deepseek-v4.1-flash | $0.0050 | 2/2 | 2/2 | 2/2 |
| z-ai/glm-5.3-flash | $0.0072 | 2/2 | 2/2 | 2/2 |
| openai/gpt-6-luna | $0.0022 | 2/2 | 2/2 | 0/2 |


GPT-6-luna không để lại HANDOFF.md hợp lệ ở cả hai lượt mẫu (n = 2, chưa nói được gì).

Tổng $0.0144 (chi phí do OpenRouter báo, `usage.cost`), TB $0.0024/lượt. Ngoại suy 120 lượt ≈ $0.29 (≈ $0.87 nếu sai số gấp 3). **Đây là n = 2 mỗi mô hình — không kết luận gì về hiệu quả.** Tệp mẫu không được commit; không gộp vào kết quả n = 20.

## Kết quả chạy thật (bước 2)

3 mô hình × 2 nhiệm vụ × n = 20 = **120 lượt** nhánh `prompt-rules`, 0 lỗi hạ tầng. Chi phí thực **$0.227** (OpenRouter `usage.cost`; cộng mẫu thử $0.0144 → $0.241, dưới trần $1). Chạy bị ngắt một lần giữa chừng (hết giới hạn thời gian nền ở 76/120) rồi chạy tiếp đúng phần còn thiếu, không trùng lượt. Số liệu thô: `evals/benchmarks/ket-qua-2026-10-04-prompt-rules-n20.jsonl`; hai nhánh còn lại lấy từ `ket-qua-2026-10-04-n20.jsonl` (cùng ngày, cùng mô hình và nhiệm vụ, nhưng chạy ở lượt khác — không xen kẽ với `prompt-rules`).

Gộp hai nhiệm vụ, đạt/n [khoảng tin cậy Wilson 95%], n = 40 mỗi ô:

| Mô hình | Nhánh | CI xanh | Phạm vi sạch | Bàn giao |
|---|---|---|---|---|
| deepseek-v4.1-flash | plain | 40/40 [91–100%] | 19/40 [33–63%] | 0/40 [0–9%] |
| | prompt-rules | 40/40 [91–100%] | 39/40 [87–100%] | 40/40 [91–100%] |
| | template | 40/40 [91–100%] | 40/40 [91–100%] | 40/40 [91–100%] |
| gpt-6-luna | plain | 40/40 [91–100%] | 20/40 [35–65%] | 0/40 [0–9%] |
| | prompt-rules | 40/40 [91–100%] | 40/40 [91–100%] | **11/40 [16–43%]** |
| | template | 40/40 [91–100%] | 40/40 [91–100%] | **27/40 [52–80%]** |
| glm-5.3-flash | plain | 32/40 [65–90%] | 21/40 [37–67%] | 0/40 [0–9%] |
| | prompt-rules | 29/40 [57–84%] | 40/40 [91–100%] | 29/40 [57–84%] |
| | template | 33/40 [68–91%] | 40/40 [91–100%] | 33/40 [68–91%] |

Đọc kết quả (chỉ nêu điều mà khoảng tin cậy không chồng nhau; phần còn lại là "không phân biệt được"):

- **Giữ phạm vi:** `prompt-rules` và `template` đều ≈ 100% ở cả ba mô hình (1 vi phạm duy nhất của `prompt-rules`: tạo một tệp gỡ lỗi tạm trong thư mục tests của repo tạm (tên có trong tệp JSONL)), còn `plain` chỉ ~50% — khoảng tin cậy không chồng. Với các mô hình và nhiệm vụ này, lợi ích về phạm vi đến từ việc NÊU luật, không cần cấu trúc template; giữa `prompt-rules` và `template` không có khác biệt đo được.
- **Bàn giao:** DeepSeek ngang nhau (40/40). GPT-6-luna: `template` 27/40 hơn hẳn `prompt-rules` 11/40 (khoảng không chồng) — **kết quả âm cho `prompt-rules`**: luật bàn giao trong lời nhắc ít được theo hơn khi nằm trong AGENTS.md ở mô hình này. GLM: 33/40 so với 29/40, chồng nhau, không kết luận. Nguyên nhân gốc chưa kiểm (đoán: vị trí luật trong ngữ cảnh), không nên coi là đã biết.
- **CI xanh:** không khác biệt đo được giữa các nhánh; GLM thấp hơn ở nhiệm vụ sửa lỗi ở cả ba nhánh (9–13/20), nên đó là chuyện của mô hình/nhiệm vụ, không phải của nhánh.
- **Tệp vi phạm:** tên tệp chỉ được lưu từ lượt chạy này, nên bảng tệp chỉ có nhánh `prompt-rules`; chưa trả lời được "plain hay sửa tệp nào" vì dữ liệu cũ không có trường đó (cần chạy lại `plain` để có).

## Giới hạn

- **Một nhà cung cấp** (OpenRouter, ba mô hình rẻ), một vòng lặp công cụ tối giản — không phải Claude Code/Codex. Chưa có khoá nhà cung cấp thứ hai; kết quả không nói gì về agent khác.
- Hai nhiệm vụ nhỏ, một ngôn ngữ; n = 20/ô nên chỉ thấy chênh lệch lớn.
- `prompt-rules` chạy ở lượt khác với `plain`/`template` (không xen kẽ), nên trôi theo thời gian của mô hình không được loại trừ.
- Lời nhắc `prompt-rules` do tôi soạn; cách diễn đạt khác có thể cho kết quả khác.
- Hạn chế cũ vẫn còn: không đo thời gian người duyệt.
