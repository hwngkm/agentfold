# RULE 10 — An toàn miền (dự án điền)

> Owner: **R2** (chủ miền) + **R1**. Đây là KHUNG: mỗi dự án thay phần ví dụ bằng bất biến của miền mình,
> đăng ký chúng vào `docs/design/invariants.yaml`, và viết lưới canh cho từng cái.

## R10.1 — Luật đỏ của miền

Luật đỏ là điều mà vi phạm thì gây hại thật cho người dùng, không phải bug thường. Viết mỗi luật theo mẫu:

| Trường | Nội dung |
|---|---|
| Phát biểu | một câu, kiểm được bằng máy |
| Vì sao | hại cụ thể nếu vi phạm |
| Cưỡng chế | test/lưới canh nào đỏ khi vi phạm (đường dẫn) |
| Chủ | vai trò quyết định khi có tranh cãi |

**Ví dụ cho một ứng dụng LLM có nội dung chuyên môn nhạy cảm (tư vấn có con số, như tài chính hay y tế):**

1. *Mô hình ngôn ngữ chỉ chọn mục + số lượng; mọi con số dẫn xuất tính bằng truy vấn SQL từ bảng dữ liệu có nguồn.*
   Cưỡng chế: schema đầu ra của mô hình chỉ có hai trường; tầng tính toán cấm import SDK LLM.
2. *Không con số nào không có nguồn;* giá trị ước tính phải gắn nhãn "ước tính" và độ tin cậy.
3. *Nội dung chưa được chuyên gia duyệt không bao giờ tới người dùng cuối* — qua API, giao diện, email hay xuất file.

Template minh hoạ luật 1–2 bằng miền báo giá mẫu (`src/domain/catalog/pricing.py`, `src/agents/quote_agent.py`)
và luật 3 bằng sổ hành động rủi ro (`src/agents/actions.py`).

## R10.2 — Con số nghiệp vụ chỉ có một nguồn

Ngưỡng, hệ số, đơn giá, giới hạn… nằm ở MỘT chỗ có nguồn (bảng dữ liệu hoặc hằng số có `source_ref` trong
docstring), không rải trong prompt, giao diện hay test. Không tra được nguồn: **nói không biết**, không đoán.
Agent không bao giờ tự đặt con số nghiệp vụ — mở câu hỏi cho chủ miền.

## R10.3 — Phạm vi cho phép của hệ thống

Liệt kê điều hệ thống **không** làm (vd. chẩn đoán, kê đơn, tư vấn đầu tư cá nhân) và câu trả lời chuẩn khi
người dùng hỏi những điều đó. Câu trả lời chuẩn nằm trong code (một chỗ), có test chặn.

## R10.4 — Người là cổng cuối

Mọi nội dung có hệ quả tới người dùng cuối đi qua trạng thái duyệt. Không có cờ, biến môi trường, tham số
API hay đường "admin" nào cho phép bỏ qua. Test phải tấn công vào đường đi THẬT của dữ liệu (gọi API như người
dùng), không chỉ gọi hàm kiểm quyền rồi tự khen.

## R10.5 — Khi hệ thống không chắc

Thiếu dữ liệu, xung đột quy tắc, độ tin cậy thấp: thu hẹp dịch vụ, hỏi lại cụ thể, hoặc chuyển người — không
đoán. Cờ "cần người xem" chỉ bật khi thật sự xung đột; bật cho mọi ca thì người duyệt sẽ thôi đọc cờ.

## R10.6 — Checklist trước khi merge PR chạm miền

- [ ] Không con số nghiệp vụ mới nào thiếu nguồn.
- [ ] Không đường nào để đầu ra mô hình ngôn ngữ thành con số người dùng thấy.
- [ ] Không đường vòng qua trạng thái duyệt.
- [ ] Lưới canh của bất biến miền xanh, và PR không nới lưới nào.
- [ ] Chủ miền (R2) đã review.
