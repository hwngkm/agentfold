---
name: tdd-loop
description: Vòng đỏ → xanh → dọn có bằng chứng — viết test hành vi qua giao diện công khai, chạy thấy ĐỎ đúng lý do, viết code tối thiểu cho xanh, rồi dọn. Dùng khi bắt đầu một tính năng hay sửa lỗi có hành vi kiểm được, khi agent định viết code trước test, hoặc khi cần chứng minh một test mới thực sự bảo vệ điều nó nói.
---

# TDD: bằng chứng là test từng ĐỎ đúng lý do

## Vòng lặp

1. **Viết MỘT test** cho hành vi tiếp theo — qua giao diện công khai (hàm public, endpoint, CLI), không qua chi
   tiết bên trong. Tên test nói hành vi: `test_hai_agent_ghi_cung_tieu_de_ra_hai_file_khac_nhau`, không `test_func2`.
2. **Chạy, thấy đỏ, ĐỌC thông điệp đỏ.** Đỏ phải đúng lý do (assert sai giá trị / hành vi chưa có). Đỏ vì
   `ImportError`, sai tên fixture, lỗi cú pháp thì chưa phải đỏ — sửa test rồi chạy lại.
3. **Code tối thiểu cho xanh.** Không thêm nhánh, tham số, "tiện thể" mà test chưa đòi.
4. **Chạy lại cả nhóm liên quan**, không chỉ test vừa viết: `python -m pytest tests/unit -q` hoặc
   `make check-fast`.
5. **Dọn** khi đang xanh: đặt tên, bỏ lặp, tách hàm. Chạy lại sau mỗi bước dọn.
6. Lặp với hành vi tiếp theo. Commit ở mỗi điểm xanh có ý nghĩa.

## Sửa lỗi

Bắt đầu bằng test **tái hiện lỗi** — đỏ trên code hiện tại vì đúng lỗi được báo. Sau đó mới sửa. Lỗi không tái
hiện được bằng test thì chưa hiểu lỗi; đừng sửa theo phỏng đoán.

## Khi test đã có sẵn trước code (viết sau)

Chứng minh test đỏ được bằng cách **gỡ tạm bản vá** (hoặc đổi một hằng số trong code) và chạy lại — thấy đỏ thì
khôi phục. Ghi việc này vào PR. Khôi phục bằng công cụ sửa file hoặc `git checkout -- <file>` khi cây không có
tiến trình khác đang dùng (R70.5); kiểm `git diff` sạch sau khi khôi phục.

## Bẫy hay gặp

| Bẫy | Dấu hiệu | Sửa |
|---|---|---|
| Test kiểm mock | assert đúng giá trị mock vừa trả | assert hành vi quan sát được ở đầu ra |
| Test xanh ngay lần đầu | chưa từng thấy đỏ | gỡ tạm code / đổi kỳ vọng để thấy đỏ |
| Một test kiểm 5 hành vi | đỏ không biết hỏng cái nào | tách; mỗi test một lý do đỏ |
| Phụ thuộc thứ tự | đỏ khi chạy riêng lẻ | mỗi test tự dựng dữ liệu (`tmp_path`, fixture) |
| Phụ thuộc giờ/mạng | đỏ lúc nửa đêm / khi mất mạng | cố định thời gian, giả mạo ranh giới ngoài |
| Sửa test cho xanh | đổi kỳ vọng mà không hiểu vì sao đỏ | đọc lại yêu cầu; sai ở code thì sửa code |

Không bao giờ sửa, nới, `skip` hay `xfail` test trong `tests/guards/` để xanh (AGENTS.md luật 5).

## Báo cáo

"Xong" = tên test + lệnh đã chạy + kết quả, và câu "đã thấy đỏ trước khi có code" (hoặc "đã gỡ bản vá để thấy
đỏ"). Test nào không làm được bước đỏ thì nói thẳng.
