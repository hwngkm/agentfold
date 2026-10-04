---
name: incident
description: Xử lý và ghi một sự cố không đổ lỗi — chặn thiệt hại trước, rồi mốc thời gian, tác động đo được, nguyên nhân gốc (không dừng ở nguyên nhân gần), và một lưới canh mới để lớp sự cố đó không lặp lại. Dùng khi production hỏng, dữ liệu sai đã tới người dùng, bí mật bị lộ, CI/deploy để lọt lỗi, hoặc khi agent (kể cả chính mình) gây hỏng việc.
---

# Sự cố: chặn → hiểu → khoá lại bằng máy

## 1. Chặn thiệt hại (phút đầu)

| Loại | Làm ngay |
|---|---|
| Bản mới làm hỏng production | quay lui (skill `deploy-gate`), điều tra sau |
| Lộ bí mật | THU HỒI/xoay khoá trên nhà cung cấp → cập nhật biến môi trường → rồi mới dọn repo (`git` không rút lại thứ đã đẩy) |
| Dữ liệu sai đã tới người dùng | tắt tính năng (cờ) hoặc chặn đường xuất; giữ nguyên bằng chứng (log, bản ghi) |
| Agent đang phá cây làm việc | dừng tiến trình; không `reset --hard`/`stash` khi chưa biết còn gì đang chạy (R70.5) |

Báo người phụ trách (R1/R3 theo `docs/GOVERNANCE.md`) ngay khi chặn xong, không đợi viết xong báo cáo.

## 2. Ghi lại

```bash
python -m tools.agentctl new incident --role R3 --title "Commit đỏ lên production vì Render không chờ CI"
```

Điền theo khuôn, bằng SỰ THẬT kiểm được:

- **Chuyện gì xảy ra:** mốc thời gian (UTC) từ dấu hiệu đầu tiên tới khi chặn xong — lấy từ log/commit, không
  từ trí nhớ.
- **Tác động:** con số đo được (bao nhiêu yêu cầu lỗi, người dùng nào, bao lâu). Chưa đo được thì ghi "chưa đo".
- **Nguyên nhân gốc:** hỏi "vì sao" tới khi gặp một **cơ chế** còn thiếu (một cổng, một lưới canh, một luật chưa
  được máy kiểm) — "agent sơ suất" không phải nguyên nhân gốc, vì lần sau agent khác cũng sơ suất được.

## 3. Phòng ngừa = lưới canh

Mỗi sự cố có ít nhất một thứ **máy kiểm** sinh ra từ nó (skill `guard-net`): test trong `tests/guards/` kèm docstring
kể lại sự cố, hoặc bước CI, hoặc cổng cấu hình. Ghi đường dẫn test vào mục "Phòng ngừa". Không thêm được lưới
thì ghi vì sao và luật nào thay thế.

## Không đổ lỗi

Viết về hệ thống, không về người/agent. Sự cố do chính agent đang viết gây ra cũng ghi đầy đủ — giấu sự cố của
mình là vi phạm R00.5 nặng hơn chính sự cố.
