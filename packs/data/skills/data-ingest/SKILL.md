---
name: data-ingest
description: Viết hoặc sửa bước nạp dữ liệu từ nguồn ngoài (file, API, trang web, CSDL khác) — provenance bắt buộc trên từng dòng, mặc định chạy thử, chạy lại nhiều lần không nhân bản, lưu bản gốc tách khỏi bản chuẩn hoá, và tôn trọng giấy phép/robots. Dùng khi thêm nguồn dữ liệu mới, khi viết script crawl/import, khi pipeline nạp ra dòng trùng hoặc thiếu nguồn, hoặc khi cần nạp lại sau khi đổi logic chuẩn hoá.
---

# Nạp dữ liệu: biết từng dòng từ đâu tới, và chạy lại không hỏng

Luật nền: `docs/rules/40-data.md` — R40.2 (không dòng nào thiếu nguồn), R40.7 (giấy phép), R40.10 (dữ liệu không
vào git), R40.12 (gộp lần chạy tốn kém).

## Kiến trúc tối thiểu

```
nguồn → raw/ (bản gốc nguyên vẹn, kèm metadata tải) → normalized/ (bản chuẩn hoá) → nạp CSDL/chỉ mục
```

- **Giữ bản gốc** (byte nguyên vẹn + URL/đường dẫn + thời điểm tải + băm). Đổi logic chuẩn hoá thì chạy lại từ
  `raw/`, không tải lại nguồn.
- Thư mục dữ liệu nằm trong `data/` (gitignored) hoặc kho dữ liệu riêng; chỉ mã và fixture nhỏ vào git.

## Provenance trên từng dòng

Mỗi bản ghi chuẩn hoá có: `source` (tổ chức/bộ dữ liệu), `source_ref` (URL, trang, mã — người khác kiểm lại được),
`fetched_at`, `content_hash`, và nếu trích từ văn bản: vị trí (`char_start`, `char_end`) hoặc câu trích nguyên văn
để đối chiếu.

## Thủ tục viết một bước nạp

1. **Chạy thử mặc định:** lệnh không có `--apply` chỉ in sẽ thêm/sửa/xoá bao nhiêu bản ghi, không ghi gì.
2. **Idempotent:** khoá tự nhiên (vd. `source` + `source_ref`) và upsert; chạy hai lần cho cùng kết quả. Test bằng
   cách chạy hai lần trên fixture và so số bản ghi.
3. **Lỗi từng dòng không giết cả lô:** ghi dòng lỗi vào báo cáo (lý do, vị trí), tiếp tục; cuối lần chạy in tổng
   *thành công / bỏ qua / lỗi*. Tỷ lệ lỗi vượt ngưỡng ghi trong ticket thì dừng có mã lỗi.
4. **Giới hạn và lịch sự với nguồn:** tôn trọng `robots.txt` và điều khoản; giới hạn tốc độ; không vượt rào chắn
   truy cập; ghi `User-Agent` nhận diện được.
5. **Fixture nhỏ trong `tests/`** cắt từ dữ liệu thật đã khử định danh hoặc tự viết — không dùng dữ liệu thật trong test.

## Trước khi chạy lớn

Ước thời gian/chi phí trên mẫu nhỏ (R40.12, skill `cost-guard` nếu pack `ops` bật). Chạy xong: kiểm chất lượng
(skill `data-quality`) TRƯỚC khi nạp vào nơi người dùng thấy.
