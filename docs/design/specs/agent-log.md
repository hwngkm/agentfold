# Spec: agent-log

### Requirement: Thư đến tay người nhận mà không cần MCP hay server
Hộp thư SHALL chuyển thư giữa các bản clone chỉ bằng git, và người nhận SHALL thấy thư trong hộp thư đến cho tới khi xác nhận.

#### Scenario: Gửi, nhận, xác nhận
- **WHEN** agent A gửi thư cần xác nhận cho agent B ở một bản clone khác, rồi B xác nhận
- **THEN** thư hiện trong hộp thư đến của B, không hiện lại cho A, và biến mất sau khi B xác nhận
- **Test:** tests/tools/test_mail.py::test_gui_nhan_xac_nhan_qua_hai_ban_clone

#### Scenario: Gửi theo vai trò hoặc cho tất cả
- **WHEN** thư gửi tới `role:R3` hoặc `all`
- **THEN** mọi agent đang làm thay vai trò đó (hoặc mọi agent) đều nhận được
- **Test:** tests/tools/test_mail.py::test_gui_theo_vai_tro_va_toan_bo

### Requirement: Ghi đồng thời không mất thư
Hộp thư SHALL giữ cả hai thư khi hai agent ghi cùng lúc, bằng cách đọc lại và ghi lại khi lần đẩy bị từ chối.

#### Scenario: Hai agent ghi trên đầu nhánh cũ
- **WHEN** một agent ghi dựa trên đầu nhánh đã cũ vì agent khác vừa ghi
- **THEN** lần đẩy đầu bị từ chối, ghi lại trên đầu nhánh mới, và cả hai thư còn trong thread
- **Test:** tests/tools/test_mail.py::test_hai_agent_gui_cung_luc_khong_mat_thu

### Requirement: Chạy được khi không có remote và khi mất mạng
Hộp thư SHALL hoạt động trên nhánh cục bộ khi repo không có remote, và chế độ offline SHALL chỉ đọc bản đã kéo về mà không gọi mạng.

#### Scenario: Máy cá nhân không remote
- **WHEN** repo không có remote
- **THEN** gửi và nhận chạy trên nhánh cục bộ `agent-mail`
- **Test:** tests/tools/test_mail.py::test_che_do_cuc_bo_khi_khong_co_remote

#### Scenario: Hook đầu phiên mất mạng
- **WHEN** hộp thư mở ở chế độ offline
- **THEN** chỉ thấy thư đã kéo về, và thấy thư mới sau khi bản online kéo
- **Test:** tests/tools/test_mail.py::test_che_do_offline_khong_goi_mang

### Requirement: Trạng thái yêu cầu theo thư trả lời mới nhất
Hộp thư SHALL suy trạng thái một yêu cầu từ thư `status` mới nhất trỏ tới nó, theo chuỗi submitted, working, input-required, completed, failed, canceled, rejected.

#### Scenario: Agent báo cần quyết định
- **WHEN** agent gửi `working` rồi `input-required` cho cùng một yêu cầu
- **THEN** trạng thái hiện tại của yêu cầu là `input-required`
- **Test:** tests/tools/test_mail.py::test_trang_thai_yeu_cau_theo_thu_tra_loi_moi_nhat

### Requirement: Thư sai khuôn bị từ chối
Hộp thư SHALL từ chối thư có loại, trạng thái, định danh hoặc người nhận không hợp lệ, trước khi ghi.

#### Scenario: Thư sai
- **WHEN** thư có `kind` lạ, `state` lạ, định danh có khoảng trắng hoặc không có người nhận
- **THEN** lệnh gửi báo lỗi nêu đúng trường sai và không ghi gì
- **Test:** tests/tools/test_mail.py::test_thu_sai_bi_tu_choi
