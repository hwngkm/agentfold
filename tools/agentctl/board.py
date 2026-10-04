"""Bảng trạng thái SUY RA — không ai sửa tay, nên không bao giờ lệch sự thật và không sinh xung đột.

- `ready`        : ticket đã duyệt, chưa ai claim.
- `đang làm`     : có claim còn hạn.
- `claim quá hạn`: lease hết mà chưa release — agent có thể đã dừng giữa chừng.
- `đã merge`     : mã ticket xuất hiện trong lịch sử nhánh gốc.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TypeVar

from tools.agentctl.claims import Claim, ClaimRegistry
from tools.agentctl.entries import WORK_DIR
from tools.agentctl.errors import AgentctlError
from tools.agentctl.gitutil import list_files, show_file
from tools.agentctl.handoff import open_handoffs_on_branches
from tools.agentctl.lifecycle import load_context
from tools.agentctl.tickets import TicketError, load_ticket, merged_ticket_ids, split_front_matter

T = TypeVar("T")
#: Số thư AGENT-LOG gần nhất hiện ở bảng HTML.
MAIL_LIMIT = 20
TICKET_GROUPS = ("đang làm", "claim quá hạn", "ready", "proposed", "đã merge")


@dataclass(frozen=True)
class BoardItem:
    """Một dòng của bảng. `parts` là các mảnh nối bằng " · " — văn bản và HTML cùng dựng từ đây, không có logic thứ hai."""

    parts: tuple[str, ...]

    @property
    def text(self) -> str:
        return " · ".join(self.parts)


def _item(*parts: str) -> BoardItem:
    return BoardItem(tuple(parts))


@dataclass(frozen=True)
class Board:
    """Dữ liệu của bảng việc, độc lập cách hiển thị (văn bản `agentctl board`, HTML `scripts/render_board.py`)."""

    base_ref: str
    fetched: bool
    tickets: dict[str, list[BoardItem]]
    questions: list[BoardItem]
    plans: list[BoardItem]
    handoffs: list[BoardItem]
    broken: list[str] = field(default_factory=list)
    mail: list[BoardItem] = field(default_factory=list)


def _open_entries(
    repo: Path, base_ref: str, folder: str, describe: Callable[[dict, str], T], status: str = "open"
) -> list[T]:
    """Các mục có `status` đã cho (mặc định `open`) trong một thư mục của `docs/work/`, đọc từ nhánh gốc."""
    found: list[T] = []
    for path in list_files(repo, base_ref, f"{WORK_DIR}/{folder}/"):
        text = show_file(repo, base_ref, path)
        if not text or path.endswith("README.md"):
            continue
        try:
            data, _body = split_front_matter(text)
        except TicketError:
            continue
        if data.get("status") == status:
            found.append(describe(data, path))
    return found


def _recent_mail(repo: Path, policy_remote: str, mail_branch: str, *, fetch: bool) -> list[BoardItem]:
    """Thư AGENT-LOG gần nhất. Chưa có hộp thư hoặc không đọc được thì trả rỗng — bảng không được đổ vì phần phụ."""
    from tools.agentctl.mail import Mailbox

    try:
        messages = Mailbox(repo, remote=policy_remote, branch=mail_branch, offline=not fetch).messages()
    except AgentctlError:
        return []
    recent = sorted(messages, key=lambda m: (m.created, m.id), reverse=True)[:MAIL_LIMIT]
    return [
        _item(msg.created, f"{msg.sender} → {', '.join(msg.to)}", f"{msg.kind} · {msg.thread}", msg.subject)
        for msg in recent
    ]


def collect_board(repo: Path, *, fetch: bool, moment: datetime, with_mail: bool = False) -> Board:
    """Hàm dựng dữ liệu DUY NHẤT của bảng việc. `with_mail` chỉ cần cho bảng HTML (đọc thêm nhánh hộp thư)."""
    policy, base_ref = load_context(repo, fetch=fetch)
    registry = ClaimRegistry(repo, policy)
    claims: dict[str, Claim] = registry.read(registry.fetch() if fetch else registry.local_tip())
    merged = merged_ticket_ids(repo, base_ref)

    rows: dict[str, list[BoardItem]] = {name: [] for name in TICKET_GROUPS}
    broken: list[str] = []
    for path in list_files(repo, base_ref, f"{policy.tickets_dir}/"):
        name = path.rsplit("/", 1)[-1]
        if not name.endswith(".md") or name.startswith("_") or name == "README.md":
            continue
        try:
            ticket = load_ticket(repo, policy, name[:-3], base_ref)
        except TicketError as exc:
            broken.append(str(exc))
            continue
        if ticket is None or ticket.state == "cancelled":
            continue
        claim = claims.get(ticket.id)
        label = f"{ticket.id} — {ticket.title} [{ticket.owner_role}]"
        if claim and not claim.expired(moment):
            rows["đang làm"].append(_item(label, claim.on_behalf_of, f"`{claim.branch}`", f"hạn {claim.lease_until}"))
        elif claim:
            rows["claim quá hạn"].append(_item(label, claim.on_behalf_of, f"hết hạn {claim.lease_until}"))
        elif ticket.id in merged:
            rows["đã merge"].append(_item(label))
        else:
            rows[ticket.state].append(_item(label))

    questions = _open_entries(
        repo,
        base_ref,
        "questions",
        lambda data, path: _item(
            f"{data.get('id', path)} → {data.get('answer_by', '?')}", f"chặn {data.get('blocking') or []}"
        ),
    )
    plans = _open_entries(
        repo,
        base_ref,
        "plans",
        lambda data, path: _item(
            str(data.get("id", path)), f"ticket {data.get('ticket', '?')}", f"soạn bởi {data.get('author_role', '?')}"
        ),
        status="proposed",
    )
    handoffs = _open_entries(
        repo,
        base_ref,
        "handoffs",
        lambda data, path: _item(
            str(data.get("id", path)),
            f"từ {data.get('from_role', '?')}",
            f"ticket {data.get('ticket') or '—'}",
            f"nhánh `{data.get('branch', '?')}` @ {data.get('head', '?')}",
        ),
    )
    handoffs += [
        _item(
            hid,
            f"từ {data.get('from_role', '?')}",
            f"ticket {data.get('ticket') or '—'}",
            f"chưa merge, trên `{ref}` @ {data.get('head', '?')}",
        )
        for hid, data, ref in open_handoffs_on_branches(
            repo, remote=policy.remote, base_ref=base_ref, claims_branch=policy.claims_branch, fetch=fetch
        )
    ]
    mail = _recent_mail(repo, policy.remote, policy.mail_branch, fetch=fetch) if with_mail else []
    return Board(base_ref, fetch, rows, questions, plans, handoffs, broken, mail)


def render_text(board: Board) -> str:
    """Hiển thị văn bản (`agentctl board`). Không in thư AGENT-LOG: đầu ra văn bản giữ nguyên như trước khi tách hàm."""
    lines = [f"Bảng công việc tại `{board.base_ref}`" + ("" if board.fetched else " (chưa kéo mới)")]
    for title, items in board.tickets.items():
        lines.append(f"\n## {title} ({len(items)})")
        lines += [f"- {item.text}" for item in items] or ["- (trống)"]
    lines.append(f"\n## câu hỏi đang mở ({len(board.questions)})")
    lines += [f"- {item.text}" for item in board.questions] or ["- (trống)"]
    lines.append(f"\n## kế hoạch chờ duyệt ({len(board.plans)}) — chưa viết mã khi chưa `approved`")
    lines += [f"- {item.text}" for item in board.plans] or ["- (trống)"]
    lines.append(f"\n## bàn giao đang chờ người nhận ({len(board.handoffs)}) — đọc trước khi làm tiếp")
    lines += [f"- {item.text}" for item in board.handoffs] or ["- (trống)"]
    if board.broken:
        lines.append(f"\n## ticket hỏng ({len(board.broken)}) — sửa trước khi ai claim")
        lines += [f"- {item}" for item in board.broken]
    return "\n".join(lines)


def render_board(repo: Path, *, fetch: bool, moment: datetime) -> str:
    return render_text(collect_board(repo, fetch=fetch, moment=moment))
