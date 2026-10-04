---
name: multi-agent
description: Dùng tools/agentctl để nhiều AI agent hoặc nhiều người làm song song trên cùng repo mà không giẫm chân — claim phạm vi, worktree riêng, kiểm phạm vi trước khi commit. Dùng khi biết có từ hai phiên trở lên cùng làm trong một khung giờ, khi cần biết ai đang giữ phần nào, hoặc khi hook chặn ghi file và cần hiểu vì sao.
---

# Điều phối nhiều agent

Luật đầy đủ: `docs/rules/70-multi-agent-coordination.md`. Quyết định nền: `docs/design/adr/0001-*.md`.

## Trước hết: có cần không?

**Cần** khi ≥2 phiên agent/người sẽ động vào repo trong cùng khung giờ trên các việc khác nhau.

**Không cần** khi một người/một phiên làm tuần tự — thêm ticket file + claim chỉ là chi phí thừa khi không
có ai tranh chấp. Quy trình thường trong skill `ticket-flow` đã đủ.

Công cụ này **opt-in**: repo không bật nó vẫn chạy bình thường, CI vẫn xanh.

## Vòng đời

```bash
python -m tools.agentctl board                  # ai đang giữ gì, ticket nào ready
python -m tools.agentctl start <MÃ> --role R3   # claim + tạo worktree riêng trên nhánh riêng
cd .worktrees/<MÃ>
# ... làm việc như bình thường (skill ticket-flow)
python -m tools.agentctl check-scope            # tự kiểm trước khi mở PR
git push -u origin HEAD && gh pr create --draft
python -m tools.agentctl release <MÃ>           # sau khi merge, hoặc khi bỏ việc giữa chừng
```

Claim tự hết hạn (mặc định 24h, tối đa 72h). `reap` dọn claim bỏ dở — không cần ai đi gỡ tay.

## Phạm vi đến từ đâu

`docs/work/tickets/<MÃ>.md` khai `scope.allow` (file được sửa), `scope.exclusive` (làn độc quyền),
`scope.protected` (vùng bảo vệ đã được duyệt trước cho ticket này).

🔒 **Khi phân xử, ticket và chính sách luôn đọc từ NHÁNH GỐC (`origin/main`), không từ nhánh đang làm.**
Tự nới `scope.allow` trong nhánh của mình không có tác dụng — bên bị kiểm không cầm bộ kiểm. Cần thêm
phạm vi thì mở câu hỏi:

```bash
python -m tools.agentctl new question --title "..." --blocking <MÃ>
```

## Khi hook chặn ghi file

Hook (`PreToolUse`/`BeforeTool` → `scripts/hooks/guard_write.py`) chặn **lúc soạn**, sớm hơn commit và PR.
Bị chặn nghĩa là file bạn định sửa nằm ngoài phạm vi ticket đang claim. Ba đường đi đúng:

1. File đó đáng lẽ thuộc ticket này ⇒ mở câu hỏi xin mở rộng phạm vi, người duyệt sửa ticket trên `main`.
2. File đó thuộc việc khác ⇒ đó là ticket khác, làm riêng.
3. File nằm trong `always_allowed` (nhật ký, quyết định, câu hỏi, sự cố) ⇒ không bị chặn; nếu vẫn bị,
   báo lỗi công cụ.

**Không** vòng qua hook bằng cách tắt nó hay `--no-verify`.

## Giới hạn — nói thật

- **Không phải ranh giới bảo mật.** Agent có quyền gắn nhãn PR vẫn gắn được nhãn duyệt. Chốt thật vẫn là
  CODEOWNERS + review người.
- **Claim cần mạng tới `origin`.** Mất mạng thì chỉ `board --offline`/`status --offline` dùng được.
- Công cụ chặn **giẫm chân về phạm vi file**, không chặn được hai người hiểu sai cùng một yêu cầu.

## Nhiều phiên trên CÙNG một cây làm việc

Đây là ca nguy hiểm nhất và công cụ **không** giải quyết được: `git` chỉ có một cây làm việc, một HEAD.
Hai phiên cùng `cd` vào một thư mục sẽ thấy nhánh của nhau.

- Mỗi phiên làm trong **worktree riêng** (`agentctl start` tạo sẵn) — đó là cách tránh.
- Nếu buộc phải dùng chung: **không bao giờ `git add -A`/`git add .`** (cuốn theo việc dở của phiên khác),
  liệt kê đúng file rồi soát bằng `git diff --cached --name-only`; không `git checkout`/`reset` khi phiên
  khác đang chạy test nền; báo cho nhau trước khi đổi nhánh.
