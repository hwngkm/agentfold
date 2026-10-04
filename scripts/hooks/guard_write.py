"""Hook TRƯỚC KHI GHI FILE: chặn agent ghi vào vùng bảo vệ, hoặc ra ngoài phạm vi ticket đang làm.

Một script cho ba công cụ, vì cả ba chặn thao tác khi hook thoát mã 2 và đọc lý do từ stderr:
Claude Code (`PreToolUse`), Codex CLI (`PreToolUse`, sửa file qua `apply_patch`), Gemini CLI
(`BeforeTool`, công cụ `write_file`/`replace`). Công cụ không có hook chặn được thì vẫn gặp đúng luật
này ở pre-commit và CI — cùng hàm `tools.agentctl.scope.evaluate`.

🔒 Hook là phản hồi SỚM, không phải luật. Luật nằm ở CI.
🔒 Môi trường trục trặc (thiếu git/PyYAML, repo lạ, JSON lạ) ⇒ CHO QUA và cảnh báo: một hook hỏng không
   được làm đứng hình cả phiên làm việc.
🔓 Việc chạm vùng bảo vệ đã được người chủ phiên duyệt: đặt `AGENTCTL_HOOKS=off` cho phiên đó.

Khi nhánh hiện tại KHÔNG gắn ticket, hook chỉ chặn vùng bảo vệ — không chặn mọi file — để người dùng
agent cho việc khám phá ngoài quy trình ticket không bị cản.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BLOCK = 2
_PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+?)\s*$", re.MULTILINE)
_PATCH_MOVE = re.compile(r"^\*\*\* Move to: (.+?)\s*$", re.MULTILINE)


def target_paths(payload: dict[str, Any]) -> list[str]:
    """Đường dẫn mà lượt gọi công cụ sắp ghi, bất kể công cụ nào gửi payload."""
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        return []
    paths = [
        value
        for key in ("file_path", "path", "absolute_path", "notebook_path")
        if isinstance(value := tool_input.get(key), str)
    ]
    for edit in tool_input.get("edits") or []:
        if isinstance(edit, dict) and isinstance(edit.get("file_path"), str):
            paths.append(edit["file_path"])
    command = tool_input.get("command")
    if isinstance(command, list):
        command = "\n".join(part for part in command if isinstance(part, str))
    if isinstance(command, str) and "*** Begin Patch" in command:
        paths += _PATCH_FILE.findall(command) + _PATCH_MOVE.findall(command)
    return paths


def new_texts(payload: dict[str, Any]) -> list[str]:
    """Nội dung mà lượt gọi công cụ sắp ghi (Write `content`, Edit `new_string`, patch...), để phát hiện tự duyệt kế hoạch."""
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        return []
    texts = [v for k in ("content", "new_string", "new_str", "text") if isinstance(v := tool_input.get(k), str)]
    texts += [
        v
        for edit in tool_input.get("edits") or []
        if isinstance(edit, dict) and isinstance(v := edit.get("new_string"), str)
    ]
    command = tool_input.get("command")
    if isinstance(command, list):
        command = "\n".join(part for part in command if isinstance(part, str))
    if isinstance(command, str) and "*** Begin Patch" in command:
        texts.append(command)
    return texts


def _nearest_existing_dir(path: Path) -> Path:
    for candidate in [path, *path.parents]:
        if candidate.is_dir():
            return candidate
    return Path(path.anchor) if path.anchor else Path.cwd()


def problems_for(repo: Path, rel: str, status: str, texts: Sequence[str] = ()) -> list[str]:
    from tools.agentctl.gitutil import Change, current_branch, resolve, show_file
    from tools.agentctl.policy import POLICY_PATH, load_policy
    from tools.agentctl.scope import evaluate, is_self_approval, plan_status, plan_ticket
    from tools.agentctl.tickets import load_ticket, ticket_id_from_branch

    if not (repo / POLICY_PATH).is_file():
        return []  # repo không dùng agentctl
    local = load_policy(repo, None)
    base = local.base_ref if resolve(repo, local.base_ref) else None
    policy = load_policy(repo, base) if base else local
    ticket_id = ticket_id_from_branch(current_branch(repo))
    # Cổng thật (`check-scope`) so với nhánh GỐC: tệp chưa có ở gốc là THÊM dù đã có trên đĩa. Hook phải phân xử y hệt,
    # nếu không agent không điền được tệp mình vừa tạo (vd. kế hoạch do `agentctl new plan` tạo).
    base_text = show_file(repo, base, rel) if base else None
    if base and base_text is None:
        status = "A"
    plan_of = plan_ticket(rel)
    if plan_of is not None:
        if any(is_self_approval(text) for text in texts):
            return [f"{rel} — duyệt kế hoạch (`status: approved`, `approved_by`) là việc của người, không phải agent"]
        # Kế hoạch `proposed` của CHÍNH ticket đang làm thì điền được; đã duyệt hoặc của ticket khác thì chặn như cũ.
        if status == "M" and plan_status(base_text) == "proposed" and plan_of == ticket_id:
            return []
    ticket = load_ticket(repo, policy, ticket_id, base) if ticket_id and base else None
    if ticket is None:
        return [
            f"{rel} — vùng bảo vệ `{zone.id}` ({zone.why})"
            for zone in policy.zones_for(rel)
            if not (status == "A" and zone.allow_additions)
        ]
    verdict = evaluate([Change(status, rel)], policy=policy, ticket_id=ticket.id, ticket=ticket, approved=False)
    return [*verdict.errors, *verdict.approvals_needed]


def decide(payload: dict[str, Any], *, cwd: Path) -> tuple[int, str]:
    from tools.agentctl.errors import AgentctlError
    from tools.agentctl.gitutil import project_root

    if os.environ.get("AGENTCTL_HOOKS", "").strip().lower() == "off":
        return 0, ""
    base_dir = Path(payload["cwd"]) if isinstance(payload.get("cwd"), str) else cwd
    found: list[str] = []
    for raw in target_paths(payload):
        path = Path(raw) if Path(raw).is_absolute() else base_dir / raw
        path = path.resolve()
        try:
            repo = project_root(_nearest_existing_dir(path.parent))
        except AgentctlError:
            continue  # ngoài repo git: không thuộc quyền điều phối
        try:
            rel = path.relative_to(repo.resolve()).as_posix()
        except ValueError:
            continue
        found += problems_for(repo, rel, "M" if path.exists() else "A", new_texts(payload))
    if not found:
        return 0, ""
    message = (
        "🛑 agentctl chặn thao tác ghi:\n"
        + "\n".join(f"  - {item}" for item in found)
        + "\nKhông tìm cách lách. Cần sửa ngoài phạm vi hoặc vùng người sở hữu thì mở câu hỏi và làm tiếp phần khác:\n"
        + '  python -m tools.agentctl new question --role <Rn> --title "..." --blocking <ID>\n'
        + "(Người chủ phiên ĐÃ duyệt việc này? Họ đặt AGENTCTL_HOOKS=off cho phiên — agent không tự đặt.)"
    )
    return BLOCK, message


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        from tools.agentctl.errors import AgentctlError

        try:
            code, message = decide(payload, cwd=Path.cwd())
        except (AgentctlError, OSError, ValueError) as exc:
            print(f"⚠️  agentctl hook bỏ qua kiểm tra: {exc}", file=sys.stderr)
            return 0
    except ImportError as exc:
        print(f"⚠️  agentctl hook không nạp được công cụ: {exc}", file=sys.stderr)
        return 0
    if message:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
