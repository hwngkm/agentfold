---
name: benchmark
description: Đo hiệu năng (tốc độ, độ trễ, thông lượng, bộ nhớ) của mô hình hoặc pipeline một cách công bằng — warmup, nhiều lần chạy, báo phân vị và phương sai, cùng phần cứng và cùng đầu vào, tách cold start, và ghi đủ điều kiện để người khác chạy lại. Dùng khi so hai mô hình/thư viện/phần cứng (CPU vs GPU, lượng tử hoá), khi ước thời gian cho một đợt chạy lớn, khi tối ưu tốc độ, hoặc khi một con số "nhanh gấp N lần" cần kiểm.
---

# Benchmark: so công bằng, báo phân phối chứ không một con số

## 1. Điều kiện cố định

- Cùng máy, cùng phần cứng (ghi tên CPU/GPU, RAM/VRAM, driver), cùng phiên bản thư viện, không tiến trình nặng khác
  chạy cùng (kiểm `nvidia-smi`/trình quản lý tác vụ).
- Cùng **bộ đầu vào** — với văn bản, phân bố độ dài ảnh hưởng mạnh tới tốc độ; dùng mẫu đại diện của dữ liệu thật, ghi
  phân bố độ dài.
- Cùng cấu hình xử lý theo lô và đệm (padding): đệm khác nhau có thể đổi cả tốc độ lẫn KẾT QUẢ (vector khác) — kiểm
  đầu ra hai bên giống nhau trước khi so tốc độ.

## 2. Đo

1. **Warmup:** bỏ vài lần chạy đầu (nạp mô hình, biên dịch, cache).
2. **Lặp N lần** (≥ 5 cho việc dài, nhiều hơn cho việc ngắn); đo bằng đồng hồ đơn điệu (`time.perf_counter`).
   GPU: đồng bộ (`torch.cuda.synchronize()`) trước khi bấm giờ dừng.
3. Báo **P50, P95, (P99)**, trung bình và độ lệch chuẩn, min/max — không chỉ trung bình. Thông lượng: đơn vị/giây
   kèm kích thước lô.
4. **Cold start báo riêng** (lần đầu sau khởi động) — người dùng gặp nó thật.
5. Bộ nhớ đỉnh (RAM/VRAM) — một cấu hình nhanh mà tràn bộ nhớ trên máy đích là không dùng được.

## 3. So sánh

- Chênh lệch nhỏ hơn dao động giữa các lần chạy thì chưa phân biệt được.
- So với baseline trên cùng điều kiện; ghi tỷ lệ kèm cả hai con số tuyệt đối.
- Tối ưu tốc độ thì kiểm lại chất lượng (chỉ số đánh giá) — lượng tử hoá/rút gọn có thể làm giảm chất lượng.

## 4. Ước cho đợt chạy lớn

Đo trên mẫu đại diện → nhân theo số lượng và phân bố độ dài → cộng biên an toàn → so ngân sách thời gian trong ticket
trước khi chạy (R40.12). Chạy dài: ghi tiến độ và kết quả từng phần ra đĩa để dừng/tiếp được.

## Đầu ra

Bảng: cấu hình × (P50, P95, thông lượng, bộ nhớ đỉnh, chỉ số chất lượng) + điều kiện đo (phần cứng, phiên bản, đầu
vào, N, warmup) + lệnh tái hiện.
