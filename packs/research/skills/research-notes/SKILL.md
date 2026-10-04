---
name: research-notes
description: Ghi chú nghiên cứu tái hiện được và trung thực — mỗi kết quả kèm lệnh chạy, phiên bản dữ liệu/mã/mô hình, số đo trước-sau, cỡ mẫu và giới hạn; tách rõ đã đo, ước tính và giả thuyết; ghi cả kết quả âm và việc đang dở. Dùng khi kết thúc một lượt thử nghiệm hay phân tích, khi bàn giao việc nghiên cứu cho người/agent khác, khi viết báo cáo cho người duyệt, hoặc khi một con số trong báo cáo không còn ai nhớ từ đâu ra.
---

# Ghi chú nghiên cứu: người khác chạy lại được và tin được

Ghi chú nghiên cứu là nơi duy nhất trả lời *"con số này ở đâu ra?"* sau hai tuần. Viết cho người đọc chưa từng ở
trong phiên làm việc.

## Vị trí và định dạng

- Một file mỗi chủ đề (vd. `research/<chu-de>/docs/research-notes.md`), các mục có ngày, mục mới thêm ở cuối; sửa sai
  bằng mục đính chính, không xoá lịch sử. Quyết định đáng kể → DEC/ADR, ghi chú trỏ sang.
- Ngôn ngữ thống nhất với nhóm; thuật ngữ chuyên môn giữ nguyên tiếng gốc lần đầu xuất hiện.

## Mỗi kết quả có đủ

```markdown
### 2026-10-03 — Reranker trên bộ hỏi đáp mức đoạn (ví dụ minh hoạ, số không có thật)
- Câu hỏi / giả thuyết: …
- Lệnh: `uv run python eval/ablation.py --set qa-v1 --branches A1,A1+rerank --seed 13`
- Phiên bản: mã `<commit>`, dữ liệu `<mã phát hành>`, mô hình `<tên@revision>`
- Bộ đo: qa-v1 (n = 240, tập kiểm tra), gold-draft (n = 25)
- Kết quả: R@1 0,62 → 0,71 (chênh +0,09, KTC95% [+0,04; +0,14]); R@10 không đổi; P50 tăng từ 0,4 s lên 3,8 s
- Giới hạn: gold-draft quá nhỏ để kết luận; đo trên CPU, chưa đo GPU
- Quyết định: chưa đổi mặc định (độ trễ vượt ngân sách) — xem DEC-…
```

## Tách ba loại khẳng định

| Loại | Cách viết |
|---|---|
| **Đã đo** | con số + lệnh + cỡ mẫu |
| **Ước tính** | ghi "ước tính", cách ước (vd. "đo trên 1% rồi nhân 100") |
| **Giả thuyết / chưa kiểm** | ghi "chưa kiểm", việc cần làm để kiểm |

Không làm tròn con số ước tính thành "đo được"; không bỏ nhãn "ước tính" cho gọn (R40.5).

## Kết quả âm và việc dở

Thử mà không cải thiện → vẫn ghi (lệnh, số đo, kết luận "không đáng dùng" và vì sao). Việc chưa xong ghi là "đang
làm" kèm tiêu chí còn thiếu — không ghi "xong" khi còn dở (R40.11). Dừng giữa chừng: kèm mục bàn giao
(`python -m tools.agentctl new handoff`).

## Kiểm trước khi gửi

Chọn ngẫu nhiên một con số trong ghi chú và chạy lại lệnh của nó: ra cùng con số (trong dao động đã nêu) thì ghi chú
đạt. Không chạy lại được → sửa ghi chú, không gửi.
