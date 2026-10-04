---
name: finetune
description: Quyết định có nên fine-tune mô hình hay không, và nếu có thì làm có kiểm soát — trả lời trước vì sao prompt, truy hồi hay quy tắc không đủ, dữ liệu huấn luyện sạch có giấy phép, phương pháp hiệu quả tham số (LoRA/QLoRA) khi tài nguyên hạn chế, đánh giá trước-sau trên cùng tập giữ lại, và kiểm mô hình không mất khả năng cũ. Dùng khi có đề xuất fine-tune, khi chuẩn bị bộ dữ liệu huấn luyện, khi chọn phương pháp và phần cứng, hoặc khi đánh giá một mô hình đã fine-tune.
---

# Fine-tune: phương án cuối, không phải đầu tiên

## 1. Trả lời "vì sao KHÔNG phải cách rẻ hơn" (ghi vào ADR)

| Vấn đề | Thử trước |
|---|---|
| Mô hình thiếu kiến thức miền, tài liệu đổi thường xuyên | truy hồi (skill `rag`) — fine-tune không cập nhật được kiến thức mới |
| Đầu ra sai định dạng | structured output + schema (skill `prompt-io`) |
| Hành vi chưa đúng ý | prompt rõ hơn + vài ví dụ; quy tắc tất định cho phần cứng |
| Chi phí/độ trễ của mô hình lớn quá cao | mô hình nhỏ hơn sẵn có; chưng cất từ mô hình lớn là một dạng fine-tune |

Fine-tune hợp lý khi: cần phong cách/định dạng/kỹ năng ổn định mà prompt không giữ được, cần mô hình nhỏ chạy cục
bộ (dữ liệu không được rời máy chủ), hoặc nhiệm vụ hẹp có đủ dữ liệu gán nhãn tốt — và bằng chứng các cách trên đã thử.

## 2. Dữ liệu

- Nguồn có giấy phép cho phép huấn luyện; dữ liệu người dùng đã khử định danh và đúng mục đích đã cam kết (R40.7, R40.8).
- Chất lượng hơn số lượng: rút mẫu đọc (skill `data-quality` của pack `data`), loại trùng, cân bằng loại nhiệm vụ.
- Tách tập giữ lại TRƯỚC khi làm gì khác; kiểm không trùng với dữ liệu huấn luyện (skill `train-eval`).

## 3. Phương pháp và tài nguyên

- GPU ít bộ nhớ → phương pháp hiệu quả tham số (LoRA; QLoRA với mô hình nền lượng tử hoá). Ước bộ nhớ trên một lô nhỏ
  trước khi chạy cả đêm (R40.12).
- Ghim revision mô hình nền; ghi siêu tham số, seed, phiên bản thư viện (skill `experiment-tracking`).
- Lưu adapter/checkpoint ngoài git; đẩy lên kho mô hình riêng tư nếu cần chia sẻ (CLI `hf`, token qua `HF_TOKEN`).

## 4. Đánh giá

- **Trước-sau trên cùng tập giữ lại**: mô hình nền (cùng prompt) vs mô hình đã fine-tune, kèm khoảng tin cậy.
- **Không thoái hoá:** bộ kiểm nhỏ về khả năng chung và an toàn (từ chối yêu cầu nguy hiểm, không bịa nguồn) — fine-tune
  hẹp hay làm mất khả năng khác.
- So chi phí vận hành (phần cứng, độ trễ) với phương án không fine-tune.

## 5. Phát hành

Như mọi thay đổi mô hình: cổng eval, bật dần, theo dõi (skill `ai-release` của pack `ai-product`). Model card ghi
dữ liệu, mục đích dùng, giới hạn, kết quả đánh giá.
