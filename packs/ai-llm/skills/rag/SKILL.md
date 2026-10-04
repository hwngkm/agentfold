---
name: rag
description: Dựng và cải thiện hệ thống truy hồi-rồi-sinh (RAG) theo thứ tự đúng — đo truy hồi riêng trước khi chỉnh prompt, chia đoạn và embedding có kiểm chứng, ngưỡng từ chối khi không tìm thấy, trích dẫn nguồn kiểm được. Dùng khi thêm tính năng hỏi đáp trên tài liệu, khi câu trả lời RAG sai hoặc bịa, khi đổi cách chia đoạn/embedding/model, hoặc khi cần chứng minh câu trả lời bám vào nguồn.
---

# RAG: sửa truy hồi trước, đừng chỉnh prompt để bù

## Nguyên tắc số một: tách hai tầng khi đo

RAG sai có hai nguyên nhân khác hẳn nhau, sửa khác nhau:

| Tầng | Câu hỏi | Nếu hỏng thì |
|---|---|---|
| **Truy hồi** | Đoạn chứa đáp án có nằm trong top-k không? | Chỉnh prompt **vô ích** — mô hình không thể trả lời từ thứ nó không được đưa |
| **Sinh** | Có đoạn đúng rồi, mô hình có dùng đúng không? | Chỉnh prompt, định dạng ngữ cảnh, trích dẫn |

**Luôn đo truy hồi riêng trước.** Nếu đáp án không có trong top-k ở 40% ca, mọi công sức chỉnh prompt đều
đang đánh vào sai tầng.

## 1. Bộ ca cho truy hồi

Mỗi ca: câu hỏi + **id các đoạn chứa đáp án** (không chỉ đáp án chữ). Không có id đoạn chuẩn thì không đo
được truy hồi, chỉ đo được đầu ra cuối — tức lại gộp hai tầng.

Thêm các ca **không có đáp án trong kho** — hệ thống phải từ chối, không bịa. Thiếu loại ca này thì một hệ
thống luôn trả lời tự tin sẽ đạt điểm cao.

## 2. Chỉ số truy hồi

| Chỉ số | Đo gì | Khi nào dùng |
|---|---|---|
| **Recall@k** | Tỷ lệ ca có ít nhất một đoạn đúng trong top-k | Chỉ số chính: mô hình có *cơ hội* trả lời không |
| **MRR** | Trung bình của 1/(hạng của đoạn đúng đầu tiên) | Đoạn đúng có nằm **gần đầu** không (đầu ngữ cảnh thường được dùng tốt hơn) |
| Precision@k | Tỷ lệ đoạn đúng trong top-k | Khi ngữ cảnh ngắn và đoạn nhiễu làm hỏng câu trả lời |

Chọn k **bằng đúng số đoạn thực sự đưa vào prompt** ở production. Recall@20 đẹp không cứu được hệ thống chỉ
đưa 5 đoạn vào prompt.

## 3. Chia đoạn (chunking)

- **Không có kích thước đoạn "đúng" chung cho mọi kho** — chọn bằng cách **đo Recall@k trên bộ ca** với vài
  kích thước, không chọn theo con số trong bài blog.
- **Không cắt ngang đơn vị ngữ nghĩa**: một bảng, một mục, một điều khoản bị cắt đôi thì cả hai nửa đều vô
  dụng. Cắt theo cấu trúc (tiêu đề, mục) trước, theo độ dài sau.
- **Mỗi đoạn mang siêu dữ liệu nguồn**: tài liệu gốc, mục/trang, phiên bản, ngày. Đó là thứ dùng để trích dẫn
  và để lọc tài liệu hết hiệu lực.
- **Đổi cách chia đoạn = phải embedding lại toàn bộ và chạy lại bộ ca truy hồi.** Ghi phiên bản cách chia
  đoạn cạnh chỉ mục; chỉ mục trộn hai cách chia là chỉ mục không đo được.

## 4. Embedding và tìm kiếm

- **Truy vấn và tài liệu phải embedding bằng cùng một model cùng phiên bản.** Đổi model embedding mà không
  embedding lại kho ⇒ khoảng cách vô nghĩa, và **không báo lỗi gì**.
- Thử **tìm kiếm lai** (từ khoá + vector) khi kho có mã, tên riêng, số hiệu văn bản: vector thường yếu với
  chuỗi chính xác. Quyết định bằng Recall@k trên bộ ca, không bằng cảm giác.
- **Rerank** (chấm lại top-N rộng rồi cắt còn k) thường tăng MRR — đo trước khi thêm, vì nó tốn thêm độ trễ
  và chi phí (skill `latency-slo`, `token-economics`).

## 5. Ngưỡng từ chối — "không tìm thấy" là một câu trả lời hợp lệ

- Điểm tương đồng của đoạn tốt nhất dưới ngưỡng ⇒ **trả lời không biết**, không đưa đoạn yếu cho mô hình tự
  đoán.
- **Chọn ngưỡng trên bộ ca**, cân giữa hai lỗi: ngưỡng cao quá ⇒ từ chối cả câu có đáp án; thấp quá ⇒ trả lời
  bịa cho câu không có đáp án. Báo **cả hai** tỷ lệ, không chỉ độ chính xác.
- Dặn mô hình trong prompt "chỉ trả lời từ ngữ cảnh; không có thì nói không biết" là cần nhưng **không đủ** —
  ngưỡng ở tầng truy hồi mới là rào chắn chạy được.

## 6. Trích dẫn kiểm được

- Mỗi khẳng định trong câu trả lời gắn với **id đoạn** đã đưa vào — dùng cơ chế trích dẫn của nhà cung cấp
  nếu có (Anthropic: `citations` trên khối document), hoặc yêu cầu schema đầu ra có trường id đoạn.
- **Kiểm bằng code** rằng mọi id được trích có thật trong tập đã đưa vào. Id không tồn tại = trích dẫn bịa.
- Với miền có rủi ro (y tế, tài chính, pháp lý): con số trong câu trả lời phải truy được về nguồn; không truy
  được thì không hiển thị (xem skill `prompt-io`: mô hình chọn, code tính).

## 7. Tài liệu trong kho là dữ liệu không tin cậy

Một tài liệu có thể chứa câu như "bỏ qua hướng dẫn trước đó". Đoạn truy hồi được đưa vào prompt **qua
`fence`** như mọi văn bản không tin cậy (skill `prompt-io` §3), không ghép thẳng vào system prompt.

## Thứ tự làm khi RAG trả lời sai

```text
1. Có đoạn chứa đáp án trong kho không?        không → vấn đề nạp dữ liệu, không phải RAG
2. Đoạn đó có trong top-k không? (Recall@k)    không → chunking / embedding / hybrid / rerank
3. Đoạn đó có bị ngưỡng loại không?            có    → chỉnh ngưỡng trên bộ ca
4. Có trong ngữ cảnh mà vẫn trả lời sai?              → lúc này mới chỉnh prompt / định dạng ngữ cảnh
```

Nhảy thẳng tới bước 4 là cách phổ biến nhất để tốn một tuần chỉnh prompt cho một lỗi nằm ở bước 2.
