"""`python -m tools.agentctl pr-body` — tiêu đề và nội dung PR sinh từ ticket + git, không cần `gh`, MCP hay mạng.

Chỉ ĐỌC git cục bộ (log, diff, ref đã kéo về). Việc mở PR vẫn do người/agent làm bằng công cụ có sẵn: `gh`, công cụ GitHub MCP, hoặc dán
nội dung vào giao diện web. Nội dung KHÔNG ghi công công cụ hay mô hình AI; phần "Bằng chứng" chỉ liệt kê lệnh cần chạy để người điền kết quả,
không bao giờ tự điền kết quả.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.agentctl.commitmsg import MAX_SUBJECT, check_commit_message
from tools.agentctl.errors import AgentctlError
from tools.agentctl.gitutil import current_branch, diff_changes, resolve, run_git
from tools.agentctl.policy import load_policy
from tools.agentctl.tickets import Ticket, load_ticket, ticket_path

_TYPE_BY_BRANCH = {
    "feature": "feat",
    "fix": "fix",
    "docs": "docs",
    "chore": "chore",
    "refactor": "refactor",
    "test": "test",
    "perf": "perf",
    "ci": "ci",
}
_PREFIX = re.compile(r"^([A-Z][A-Z0-9]*)-")
# `check_commit_message` miễn kiểm các dòng `Merge ...`/`Revert ...`; tiêu đề PR thì phải đúng dạng conventional.
_CONVENTIONAL_HEAD = re.compile(r"^(feat|fix|docs|test|refactor|chore|perf|ci)(\([a-z0-9][a-z0-9-]*\))?!?: \S")
MAX_LINES = 40


def _ticket(repo: Path, ticket_id: str) -> tuple[Ticket, str | None, str]:
    policy = load_policy(repo, None)
    base = policy.base_ref if resolve(repo, policy.base_ref) else None
    ticket = load_ticket(repo, policy, ticket_id, base) or load_ticket(repo, policy, ticket_id, None)
    if ticket is None:
        raise AgentctlError(f"không thấy ticket `{ticket_id}` ở `{ticket_path(policy, ticket_id)}`")
    return ticket, base, ticket_path(policy, ticket_id)


def _lines(output: str) -> list[str]:
    return [line for line in output.splitlines() if line.strip()]


# Loại commit coi là "thay đổi tính năng" khi chọn tiêu đề PR: nhật ký và kế hoạch (`docs(work)`) thường là commit cuối nhưng không mô tả PR.
_FEATURE_TYPES = ("feat", "fix", "refactor", "perf", "test", "chore")
MAX_SCAN = 50


def _candidate_subjects(repo: Path, base: str | None) -> list[str]:
    """Chủ đề các commit CỦA NHÁNH (base..HEAD) từ mới đến cũ; không có base thì lấy vài commit gần nhất."""
    args = ["log", "--format=%s", f"{base}..HEAD"] if base else ["log", f"-n{MAX_SCAN}", "--format=%s"]
    return _lines(run_git(repo, args).stdout)


def _pick_subject(subjects: list[str], ticket_id: str) -> str | None:
    """Commit tính năng hợp lệ gần nhất; nếu nhánh không có thì commit hợp lệ gần nhất loại khác (vd. `docs(work)`); không có thì None."""
    valid = [s for s in subjects if _CONVENTIONAL_HEAD.match(s) and not check_commit_message(s, ticket_id)]
    for subject in valid:
        if subject.split("(", 1)[0].split(":", 1)[0].rstrip("!") in _FEATURE_TYPES:
            return subject
    return valid[0] if valid else None


def build_title(repo: Path, ticket: Ticket, base: str | None = None) -> str:
    """Chủ đề commit tính năng gần nhất của nhánh nếu đã đúng quy ước; không có thì commit hợp lệ gần nhất; không có nữa thì dựng từ nhánh +
    tiêu đề ticket. Luôn qua kiểm thông điệp commit."""
    picked = _pick_subject(_candidate_subjects(repo, base), ticket.id)
    if picked:
        return picked
    branch = current_branch(repo) or ""
    kind = _TYPE_BY_BRANCH.get(branch.split("/", 1)[0], "chore")
    match = _PREFIX.match(ticket.id)
    scope = (match.group(1) if match else "work").lower()
    suffix = f" ({ticket.id})"
    head = f"{kind}({scope}): "
    room = MAX_SUBJECT - len(head) - len(suffix)
    title = f"{head}{ticket.title.strip()[: max(room, 1)].rstrip()}{suffix}"
    problems = check_commit_message(title, ticket.id)
    if problems:
        raise AgentctlError(f"không dựng được tiêu đề hợp lệ cho `{ticket.id}`: {'; '.join(problems)}")
    return title


def _bullets(items: list[str]) -> str:
    shown = [f"- {item}" for item in items[:MAX_LINES]]
    if len(items) > MAX_LINES:
        shown.append(f"- ... và {len(items) - MAX_LINES} mục nữa")
    return "\n".join(shown) if shown else "- (không có)"


def build_body(repo: Path, ticket: Ticket, base: str | None, ticket_file: str) -> str:
    commits = _lines(run_git(repo, ["log", "--format=%s", f"{base}..HEAD"]).stdout) if base else []
    changed = [f"`{c.path}`" for c in diff_changes(repo, base, "HEAD")] if base else []
    scope = [f"`{pattern}`" for pattern in ticket.allow]
    scope += [f"làn `{lane}`" for lane in ticket.exclusive] + [f"vùng bảo vệ `{zone}`" for zone in ticket.protected]
    refs = [f"`{ref}`" for ref in ticket.design_refs]
    return "\n".join(
        [
            "## Ticket",
            "",
            f"`{ticket.id}` — {ticket_file}",
            "",
            "## Thay đổi",
            "",
            "Commit:",
            _bullets(commits),
            "",
            "File đã đổi:",
            _bullets(changed),
            "",
            "## Vì sao / tham chiếu thiết kế",
            "",
            _bullets(refs),
            "",
            "## Tiêu chí nghiệm thu (từ ticket)",
            "",
            "\n".join(f"- [ ] {criterion}" for criterion in ticket.acceptance) or "- (không có)",
            "",
            "## Phạm vi (từ ticket)",
            "",
            _bullets(scope),
            "",
            "## Bằng chứng (điền kết quả lệnh đã chạy)",
            "",
            "- [ ] `python scripts/ci_local.py` →",
            "- [ ] `python -m tools.agentctl check-scope` →",
            "- [ ] Test mới đã thấy ĐỎ trước khi có code:",
            "",
            "## Câu hỏi mở / quyết định mới",
            "",
            "-",
            "",
        ]
    )


def render_pr(repo: Path, ticket_id: str, *, part: str = "both") -> str:
    ticket, base, ticket_file = _ticket(repo, ticket_id)
    title = build_title(repo, ticket, base)
    if part == "title":
        return title + "\n"
    body = build_body(repo, ticket, base, ticket_file)
    return body if part == "body" else f"{title}\n\n{body}"
