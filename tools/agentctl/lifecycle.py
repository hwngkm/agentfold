"""Vòng đời một claim: start/claim → renew → release; reap dọn lease hết hạn.

Mọi quyết định đọc ticket và chính sách từ NHÁNH GỐC đã kéo mới (`origin/main`), không từ cây làm
việc: agent không thể tự nới phạm vi của mình bằng cách sửa ticket cục bộ rồi claim.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from tools.agentctl.claims import Claim, ClaimRefusedError, ClaimRegistry, Update, claim_file, find_conflicts, new_lease
from tools.agentctl.clock import iso
from tools.agentctl.entries import slugify
from tools.agentctl.errors import AgentctlError
from tools.agentctl.gitutil import git, repo_root, resolve, run_git
from tools.agentctl.policy import POLICY_PATH, Policy, load_policy
from tools.agentctl.tickets import Ticket, load_ticket, merged_ticket_ids

WORKTREES_DIR = ".worktrees"


@dataclass(frozen=True)
class ClaimRequest:
    ticket_id: str
    role: str
    session: str
    branch: str | None = None
    hours: int | None = None
    allow_unmerged_deps: bool = False


def load_context(repo: Path, *, fetch: bool) -> tuple[Policy, str]:
    """Chính sách tại nhánh gốc. Tên remote/nhánh gốc lấy từ bản cục bộ, còn nội dung phân xử lấy từ gốc."""
    local = load_policy(repo, None) if (repo / POLICY_PATH).is_file() else None
    remote = local.remote if local else "origin"
    base_branch = local.base_branch if local else "main"
    base_ref = f"{remote}/{base_branch}"
    if fetch:
        result = run_git(repo, ["fetch", "--no-tags", remote, f"+refs/heads/{base_branch}:refs/remotes/{base_ref}"])
        if result.returncode != 0:
            raise AgentctlError(f"không kéo được `{base_ref}`: {result.stderr.strip()}")
    if resolve(repo, base_ref) is None:
        raise AgentctlError(f"không thấy `{base_ref}` — repo chưa có remote `{remote}` hoặc chưa fetch")
    return load_policy(repo, base_ref), base_ref


def branch_for(ticket: Ticket) -> str:
    return f"feature/{ticket.id}-{slugify(ticket.title)}"


def _ready_ticket(repo: Path, policy: Policy, base_ref: str, request: ClaimRequest) -> Ticket:
    ticket = load_ticket(repo, policy, request.ticket_id, base_ref)
    if ticket is None:
        raise ClaimRefusedError(
            f"ticket `{request.ticket_id}` không có trên `{base_ref}` — kế hoạch phải được merge (người duyệt) "
            "trước khi claim. Ticket chỉ nằm ở nhánh của bạn thì chưa phải kế hoạch đã duyệt."
        )
    if ticket.state != "ready":
        raise ClaimRefusedError(
            f"ticket `{ticket.id}` đang `{ticket.state}` — chỉ claim được ticket `ready`, trạng thái do người duyệt đặt"
        )
    missing = [dep for dep in ticket.depends_on if dep not in merged_ticket_ids(repo, base_ref)]
    if missing and not request.allow_unmerged_deps:
        raise ClaimRefusedError(
            f"`{ticket.id}` phụ thuộc {missing} nhưng chưa thấy chúng merge vào `{base_ref}`. "
            "Nếu người điều phối đã xác nhận phụ thuộc không chặn, chạy lại với `--allow-unmerged-deps`."
        )
    return ticket


def claim_ticket(repo: Path, request: ClaimRequest, moment: datetime) -> tuple[Claim, tuple[str, ...]]:
    policy, base_ref = load_context(repo, fetch=True)
    ticket = _ready_ticket(repo, policy, base_ref, request)
    branch = request.branch or branch_for(ticket)
    candidate = Claim(
        ticket=ticket.id,
        on_behalf_of=request.role,
        session=request.session,
        branch=branch,
        claimed_at=iso(moment),
        lease_until=new_lease(moment, request.hours or policy.lease_default_hours, policy),
        allow=ticket.allow,
        exclusive=ticket.exclusive,
        protected=ticket.protected,
    )
    final: list[Claim] = []

    def decide(claims: dict[str, Claim]) -> Update:
        notes: list[str] = []
        chosen = candidate
        current = claims.get(ticket.id)
        if current and not current.expired(moment):
            if current.branch != branch:
                raise ClaimRefusedError(
                    f"`{ticket.id}` đang được {current.on_behalf_of} giữ trên nhánh `{current.branch}` "
                    f"tới {current.lease_until}"
                )
            chosen = dataclasses.replace(candidate, claimed_at=current.claimed_at)
            notes.append("claim đã có trên cùng nhánh — chỉ gia hạn lease")
        elif current:
            notes.append(f"claim cũ của {current.on_behalf_of} đã hết hạn {current.lease_until} — tiếp quản")
        active = [c for c in claims.values() if c.ticket != ticket.id and not c.expired(moment)]
        conflicts = find_conflicts(chosen, active, policy)
        if conflicts:
            raise ClaimRefusedError(
                f"không claim được `{ticket.id}` — phạm vi đang có người giữ:\n  - "
                + "\n  - ".join(conflict.describe() for conflict in conflicts)
                + "\nXử lý: chờ họ release, chọn ticket khác, hoặc mở câu hỏi nhờ người lập kế hoạch tách phạm vi."
            )
        final[:] = [chosen]
        return Update(
            {claim_file(ticket.id): chosen.to_json()}, f"claim {ticket.id} ({request.role}, {branch})", tuple(notes)
        )

    update = ClaimRegistry(repo, policy).update(decide)
    return final[0], update.notes if update else ()


def _owned(claims: dict[str, Claim], ticket_id: str, branch: str | None, override_reason: str | None) -> Claim:
    current = claims.get(ticket_id)
    if current is None:
        raise AgentctlError(f"sổ không có claim nào cho `{ticket_id}`")
    if current.branch != branch and not override_reason:
        raise ClaimRefusedError(
            f"claim `{ticket_id}` thuộc nhánh `{current.branch}`, bạn đang ở `{branch}`. Chạy từ đúng worktree; "
            'người điều phối dọn claim bỏ dở thì dùng `--override --reason "..."`.'
        )
    return current


def renew_claim(repo: Path, ticket_id: str, branch: str | None, hours: int | None, moment: datetime) -> Claim:
    policy, _ = load_context(repo, fetch=True)
    renewed: list[Claim] = []

    def decide(claims: dict[str, Claim]) -> Update:
        current = _owned(claims, ticket_id, branch, None)
        lease = new_lease(moment, hours or policy.lease_default_hours, policy)
        renewed[:] = [dataclasses.replace(current, lease_until=lease)]
        return Update({claim_file(ticket_id): renewed[0].to_json()}, f"renew {ticket_id} tới {lease}")

    ClaimRegistry(repo, policy).update(decide)
    return renewed[0]


def release_claim(repo: Path, ticket_id: str, branch: str | None, override_reason: str | None) -> Claim:
    policy, _ = load_context(repo, fetch=True)
    released: list[Claim] = []

    def decide(claims: dict[str, Claim]) -> Update:
        released[:] = [_owned(claims, ticket_id, branch, override_reason)]
        suffix = f" (override: {override_reason})" if override_reason and released[0].branch != branch else ""
        return Update({claim_file(ticket_id): None}, f"release {ticket_id}{suffix}")

    ClaimRegistry(repo, policy).update(decide)
    return released[0]


def reap_expired(repo: Path, moment: datetime) -> list[Claim]:
    policy, _ = load_context(repo, fetch=True)
    reaped: list[Claim] = []

    def decide(claims: dict[str, Claim]) -> Update | None:
        reaped[:] = sorted((c for c in claims.values() if c.expired(moment)), key=lambda c: c.ticket)
        if not reaped:
            return None
        return Update({claim_file(c.ticket): None for c in reaped}, "reap " + ", ".join(c.ticket for c in reaped))

    ClaimRegistry(repo, policy).update(decide)
    return reaped


def main_worktree_root(repo: Path) -> Path:
    """Gốc checkout chính — để worktree mới không bị lồng trong worktree của agent khác."""
    common = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    common_path = Path(common)
    return common_path.parent if common_path.name == ".git" else repo


def project_prefix(repo: Path) -> str:
    """Vị trí dự án trong repo (rỗng nếu dự án là gốc repo) — dùng để trỏ đúng thư mục trong worktree mới."""
    return repo.resolve().relative_to(repo_root(repo).resolve()).as_posix().strip(".")


def create_worktree(repo: Path, claim: Claim, base_ref: str) -> tuple[Path, bool]:
    """Tạo worktree cho nhánh của claim; trả về thư mục DỰ ÁN bên trong worktree đó.

    `--no-track`: nhánh mới KHÔNG nhận `main` làm upstream — nếu nhận, một lệnh `git push` trần với
    `push.default=upstream` sẽ đẩy thẳng vào `main`.
    """
    prefix = project_prefix(repo)
    base_dir = main_worktree_root(repo) / prefix if prefix else main_worktree_root(repo)
    path = base_dir / WORKTREES_DIR / claim.ticket
    project_dir = path / prefix if prefix else path
    if path.exists():
        return project_dir, False
    if resolve(repo, f"refs/heads/{claim.branch}"):
        git(repo, "worktree", "add", str(path), claim.branch)
    else:
        git(repo, "worktree", "add", "--no-track", "-b", claim.branch, str(path), base_ref)
    return project_dir, True
