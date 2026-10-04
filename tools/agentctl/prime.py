"""`python -m tools.agentctl prime` — bối cảnh đầu phiên trong MỘT lệnh, cho mọi agent và mọi công cụ.

In: luật tối cao (rút từ AGENTS.md §2), vị trí git, ticket + claim của nhánh hiện tại, thư AGENT-LOG chưa xử lý,
bàn giao đang chờ, skill đang bật, và bước tiếp theo. Mỗi phần tự bắt lỗi của mình: repo chưa có remote, chưa có policy
hay chưa có hộp thư thì phần đó ghi "(không đọc được: …)" và các phần khác vẫn in — một lệnh mồi bối cảnh không được
làm đứng phiên. Claude Code gọi lệnh này ở hook `SessionStart`; công cụ khác chạy theo AGENTS.md §1.

Ý tưởng mượn từ `bd prime` (gastownhall/beads).
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from tools.agentctl.errors import AgentctlError
from tools.agentctl.gitutil import current_branch, run_git
from tools.agentctl.handoff import collect_facts, open_handoffs_on_branches
from tools.agentctl.tickets import ticket_id_from_branch

_RULE = re.compile(r"^\d+\. \*\*(.+?)\*\*")
_SKILL_ROW = re.compile(r"^\| `([^`]+)` \| ([^|]+) \|")
MAX_ITEMS = 6
ENV_FIX = "bash scripts/cloud_setup.sh"
ENV_TOOLS = ("pytest", "ruff", "mypy")


def _rules(repo: Path) -> list[str]:
    path = repo / "AGENTS.md"
    if not path.is_file():
        return ["(không có AGENTS.md)"]
    text = path.read_text(encoding="utf-8")
    start = text.find("\n## 2.")
    end = text.find("\n## ", start + 5)
    section = text[start:end] if start >= 0 else ""
    return [m.group(1) for line in section.splitlines() if (m := _RULE.match(line.strip()))] or [
        "(AGENTS.md không có mục §2)"
    ]


def _position(repo: Path) -> list[str]:
    facts = collect_facts(repo)
    log = run_git(repo, ["log", "--oneline", "-3"]).stdout.strip().splitlines()
    return [
        f"nhánh `{facts['branch']}` @ {facts['head']} — {facts['dirty_count']} tệp chưa commit",
        *[f"  {line}" for line in log],
    ]


def _work(repo: Path, fetch: bool) -> tuple[list[str], str]:
    """Trả (dòng mô tả, bước tiếp theo)."""
    from tools.agentctl.claims import ClaimRegistry
    from tools.agentctl.lifecycle import load_context
    from tools.agentctl.tickets import load_ticket

    branch = current_branch(repo)
    ticket_id = ticket_id_from_branch(branch) if branch else None
    if not ticket_id:
        return [
            "nhánh không gắn ticket"
        ], "`python -m tools.agentctl board` để chọn việc `ready`, rồi `agentctl start <ID> --role Rn`"
    policy, base_ref = load_context(repo, fetch=fetch)
    ticket = load_ticket(repo, policy, ticket_id, base_ref)
    if ticket is None:
        return [f"{ticket_id}: không có trên `{base_ref}`"], "ticket phải được merge (`state: ready`) trước khi làm"
    lines = [f"{ticket.id} — {ticket.title} [{ticket.state}]", *[f"  ✓? {a}" for a in ticket.acceptance]]
    registry = ClaimRegistry(repo, policy)
    claim = registry.read(registry.fetch() if fetch else registry.local_tip()).get(ticket.id)
    if claim is None:
        lines.append("chưa có claim")
        return lines, f"`python -m tools.agentctl start {ticket.id} --role <Rn>` (hoặc `claim` nếu đã ở đúng nhánh)"
    lines.append(f"claim: {claim.on_behalf_of} · hạn {claim.lease_until}")
    return lines, "đọc tiêu chí ở trên → viết test trước → `make check-fast` trước mỗi commit"


def _mail(repo: Path, agent: str | None, fetch: bool) -> list[str]:
    if not agent:
        return ["chưa đặt định danh — đặt AGENTCTL_AGENT (vd. codex-1) hoặc `--as` để đọc hộp thư"]
    from tools.agentctl.mail_cli import mailbox

    msgs = mailbox(repo, offline=not fetch).inbox(agent)
    lines = [f"{len(msgs)} thư chưa xác nhận cho `{agent}`"]
    for msg in msgs[:MAX_ITEMS]:
        ack = " ✋cần xác nhận" if msg.ack_required else ""
        lines.append(f"  {msg.id} · {msg.sender} · {msg.kind} · {msg.subject}{ack}")
    return lines


def _handoffs(repo: Path, fetch: bool) -> list[str]:
    from tools.agentctl.board import _open_entries
    from tools.agentctl.lifecycle import load_context

    policy, base_ref = load_context(repo, fetch=fetch)
    items = _open_entries(repo, base_ref, "handoffs", lambda data, path: f"{data.get('id', path)} (main)")
    items += [
        f"{hid} (nhánh `{ref}`)"
        for hid, _data, ref in open_handoffs_on_branches(
            repo, remote=policy.remote, base_ref=base_ref, claims_branch=policy.claims_branch, fetch=fetch
        )
    ]
    return items[:MAX_ITEMS] or ["(không có)"]


def _skills(repo: Path) -> list[str]:
    path = repo / "SKILLS.md"
    if not path.is_file():
        return ["(chưa có SKILLS.md)"]
    rows = [m.group(1) for line in path.read_text(encoding="utf-8").splitlines() if (m := _SKILL_ROW.match(line))]
    return [f"{len(rows)} skill: {', '.join(rows)} — mục lục + cách làm khi thiếu MCP/plugin: SKILLS.md"]


def environment_problems(repo: Path) -> list[str]:
    """Môi trường chưa dựng: hook git không chạy, thiếu công cụ kiểm. Chỉ ĐỌC, không sửa gì."""
    problems: list[str] = []
    if not run_git(repo, ["config", "--get", "core.hooksPath"]).stdout.strip():
        problems.append(
            "`core.hooksPath` rỗng — hook git KHÔNG chạy, phạm vi và định dạng commit không được kiểm cục bộ"
        )
    missing = [name for name in ENV_TOOLS if importlib.util.find_spec(name) is None]
    if missing:
        problems.append(f"thiếu công cụ kiểm: {', '.join(missing)}")
    return problems


def _environment(repo: Path) -> list[str]:
    problems = environment_problems(repo)
    if not problems:
        return ["đã dựng (hook git bật, đủ pytest/ruff/mypy)"]
    return [*problems, f"sửa bằng ĐÚNG MỘT lệnh: `{ENV_FIX}` (hoặc chạy lại `prime --fix-env`)"]


def fix_environment(repo: Path) -> int:
    """Chạy script dựng môi trường. Chỉ gọi khi người cho phép (`prime --fix-env`); không bao giờ tự chạy."""
    return subprocess.run(["bash", "scripts/cloud_setup.sh"], cwd=repo, check=False).returncode


def _safe(section: Callable[[], list[str]]) -> list[str]:
    try:
        return section()
    except (AgentctlError, OSError, ValueError) as exc:
        return [f"(không đọc được: {exc})"]


def render_prime(repo: Path, *, agent: str | None, fetch: bool, moment: datetime) -> str:
    try:
        work, next_step = _work(repo, fetch)
    except (AgentctlError, OSError, ValueError) as exc:
        work, next_step = [f"(không đọc được: {exc})"], "`git log --oneline -10 && git status`, rồi đọc AGENTS.md"
    blocks = [
        ("Luật tối cao (AGENTS.md §2 — đọc đủ file khi chưa đọc)", _safe(lambda: _rules(repo))),
        ("Môi trường", _safe(lambda: _environment(repo))),
        ("Vị trí", _safe(lambda: _position(repo))),
        ("Việc của nhánh này", work),
        ("Hộp thư AGENT-LOG", _safe(lambda: _mail(repo, agent, fetch))),
        ("Bàn giao đang chờ người nhận", _safe(lambda: _handoffs(repo, fetch))),
        ("Kỹ năng", _safe(lambda: _skills(repo))),
        ("Bước tiếp theo", [next_step]),
    ]
    out = [f"# agentctl prime — {moment.strftime('%Y-%m-%d %H:%M')} UTC"]
    for title, lines in blocks:
        out.append(f"\n## {title}")
        out += [f"- {line}" if not line.startswith("  ") else line for line in lines]
    return "\n".join(out)
