# RULE 40 — Dữ liệu

> Owner: **R2**.

## R40.1 — Dữ liệu có cấu trúc dùng truy vấn chính xác; văn bản dùng truy hồi

Con số nghiệp vụ tra bằng SQL theo khoá, không qua tìm kiếm ngữ nghĩa (sai số của truy hồi không được chảy vào
con số). Tìm kiếm vector chỉ cho văn bản phi cấu trúc — và mọi đoạn truy hồi vào prompt là dữ liệu KHÔNG tin cậy.

## R40.2 — Không dòng dữ liệu nào thiếu nguồn

Mỗi dòng: `source` (cơ quan/bộ dữ liệu), `source_ref` (bảng/trang/mã cụ thể — người khác kiểm lại được), và cờ
`is_estimated` + độ tin cậy khi là ước tính. Script kiểm dữ liệu chặn dòng thiếu nguồn ở CI.

## R40.3 — Dữ liệu mới phải làm sạch trước khi dùng

Chuẩn hoá mã hoá (UTF-8, không BOM), đơn vị, khoảng trắng, danh mục viết nhiều kiểu (`rau` / `rau củ`), khoá
trùng. Không giả định file mới "đã sẵn sàng". Sửa dữ liệu seed ⇒ chạy script kiểm dữ liệu trước khi commit.

## R40.4 — Lọc theo hai lưới khi trường phân loại không đáng tin

Trường nhập tay (danh mục, loại) thường trống hoặc lệch cách viết. Phân nhóm dựa trên nó thì kiểm thêm lưới thứ
hai (từ khoá trong tên) — lưới đơn đã từng sót dòng thật.

## R40.5 — Ước tính phải trung thực

Không làm tròn độ tin cậy lên, không ẩn nhãn ước tính cho gọn. Một con số ước tính được trình bày như đo thật là
vi phạm R40.2.

## R40.6 — Kiểm chứng số liệu trước khi công bố

Mọi số liệu trong tài liệu, slide, giao diện: có nguồn sơ cấp truy được. Không tìm thấy nguồn ⇒ xoá số đó,
không giữ "cho đẹp". Nguồn thứ cấp (blog phổ biến kiến thức) phải ghi rõ là thứ cấp.

## R40.7 — Bản quyền và giấy phép

Ghi giấy phép của từng bộ dữ liệu. PDF/tài liệu gốc có bản quyền không vào git — chỉ bản trích dẫn/đã chuẩn hoá
được phép.

## R40.8 — Dữ liệu cá nhân

Dữ liệu người thật chỉ dùng đúng mục đích đã cam kết, đã khử định danh khi dùng cho phát triển; mã định danh gốc
không vào prompt, log hay tên file. Sao lưu CSDL chứa dữ liệu người dùng không vào git.

## R40.9 — Phiên bản hoá dữ liệu

Bản dữ liệu dùng ở production có mã phát hành và người ký duyệt; production từ chối dữ liệu chưa ký nếu dự án
bật cơ chế này. Thay đổi dữ liệu dùng chung là hành động HIGH.

## R40.10 — Dữ liệu không vào git; đồng bộ qua kho riêng

`data/` chỉ giữ `.gitkeep`; tệp cột/nhị phân (`parquet`, `feather`, `h5`, `npy`, `pkl`…) và CSDL không vào git
(`scripts/check_structure.py` chặn ở pre-commit lẫn CI). Dữ liệu dùng chung giữa người/agent đi qua một kho dữ
liệu riêng (bucket, dataset riêng tư) với một `manifest.json` ghi mã phát hành, danh sách file, kích thước và
băm — đủ để người nhận kiểm đã tải nguyên vẹn. Agent không tự đẩy dữ liệu lên kho ngoài phạm vi ticket cho phép.
Seed nhỏ, đọc được bằng mắt (CSV/JSONL < 5 MB) vẫn commit được ngoài `data/`, kèm `source`/`source_ref` (R40.2).

## R40.11 — Số đo chỉ có giá trị nếu không tự chấm chính nó

Nguồn: một dự án nhiều agent thay phiên, nơi nhiều lần nghiệm thu bị trả lại vì đạt chỉ tiêu bằng cách đếm.

- **Kiểm nội dung, không chỉ đếm.** "300 câu" đạt bằng câu mẫu lặp hay số liệu giả vẫn là 300. Người nghiệm
  thu rút mẫu ngẫu nhiên và đọc.
- **Không dùng một nguồn để chấm chính nó.** Quy tắc trích xuất vừa viết không được dùng để tuyên bố "0 lỗi"
  của chính nó; kiểm bằng nguồn độc lập (văn bản gốc, người, hoặc bộ nhãn tách riêng).
- **Ghi cỡ mẫu và giới hạn thống kê.** "29/30 đúng" không chứng minh "≥ 95%". Báo số tuyệt đối trước, phần
  trăm sau, kèm khoảng tin cậy khi mẫu nhỏ (kỹ thuật chi tiết: skill `eval-harness`, nếu pack `ai-llm` bật).
- **Không đạt tiêu chí thì nói thẳng** và ghi vào báo cáo; không đổi thước đo hay làm tròn để qua. Việc chưa
  đạt mọi tiêu chí hoàn thành là *đang làm*, không phải *xong*.
- **Đừng đổi mặc định chỉ dựa trên bộ đo nhỏ.** Một cấu hình tốt hơn trên 25 ca nhưng kém hơn trên bộ lớn thì
  giữ mặc định cũ và ghi kết quả.

## R40.12 — Bước tốn kém và làm mất cache: gộp thành MỘT lần chạy

Pipeline mà đổi mã khiến phải dựng lại toàn bộ (thực tế: ~2,4 giờ cho 89 nghìn tài liệu) thì:

1. Gom MỌI thay đổi cần làm vào một lần dựng; không dựng lại sau từng sửa nhỏ.
2. **Ước tính thời gian TRƯỚC khi chạy** (đo trên mẫu nhỏ, nhân tỷ lệ). Vượt ngân sách đã nêu trong ticket thì
   thu hẹp phạm vi (vd. chỉ phần cần cho nghiệm thu) và báo lại, không lặng lẽ chạy cả đêm.
3. Hai tiến trình dài trên cùng đích ghi (CSDL, thư mục chỉ mục) thì chỉ MỘT bên được ghi; bên kia ghi ra file
   riêng rồi gộp. Kiểm mẫu lớn kết quả sau khi chạy xong (thực tế: chạy song song CPU/GPU từng ghi sai vector của
   ~8% đoạn vì khác cách đệm — chỉ lộ ra nhờ kiểm mẫu).
