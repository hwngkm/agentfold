# RULE 50 — Quy trình, CI, triển khai

> Owner: **R3** (CI/deploy) + **R1** (nhịp làm việc). Điều phối nhiều agent: `70-multi-agent-coordination.md`.

## R50.1 — Vòng đời ticket

`proposed` → `ready` (người duyệt) → claim (`agentctl start`) → PR nháp → Ready for review → merge → `release`.
Mỗi người/agent một ticket đang làm tại một thời điểm. Ba việc dở bằng không việc nào xong.

## R50.2 — Nhánh và commit

- Nhánh: `feature/<ID>-<slug>` (hoặc `fix/`, `chore/`, `docs/`...) — `agentctl start` tự đặt.
- Commit: `type(scope): mô tả (<ID>)`, type ∈ `feat|fix|docs|test|refactor|chore|perf|ci`. Hook `commit-msg` kiểm.
- Không `--no-verify`, không `--force`, không đẩy thẳng `main`.

## R50.3 — Pull request

Mô tả theo `.github/pull_request_template.md`: thay đổi · vì sao (ticket, thiết kế) · bằng chứng · phạm vi.
PR > 400 dòng thì tách (trừ dữ liệu/tệp sinh ra). Tài liệu thuần đi PR riêng (không kéo CI đầy đủ).

## R50.4 — Review

Đọc thật theo `coordination/roles/reviewer.md`. Reviewer lý tưởng là người khác, hoặc agent của nhà cung cấp
khác với agent viết PR. Tác giả không tự duyệt thay đổi chạm vùng bảo vệ.

## R50.5 — CI là luật

CI đỏ = không merge. CI hỏng vì hạ tầng thì sửa hạ tầng, không tắt check. Test cổng an toàn đỏ thì ĐỌC báo cáo
(trace, ảnh chụp) trước khi chạy lại — chạy lại tới khi xanh là giấu lỗi.

## R50.6 — Kiểm cục bộ trước, CI một lần

- Trong lúc làm: `make check-fast` trước mỗi commit.
- Trước khi mở/cập nhật PR: `python scripts/ci_local.py` (chạy hết rồi mới tổng kết, ép `TZ=UTC`, kiểm cây git sạch).
- PR ở chế độ **nháp**: mọi job CI tự bỏ qua PR nháp (0 phút). Xong thì "Ready for review" ⇒ CI chạy đủ một lần.
- Lý do bằng tiền: một lượt CI đầy đủ ~30 phút; gói GitHub Free cho repo private có 2.000 phút/tháng và CHẶN job
  khi hết. một dự án đã tiêu hơn hai nghìn phút trong hai tuần vì thói quen đẩy từng commit lên PR đang mở.

## R50.7 — Cấu trúc CI (khoá bởi `tests/guards/test_deploy_waits_for_ci.py`)

- Các job **không `needs` nhau.** GitHub chỉ tạo check run của job con khi job cha xong — trong khoảng đó commit
  mang đúng một check xanh, và nền tảng deploy "chờ check qua" có thể deploy trước khi test an toàn tồn tại.
- Điều kiện `if:` DUY NHẤT trên job là bỏ qua PR nháp. `skipped` được nền tảng deploy tính là QUA, nên job bỏ
  qua được một lần đẩy vào `main` là một đường deploy không kiểm.
- Không `continue-on-error`, không `if:` theo sự kiện/nhánh trên bước test, Playwright `retries: 0`.
- Tên job là hợp đồng với Vercel Deployment Checks — đổi tên job phải đổi dashboard cùng lúc.

## R50.8 — Deploy chờ CI

- Render: `autoDeployTrigger: checksPass` trong `render.yaml` **và** bật "After CI Checks Pass" trong dashboard
  (trường trong blueprint chỉ áp cho dịch vụ mới).
- Vercel: Deployment Checks chọn đủ các job của `ci.yml`. Gác backend mà không gác frontend thì frontend mới chạy
  trước backend cũ.
- **Merge bằng nút Merge của nền tảng**, không fast-forward thủ công vào `main`: check `skipped` của lần đẩy lên PR
  nháp gắn vào commit; đưa nguyên commit đó lên `main` là mang sẵn check "qua" trước khi CI thật kịp chạy.
- Deploy tay coi như KHÔNG chờ CI — chỉ deploy commit đã xanh.

## R50.9 — Nhánh sổ claim và hộp thư không phải nhánh code

`agent-claims` và `agent-mail` (AGENT-LOG) không chạy CI, không deploy (Vercel: `web/vercel.json` tắt deploy cho hai nhánh đó), không bảo vệ
chặn push (agent phải ghi được), không bao giờ merge vào `main`.

## R50.10 — Runner CI tự host (nếu dùng)

Chọn runner bằng biến repo (`CI_RUNNER`), không bằng commit. Runner đặt trên máy/bản Linux RIÊNG cho CI — bước
cài thư viện hệ thống (`playwright install --with-deps`) sửa máy chạy job. Cách ly bằng máy riêng là chống TAI
NẠN, không phải ranh giới bảo mật: gói phụ thuộc độc hại vẫn đọc được mọi thứ tài khoản runner đọc được.

## R50.11 — Máy Windows: những bẫy làm hỏng file im lặng

Nguồn: một dự án thực tế, nơi agent chạy trên Windows 11 với Git Bash + PowerShell. Các lỗi dưới đây đều đã xảy ra
và đều im lặng — chỉ lộ ra ở diff hoặc ở người đọc sau.

- **Xuống dòng LF.** Repo dùng LF (`.gitattributes`, `.editorconfig`). Ghi file bằng Python thì
  `Path.write_bytes(text.encode())` hoặc `open(..., newline="\n")`; PowerShell `Set-Content`/`>` có thể thêm BOM
  hoặc CRLF. Trước commit: `git diff --stat` và `git diff --stat --ignore-cr-at-eol` phải gần bằng nhau — lệch
  nhiều là cả file bị đổi xuống dòng.
- **Không dựng mã có `\n`, `\1`, ký tự không ASCII bằng heredoc shell.** Heredoc có thể làm hỏng escape và tiếng
  Việt; sửa file bằng công cụ sửa file của IDE/agent, không bằng `cat <<EOF`.
- **`grep` trong Git Bash đôi khi sập** (mã 134) với đầu ra Unicode: ghi đầu ra ra file rồi đọc file, hoặc dùng
  công cụ tìm kiếm của agent.
- **Đặt mã hoá rõ ràng:** `PYTHONIOENCODING=utf-8`; mọi `open()`/`read_text()` truyền `encoding="utf-8"`.
- **Trình quản lý gói tạo liên kết cứng/symlink** có thể hỏng khi cache và dự án khác ổ đĩa: đặt chế độ sao chép
  (vd. `UV_LINK_MODE=copy` với uv) thay vì để lỗi quyền lẻ tẻ.
- **Gói cài ngoài lock** (`pip install`/`uv pip install` lẻ) làm môi trường lệch bản chốt: thêm thư viện bằng lệnh
  của trình quản lý gói để lock cập nhật, commit cả file lock.

## R50.12 — Leo thang khi bị chặn

| Bị chặn | Làm |
|---|---|
| 90 phút | câu hỏi (`new question`) + nhắn nhóm: đang làm gì, đã thử gì, lỗi gì |
| 4 giờ | gọi chủ module |
| 1 ngày | đổi cách tiếp cận hoặc tách ticket |
| 2 ngày | R1 quyết: phương án thay thế, hoặc cắt phạm vi |
