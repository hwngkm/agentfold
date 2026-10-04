---
name: experiment-design
description: Thiết kế một thí nghiệm hoặc phép so sánh (ablation, chọn cấu hình, so mô hình) trước khi chạy — giả thuyết, biến đo chính, baseline, bộ đo tách tập hiệu chỉnh và tập kiểm tra, cỡ mẫu đủ để thấy khác biệt, tiêu chí quyết định ghi sẵn, và khoảng tin cậy cho chênh lệch. Dùng khi cần chọn giữa nhiều cấu hình/phương pháp, khi định đổi mặc định của hệ thống dựa trên số đo, khi chạy ablation, hoặc khi một kết quả "tốt hơn" chưa rõ có thật không.
---

# Thiết kế thí nghiệm: chốt cách thắng TRƯỚC khi biết ai thắng

## 1. Viết trước khi chạy (trong ghi chú nghiên cứu)

| Mục | Ví dụ |
|---|---|
| Giả thuyết | "Thêm reranker làm tăng R@1 trên bộ hỏi đáp mà không tăng P95 quá 3 s" |
| Biến đo chính (một) + phụ | chính: R@1; phụ: R@10, MRR, P95, chi phí |
| Baseline | cấu hình mặc định hiện tại, và một baseline tầm thường (ngẫu nhiên, BM25, lớp đa số) |
| Bộ đo | tên + phiên bản + cỡ mẫu; tập hiệu chỉnh và tập kiểm tra tách nhau |
| Tiêu chí quyết định | "đổi mặc định chỉ khi chính tăng ≥ X VÀ bộ đo thứ hai không giảm quá Y" |

Tiêu chí ghi trước thì không thể vô tình chọn ngưỡng theo kết quả.

## 2. Bộ đo

- Tách **tập hiệu chỉnh** (chọn ngưỡng, chỉnh tham số) và **tập kiểm tra** (chỉ chạy để báo cáo). Chỉnh trên tập
  kiểm tra = số báo cáo lạc quan giả.
- Không dùng một nguồn để chấm chính nó; không dùng quy tắc vừa viết để tuyên bố "0 lỗi" (R40.11).
- Bộ nhỏ (vài chục ca) chỉ đủ để thấy khác biệt lớn — kiểm sàn nhiễu trước (skill `eval-harness` mục 5 nếu pack
  `ai-llm` bật): nửa độ rộng khoảng tin cậy cỡ `1/√n` với tỷ lệ đạt.
- Có ít nhất hai bộ đo độc lập khi định đổi mặc định: cải thiện trên bộ nhỏ mà giảm trên bộ lớn thì giữ mặc định.

## 3. Chạy

- Mọi nhánh chạy **cùng bộ đo, cùng phiên bản dữ liệu, cùng phần cứng**, bằng một script (vd. `eval/ablation.py`)
  xuất bảng — không chạy tay từng nhánh.
- Cố định seed; lặp lại khi có ngẫu nhiên (mô hình sinh, lấy mẫu); ghi phiên bản mô hình/thư viện.
- Ước thời gian/chi phí trên mẫu nhỏ trước (R40.12).

## 4. Phân tích

- Báo **chênh lệch so với baseline kèm khoảng tin cậy 95%** (bootstrap theo ca, hoặc phép kiểm cặp) — không chỉ hai
  con số trung bình.
- Báo theo nhóm (loại câu hỏi, nguồn): trung bình tốt có thể che một nhóm sập.
- Quyết định đúng theo tiêu chí ở mục 1. Không đạt → nói thẳng, giữ nguyên, ghi kết quả âm — kết quả âm cũng là
  kết quả (người sau không phải thử lại).

## Đầu ra

Bảng Markdown: nhánh × chỉ số (kèm khoảng tin cậy chênh lệch) × bộ đo; cỡ mẫu; lệnh tái hiện; quyết định + lý do.
