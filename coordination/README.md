# coordination — Giao thức để nhiều AI agent cùng làm một repo

Đọc cùng: `docs/rules/70-multi-agent-coordination.md` (luật đầy đủ, lý do và bằng chứng).

## Mô hình trong một câu

**Con người chốt thiết kế và kế hoạch; agent thực thi trong phạm vi đã duyệt; git và CI phân xử.**
Không agent nào — dù của nhà cung cấp nào — cần tin agent khác đã đọc cùng hướng dẫn: mọi ràng buộc
quan trọng được kiểm bằng máy ở những chỗ MỌI agent bắt buộc đi qua (git, CI).

## Vòng đời một ticket

```
người lập kế hoạch ──► docs/work/tickets/ABC-01.md (state: proposed)
người duyệt       ──► PR đổi state: ready  (vùng bảo vệ work-plan ⇒ cần duyệt)
agent             ──► python -m tools.agentctl start ABC-01 --role R3
                        ├─ đọc ticket + policy từ origin/main (không từ bản cục bộ)
                        ├─ từ chối nếu phạm vi chồng một claim còn hạn hoặc trùng làn độc quyền
                        ├─ ghi claim NGUYÊN TỬ lên nhánh agent-claims
                        └─ tạo worktree .worktrees/ABC-01 trên nhánh feature/ABC-01-<slug> (không track main)
agent             ──► code + test trong worktree · commit "feat(api): ... (ABC-01)"
pre-commit        ──► check-scope --staged (cùng hàm với CI)
agent             ──► PR nháp → Ready for review
CI scope-guard    ──► check-scope bằng CÔNG CỤ Ở NHÁNH GỐC · đòi nhãn duyệt nếu chạm vùng bảo vệ · đòi claim
người review      ──► đọc diff, gắn nhãn nếu cần, merge bằng nút Merge
agent             ──► python -m tools.agentctl release ABC-01
```

## Lệnh

| Lệnh | Việc |
|---|---|
| `start <ID> --role Rn` | claim + tạo worktree/nhánh riêng |
| `claim <ID> --role Rn` | chỉ claim (đã có nhánh) |
| `renew [<ID>] [--hours N]` | gia hạn lease, chạy từ worktree của claim |
| `release [<ID>]` | nhả claim sau khi merge hoặc bỏ việc |
| `release <ID> --override --reason "..."` | người điều phối dọn claim bỏ dở của nhánh khác |
| `reap` | dọn mọi claim đã hết hạn |
| `status [--offline]` | liệt kê claim |
| `board [--offline]` | bảng công việc suy ra (ready / đang làm / quá hạn / đã merge / câu hỏi mở) |
| `check-scope [--staged]` | so thay đổi với phạm vi ticket |
| `check-work` | kiểm cấu trúc mọi mục trong `docs/work/` |
| `new log\|decision\|question\|incident\|ticket` | tạo mục công việc thành file riêng |
| `new handoff --role Rn --title "..."` | bàn giao khi dừng giữa chừng; nhánh, commit cuối, file chưa commit điền sẵn từ git |

Tất cả chạy bằng `python -m tools.agentctl <lệnh>`. Mã thoát: 0 ổn · 1 vi phạm · 2 sai cú pháp · 3 môi trường thiếu công cụ.

## `policy.yaml` quyết định gì

| Khối | Nghĩa | Ví dụ |
|---|---|---|
| `always_allowed` | sửa được trong mọi ticket vì mỗi mục là file riêng | `docs/work/log/**` |
| `protected` | vùng người sở hữu: cần nhãn duyệt, hoặc ticket duyệt trước bằng `scope.protected` | `docs/design/`, `tests/guards/` |
| `allow_additions` | trong vùng bảo vệ, THÊM file mới thì không cần duyệt | thêm lưới canh mới, thêm ticket đề xuất |
| `exclusive` | làn chỉ một ticket giữ tại một thời điểm | `alembic/versions/`, lockfile, `contracts/openapi.json` |

## Vì sao sổ claim là một nhánh git mồ côi

- **Nguyên tử:** `git push` từ chối lần đẩy không fast-forward — hai agent claim cùng lúc thì đúng một
  người thắng; người kia đọc lại sổ và thấy claim vừa ghi (có test: `tests/tools/test_claims.py`).
- **Không phụ thuộc nhà cung cấp hay git host:** không cần token API, không cần dịch vụ ngoài.
- **Không đụng cây làm việc:** chỉ dùng plumbing trên index tạm — không `checkout`, không `stash`.
- **Không làm bẩn `main`:** không PR nào mang file claim.

Xem sổ bằng tay: `git fetch origin agent-claims && git ls-tree -r --name-only origin/agent-claims`.

## Khi có trục trặc

| Triệu chứng | Nguyên nhân thường gặp | Làm gì |
|---|---|---|
| `claim` bị từ chối "phạm vi đang có người giữ" | ticket khác còn hạn chạm cùng file | chọn ticket khác, chờ release, hoặc mở câu hỏi xin tách phạm vi |
| "ticket không có trên origin/main" | kế hoạch chưa merge | nhờ người duyệt merge ticket trước |
| "không kéo được origin/main" | không có mạng / chưa có remote | `status --offline`, `board --offline`; claim bắt buộc cần remote |
| `check-scope` báo file ngoài scope | agent "tiện tay" sửa thêm | hoàn tác phần đó; nếu thật sự cần thì mở câu hỏi — **không** sửa ticket trong nhánh |
| hook chặn ghi file | file thuộc vùng bảo vệ hoặc ngoài scope | đọc thông điệp; người chủ phiên có thể đặt `AGENTCTL_HOOKS=off` cho việc đã được duyệt |
| claim quá hạn trên `board` | agent dừng giữa chừng | người điều phối kiểm nhánh, rồi `reap` hoặc `release --override` |

## Giới hạn — nói thật

- Nhãn duyệt trên PR **không phải ranh giới bảo mật**: agent dùng token có quyền gắn nhãn thì tự gắn
  được. Chốt thật là branch protection "Require review from Code Owners" + agent dùng tài khoản/token
  **không** có quyền duyệt. Nếu agent làm việc bằng chính tài khoản của người, không cơ chế nền tảng nào
  phân biệt được hai bên — cổng khi đó là kỷ luật quy trình, và phải được ghi rõ như vậy.
- Hook chặn ghi chỉ có ở công cụ hỗ trợ (Claude Code, Codex CLI, Gemini CLI). Công cụ khác chỉ bị chặn
  ở pre-commit và CI — nên CI mới là luật, hook chỉ là phản hồi sớm.
