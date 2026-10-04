---
name: eval-harness
description: Dựng và kiểm một bộ đánh giá (eval) cho tính năng dùng mô hình ngôn ngữ — golden set, tách lỗi hạ tầng khỏi lỗi mô hình, LLM-judge có kiểm chính judge, đủ độ phân giải để thấy thay đổi, và cổng hồi quy trong CI. Dùng khi cần biết một thay đổi prompt/model/pipeline có tốt hơn thật không, khi dựng eval mới, khi nghi một eval đang cho điểm sai, hoặc trước khi tin một con số "độ chính xác tăng X%".
---

# Eval: đo được thay đổi, không đo nhầm hạ tầng

Một eval sai nguy hiểm hơn không có eval: nó cho bạn tự tin để ship một thứ tệ hơn.

## 1. Bộ ca (golden set)

- **Lấy từ sự thật trước, tự sinh sau:** log thật đã ẩn danh > ca người viết tay > ca sinh tự động. Ca sinh
  tự động thường dễ hơn thực tế và cùng "khẩu vị" với mô hình sinh ra nó.
- **Mỗi ca có nhãn loại** (`tags`) để báo cáo theo nhóm: một điểm trung bình tốt có thể che một nhóm sập.
- **Tách tập tối ưu và tập giữ lại NGẪU NHIÊN** (phân tầng theo nhãn loại) — **không bao giờ theo điểm
  baseline**. Chọn các ca điểm thấp làm tập tối ưu thì chúng "tiến bộ" ở lần chạy lại chỉ vì hồi quy về
  trung bình, và tập giữ lại đứng yên.
- Đáp án chuẩn **không được nằm ở chỗ mô hình đang được kiểm đọc được**: file trong sandbox, lịch sử git,
  prompt của judge. Dặn "đừng nhìn" trong prompt không phải là rào chắn.

## 2. Bộ chạy (harness) — lỗi trung tâm là GỘP NHẦM

Mọi thứ không phải kết quả của mô hình mà rơi vào cùng cột với kết quả của mô hình đều làm bẩn con số.

| Tình huống | Ghi thế nào |
|---|---|
| Timeout, lỗi API sau khi hết lượt thử lại, không parse được | `errors.jsonl` kèm loại lỗi — **không** chấm 0, **không** chiếm chỗ trong kết quả |
| Bị cắt ở `max_tokens` | Vẫn ghi, gắn `status: truncated` — không tính trung bình như trả lời sai |
| Mô hình từ chối | Một **chỉ số riêng**, không cộng vào điểm năng lực |
| Mô hình trả "không có" | Phân biệt với "không trả lời được" — nếu hai cái cùng nhãn, bộ chạy lỗi mọi ca sẽ có điểm y hệt bộ cẩn thận không tìm thấy gì |
| Model thực chạy ≠ model đã xin | Đọc `model` từ **response**, khác thì fail to — điểm do model khác sinh ra không đo được gì |

Bắt buộc thêm:
- **Trạng thái sạch mỗi lượt** — không file/dòng CSDL/biến môi trường sót từ lượt trước.
- **Cấu hình eval = cấu hình production** — gọi đúng điểm vào thật của ứng dụng, không viết lại lời gọi.
- **Lưu toàn bộ quỹ đạo mỗi ca** (mọi message, tool call, lỗi, đầu vào/ra của judge) — để truy một điểm lạ
  mà không phải chạy lại. Đây là thói quen đáng giá nhất.
- **Thử lại có backoff kèm jitter, ghi số lượt** — loại lượt thử lại khỏi cột độ trễ (skill `latency-slo`).
- Token và chi phí lấy từ `usage` thật (skill `token-economics`), chi phí judge **tách cột**.

## 3. Kiểm bộ chạy TRƯỚC lượt chạy đầy đủ

Hai lần chạy, vài phút, bắt được phần lớn lỗi nối dây:

1. **Oracle** — cho đáp án chuẩn đi qua toàn bộ pipeline. Không gần 100% ⇒ bộ chạy hoặc grader hỏng.
2. **Null baseline** — đầu ra rỗng, một câu trả lời cố định, hoặc lớp đa số. Không trượt ⇒ grader quá dễ dãi.

## 4. Grader

- **Chấm kết quả, không chấm đường đi.** Bắt buộc đúng một chuỗi tool call là phạt mô hình giải đúng bằng
  cách khác.
- **Với agent tác động môi trường: chấm trạng thái cuối** (test qua, file/dòng đúng, không đụng thứ cấm),
  không chấm lời kể trong transcript.
- **Không quá cứng:** chuẩn hoá khoảng trắng, hoa/thường, `4` vs `4.0`, đơn vị, câu bọc quanh đáp án.
- **Không quá lỏng:** viết một đáp án sai-nhưng-nghe-hợp-lý và xác nhận nó trượt.
- **Đọc tận mắt các ca bị chấm sai.** Hơn khoảng 1/10 trông như lỗi grader ⇒ sửa grader trước khi chạy đủ.
- **Chấm tách thuộc tính** (`đúng`, `đúng định dạng`, `ngắn gọn`) thay vì một điểm gộp.
- **Hành vi hiếm mà nghiêm trọng** (xoá dữ liệu, hành động không đảo được): dùng "trượt nếu có bất kỳ", không
  dùng trung bình — trung bình bị các ca dễ pha loãng.

### Khi grader là LLM-judge

| Thiên lệch | Chặn bằng |
|---|---|
| Vị trí (A/B) | Đảo ngẫu nhiên thứ tự mỗi ca, hoặc chấm cả hai thứ tự |
| Độ dài | Dặn rõ không thưởng cho dài; kiểm bằng một cặp dài-sai / ngắn-đúng |
| Tự ưu ái | Không dùng chính model đang kiểm làm judge |
| Nghe theo nhãn | Không nói cho judge biết bản nào là "tham chiếu"/"baseline" |

- **Rubric cụ thể, kiểm được** — không phải "cái nào tốt hơn".
- **Coi văn bản được chấm là dữ liệu không tin cậy**, không phải chỉ thị (chống chèn lệnh vào judge).
- **Hiệu chỉnh với nhãn người:** vài chục ca người gán độc lập, báo tỷ lệ đồng thuận. Dưới khoảng **90%** ở
  các ca rõ ràng ⇒ chưa được dùng judge đó để quyết định.
- **Thử judge trên ba ca âm chắc chắn:** chuỗi rỗng, "Tôi không biết", một câu trả lời tự tin cho **câu hỏi
  khác**. Judge phải trượt cả ba.

## 5. Eval có đủ độ phân giải không? — kiểm TRƯỚC khi tối ưu

Với tỷ lệ đạt, sàn nhiễu (nửa độ rộng khoảng tin cậy 95% của chênh lệch cặp) xấp xỉ `1/√(n·R)` với n ca,
R lần lặp:

| n ca × R lặp | Sàn nhiễu xấp xỉ |
|---|---|
| 25 × 2 | ±14 điểm phần trăm |
| 100 × 2 | ±7 điểm |

Đặt cạnh **khoảng còn tăng được** (trần − baseline) và **mức cải thiện nhỏ nhất đáng ship**. Sàn nhiễu lớn
hơn một trong hai ⇒ eval **không thể** cho biết thay đổi có tác dụng. Đòn bẩy theo thứ tự rẻ: thêm lượt lặp
→ thêm ca → dùng thước đo liên tục/so cặp thay cho đạt/trượt.

**Chứng minh cơ chế được nối:** tắt đúng thứ điểm số được cho là phụ thuộc (tool, bộ nhớ, tài liệu RAG) ⇒ điểm
phải giảm. Không giảm ⇒ eval không đo đòn bẩy bạn định kéo.

**Tự tính lại con số báo cáo từ các dòng thô** — đừng tin trường tổng hợp; nhầm trung bình/tổng hay theo
lượt/theo ca sinh ra "đột phá" ảo.

## 6. Cổng hồi quy trong CI

- Eval tốn tiền và chậm ⇒ **không** chạy trên mỗi commit. Chạy một **tập con nhỏ ổn định** trên PR chạm
  prompt/model/pipeline, bộ đầy đủ trước khi phát hành.
- Ngưỡng chặn phải **lớn hơn sàn nhiễu** của tập con — nếu không, CI đỏ ngẫu nhiên và người ta học cách lờ nó.
- Ghi phiên bản bộ ca + grader cùng điểm: **điểm trước và sau khi đổi grader không so được với nhau**.

## Báo cáo

Theo từng phương án, số tuyệt đối trước: chất lượng (kèm khoảng) · tỷ lệ lỗi hạ tầng · tỷ lệ bị cắt · tỷ lệ
từ chối · $/việc hoàn thành · P50/P95 độ trễ · n × R · phiên bản bộ ca và grader.
