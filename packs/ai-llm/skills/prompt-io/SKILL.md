---
name: prompt-io
description: Thiết kế đầu vào/đầu ra của một lời gọi mô hình ngôn ngữ theo mẫu "mô hình chọn, code tính" — schema hẹp cấm trường lạ, dữ liệu không tin cậy được rào lại, kiểm stop_reason trước khi đọc kết quả, thử lại có giới hạn. Dùng khi thêm một lời gọi LLM mới, khi mô hình trả về định dạng sai hoặc trường thừa, khi đầu vào đến từ người dùng/tài liệu ngoài, hoặc khi có ý định để mô hình tự tính một con số.
---

# Vào/ra của lời gọi mô hình: hẹp, có rào, kiểm trước khi tin

Mẫu chuẩn của template: `src/agents/quote_agent.py`. Đọc nó trước — skill này giải thích **vì sao** từng
chỗ ở đó được viết như vậy, để áp lại cho lời gọi mới.

## 1. Mô hình chọn, code tính

Trước khi viết schema, trả lời: **con số nào người dùng sẽ thấy?** Mọi con số đó phải do code tất định
tính từ dữ liệu có nguồn (`src/domain/`), không do mô hình sinh.

```python
# ❌ mô hình trả về tổng tiền — không kiểm được, không có nguồn
class Bad(BaseModel):
    items: list[str]
    total_price: float


# ✅ mô hình chỉ chọn mã + số lượng; code tra giá từ danh mục có nguồn rồi tính
class ItemChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: str = Field(min_length=1, max_length=64)
    quantity: int = Field(gt=0, le=MAX_QUANTITY)
```

Hệ quả an toàn: kể cả khi prompt injection **thành công hoàn toàn**, kẻ tấn công chỉ đổi được *chọn gì*,
không đổi được *bao nhiêu* — mã lạ bị danh mục từ chối, số lượng bị chặn bởi `le=`.

## 2. Schema hẹp nhất có thể

- **`extra="forbid"`** — trường lạ (ví dụ mô hình tự thêm `total`) làm lời gọi **hỏng to**, không im lặng bỏ
  qua. Im lặng bỏ qua là cách một trường "tiện thể" lọt vào production.
- **Giới hạn mọi thứ:** độ dài chuỗi, khoảng số, kích thước danh sách (`max_length=`). Không giới hạn = một
  đầu ra lỗi có thể làm nổ bộ nhớ hoặc hoá đơn.
- **Enum thay cho chuỗi tự do** khi tập giá trị đóng.
- Dùng cơ chế structured output **của chính nhà cung cấp** (Anthropic: `output_config.format`, hoặc
  `strict: true` trên định nghĩa tool) trong adapter ở `src/llm/` — nhưng **vẫn validate lại bằng Pydantic**
  ở phía mình. Ràng buộc phía nhà cung cấp là lớp thứ nhất, không phải lớp duy nhất.

## 3. Dữ liệu không tin cậy phải được rào

Mọi văn bản đến từ người dùng, tài liệu ngoài, kết quả tool, trang web là **dữ liệu**, không phải **chỉ thị**.

| Bước | Hàm trong `src/llm/safety.py` | Làm gì |
|---|---|---|
| Phát hiện | `scan_for_injection(text, source=...)` | Ghi log dấu hiệu chèn lệnh — không chặn, để điều tra |
| Làm sạch + rào | `sanitize_untrusted()`, `fence(label, content)` | Cắt độ dài, làm phẳng xuống dòng, bọc trong khối có nhãn |
| Chặn rò rỉ | `assert_no_egress(text, known_secrets=...)` | Bí mật/PII trong prompt ⇒ **từ chối gửi** (fail closed) |

Thứ tự gọi xem `draft_quote` trong `quote_agent.py`. **Không** đưa định danh cá nhân vào prompt khi không
bắt buộc cho nhiệm vụ.

## 4. Kiểm `stop_reason` TRƯỚC khi đọc nội dung

Response trả về HTTP 200 **không** có nghĩa là có câu trả lời dùng được:

| `stop_reason` (tên theo Anthropic) | Nghĩa | Xử lý |
|---|---|---|
| `end_turn` | Xong bình thường | Parse + validate |
| `max_tokens` | Bị cắt giữa chừng | **Không** parse như bản đầy đủ — JSON cụt parse "thành công" một phần là lỗi âm thầm. Tăng giới hạn hoặc báo lỗi |
| `refusal` | Mô hình từ chối | Nhánh xử lý riêng, không coi là lỗi mạng, không thử lại nguyên xi |
| `tool_use` | Muốn gọi tool | Chạy tool, gửi lại kết quả |

Tên giá trị khác nhau giữa các nhà cung cấp — ánh xạ về tên trung lập trong adapter ở `src/llm/`.

**Parse đầu vào tool bằng `json.loads`/`model_validate_json`**, không bao giờ so khớp chuỗi thô: cách escape
ký tự (Unicode, dấu `/`) có thể khác nhau giữa các phiên bản model.

## 5. Thử lại có giới hạn, và biết thứ gì KHÔNG được thử lại

- Thử lại: 429, 5xx, lỗi kết nối, timeout — **có backoff kèm jitter, có trần số lượt**. SDK chính thức thường
  đã tự làm; đừng bọc thêm một vòng thử lại thứ hai quanh nó (nhân số lượt lên).
- **Không** thử lại nguyên xi: 400 (request sai — lặp lại vẫn sai), `refusal`, lỗi validate schema lặp lại
  (nếu thử lại, đưa lỗi validate vào lượt sau và **giới hạn 1–2 lần**, rồi fail to).
- Mô hình không khả dụng ⇒ `LLMUnavailableError` (`src/llm/gateway.py`) ⇒ tầng trên trả lỗi có thể thử lại
  (503 + `Retry-After`), không đoán thay.

## 6. Test không cần mạng

`ScriptedGateway` trong `src/llm/gateway.py` trả về các response dựng sẵn — dùng nó để test **mọi nhánh**:
đầu ra đúng, trường lạ (phải hỏng), mã không có trong danh mục (phải từ chối), số lượng vượt trần, prompt
chứa bí mật (phải bị chặn trước khi gửi). Không test nhánh lỗi thì nhánh lỗi là nhánh chưa từng chạy.

## Kiểm nhanh trước khi mở PR

- [ ] Không con số nào người dùng thấy do mô hình sinh ra
- [ ] Mọi model Pydantic đầu ra có `extra="forbid"` và giới hạn kích thước
- [ ] Văn bản không tin cậy đi qua `fence` + `scan_for_injection`; prompt đi qua `assert_no_egress`
- [ ] Có nhánh xử lý `max_tokens` và `refusal`, không chỉ nhánh thành công
- [ ] Import SDK nhà cung cấp chỉ trong `src/llm/` (lưới `test_import_boundaries.py` sẽ bắt nếu sai)
- [ ] Test bằng `ScriptedGateway` phủ nhánh trường lạ và nhánh bị chặn
