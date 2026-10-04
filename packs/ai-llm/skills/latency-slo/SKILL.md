---
name: latency-slo
description: Đo độ trễ của hệ thống có gọi mô hình ngôn ngữ cho đúng — P50/P95/P99 từ mẫu thô, tách TTFT khỏi tổng thời gian, tách cold start, nêu tải đồng thời — và đặt SLO kiểm được. Dùng khi cần báo độ trễ, so tốc độ hai phương án/model, đặt hoặc kiểm SLO, điều tra "app chậm", hoặc trước khi tuyên bố một thay đổi làm hệ thống nhanh hơn.
---

# Độ trễ: đo đúng trước khi kết luận

## Bốn lỗi làm con số độ trễ vô nghĩa

1. **Lấy trung bình các percentile.** P95 của từng lô rồi lấy trung bình **không phải** P95 của toàn bộ.
   Percentile phải tính lại từ **mẫu thô** gộp chung (hoặc từ histogram gộp được, như HDR histogram).
2. **Báo percentile đuôi từ quá ít mẫu.** Số mẫu nằm phía trên P*p* là `n × (1 − p)`:
   - 20 request ⇒ P95 dựa trên **1** mẫu, P99 dựa trên **0,2** mẫu — tức không tồn tại.
   - 100 request ⇒ P95 dựa trên 5 mẫu (còn rất nhiễu), P99 trên 1.
   - 1 000 request ⇒ P99 dựa trên 10 mẫu.
   **Quy tắc:** chỉ báo P*p* khi `n × (1 − p) ≥ 10`. Không đủ mẫu thì báo "chưa đủ mẫu", không in ra số.
3. **Tính cả lượt thử lại và thời gian chờ backoff vào độ trễ mô hình.** Phương án gặp nhiều lỗi 429 sẽ
   trông chậm hơn vì lý do hạ tầng. Ghi hai cột: độ trễ **lượt thành công cuối** và tổng thời gian đồng hồ.
4. **Không nói đang chạy ở tải đồng thời bao nhiêu.** Độ trễ ở 1 request đồng thời và ở 50 là hai con số
   khác nhau; con số không kèm tải đồng thời không so sánh được với gì.

## Tách các thành phần

Với lời gọi có stream:

| Chỉ số | Đo từ → tới | Quan trọng với |
|---|---|---|
| **TTFT** (time to first token) | gửi request → token đầu tiên về | Giao diện người dùng chờ — cảm giác "app có phản hồi" |
| Thời gian sinh | token đầu → token cuối | Độ dài câu trả lời × tốc độ sinh |
| **Tổng** | gửi request → token cuối | Job nền, pipeline, agent |
| Đầu-cuối | người dùng bấm → màn hình hiển thị xong | SLO thật của sản phẩm |

**TTFT ≠ tổng.** Một thay đổi làm tổng nhanh hơn có thể làm TTFT chậm hơn (ví dụ bật suy luận dài hơn).
Với giao diện stream, TTFT thường là chỉ số người dùng cảm nhận; với job nền, tổng mới là chỉ số đúng.

Với agent nhiều bước: ghi độ trễ **từng lời gọi mô hình và từng lời gọi tool** riêng. Chỉ có tổng theo tập
thì không phân biệt được tool chậm với mô hình chậm.

## Cold start báo riêng

Dịch vụ ngủ khi rảnh (gói miễn phí nhiều nền tảng tắt tiến trình sau một khoảng không dùng), cache mô hình
chưa nóng, kết nối pool chưa mở — request đầu sau khi thức dậy chậm gấp nhiều lần. **Không trộn vào phân
phối chung**: tách thành `cold_start` riêng (đếm số lần + phân phối riêng), vì chúng sửa bằng cách khác
(giữ ấm, pre-warm) và làm P99 phình ra che mất vấn đề thật.

## Quy trình đo một phương án

```text
1. Cố định: model, cấu hình sinh, prompt, tải đồng thời, vùng máy chủ.
2. Warmup: bỏ K request đầu (ghi lại nhưng không tính) — hoặc đo riêng làm cold start.
3. Chạy đủ n để n × (1 − p) ≥ 10 cho percentile cao nhất định báo.
4. Ghi MẪU THÔ mỗi request: ttft_ms, total_ms, output_tokens, attempt, concurrency, cold (true/false).
5. Tính P50/P95/P99 từ mẫu thô gộp; loại attempt > 1 khỏi cột độ trễ mô hình.
6. Báo kèm: n, tải đồng thời, số cold start, số request lỗi (không bỏ im lặng).
```

## So hai phương án

- Chạy **xen kẽ** hoặc cùng khung giờ — độ trễ API dao động theo giờ trong ngày. Chạy phương án A buổi sáng
  và B buổi tối là đo khác biệt giữa sáng và tối.
- Cùng mức cache nóng/lạnh (xem `token-economics`).
- Khác biệt nhỏ hơn độ dao động giữa các lần chạy lặp lại **không phải khác biệt**. Chạy lặp, báo khoảng.

## SLO kiểm được

Một SLO phải trả lời được bằng log, không bằng cảm giác:

```text
"P95 của TTFT cho /chat < 1 500 ms, đo trên cửa sổ 7 ngày, loại cold start, ở tải thực tế,
 với tối thiểu 200 request trong cửa sổ (n × 0,05 ≥ 10)."
```

Thiếu một trong: percentile · chỉ số (TTFT hay tổng) · cửa sổ thời gian · điều kiện loại trừ · số mẫu tối
thiểu — thì đó là mong muốn, chưa phải SLO.
