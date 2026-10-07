"""Sổ đội agent (`coordination/team.yaml`): ai điều phối, ai làm gì, ai review ai, việc nào chỉ người làm.

Vì sao một file có hợp đồng: thẻ agent trên nhánh `agent-mail` là TỰ KHAI và đổi theo phiên; phân cấp thì là quyết định
của người. Nên phân cấp ghi một lần ở vùng bảo vệ `coordination`, và khi phân xử (`mail assign`) được đọc từ nhánh
gốc — agent sửa bản cục bộ không tự nâng quyền mình được (như `policy.yaml`).

Sổ đội KHÔNG cấp quyền vượt luật: cột `human_only` liệt kê việc không agent nào làm, kể cả điều phối viên.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from tools.agentctl.errors import AgentctlError
from tools.agentctl.gitutil import show_file
from tools.agentctl.mail import AGENT_ID, TOOLS
from tools.agentctl.tickets import Ticket

TEAM_PATH = "coordination/team.yaml"
RANKS = ("coordinator", "specialist", "generalist")
_ROLE = re.compile(r"^R\d+$")


@dataclass(frozen=True)
class Member:
    id: str
    tool: str
    vendor: str
    rank: str
    on_behalf_of: str
    reports_to: str
    strengths: tuple[str, ...]
    wake: str


@dataclass(frozen=True)
class Route:
    kind: str
    primary: str
    backup: str | None
    review: str | None


@dataclass(frozen=True)
class Team:
    members: dict[str, Member]
    routes: dict[str, Route]
    ranks: dict[str, tuple[str, ...]]
    human_only: tuple[str, ...]

    @property
    def coordinator(self) -> Member:
        return next(m for m in self.members.values() if m.rank == "coordinator")

    def route(self, kind: str) -> Route:
        if kind not in self.routes:
            raise AgentctlError(f"không có tuyến việc `{kind}` — có: {', '.join(sorted(self.routes))}")
        return self.routes[kind]

    def member(self, agent: str) -> Member:
        if agent not in self.members:
            raise AgentctlError(f"`{agent}` không có trong đội ({TEAM_PATH}) — có: {', '.join(sorted(self.members))}")
        return self.members[agent]


def _strs(value: Any, where: str, problems: list[str]) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        problems.append(f"`{where}`: cần danh sách chuỗi")
        return ()
    return tuple(value)


def parse_team(text: str, *, source: str) -> Team:
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise AgentctlError(f"{source}: YAML hỏng: {exc}") from exc
    if not isinstance(data, dict) or data.get("version") != 1:
        raise AgentctlError(f"{source}: cần mapping có `version: 1`")
    problems: list[str] = []

    members: dict[str, Member] = {}
    for agent, raw in (data.get("agents") or {}).items():
        if not isinstance(raw, dict):
            problems.append(f"`agents.{agent}`: cần mapping")
            continue
        if not AGENT_ID.match(str(agent)):
            problems.append(f"`agents.{agent}`: định danh chỉ gồm a-z, 0-9, `-`")
        member = Member(
            id=str(agent),
            tool=str(raw.get("tool", "")),
            vendor=str(raw.get("vendor", "")).strip(),
            rank=str(raw.get("rank", "")),
            on_behalf_of=str(raw.get("on_behalf_of", "")),
            reports_to=str(raw.get("reports_to", "")),
            strengths=_strs(raw.get("strengths"), f"agents.{agent}.strengths", problems),
            wake=str(raw.get("wake", "")).strip(),
        )
        if member.tool not in TOOLS:
            problems.append(f"`agents.{agent}.tool`: `{member.tool}` không thuộc {', '.join(TOOLS)}")
        if member.rank not in RANKS:
            problems.append(f"`agents.{agent}.rank`: `{member.rank}` không thuộc {', '.join(RANKS)}")
        if not _ROLE.match(member.on_behalf_of):
            problems.append(f"`agents.{agent}.on_behalf_of`: cần vai trò người dạng R1, R2…")
        if not member.vendor:
            problems.append(f"`agents.{agent}.vendor`: cần nhà cung cấp mô hình (để chọn người review khác nhà)")
        if not member.wake:
            problems.append(f"`agents.{agent}.wake`: cần cách đánh thức agent khi có thư")
        members[member.id] = member

    coordinators = [m.id for m in members.values() if m.rank == "coordinator"]
    if len(coordinators) != 1:
        problems.append(f"cần đúng một agent `coordinator`, đang có {len(coordinators)}: {coordinators}")
    for member in members.values():
        if member.reports_to != "human" and member.reports_to not in members:
            problems.append(f"`agents.{member.id}.reports_to`: `{member.reports_to}` không phải `human` hay agent")
    for member in members.values():
        chain, cursor = [member.id], member.reports_to
        while cursor in members and cursor not in chain:
            chain.append(cursor)
            cursor = members[cursor].reports_to
        if cursor != "human":
            problems.append(f"`agents.{member.id}.reports_to`: chuỗi báo cáo {' → '.join(chain)} không tới `human`")

    routes: dict[str, Route] = {}
    for kind, raw in (data.get("routes") or {}).items():
        raw = raw if isinstance(raw, dict) else {}
        route = Route(str(kind), str(raw.get("primary", "")), raw.get("backup"), raw.get("review"))
        for field_name in ("primary", "backup", "review"):
            agent = getattr(route, field_name)
            if agent is None or (field_name == "review" and agent == "human"):
                continue
            if agent not in members:
                problems.append(f"`routes.{kind}.{field_name}`: `{agent}` — agent không có trong đội")
        if (
            route.review in members
            and route.primary in members
            and members[route.review].vendor == members[route.primary].vendor
        ):
            problems.append(f"`routes.{kind}.review`: người review phải khác nhà cung cấp với `{route.primary}`")
        routes[route.kind] = route

    ranks_raw = data.get("ranks") or {}
    ranks = {rank: _strs(ranks_raw.get(rank), f"ranks.{rank}", problems) for rank in RANKS}
    human_only = _strs(data.get("human_only"), "human_only", problems)
    if not human_only:
        problems.append("`human_only`: cần liệt kê việc chỉ người được làm")

    if problems:
        raise AgentctlError(f"{source}: " + "; ".join(problems))
    return Team(members=members, routes=routes, ranks=ranks, human_only=human_only)


def load_team(repo: Path, ref: str | None) -> Team | None:
    """Sổ đội tại `ref` (phân xử: `origin/main`); `ref=None` đọc cây làm việc. Không có sổ → `None`."""
    if ref is None:
        path = repo / TEAM_PATH
        text = path.read_text(encoding="utf-8") if path.is_file() else None
    else:
        text = show_file(repo, ref, TEAM_PATH)
    return None if text is None else parse_team(text, source=f"{TEAM_PATH}@{ref or 'cây làm việc'}")


def _bullets(items: tuple[str, ...], *, code: bool = False, empty: str = "(không có)") -> list[str]:
    return [f"- `{item}`" if code else f"- {item}" for item in items] or [f"- {empty}"]


def assignment_body(
    team: Team | None,
    ticket: Ticket,
    *,
    ticket_file: str,
    sender: str,
    recipient: str,
    msg_id: str,
    role: str,
    note: str,
) -> str:
    """Thư giao việc TỰ ĐỦ bối cảnh: người nhận chỉ cần thư này + repo, không cần người dùng chép prompt."""
    me = f"--as {recipient}"
    reply = f"python -m tools.agentctl mail reply {msg_id}"
    lines = [
        f"# Giao việc {ticket.id} — {ticket.title}",
        "",
        f"Người giao: `{sender}` · Người nhận: `{recipient}` · làm thay vai trò `{role}`.",
        "",
        "## Đọc trước",
        "- `AGENTS.md` (toàn bộ)",
        f"- `{ticket_file}`",
        *[f"- `{ref}`" for ref in ticket.design_refs],
        "",
        "## Phạm vi được sửa (`scope.allow`)",
        *_bullets(ticket.allow, code=True),
    ]
    if ticket.exclusive or ticket.protected:
        lines += [f"- làn độc quyền: {', '.join(ticket.exclusive) or '—'}"]
        lines += [f"- vùng bảo vệ đã duyệt: {', '.join(ticket.protected) or '—'}"]
    lines += ["", "## Tiêu chí nghiệm thu", *_bullets(ticket.acceptance)]
    if note.strip():
        lines += ["", "## Ghi chú của người giao", note.strip()]
    lines += [
        "",
        "## Không được làm (chỉ người làm — `coordination/team.yaml`)",
        *_bullets(team.human_only if team else ("đặt ticket `ready`", "gắn nhãn duyệt", "việc không hoàn tác được")),
        "",
        "## Các bước",
        f'1. Nhận việc: `{reply} --state working --subject "Bắt đầu {ticket.id}" {me}`',
        f"2. `python -m tools.agentctl start {ticket.id} --role {role}` rồi làm trong worktree nó tạo.",
        "3. Test trước, thấy ĐỎ rồi mới viết code; `python scripts/ci_local.py --fast`; "
        "`python -m tools.agentctl check-scope`.",
        "4. Commit `type(scope): mô tả (" + ticket.id + ")`, ghi `new log`. Không merge, không release, không đẩy "
        "lên remote mạng trừ khi người giao nói rõ.",
        f"5. Bị chặn hoặc cần người quyết: `new question ...` rồi `{reply} --state input-required "
        f'--subject "..." --body "đường dẫn câu hỏi" {me}`; làm tiếp phần không bị chặn.',
        f'6. Xong: `{reply} --state completed --subject "Xong {ticket.id}, commit <hash>" '
        f'--body "bằng chứng theo AGENTS.md §9" {me}`.',
        f"   Không làm được: `--state failed` hoặc `--state rejected` kèm lý do. Báo cho `{sender}`.",
    ]
    return "\n".join(lines) + "\n"
