"""Ticket = một file Markdown có front matter YAML trong `docs/work/tickets/<ID>.md`.

Ticket chỉ chứa **kế hoạch đã duyệt** (phạm vi, tiêu chí nghiệm thu, phụ thuộc). Trạng thái động
— ai đang làm, đã merge chưa — KHÔNG ghi vào ticket mà suy ra từ sổ claim và lịch sử `main`.
Nhờ vậy không agent nào phải sửa ticket trong lúc làm, và file ticket không bao giờ thành điểm
nóng xung đột như `TICKETS.md` dùng chung (đã gặp thật).
"""

from __future__ import annotations

import re
from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.agentctl.errors import AgentctlError
from tools.agentctl.gitutil import commit_subjects, show_file
from tools.agentctl.globs import matches_everything, may_overlap
from tools.agentctl.policy import Policy, yaml, yaml_error_message

TICKET_ID = re.compile(r"^[A-Z][A-Z0-9]{1,9}-\d{2,4}$")
STATES = ("proposed", "ready", "cancelled")
_BRANCH = re.compile(r"^(?:feature|fix|chore|docs|refactor|test|perf|ci)/([A-Z][A-Z0-9]{1,9}-\d{2,4})(?:-|$)")
_ID_IN_SUBJECT = re.compile(r"\(([A-Z][A-Z0-9]{1,9}-\d{2,4})\)")
_ID_IN_MERGE = re.compile(r"/(?:feature|fix|chore|docs|refactor|test|perf|ci)/([A-Z][A-Z0-9]{1,9}-\d{2,4})(?:-|\b)")


class TicketError(AgentctlError):
    """Ticket sai cấu trúc hoặc không dùng được."""


@dataclass(frozen=True)
class Ticket:
    id: str
    title: str
    state: str
    owner_role: str
    design_refs: tuple[str, ...]
    depends_on: tuple[str, ...]
    allow: tuple[str, ...]
    exclusive: tuple[str, ...]
    protected: tuple[str, ...]
    acceptance: tuple[str, ...]


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        raise TicketError("thiếu front matter (file phải bắt đầu bằng `---`)")
    end = normalized.find("\n---", 4)
    if end == -1:
        raise TicketError("front matter không có dòng `---` đóng")
    try:
        data = yaml.safe_load(normalized[4:end])
    except yaml.YAMLError as exc:
        raise TicketError(yaml_error_message("front matter", exc)) from exc
    if not isinstance(data, dict):
        raise TicketError("front matter phải là một mapping")
    return data, normalized[end + 4 :].lstrip("\n")


def _list(value: Any, where: str, problems: list[str]) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        problems.append(f"{where}: cần danh sách chuỗi")
        return ()
    return tuple(item.strip() for item in value)


def parse_ticket(text: str, *, source: str) -> Ticket:
    data, _body = split_front_matter(text)
    problems: list[str] = []

    def field(key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"`{key}`: cần chuỗi không rỗng")
            return ""
        return value.strip()

    scope = data.get("scope") if isinstance(data.get("scope"), dict) else None
    if scope is None:
        problems.append("`scope`: cần mapping có `allow`")
        scope = {}
    ticket = Ticket(
        id=field("id"),
        title=field("title"),
        state=field("state"),
        owner_role=field("owner_role"),
        design_refs=_list(data.get("design_refs"), "design_refs", problems),
        depends_on=_list(data.get("depends_on"), "depends_on", problems),
        allow=_list(scope.get("allow"), "scope.allow", problems),
        exclusive=_list(scope.get("exclusive"), "scope.exclusive", problems),
        protected=_list(scope.get("protected"), "scope.protected", problems),
        acceptance=_list(data.get("acceptance"), "acceptance", problems),
    )
    if ticket.id and not TICKET_ID.match(ticket.id):
        problems.append(f"`id` `{ticket.id}` phải dạng `ABC-01`")
    if ticket.state and ticket.state not in STATES:
        problems.append(f"`state` `{ticket.state}` không thuộc {STATES} (`done` được suy ra, không ghi tay)")
    if not ticket.allow and not ticket.exclusive and not ticket.protected:
        problems.append("`scope` rỗng — ticket phải nói rõ được chạm vào đâu")
    if not ticket.acceptance:
        problems.append("`acceptance`: cần ít nhất một tiêu chí nghiệm thu kiểm được")
    broad = [pattern for pattern in ticket.allow if matches_everything(pattern)]
    if broad:
        problems.append(f"`scope.allow` chứa mẫu phủ cả repo {broad} — không điều phối được")
    for dep in ticket.depends_on:
        if not TICKET_ID.match(dep):
            problems.append(f"`depends_on` `{dep}` không phải mã ticket")
    if problems:
        raise TicketError(f"{source}: " + "; ".join(problems))
    return ticket


def policy_problems(ticket: Ticket, policy: Policy) -> list[str]:
    """Tham chiếu tới làn/vùng không tồn tại, và `allow` lấn vào làn/vùng mà không khai tên.

    Làn độc quyền và vùng bảo vệ chỉ được giữ BẰNG TÊN (`scope.exclusive`, `scope.protected`). Nếu
    cho liệt kê thẳng đường dẫn của chúng trong `allow`, hai ticket có thể cùng chạm
    `alembic/versions/**` mà sổ claim không thấy chúng tranh cùng một làn.
    """
    problems = [f"làn độc quyền `{lane}` không có trong policy" for lane in ticket.exclusive if not policy.lane(lane)]
    problems += [f"vùng bảo vệ `{zone}` không có trong policy" for zone in ticket.protected if not policy.zone(zone)]
    for pattern in ticket.allow:
        for lane in policy.exclusive:
            if any(may_overlap(pattern, path) for path in lane.paths):
                problems.append(
                    f"`scope.allow` mẫu `{pattern}` lấn làn `{lane.id}` — khai `{lane.id}` trong `scope.exclusive`"
                )
        for zone in policy.protected:
            if any(may_overlap(pattern, path) for path in zone.paths):
                problems.append(
                    f"`scope.allow` mẫu `{pattern}` lấn vùng bảo vệ `{zone.id}` — khai trong `scope.protected`"
                )
    return problems


def ticket_path(policy: Policy, ticket_id: str) -> str:
    return f"{policy.tickets_dir}/{ticket_id}.md"


def load_ticket(repo: Path, policy: Policy, ticket_id: str, ref: str | None) -> Ticket | None:
    """Ticket tại `ref` (thường là `origin/main`); `ref=None` đọc cây làm việc. Không có → `None`."""
    path = ticket_path(policy, ticket_id)
    if ref is None:
        file = repo / path
        text = file.read_text(encoding="utf-8") if file.is_file() else None
    else:
        text = show_file(repo, ref, path)
    if text is None:
        return None
    ticket = parse_ticket(text, source=path)
    if ticket.id != ticket_id:
        raise TicketError(f"{path}: `id` là `{ticket.id}` nhưng tên file là `{ticket_id}`")
    problems = policy_problems(ticket, policy)
    if problems:
        raise TicketError(f"{path}: " + "; ".join(problems))
    return ticket


def ticket_id_from_branch(branch: str | None) -> str | None:
    match = _BRANCH.match(branch or "")
    return match.group(1) if match else None


def merged_ticket_ids(repo: Path, ref: str) -> set[str]:
    """Mã ticket xuất hiện trong lịch sử `ref`: `feat(api): ... (API-03)` hoặc `Merge ... /feature/API-03-...`."""
    found: set[str] = set()
    for subject in commit_subjects(repo, ref):
        found.update(_ID_IN_SUBJECT.findall(subject))
        if subject.startswith("Merge "):
            found.update(_ID_IN_MERGE.findall(subject))
    return found


def validate_tickets_dir(root: Path, policy: Policy, merged: Collection[str] = frozenset()) -> list[str]:
    """Kiểm mọi ticket trong cây làm việc. Bỏ qua file bắt đầu bằng `_` (mẫu).

    Ticket đã merge (`merged`) vẫn kiểm cấu trúc nhưng KHÔNG bị kiểm lại `allow` lấn vùng/làn theo chính sách hiện tại:
    nó đã được duyệt theo chính sách lúc đó, còn chính sách mới (vd. mở rộng vùng bảo vệ) không được làm nó tự đỏ.
    """
    directory = root / policy.tickets_dir
    problems: list[str] = []
    tickets: dict[str, Ticket] = {}
    for file in sorted(directory.glob("*.md")) if directory.is_dir() else []:
        if file.name.startswith("_") or file.name == "README.md":
            continue
        rel = file.relative_to(root).as_posix()
        try:
            ticket = parse_ticket(file.read_text(encoding="utf-8"), source=rel)
        except TicketError as exc:
            problems.append(str(exc))
            continue
        if file.stem != ticket.id:
            problems.append(f"{rel}: tên file phải là `{ticket.id}.md`")
        if ticket.id in tickets:
            problems.append(f"{rel}: trùng id `{ticket.id}`")
        if ticket.id not in merged:
            problems += [f"{rel}: {p}" for p in policy_problems(ticket, policy)]
        tickets[ticket.id] = ticket
    for ticket in tickets.values():
        for dep in ticket.depends_on:
            if dep not in tickets:
                problems.append(f"{ticket.id}: phụ thuộc `{dep}` không có file ticket")
    return problems
