# Spec: handoff

### Requirement: Bàn giao điền sẵn sự thật từ git
Lệnh `new handoff` SHALL điền sẵn nhánh, commit cuối, danh sách tệp chưa commit và số commit chưa đẩy, để agent hết hạn mức bàn giao được bằng một lệnh.

#### Scenario: Cây làm việc đang dở
- **WHEN** agent chạy `new handoff` khi có tệp mới và tệp đã sửa chưa commit
- **THEN** mục bàn giao liệt kê từng tệp (kể cả tệp trong thư mục chưa theo dõi) cùng nhánh và ticket suy ra từ tên nhánh
- **Test:** tests/tools/test_handoff.py::test_bao_cao_git_that_cua_cay_lam_viec

#### Scenario: Danh sách tệp quá dài
- **WHEN** số tệp chưa commit vượt giới hạn hiển thị
- **THEN** danh sách bị cắt và ghi rõ còn bao nhiêu tệp nữa
- **Test:** tests/tools/test_handoff.py::test_cay_sach_va_danh_sach_dai_duoc_cat

### Requirement: Bàn giao luôn đọc lại được và đúng cấu trúc
Bộ kiểm cấu trúc SHALL chấp nhận bàn giao sinh bởi lệnh (kể cả khi mã commit toàn chữ số hay nhánh không gắn ticket) và từ chối bàn giao có `status` hoặc `ticket` sai.

#### Scenario: Mã commit toàn chữ số
- **WHEN** commit cuối có mã rút gọn chỉ gồm chữ số
- **THEN** front matter vẫn giữ nó là chuỗi và `check-work` không báo lỗi
- **Test:** tests/tools/test_handoff.py::test_muc_ban_giao_sinh_ra_qua_kiem_cau_truc_va_giu_nguyen_kieu

#### Scenario: Nhánh không gắn ticket
- **WHEN** agent bàn giao khi đang ở nhánh không có mã ticket
- **THEN** bàn giao hợp lệ với `ticket: null`
- **Test:** tests/tools/test_handoff.py::test_ban_giao_khong_ticket_van_hop_le

#### Scenario: Bàn giao hỏng
- **WHEN** một mục có `status` ngoài tập cho phép hoặc `ticket` không phải mã ticket
- **THEN** `check-work` báo lỗi nêu đúng trường sai
- **Test:** tests/tools/test_handoff.py::test_kiem_cau_truc_bat_ban_giao_hong

### Requirement: Bảng việc thấy bàn giao trên nhánh chưa merge
`board` SHALL liệt kê bàn giao còn `open` nằm trên nhánh feature chưa merge và SHALL kéo về cả các nhánh đó, không chỉ `main`.

#### Scenario: Agent hết hạn mức trên nhánh feature
- **WHEN** bàn giao `open` nằm trên nhánh feature chưa merge
- **THEN** `board` hiện nó kèm tên nhánh
- **Test:** tests/tools/test_board_handoffs.py::test_ban_giao_mo_tren_nhanh_chua_merge_hien_o_bang

#### Scenario: Chưa kéo nhánh về máy
- **WHEN** nhánh của agent khác chưa từng được fetch
- **THEN** `board` (không `--offline`) kéo nó về rồi mới liệt kê
- **Test:** tests/tools/test_board_handoffs.py::test_fetch_keo_ca_nhanh_feature_khong_chi_main

### Requirement: Main thắng khi cùng mã bàn giao
`board` SHALL bỏ qua bản `open` trên nhánh nếu cùng mã bàn giao đã có trên `main`, để nhánh cũ không làm sống lại việc đã đóng.

#### Scenario: Đã đóng trên main
- **WHEN** bàn giao đã `closed` trên `main` còn bản `open` ở nhánh cũ
- **THEN** `board` không báo nó
- **Test:** tests/tools/test_board_handoffs.py::test_ban_sao_tren_nhanh_khong_ghi_de_ket_qua_da_dong_tren_main

#### Scenario: Đã đóng trên nhánh
- **WHEN** bàn giao `closed` nằm trên nhánh chưa merge
- **THEN** `board` không báo nó
- **Test:** tests/tools/test_board_handoffs.py::test_ban_giao_da_dong_tren_nhanh_khong_hien
