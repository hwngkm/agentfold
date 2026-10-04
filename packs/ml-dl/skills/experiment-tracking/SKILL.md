---
name: experiment-tracking
description: Ghi mỗi lần chạy huấn luyện/đánh giá đủ để dựng lại — commit mã, cấu hình đầy đủ, seed, phiên bản dữ liệu và mô hình gốc (revision), môi trường, chỉ số theo bước, và nơi lưu checkpoint — bằng một bản ghi máy đọc được. Dùng khi bắt đầu huấn luyện hay fine-tune, khi chạy nhiều cấu hình để so, khi không dựng lại được một kết quả cũ, hoặc khi chuẩn bị bàn giao mô hình cho người khác.
---

# Theo dõi thí nghiệm: một lần chạy = một bản ghi dựng lại được

## Bản ghi tối thiểu mỗi lần chạy

```yaml
run_id: 2026-10-03T0912Z-lora-r16          # thời điểm + mô tả ngắn, không số thứ tự tăng dần
code: {commit: <sha>, dirty: false}          # dirty = true thì KHÔNG dùng kết quả để báo cáo
config: <toàn bộ cấu hình đã giải, kể cả giá trị mặc định>
seed: 13
data: {name: <bộ dữ liệu>, revision: <mã phát hành/băm>, splits: {train: n, val: n, test: n}}
base_model: {name: <org/model>, revision: <commit sha trên Hub>}
env: {python: 3.12.x, torch: x.y, cuda: x.y, gpu: <tên>, packages_lock: <băm lockfile>}
metrics: <theo bước + cuối cùng, tách val/test>
artifacts: {checkpoint: <đường dẫn ngoài git>, logs: <đường dẫn>}
```

Ghi tự động trong script huấn luyện (đầu lần chạy: cấu hình/môi trường; cuối: chỉ số/artifact), không ghi tay.

## Thủ tục

1. **Cây làm việc sạch** trước khi chạy để báo cáo (`git status` trống) — chạy thử thì được, nhưng không báo cáo.
2. **Ghim mọi thứ:** revision mô hình gốc và bộ dữ liệu khi tải (`hf download <repo> --revision <sha>` — CLI `hf`
   pack này kiểm), lockfile phụ thuộc, seed cho Python/NumPy/framework.
3. **Một cấu hình một file** (YAML), lần chạy đọc file đó; tham số dòng lệnh ghi đè thì bản ghi lưu giá trị cuối.
4. **Checkpoint và dữ liệu ngoài git** (R40.10): thư mục `data/`/kho artifact; bản ghi lưu đường dẫn + băm.
5. **So sánh** chỉ giữa các lần chạy khác đúng một yếu tố (skill `experiment-design` của pack `research`).

## Công cụ

Bắt đầu bằng file JSON/YAML mỗi lần chạy trong thư mục `runs/` (ngoài git) là đủ cho một người. Nhiều người hoặc nhiều
lần chạy → công cụ theo dõi (MLflow, Weights & Biases, Trackio…) — chọn bằng DEC, khoá API qua biến môi trường.

## Kiểm

Lấy một bản ghi cũ, dựng lại môi trường theo nó, chạy lại: chỉ số nằm trong dao động giữa các seed đã biết. Không
dựng lại được → bản ghi thiếu trường, bổ sung vào khuôn.
