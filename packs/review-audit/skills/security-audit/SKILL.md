---
name: security-audit
description: Audit bảo mật của chính dự án — mô hình mối đe doạ (STRIDE) trên sơ đồ luồng dữ liệu có biên tin cậy, rủi ro ứng dụng web, rủi ro riêng của ứng dụng LLM và agent (chèn lệnh, lộ thông tin, quyền tác tử quá rộng, đầu ra không kiểm, tiêu thụ không giới hạn), quét phụ thuộc và bí mật; phát hiện kèm bằng chứng, mức độ và cách giảm. Dùng khi sắp phát hành bản lớn, khi thêm luồng dữ liệu nhạy cảm hay tích hợp ngoài, khi thêm công cụ/quyền cho agent, sau một sự cố bảo mật, hoặc khi pháp chế/khách hàng yêu cầu đánh giá.
---

# Audit bảo mật: bắt đầu từ dữ liệu đi đâu, không từ danh sách lỗ hổng

Phạm vi: mã, cấu hình và hạ tầng **của dự án này**, được chủ dự án yêu cầu. Luật nền: `docs/rules/60-agent-security.md`,
bất biến INV-004/005/006/007.

## 1. Mô hình mối đe doạ trên DFD

Cần sơ đồ luồng dữ liệu có biên tin cậy (skill `diagram-roadmap`) và bảng tích hợp ngoài (skill `design-tables`). Với
mỗi chỗ dữ liệu **vượt biên tin cậy**, đi qua STRIDE:

| Mối đe doạ | Câu hỏi | Kiểm trong template |
|---|---|---|
| Giả mạo danh tính | ai chứng minh mình là ai ở biên này? | `src/api/security.py`, JWT, cổng production |
| Sửa đổi | dữ liệu có thể bị đổi trên đường/trong kho? | ràng buộc CSDL, quyền ghi |
| Chối bỏ | hành động quan trọng có audit không? | bảng audit, trace id |
| Lộ thông tin | dữ liệu nhạy cảm có ra log, prompt, dịch vụ ngoài? | `assert_no_egress`, R40.8 |
| Từ chối dịch vụ | có giới hạn tốc độ, kích thước, vòng lặp? | trần vòng lặp agent, timeout |
| Leo thang quyền | vai trò thấp có làm được hành động cao? | `require_approval`, ma trận quyền |

## 2. Ứng dụng web

Kiểm theo nhóm rủi ro phổ biến (danh mục OWASP Top 10 cho ứng dụng web): kiểm soát truy cập hỏng (đối tượng của người
khác qua id), chèn (SQL, lệnh — ORM có tham số, không ghép chuỗi), cấu hình sai (CORS rộng, debug bật — cổng
`production_gate.py`), xác thực yếu, thành phần có lỗ hổng (mục 4), ghi log/giám sát thiếu.

## 3. Ứng dụng LLM và agent

Đối chiếu danh mục OWASP Top 10 cho ứng dụng LLM (bản hiện hành — đọc nguồn gốc, không dựa trí nhớ). Trọng tâm:

- **Chèn lệnh (trực tiếp và gián tiếp):** mọi dữ liệu ngoài vào prompt qua `sanitize_untrusted` + `fence`? Tài liệu truy
  hồi, trang web, kết quả công cụ có thể chứa chỉ thị — thử bằng ca chèn thật trong test.
- **Lộ thông tin nhạy cảm / lộ system prompt:** prompt chứa bí mật hay dữ liệu người khác không?
- **Xử lý đầu ra không kiểm:** đầu ra mô hình có bị render HTML, chạy như code/SQL, hay thành con số nghiệp vụ (INV-005)?
- **Quyền tác tử quá rộng:** công cụ nào ghi/xoá/gửi ra ngoài; có qua cổng người (skill `human-in-the-loop`)?
- **Tiêu thụ không giới hạn:** trần token, số vòng, chi phí mỗi người dùng.
- **Điểm yếu kho vector / chuỗi cung ứng mô hình:** ai ghi được vào kho truy hồi; mô hình tải từ nguồn nào, ghim revision chưa.

## 4. Phụ thuộc và bí mật

```bash
pip-audit -r requirements.txt
cd web && npm audit --omit=dev
python scripts/check_structure.py
python -m pytest tests/guards/test_mcp_no_secrets.py -q
```

Quét sâu mã nguồn trong phiên: plugin `claude-security` (pack này gợi ý); mỗi phát hiện của công cụ vẫn phải được người
đọc xác nhận — công cụ có báo nhầm.
Không có plugin: `pip-audit`, `npm audit` ở trên + đọc tay theo mục 1–3 là đường chính; công cụ quét chỉ bổ sung.

## 5. Đầu ra

Bảng phát hiện: *mã · mô tả · bằng chứng (file:dòng, lệnh tái hiện an toàn) · mức (nghiêm trọng/cao/trung bình/thấp) ·
khả năng × tác hại · cách giảm · lưới canh đề xuất*. Viết bằng chứng đủ để người sửa tái hiện, **không** viết mã khai
thác hoàn chỉnh. Phát hiện nghiêm trọng → báo người phụ trách ngay (R60, skill `incident`), không đợi xong báo cáo.
Bí mật đã lộ → thu hồi trước (skill `secrets-env`).
