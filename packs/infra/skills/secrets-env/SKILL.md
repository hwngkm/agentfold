---
name: secrets-env
description: Quản lý cấu hình và bí mật theo môi trường (dev, staging, production) — một danh mục biến trong .env.example, bí mật chỉ trên kho/dashboard, khoá riêng mỗi môi trường, xoay khoá, và cổng cấu hình production đổ khi thiếu hoặc còn giá trị mặc định. Dùng khi thêm biến môi trường hay khoá API mới, khi thêm môi trường staging, khi nghi khoá bị lộ, hoặc khi dịch vụ chạy production với cấu hình sai mà không báo lỗi.
---

# Cấu hình và bí mật: một danh mục, nhiều môi trường, không có gì thô trong git

## Thêm một biến

1. Khai trong lớp settings của đúng miền (`src/core/settings.py`, `src/llm/settings.py`) có kiểu và mặc định an
   toàn cho dev.
2. Thêm vào `.env.example` **cùng PR**, kèm chú thích: dùng làm gì, lấy ở đâu, bí mật hay không.
3. Bí mật: thêm vào `render.yaml` với `sync: false` (giá trị đặt trên dashboard), Vercel project settings, hoặc kho
   bí mật của nền tảng.
4. Biến mà thiếu ở production sẽ gây hại im lặng → thêm vào `src/core/production_gate.py` để dịch vụ ĐỔ khi khởi
   động, kèm test trong `tests/unit/test_production_gate.py`.

## Mỗi môi trường một bộ khoá

Khoá dev ≠ staging ≠ production. Lộ khoá dev không lộ production; hoá đơn tách được; thu hồi một môi trường không
làm sập môi trường khác. Không bao giờ dùng khoá production trên máy dev "cho nhanh".

## Agent và bí mật

- Agent không cần thấy giá trị bí mật để làm việc — chỉ cần tên biến. Không dán khoá vào chat (R60.7).
- `.mcp.json` và mọi cấu hình được commit chỉ chứa `${TEN_BIEN}` (lưới canh `tests/guards/test_mcp_no_secrets.py`,
  `scripts/secret_scan.py`).
- Không in biến môi trường ra log, kể cả khi gỡ lỗi; không đưa vào thông điệp lỗi trả về client.

## Lộ khoá

1. **Thu hồi/xoay trên nhà cung cấp NGAY** — trước mọi việc khác.
2. Đặt khoá mới vào dashboard/kho bí mật của từng môi trường bị ảnh hưởng; deploy lại.
3. Rồi mới dọn repo/lịch sử. Xoá khỏi lịch sử git không rút lại thứ đã đẩy hay đã bị sao chép.
4. Ghi `new incident` (skill `incident`) và thêm lưới bắt lớp lỗi đó (vd. tiền tố khoá mới vào `scripts/secret_scan.py`).

## Xoay khoá định kỳ

Ghi ngày tạo và người sở hữu mỗi khoá (trong kho bí mật hoặc tài liệu vận hành, không trong git). Khoá không ai
nhận là chủ thì thu hồi.
