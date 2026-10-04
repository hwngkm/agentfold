"""Hook TRƯỚC KHI CHẠY LỆNH / ĐỌC FILE: chặn lệnh phá huỷ và việc đọc bí mật — cho Claude Code, Codex, Gemini CLI.

Luật đã có trên giấy (AGENTS.md luật 8, R70.12): cấm `push --force`, `--no-verify`, đẩy thẳng `main`, `alembic stamp`,
lệnh git GHI cây làm việc khi có phiên khác dùng chung. Hook này biến chúng thành chặn thật, ngay lúc agent định chạy
— trước khi việc chưa commit của người/agent khác bị xoá. Thêm: không đọc `.env`, khoá SSH/đám mây, không in toàn bộ
biến môi trường hay token — thứ đã vào ngữ cảnh mô hình thì coi như đã lộ.

Danh mục và ý tưởng mượn từ kenryu42/cc-safety-net (MIT, bản đầy đủ hơn, cần Node — pack `review-audit` gợi ý cài kèm).
Bản này không cần gì ngoài Python.

Cách đọc lệnh: tách theo `&&`, `||`, `;`, `|`, xuống dòng; mỗi đoạn xét riêng, nên lệnh bọc trong `bash -c '…'`,
`powershell -Command "…"`, `python -c "…"` vẫn bị bắt. Đoạn bắt đầu bằng lệnh tìm kiếm (`grep`, `rg`, `git grep`…) chỉ
bị xét luật đọc bí mật — tìm chữ "git push --force" trong tài liệu không phải là đẩy.

Hook hỏng (JSON lạ) ⇒ CHO QUA: một hook lỗi không được làm đứng cả phiên. Luật thật vẫn ở pre-push/CI/branch protection.
`AGENTCTL_HOOKS=off` (người đặt lúc mở công cụ, agent không đổi được giữa phiên) tắt hook như mọi hook khác của template.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import PurePosixPath
from typing import Any

BLOCK = 2
SHELL_TOOLS = {"Bash", "shell", "local_shell", "exec_command", "run_shell_command", "container.exec"}
READ_TOOLS = {"Read", "read_file", "read_many_files", "view", "NotebookRead"}
_SPLIT = re.compile(r"&&|\|\||;|\||\n")
_SEARCH = re.compile(r"^\s*(?:grep|egrep|rg|ag|findstr|Select-String|sls|git\s+grep|git\s+log|echo|printf)\b")
_SEG = r"[^;&|\n]*"

DESTRUCTIVE: list[tuple[str, re.Pattern[str]]] = [
    (
        "git push --force / -f / +refspec (R70.12)",
        re.compile(rf"\bgit\b{_SEG}\bpush\b{_SEG}(?:\s--force(?:-with-lease)?\b|\s-f\b|\s\+[\w./:-]+)"),
    ),
    ("--no-verify bỏ qua hook kiểm (R70.12)", re.compile(rf"\bgit\b{_SEG}\s--no-verify\b")),
    ("git reset --hard xoá việc chưa commit (R70.5)", re.compile(rf"\bgit\b{_SEG}\breset\b{_SEG}\s--hard\b")),
    ("git clean -f xoá tệp chưa theo dõi (R70.5)", re.compile(rf"\bgit\b{_SEG}\bclean\b{_SEG}\s-[a-zA-Z]*f")),
    (
        "git checkout/restore cả cây làm việc (R70.5)",
        re.compile(r"\bgit\b[^;&|\n]*\b(?:checkout|restore)\b(?:\s+--)?\s+\.(?=\s|$|['\"])"),
    ),
    (
        "đẩy thẳng `main` (AGENTS.md luật 8)",
        re.compile(rf"\bgit\b{_SEG}\bpush\b{_SEG}\s(?:\S+:)?(?:refs/heads/)?main(?=\s|$|['\"])"),
    ),
    ("alembic stamp để chữa head (R70.12)", re.compile(rf"\balembic\b{_SEG}\bstamp\b")),
    (
        "rm -r trên thư mục gốc/nhà/repo/.git",
        re.compile(
            r"\brm\s+(?:-[a-zA-Z-]+\s+)*-[a-zA-Z]*[rR][a-zA-Z]*\s+(?:-[a-zA-Z-]+\s+)*"
            r"(?:/|/\*|~/?|\$HOME/?|\.{1,2}/?|\*|\.git/?)(?=\s|$|['\"])"
        ),
    ),
]
SECRETS: list[tuple[str, re.Pattern[str]]] = [
    (
        "đọc tệp .env (bí mật) — dùng .env.example để biết tên biến",
        re.compile(
            r"\b(?:cat|type|less|more|head|tail|bat|Get-Content|gc|grep|rg|findstr|sed|awk|source|nl|strings)\b"
            r"[^;&|\n]*?(?:^|[\s'\"=/\\])\.env(?:\.(?!example\b)[\w-]+)?(?=$|[\s'\"|;&)])"
        ),
    ),
    (
        "đọc khoá SSH/đám mây/token cục bộ",
        re.compile(
            r"\.ssh[/\\](?:id_|[^\s'\"]*key)|\bid_(?:rsa|ed25519|ecdsa)\b|\.aws[/\\]credentials|\.netrc\b"
            r"|\.config[/\\]gh[/\\]hosts"
        ),
    ),
    (
        "in toàn bộ biến môi trường (có thể chứa khoá)",
        re.compile(r"^\s*(?:printenv|env|set|Get-ChildItem\s+env:|gci\s+env:|dir\s+env:)\s*$"),
    ),
    (
        "in token GitHub ra màn hình — dùng `export GITHUB_TOKEN=$(gh auth token)` nếu cần",
        re.compile(r"(?<!\$\()\bgh\s+auth\s+(?:token\b|status\b[^;&|\n]*--show-token)"),
    ),
]


def reason_for_command(command: str) -> str | None:
    for segment in _SPLIT.split(command):
        rules = SECRETS if _SEARCH.match(segment) else DESTRUCTIVE + SECRETS
        for reason, pattern in rules:
            if pattern.search(segment):
                return reason
    return None


def _secret_path(path: str) -> str | None:
    posix = path.replace("\\", "/")
    name = PurePosixPath(posix).name
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        return "đọc tệp .env (bí mật) — dùng .env.example để biết tên biến"
    if re.search(r"/\.ssh/|/\.aws/credentials$|/\.netrc$|/\.config/gh/hosts", "/" + posix.lstrip("/")):
        return "đọc khoá SSH/đám mây/token cục bộ"
    return None


def reason_for_payload(payload: dict[str, Any]) -> str | None:
    tool = str(payload.get("tool_name") or payload.get("toolName") or "")
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}
    if not isinstance(tool_input, dict):
        return None
    command = tool_input.get("command")
    if isinstance(command, list):
        command = " ".join(part for part in command if isinstance(part, str))
    if isinstance(command, str) and (tool in SHELL_TOOLS or isinstance(tool_input.get("command"), list)):
        if "*** Begin Patch" not in command:
            return reason_for_command(command)
    if tool in READ_TOOLS:
        for key in ("file_path", "path", "absolute_path", "notebook_path"):
            value = tool_input.get(key)
            if isinstance(value, str) and (reason := _secret_path(value)):
                return reason
    return None


def main() -> int:
    if os.environ.get("AGENTCTL_HOOKS", "on") == "off":
        return 0
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0
    reason = reason_for_payload(payload)
    if reason is None:
        return 0
    print(
        f"🔴 Chặn: {reason}.\n"
        "   Agent không chạy lệnh này. Nếu thật sự cần, NGƯỜI chủ repo tự chạy trong terminal riêng sau khi xem xét;\n"
        "   agent hãy báo lại (AGENT-LOG `mail send` hoặc báo cáo cuối phiên) thay vì tìm đường vòng.",
        file=sys.stderr,
    )
    return BLOCK


if __name__ == "__main__":
    raise SystemExit(main())
