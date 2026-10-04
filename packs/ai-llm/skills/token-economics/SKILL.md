---
name: token-economics
description: Đo và so chi phí gọi mô hình ngôn ngữ bằng số token THẬT từ response, quy về chi phí trên một đơn vị công việc để so được giữa các phiên, model và phương án. Dùng khi hỏi "một request tốn bao nhiêu", khi so hai prompt/model/phương án về chi phí, khi hoá đơn API tăng bất thường, khi thiết kế vòng lặp agent, hoặc khi cần báo token/s, token/request, $/request.
---

# Kinh tế token: đo thật, quy về việc hoàn thành

## Nguyên tắc số một: không ước lượng, đọc `usage`

Mọi con số token lấy từ khối `usage` trong **response thật** của nhà cung cấp — không phải `len(text)/4`,
không phải tokenizer của hãng khác. Ước lượng theo độ dài sai đủ lớn để **đảo ngược** kết luận so sánh
hai phương án.

Đếm trước khi gửi (ước chi phí một prompt dài): dùng endpoint đếm token của chính nhà cung cấp (Anthropic:
`messages.count_tokens`). Không dùng `tiktoken` cho mô hình không phải OpenAI.

## Ghi gì cho mỗi lời gọi

Một dòng log mỗi lời gọi mô hình (không phải mỗi request HTTP của người dùng):

| Trường | Vì sao cần |
|---|---|
| `model` **đọc từ response** | Nhà cung cấp có thể định tuyến sang model khác; chi phí tính theo model đã chạy, không phải model đã xin |
| `input_tokens` (không cache) | Giá đầy đủ |
| `cache_write_tokens` | Đắt HƠN input thường |
| `cache_read_tokens` | Rẻ hơn rất nhiều |
| `output_tokens` | Thường là phần đắt nhất |
| `stop_reason` | Phân biệt xong việc / bị cắt ở `max_tokens` / từ chối |
| `task_id`, `session_id`, `attempt` | Để cộng lên đơn vị công việc và tách lượt thử lại |
| `latency_ms` | Xem skill `latency-slo` |

**Tên trường theo nhà cung cấp** — đặt đúng một chỗ ánh xạ trong `src/llm/` (cửa ngõ duy nhất được import
SDK, xem `contracts/boundaries.yaml`), để phần còn lại của hệ thống chỉ thấy tên trung lập ở bảng trên.

| Trường trung lập | Anthropic (đã kiểm) | Nhà cung cấp khác |
|---|---|---|
| `input_tokens` | `usage.input_tokens` | **đọc tài liệu của họ, đừng đoán** |
| `cache_write_tokens` | `usage.cache_creation_input_tokens` | — |
| `cache_read_tokens` | `usage.cache_read_input_tokens` | — |
| `output_tokens` | `usage.output_tokens` | — |

## Công thức

```
chi_phí_lời_gọi = input_tokens      × giá_input
                + cache_write_tokens × giá_cache_write
                + cache_read_tokens  × giá_cache_read
                + output_tokens     × giá_output
```

**Bảng giá đặt trong một file cấu hình có `nguồn` (URL trang giá) và `ngày_kiểm`** — không rải số trong
code. Giá đổi theo thời gian; một con số không có ngày kiểm là con số không kiểm được.

Tham khảo tỷ lệ (Anthropic, bảng giá cache ngày 24/06/2026 — kiểm lại trước khi dùng): output đắt gấp
**5×** input ở mọi model hiện hành; cache write ~**1,25×** input; cache read ~**0,1×** input; Batch API
~**50%**.

## Đơn vị so sánh: công việc hoàn thành, không phải request

**`$/request` là đơn vị sai để so giữa các phiên.** Một phương án rẻ hơn mỗi request nhưng cần nhiều lượt
hơn, hoặc thử lại nhiều hơn, để làm xong cùng một việc thì **đắt hơn**.

Chọn đơn vị công việc theo dự án, rồi cộng mọi lời gọi thuộc về nó (kể cả lượt thử lại, kể cả lời gọi
của LLM-judge nếu có — nhưng ghi judge **riêng một cột**):

| Loại dự án | Đơn vị hợp lý |
|---|---|
| Chatbot/hỏi đáp | $/cuộc hội thoại giải quyết được |
| Sinh nội dung có duyệt | $/bản được **duyệt** (không phải $/bản sinh ra) |
| Agent làm việc | $/ticket hoàn thành, $/PR merge được |
| Pipeline trích xuất | $/bản ghi trích đúng |

Việc **thất bại** vẫn tốn tiền: cộng chi phí của chúng vào mẫu số theo cách bạn định nghĩa (tốn tiền
nhưng không ra việc) — nếu bỏ đi, phương án hay thất bại sẽ trông rẻ.

## Vòng lặp agent: chi phí không tuyến tính theo số bước

Mỗi bước gửi lại **toàn bộ lịch sử** trước đó. Không cache và không nén thì tổng input qua n bước tăng xấp
xỉ **bậc hai** theo n. Hệ quả thực hành:

- **Tỷ lệ cache hit là biến số chi phí chính** của vòng lặp dài, lớn hơn cả giá mỗi token.
- Đo `cache_read_tokens / (input_tokens + cache_read_tokens + cache_write_tokens)` theo từng bước. Bằng 0
  qua nhiều bước có cùng tiền tố nghĩa là có **thứ vô hiệu hoá cache âm thầm**: thời gian hiện tại hoặc
  UUID trong system prompt, `json.dumps` không sắp khoá, danh sách tool đổi thứ tự giữa các lượt.
- Tiền tố ngắn hơn ngưỡng tối thiểu (tuỳ model, khoảng vài trăm tới vài nghìn token) **không được cache mà
  không báo lỗi gì**.
- Cache gắn theo model: định tuyến qua nhiều model trong một phiên là **mất** cache giữa chúng.

## So sánh giữa các phiên — bẫy hay gặp

1. **Token không so được giữa các thế hệ tokenizer.** Cùng một văn bản, tokenizer mới có thể ra nhiều
   token hơn (Anthropic: tokenizer từ Opus 4.7 ra khoảng 1–1,35× so với thế hệ trước). So bằng **$ và đơn
   vị công việc**, không so số token thô qua các đời model.
2. **Một phương án chạy cache nóng, phương án kia chạy cache lạnh** ⇒ chênh lệch là do thứ tự chạy, không
   phải do phương án. So khi tỷ lệ cache-read tương đương, hoặc nêu rõ độ chênh.
3. **Lượt thử lại không được đếm** ⇒ phương án gặp nhiều lỗi 429 trông rẻ hơn thực tế. Đếm mọi lượt.
4. **Gộp chi phí LLM-judge vào chi phí hệ thống** ⇒ làm mờ khác biệt giữa các phương án. Tách cột.

## token/s

- `output_tokens / thời_gian_sinh` chỉ có nghĩa với **đầu ra dạng stream**, đo từ token đầu tới token cuối
  (không tính thời gian chờ token đầu — đó là TTFT, xem `latency-slo`).
- Thông lượng **hệ thống** (request/giây ở tải đồng thời X) là một số khác, đừng gộp.

## Báo cáo tối thiểu

```
phương_án | n_việc | tỷ_lệ_hoàn_thành | $/việc_hoàn_thành | cache_hit | output/input | judge_$ | ngày_kiểm_giá
```

Không có cột `tỷ_lệ_hoàn_thành` thì cột `$/việc` không đọc được.
