---
name: paper-search
description: Tìm bài báo và tài liệu khoa học qua các nguồn công khai (arXiv, OpenAlex, Semantic Scholar, PubMed) bằng một lệnh chung không cần MCP — chọn nguồn theo lĩnh vực, viết truy vấn, lần theo trích dẫn tới và lui, xử lý hạn mức và mạng chặn, kiểm DOI/link trước khi trích. Dùng khi cần tìm nghiên cứu cho một phương pháp hay quyết định, khi một agent cần trích dẫn mà không có connector nghiên cứu, hoặc khi kiểm một trích dẫn có thật không.
---

# Tìm bài báo: một lệnh cho mọi nguồn, mở bài gốc trước khi trích

Phần "tìm gì, tiêu chí chọn/loại, mức bằng chứng" nằm ở skill `literature-review`. Skill này lo phần **công cụ**.

## 1. Chọn nguồn

| Lĩnh vực | Nguồn | Lệnh |
|---|---|---|
| Học máy, NLP, khoa học máy tính (gồm preprint) | arXiv | `python -m scripts.research arxiv "retrieval augmented generation" --limit 10` |
| Mọi lĩnh vực, có số trích dẫn, tạp chí | OpenAlex | `python -m scripts.research openalex "alert fatigue clinical decision support"` |
| Mọi lĩnh vực, đồ thị trích dẫn | Semantic Scholar | `python -m scripts.research semantic-scholar "..."` (đặt `S2_API_KEY` nếu bị 429) |
| Y sinh, y khoa | PubMed | `python -m scripts.research pubmed "drug interaction alert override"` |

Thêm `--json` để lọc/ghép bằng script. arXiv hay chậm từ một số mạng — lệnh có giới hạn thời gian; chậm thì dùng
OpenAlex (cũng chỉ mục arXiv).

## 2. Viết truy vấn

- Bắt đầu bằng thuật ngữ chuẩn của ngành (tiếng Anh), rồi từ đồng nghĩa; thêm tên phương pháp/bộ đo cụ thể.
- Quá nhiều kết quả: thêm ràng buộc miền ("clinical", "Vietnamese"); quá ít: bỏ bớt từ.
- Ghi mọi truy vấn đã chạy + nguồn + ngày vào ghi chú (skill `research-notes`) — người sau lặp lại được.

## 3. Lần theo trích dẫn

Từ 2–3 bài trung tâm (nhiều trích dẫn, đúng câu hỏi): đọc phần tài liệu tham khảo (lùi) và tìm ai trích dẫn nó (tiến):
- OpenAlex: `https://api.openalex.org/works?filter=cites:<W-id>` (bài trích dẫn W-id).
- Semantic Scholar: `https://api.semanticscholar.org/graph/v1/paper/<id>/citations?fields=title,year`.

## 4. Kiểm trước khi trích

- Mở link/DOI, xác nhận tiêu đề, tác giả, năm khớp; trích từ bài gốc, ghi trang/bảng.
- **Mô hình ngôn ngữ hay bịa trích dẫn trông rất thật** — mọi trích dẫn do agent đưa ra phải có link mở được và đã được
  mở. Không mở được → không trích.
- Preprint ghi rõ "chưa bình duyệt"; bài đã rút (retraction) thì không dùng.

Không có connector/MCP nghiên cứu: toàn bộ skill này đã chạy bằng Python chuẩn và `curl`. Có connector (PubMed,
arXiv, Scholar…) trong môi trường agent thì dùng thêm — kết quả vẫn phải qua mục 4.
