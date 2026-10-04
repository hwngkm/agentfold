# ADR-0001: Mặt phẳng điều phối trong repo cho nhiều AI agent khác nhà cung cấp

- Status: Accepted — quyết định nền của template; dự án mới xác nhận lại ở buổi khởi động
- Date: 2026-09-15
- Owner: R1 — Architecture Owner
- Reviewers: R2, R3, R4
- Supersedes: N/A

## Bối cảnh

Template này rút từ kinh nghiệm một dự án nhiều tuần, nhiều người và nhiều AI agent của nhiều nhà cung cấp cùng làm một
repo (Claude Code, Codex, Gemini CLI, Cursor, Copilot). Các quan sát dưới đây là loại sự cố lặp lại khi nhiều agent chung một
repo; con số cụ thể được bỏ có chủ ý, điều đáng giữ là cơ chế gây lỗi:

| Quan sát | Lớp vấn đề |
|---|---|
| File nhật ký dùng chung bị hàng trăm commit chạm trong vài tuần; mọi nhánh nối vào cuối file | điểm nóng nối-cuối-file |
| File ticket dùng chung và bảng tính theo dõi việc; bảng tính không merge được | trạng thái ghi tay dùng chung |
| File model một khối; nhiều nhánh cùng thêm migration, phải viết hàng chục revision chỉ để gộp head | tài nguyên tuần tự bị làm song song |
| Chỉ có `CLAUDE.md` ở gốc: Codex đọc `AGENTS.md`, Gemini CLI mặc định đọc `GEMINI.md` — không nạp luật của dự án | luật không tới mọi agent |
| Một cảnh báo "chưa có nguồn" rơi mất khi chép từ nhật ký sang `CLAUDE.md` | luật bị chép thành nhiều bản rồi trôi |
| Phiên agent song song trên CÙNG cây làm việc; một lệnh `git checkout --` xoá việc chưa commit của phiên kia | không cách ly không gian làm việc |
| Kiểm cục bộ khác CI: CI đỏ nhiều lượt liên tiếp, mỗi lần một lỗi khác | hai bản logic kiểm |
| Deploy không chờ CI: một commit có test cổng duyệt ĐỎ vẫn lên production | cổng an toàn không nối vào deploy |

Không lỗi nào ở trên là lỗi khó. Tất cả có chung một gốc: **ràng buộc nằm ở lời dặn, không nằm ở chỗ mọi
agent bắt buộc phải đi qua.** Agent khác nhà cung cấp đọc file khác nhau, nhớ khác nhau, không chia sẻ trí
nhớ — nên lời dặn không phải là cơ chế phối hợp.

## Tiêu chí quyết định

1. Chạy được với MỌI agent có quyền đọc/ghi git — không phụ thuộc nhà cung cấp, IDE hay git host.
2. Con người giữ quyền quyết thiết kế và kế hoạch; agent không tự nới được phạm vi của mình.
3. Xung đột được NGĂN trước khi code được viết, không chỉ phát hiện lúc merge.
4. Mỗi ràng buộc quan trọng được kiểm bằng máy và có bằng chứng từng đỏ.
5. Không thêm dịch vụ phải vận hành.

## Phương án đã cân nhắc

### A. Một file hướng dẫn + tin agent tự giác (hiện trạng phổ biến)

Rẻ nhất. Thất bại ở tiêu chí 1, 3, 4 — chính là các số đo trong bảng Bối cảnh.

### B. Chép luật vào file riêng của từng công cụ

Mọi agent đọc được luật, nhưng N bản luật trôi khỏi nhau (đã quan sát được). Không giải quyết xung đột.

### C. Điều phối bằng GitHub Issues/Projects + nhãn

Có giao diện sẵn. Nhưng phụ thuộc một git host và token API trong môi trường agent; không có khái niệm
"phạm vi file" nên không phát hiện hai việc chạm cùng file; gán issue không nguyên tử với việc bắt đầu làm.

### D. Mặt phẳng điều phối trong repo (chọn)

1. **Một nguồn luật:** `AGENTS.md` (chuẩn chung được phần lớn công cụ tự đọc) + adapter mỏng chỉ trỏ về nó;
   lưới canh cấm adapter chứa luật riêng.
2. **Kế hoạch là dữ liệu có phạm vi:** ticket một-file có `scope.allow`, làn độc quyền, vùng bảo vệ duyệt
   trước; chỉ ticket `ready` trên `main` mới claim được, và mọi phân xử đọc ticket từ `main`.
3. **Sổ claim nguyên tử trên nhánh git mồ côi:** `git push` từ chối lần ghi không fast-forward, nên hai agent
   claim cùng lúc thì đúng một người thắng. Không dịch vụ ngoài, không token API.
4. **Cách ly:** mỗi claim một worktree + nhánh không track `main`.
5. **Một hàm kiểm phạm vi dùng ở ba lớp:** hook ghi file (Claude Code/Codex/Gemini) → pre-commit (mọi agent) →
   CI. Trên CI, công cụ chạy từ commit GỐC để PR không tự sửa được bộ kiểm.
6. **Triệt tiêu điểm nóng:** mục công việc một-file-một-mục, mã theo ngày+slug; router/model tự khám phá;
   settings theo miền; trạng thái suy ra, không ghi tay.
7. **Bất biến là test:** `docs/design/invariants.yaml` trỏ tới lưới canh thật; lưới canh tự kiểm chính nó.

## Quyết định

Chọn **D**. Xem lại nếu: một nền tảng cung cấp khoá file/phạm vi nguyên tử độc lập nhà cung cấp; hoặc đội
dưới 2 người và không dùng quá một agent cùng lúc (khi đó phần claim là thừa, phần luật và lưới canh vẫn giữ).

## Hệ quả

- Tích cực: xung đột chặn ở lúc claim thay vì lúc merge; mọi agent gặp cùng luật ở cùng chỗ; người duyệt
  thấy mọi thay đổi thiết kế trong diff; bảng công việc không lệch sự thật.
- Đánh đổi: lập kế hoạch tốn công hơn (phải viết phạm vi); claim cần mạng tới remote; phạm vi viết hẹp quá
  thì agent phải hỏi thêm — cái giá chọn có chủ đích.
- Giới hạn trung thực: nhãn duyệt không phải ranh giới bảo mật nếu agent có quyền gắn nhãn; hook chặn chỉ có ở
  công cụ hỗ trợ — luật thật nằm ở CI và branch protection.

## Kiểm chứng

`tests/tools/` (claim trên git thật, kể cả ghi đồng thời; kiểm phạm vi đọc từ gốc; hook ba công cụ) và
`tests/guards/` (một nguồn luật, ranh giới lớp, migration, hợp đồng API, deploy chờ CI). Mỗi cơ chế chính đã
được phá thử (force-push thay CAS, bỏ kiểm chồng, đọc ticket từ cây cục bộ, bỏ `--no-track`...) và test tương
ứng đỏ.

## Rút lui

Mọi thành phần độc lập: bỏ claim vẫn giữ được luật một nguồn và lưới canh; bỏ hook vẫn còn pre-commit và CI.
Dữ liệu (ticket, nhật ký, quyết định) là Markdown thường, không khoá vào công cụ nào.
