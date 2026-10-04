---
name: literature-review
description: Tìm và tổng hợp tài liệu (bài báo, hướng dẫn chuyên môn, tài liệu kỹ thuật, bộ dữ liệu, mô hình) có hệ thống — câu hỏi rõ, nơi tìm và tiêu chí chọn/loại ghi trước, đọc nguồn sơ cấp, phân biệt mức bằng chứng, trích dẫn kiểm lại được. Dùng khi bắt đầu một hướng nghiên cứu hoặc tính năng dựa trên kiến thức chuyên môn, khi cần chọn phương pháp/mô hình/bộ dữ liệu, khi viết phần tổng quan, hoặc khi một con số trong tài liệu chưa có nguồn.
---

# Tổng quan tài liệu: tìm có hệ thống, trích nguồn sơ cấp

Luật nền: R40.6 (số liệu phải có nguồn sơ cấp), R40.7 (giấy phép), R00.5 (nói thật về giới hạn).

## 1. Chốt trước khi tìm

Ghi vào ghi chú nghiên cứu (skill `research-notes`):
- **Câu hỏi** cụ thể, trả lời được ("phương pháp truy hồi nào cho recall@10 cao nhất trên văn bản y khoa tiếng
  Việt?", không "tìm hiểu về RAG").
- **Nơi tìm** và **từ khoá** (cả tiếng Việt và tiếng Anh, từ đồng nghĩa).
- **Tiêu chí chọn/loại**: khoảng năm, loại tài liệu, ngôn ngữ, miền. Ghi trước để không chọn theo kết quả mình muốn.

## 2. Nơi tìm

| Loại | Nơi | Ghi chú |
|---|---|---|
| Bài báo y sinh | PubMed | bài có cấu trúc, phân biệt loại nghiên cứu |
| Học máy, NLP, khoa học máy tính | arXiv (preprint — chưa bình duyệt), hội nghị/tạp chí | ghi rõ preprint |
| Mô hình, bộ dữ liệu | Hugging Face Hub (CLI `hf`, pack này kiểm) | đọc model/dataset card: giấy phép, dữ liệu huấn luyện, giới hạn |
| Hướng dẫn chuyên môn, văn bản pháp quy | trang chính thức của cơ quan ban hành | bản hiện hành, số hiệu, ngày hiệu lực |
| Tài liệu thư viện/API | tài liệu chính thức, MCP `context7` nếu pack bật | không dựa vào trí nhớ của mô hình |

Không có MCP hay connector nào: mọi nguồn trên đều có trang web hoặc API công khai — dùng `python -m scripts.research`
(pack `research`) hoặc `curl`; skill `paper-search` liệt kê lệnh cho từng nguồn.

Nếu tài khoản có bật connector nghiên cứu (PubMed, arXiv/alphaXiv, Scholar…) trong môi trường agent thì dùng chúng
để tìm; luôn mở và đọc nguồn gốc trước khi trích.

## 3. Đọc và trích

- Đọc **nguồn sơ cấp**; blog/tổng hợp chỉ dùng để tìm nguồn, nếu trích thì ghi rõ là thứ cấp.
- Mỗi khẳng định ghi: nguồn (tác giả, năm, tên, DOI/URL), vị trí (trang, bảng), câu trích hoặc con số nguyên văn.
- Ghi **mức bằng chứng**: thử nghiệm có đối chứng / quan sát / ý kiến chuyên gia; benchmark công khai / tự đo; cỡ mẫu.
- Ghi điều kiện áp dụng: ngôn ngữ, miền, phần cứng — kết quả trên tiếng Anh không tự động đúng cho tiếng Việt.

## 4. Tổng hợp

Bảng so sánh các phương án theo tiêu chí của câu hỏi; mỗi ô có nguồn. Nêu rõ: chỗ các nguồn mâu thuẫn, chỗ không có
bằng chứng (sẽ phải tự đo — skill `experiment-design`), và khuyến nghị kèm mức chắc chắn.

## Không làm

Trích con số không mở được nguồn · trích DOI/URL từ trí nhớ mà không kiểm (mô hình hay bịa trích dẫn) · gửi dữ liệu
nội bộ/người dùng vào công cụ tìm kiếm ngoài.
