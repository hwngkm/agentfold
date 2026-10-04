# SKILLS.md — mục lục kỹ năng đang bật (SINH TỰ ĐỘNG, đừng sửa tay)

> Sinh bởi `python scripts/packs.py --install/--remove`; CI kiểm khớp (`--check`). Skill được cài ở HAI nơi giống
> hệt nhau: `.claude/skills/` (Claude Code tự nạp) và `.agents/skills/` (Codex, Cursor, Antigravity, Gemini CLI,
> GitHub Copilot, OpenCode tự nạp). Công cụ không tự nạp ở đâu cả (Aider…): khi việc khớp cột "Dùng khi", MỞ
> file SKILL.md tương ứng và làm theo — nội dung là Markdown thuần, không cần kết nối gì.

| Skill | Pack | Dùng khi (trích mô tả) | File |
|---|---|---|---|
| `adr` | lõi | Dùng khi sắp sửa contracts/boundaries.yaml hoặc invariants.yaml, khi thêm/bỏ dependency hay đổi nhà cung cấp LLM, khi nới một ràng buộc an toàn, hoặc khi hai phương án đã tranh luận quá 15 phút mà chưa ngã ngũ. | `.claude/skills/adr/SKILL.md` |
| `bug-fix` | lõi | Dùng khi nhận một báo lỗi hay CI đỏ do lỗi thật, khi agent định sửa theo phỏng đoán, hoặc khi cần chứng minh một lỗi đã được sửa thật. | `.claude/skills/bug-fix/SKILL.md` |
| `diagram` | lõi | Dùng khi thêm lớp/gói mới, đổi ranh giới import, đổi vùng bảo vệ hay chủ vùng, khi CI báo sơ đồ lệch nguồn, hoặc khi cần vẽ luồng/ERD/máy trạng thái mới. | `.claude/skills/diagram/SKILL.md` |
| `guard-net` | lõi | Dùng khi vừa sửa xong một bug đáng nhớ, khi chốt một ràng buộc kiến trúc, khi review thấy "chỗ này ai đó sẽ phá lại", hoặc khi một lưới canh đỏ vì PR đổi cơ chế hợp lệ. | `.claude/skills/guard-net/SKILL.md` |
| `idea-assessment` | lõi | Dùng khi có ý tưởng tính năng hoặc sản phẩm chưa có ticket, khi yêu cầu mơ hồ hoặc tốn công, hoặc khi cả nhóm hào hứng nhưng chưa ai hỏi vì sao nên làm. | `.claude/skills/idea-assessment/SKILL.md` |
| `multi-agent` | lõi | Dùng tools/agentctl để nhiều AI agent hoặc nhiều người làm song song trên cùng repo mà không giẫm chân — claim phạm vi, worktree riêng, kiểm phạm vi trước khi commit. Dùng khi biết có từ hai phiên trở lên cùng làm trong một khung giờ, khi cần biết ai đang giữ phần nào, hoặc khi hook chặn ghi file và cần hiểu vì sao. | `.claude/skills/multi-agent/SKILL.md` |
| `ticket-flow` | lõi | Dùng khi bắt đầu một việc mới có mã ticket, khi chuẩn bị mở PR, hoặc khi không chắc bước tiếp theo trong vòng đời một thay đổi. | `.claude/skills/ticket-flow/SKILL.md` |
