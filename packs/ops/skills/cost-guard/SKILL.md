---
name: cost-guard
description: Giữ chi phí trong ngân sách — phút CI, chi phí API mô hình, hạ tầng — bằng số đo thật, ngưỡng cảnh báo trước khi chạm trần, và quy về chi phí trên một đơn vị công việc. Dùng khi CI tốn phút bất thường, khi hoá đơn API/hạ tầng tăng, khi thêm job hoặc tính năng gọi mô hình, hoặc khi lập ngân sách cho một đợt chạy lớn (eval, embed, huấn luyện).
---

# Chi phí: đo từ nguồn thật, báo trước khi chạm trần

## 1. Ba nguồn tiền hay trôi

| Nguồn | Đo ở đâu | Bẫy đã gặp |
|---|---|---|
| Phút CI | GitHub → Settings → Billing; `gh run list --json durationMs` | đẩy từng commit lên PR đang mở — từng tiêu hơn hai nghìn phút trong hai tuần (R50.6) |
| API mô hình | trường `usage` trong từng response, cộng dồn | ước theo số ký tự thay vì token thật; quên token cache/ngữ cảnh lặp lại |
| Hạ tầng | dashboard nhà cung cấp | dịch vụ thử nghiệm quên tắt; ổ đĩa/sao lưu tăng dần |

Chi tiết token và cache: skill `token-economics` (pack `ai-llm`).

## 2. Ngân sách trước khi chạy việc lớn

Trước một đợt eval/embed/huấn luyện/chạy hàng loạt:
1. Chạy trên mẫu nhỏ (1–5%), đo chi phí và thời gian thật.
2. Nhân lên, cộng biên an toàn, ghi vào ticket.
3. Vượt ngân sách ticket cho phép → thu hẹp phạm vi và báo lại, không lặng lẽ chạy (R40.12).

## 3. Ngưỡng cảnh báo

- Đặt cảnh báo chi tiêu trên nhà cung cấp ở ~50% và ~80% ngân sách tháng — cảnh báo ở 100% là quá muộn.
- Khoá API riêng cho mỗi môi trường (dev/staging/prod) để biết tiền đi đâu và thu hồi riêng được.
- Trong code: giới hạn cứng số lần gọi/vòng lặp agent và độ dài đầu ra (`max_tokens`); vượt thì dừng có lỗi rõ.

## 4. Báo cáo

Quy về **chi phí trên một đơn vị công việc** (mỗi câu trả lời, mỗi tài liệu, mỗi lượt CI) để so được giữa hai
phương án. Ghi nguồn số liệu và ngày lấy — giá nhà cung cấp đổi, con số không có ngày thì không so được.
