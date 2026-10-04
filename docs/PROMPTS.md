# Prompt khởi động cho agent

Hai prompt dán sẵn để bắt đầu một phiên (cloud hoặc local) mà không phải viết lại. Cả hai chỉ trỏ vào tệp trong repo, nên
nội dung thật nằm ở `AGENTS.md`, bàn giao và ticket, không nằm ở đây. Đã chỉnh theo ca thử cloud đầu tiên (04/10/2026,
xem AGENT-LOG của ngày đó): các điểm đó được đánh dấu **(từ ca thử cloud)**.

Thay `<bàn-giao>` bằng bàn giao mới nhất trong `docs/work/handoffs/` và `<TICKET>` bằng ticket cần làm.

## Phiên cloud

```text
Bạn làm việc trong repo agentfold (phiên cloud). Ngoài việc làm ticket, hãy ghi lại những giả định
về môi trường cloud nào đúng, nào sai.

1. Setup script của môi trường có thể KHÔNG tự chạy (từ ca thử cloud). Kiểm: git config core.hooksPath phải ra
   scripts/githooks. Nếu rỗng, chạy: bash scripts/cloud_setup.sh
   Rồi: export AGENTCTL_AGENT=<định-danh-cloud> && python -m tools.agentctl prime
2. Đọc theo thứ tự: AGENTS.md, rồi <bàn-giao> (mục "Cấu hình môi trường cloud", "Đã thử và SAI", "Câu hỏi mở").
3. Nhận <TICKET> trong docs/work/tickets/. Ticket còn state `proposed` thì CHƯA claim: lập kế hoạch rồi DỪNG chờ duyệt.
   Hook chặn sửa tệp kế hoạch do `agentctl new plan` tạo (vùng work-plan) (từ ca thử cloud), nên đặt kế hoạch trong
   một câu hỏi: python -m tools.agentctl new question --title "..." --blocking <TICKET>
4. Sau khi người đổi ticket sang `ready` và duyệt kế hoạch: python -m tools.agentctl start <TICKET> --role <vai>,
   viết test trước và thấy đỏ, rồi sửa. ruff, mypy, pytest và python scripts/ci_local.py --fast phải xanh.
5. Ghi vào AGENT-LOG (python -m tools.agentctl new log) những gì đã kiểm: Python >= 3.11, mạng, hook git, quyền push,
   công cụ nào dùng được.

Ghi chú nền tảng cloud (từ ca thử cloud):
- Nhánh làm việc do nền tảng đặt (dạng claude/...). Cứ làm trên nhánh đó, không tự đổi tên; ghi vào log nếu quy ước
  feature/<TICKET>-... cần được áp dụng.
- gh có thể không đăng nhập được. Dùng công cụ GitHub MCP của nền tảng để tạo và theo dõi PR; không dựa vào gh pr create.
- Không in toàn bộ biến môi trường (hook chặn, và có thể chứa bí mật).

Sau khi PR đã merge, mọi commit mới phải đi qua PR MỚI: không đẩy thêm lên nhánh của PR đã merge (commit đến sau
merge không thuộc PR nào và claim không được release). Kết quả đến muộn thì mở PR bổ sung rồi mới release.
Luật cứng: không push lên main (chỉ đẩy nhánh làm việc); không thêm Co-Authored-By hay ghi công AI vào commit/PR;
không sửa vùng bảo vệ ngoài những gì ticket khai trong scope.protected; không đoán, giả định chưa kiểm phải ghi rõ.
Kết thúc: báo cáo ngắn bằng tiếng Việt (đã làm, bằng chứng, giả định sai, việc dở) rồi dừng.
```

## Phiên cloud theo hàng đợi (nhiều ticket, làm lần lượt)

Claim độc quyền theo vùng bảo vệ, nên nhiều ticket được giao cho MỘT phiên làm lần lượt; chạy song song chỉ khi vùng bảo vệ không chồng
(mỗi phiên một `AGENTCTL_AGENT` riêng). Sửa danh sách và các dòng "chú ý riêng".

```text
Bạn làm việc trong repo agentfold (phiên cloud, định danh <ID>). Bạn được giao MỘT HÀNG ĐỢI ticket,
làm LẦN LƯỢT, mỗi ticket một PR riêng.

HÀNG ĐỢI:
  1. <TICKET-1>
  2. <TICKET-2>

KHỞI ĐỘNG: như prompt phiên cloud ở trên (kiểm hooksPath, prime, đọc AGENTS.md và bàn giao).

VÒNG LẶP cho từng ticket T:
1. python -m tools.agentctl start T --role R3. Bị từ chối (claim chồng, phụ thuộc chưa xong) thì DỪNG, báo lý do, chờ người;
   đừng ép và đừng nhảy ticket khác.
2. Đọc ticket và mã thật. `scope.allow` là DỰ KIẾN: thiếu file cần sửa thì mở câu hỏi (new question --blocking T) và DỪNG.
3. Test trước và thấy ĐỎ, rồi sửa. ruff, mypy, pytest tests/guards tests/tools và scripts/ci_local.py --fast phải xanh trước khi mở PR.
4. Dựng nội dung PR bằng python -m tools.agentctl pr-body --ticket T; mở PR nháp bằng công cụ GitHub MCP nếu gh không đăng nhập được.
5. Ghi AGENT-LOG ngắn, rồi DỪNG chờ người: Ready for review, human-approved nếu cần, Merge.
6. Khi PR đã merge: python -m tools.agentctl release T, rồi sang ticket kế tiếp. Không đẩy thêm lên nhánh của PR đã merge.

LUẬT CỨNG: không push main; không Co-Authored-By hay ghi công AI; không đoán, giả định chưa kiểm phải ghi rõ;
không in toàn bộ biến môi trường hay khoá; mỗi lúc chỉ giữ MỘT claim; việc tốn tiền chỉ chạy trong trần người đã duyệt.
KẾT THÚC mỗi ticket: báo cáo ngắn tiếng Việt (đã làm, bằng chứng, việc dở, câu hỏi mở); KẾT THÚC hàng đợi: báo cáo tổng.
```

## Phiên local (Claude Code, Codex, Antigravity, Cursor…)

```text
Repo: <đường-dẫn-repo> (remote <owner>/agentfold).
Bắt đầu: git log --oneline -10 và git status để biết agent trước làm tới đâu.
Đọc AGENTS.md, rồi <bàn-giao>. Sau đó:
  .\.venv\Scripts\Activate.ps1
  $env:AGENTCTL_AGENT="<tên-agent>-local"
  python -m tools.agentctl prime
  python -m tools.agentctl board
Chọn việc từ board theo thứ tự trong bàn giao (chỉ nhận ticket có state ready; ticket `proposed` thì lập kế hoạch
rồi báo người duyệt, chưa viết mã).
Luật: một ticket một nhánh; test trước; không push; không Co-Authored-By; không động vùng bảo vệ ngoài ticket;
kiểm bằng python scripts/ci_local.py trước khi báo xong. Xong thì ghi AGENT-LOG và dừng chờ duyệt.
```

## Khi tạo thư mục mới trên máy khác

Tạo lại môi trường ảo thay vì chép: `python -m venv .venv`, kích hoạt, `pip install -r requirements-dev.txt`,
`git config core.hooksPath scripts/githooks` (hoặc `bash scripts/cloud_setup.sh`).
