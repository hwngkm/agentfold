---
name: model-hub-research
description: Chọn mô hình hoặc bộ dữ liệu có sẵn trên Hugging Face Hub (và nguồn tương tự) có kiểm chứng — tìm, đọc model/dataset card, kiểm giấy phép và điều khoản dùng, ngôn ngữ hỗ trợ, kích thước và phần cứng cần, đánh giá công bố so với tự đo trên dữ liệu của mình, ghim revision. Dùng khi cần embedding, reranker, mô hình phân loại/sinh, bộ dữ liệu huấn luyện hay đánh giá; khi so sánh mô hình mở với API thương mại; hoặc trước khi đưa một mô hình tải về vào sản phẩm.
---

# Mô hình và bộ dữ liệu trên Hub: tự đo trên dữ liệu của mình trước khi tin

## 1. Tìm

```bash
python -m scripts.research hf-models "vietnamese embedding" --limit 10      # không cần MCP; tôn trọng HF_ENDPOINT
python -m scripts.research hf-datasets "vietnamese medical qa" --limit 10
```

Nếu huggingface.co bị chặn ở mạng của bạn: đặt `HF_ENDPOINT` sang một gương (vd. `https://hf-mirror.com`) — cả công cụ trên
và thư viện `huggingface_hub` đều đọc biến này. Lượt tải là tín hiệu phổ biến, không phải chất lượng.

## 2. Đọc card — bảng kiểm

| Mục | Hỏi | Cờ đỏ |
|---|---|---|
| Giấy phép | tag `license:` + file LICENSE; dùng thương mại được không? | không ghi giấy phép; "research only" cho sản phẩm |
| Điều khoản riêng | `gated` (phải đồng ý), điều khoản sử dụng của mô hình nền | gated mà chưa có người đồng ý thay tổ chức |
| Dữ liệu huấn luyện | nguồn, ngôn ngữ, ngày cắt; có dữ liệu cá nhân/bản quyền? | không công bố nguồn dữ liệu |
| Ngôn ngữ & miền | có tiếng Việt? miền nào? | chỉ đánh giá tiếng Anh |
| Kích thước & phần cứng | số tham số, định dạng (`safetensors`), RAM/VRAM, có bản lượng tử hoá/ONNX | chỉ có file pickle (`.bin` cũ) từ nguồn lạ |
| Đánh giá công bố | bộ đo nào, ai đo, đo lại được không? | chỉ có con số, không có cách tái hiện |
| Bảo trì | ngày cập nhật, người duy trì, issue/discussion | bỏ hoang, tác giả không phản hồi |

## 3. Tự đo — bắt buộc trước khi chọn

1. Bộ đo nhỏ **từ dữ liệu của mình** (tập kiểm tra tách riêng — skill `experiment-design`), cộng baseline hiện có.
2. Chạy 2–4 ứng viên cùng điều kiện, đo chất lượng + độ trễ + bộ nhớ (skill `benchmark` của pack `ml-dl`).
3. Báo chênh lệch kèm khoảng tin cậy; con số trên card chỉ là gợi ý.

## 4. Đưa vào dự án

- **Ghim revision** (commit sha trên Hub) khi tải: `hf download <repo> --revision <sha>` / `revision=` trong code.
- Trọng số ngoài git (R40.10); ghi nguồn, revision, giấy phép, băm vào ghi chú nghiên cứu và model card nội bộ.
- `trust_remote_code=True` = chạy mã của người khác trên máy bạn: chỉ sau khi đọc mã đó, ghi lý do trong DEC.
- Token `HF_TOKEN` qua biến môi trường, không trong code hay log.

Không có CLI `hf` hay MCP Hugging Face: `python -m scripts.research hf-...` + trang web của Hub cho mọi bước trên.
