"""Sổ claim: ai đang làm ticket nào, giữ phạm vi nào — lưu trên một nhánh git mồ côi.

Vì sao là nhánh git, không phải GitHub Issues hay một file trong `main`
---------------------------------------------------------------------
- **Nguyên tử.** `git push` từ chối lần đẩy không fast-forward, nên cập nhật ref là một phép
  so-sánh-rồi-ghi (CAS). Hai agent claim cùng lúc: đúng một lần đẩy thắng; lần kia bị từ chối, đọc
  lại sổ, và thấy claim của người thắng trước khi quyết định tiếp.
- **Không phụ thuộc nhà cung cấp.** Chạy trên mọi git host, với mọi agent có quyền push — không
  token API, không dịch vụ ngoài.
- **Không đụng cây làm việc.** Chỉ dùng plumbing (`read-tree`, `hash-object`, `commit-tree`) trên
  một index tạm. Không `checkout`, không `stash` — đúng loại lệnh từng xoá việc chưa commit của một
  phiên agent song song (đã gặp thật).
- **Không sinh xung đột trên `main`.** Claim sống ngoài `main`, nên không PR nào phải mang nó.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from tools.agentctl.clock import iso, parse_iso
from tools.agentctl.errors import AgentctlError
from tools.agentctl.gitutil import GitError, git, identity_env, list_files, resolve, run_git
from tools.agentctl.globs import may_overlap
from tools.agentctl.policy import Policy

CLAIMS_DIR = "claims"
_MAX_ATTEMPTS = 5
_MAX_REASONS = 6


class ClaimRefusedError(AgentctlError):
    """Claim bị từ chối vì chồng phạm vi, trùng làn, hoặc ticket đang có người giữ."""


@dataclass(frozen=True)
class Claim:
    ticket: str
    on_behalf_of: str
    session: str
    branch: str
    claimed_at: str
    lease_until: str
    allow: tuple[str, ...] = ()
    exclusive: tuple[str, ...] = ()
    protected: tuple[str, ...] = ()

    def expired(self, moment: datetime) -> bool:
        return parse_iso(self.lease_until) <= moment

    def patterns(self, policy: Policy) -> tuple[str, ...]:
        """Mọi mẫu đường dẫn claim này giữ: scope + đường dẫn của làn và vùng đã được duyệt trước."""
        return self.allow + policy.paths_of(lanes=self.exclusive, zones=self.protected)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_json(cls, text: str, *, source: str) -> Claim:
        try:
            data: dict[str, Any] = json.loads(text)
            return cls(
                ticket=str(data["ticket"]),
                on_behalf_of=str(data["on_behalf_of"]),
                session=str(data["session"]),
                branch=str(data["branch"]),
                claimed_at=str(data["claimed_at"]),
                lease_until=str(data["lease_until"]),
                allow=tuple(data.get("allow", ())),
                exclusive=tuple(data.get("exclusive", ())),
                protected=tuple(data.get("protected", ())),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise AgentctlError(f"claim hỏng ở `{source}`: {exc}") from exc


@dataclass(frozen=True)
class Conflict:
    other: Claim
    reasons: tuple[str, ...]

    def describe(self) -> str:
        return (
            f"`{self.other.ticket}` (giữ bởi {self.other.on_behalf_of}, nhánh `{self.other.branch}`, "
            f"hết hạn {self.other.lease_until}): " + "; ".join(self.reasons)
        )


@dataclass(frozen=True)
class Update:
    """Kết quả một lần sửa sổ: file cần ghi (`None` = xoá) và thông điệp commit."""

    changes: Mapping[str, str | None]
    message: str
    notes: tuple[str, ...] = field(default_factory=tuple)


def claim_file(ticket_id: str) -> str:
    return f"{CLAIMS_DIR}/{ticket_id}.json"


def find_conflicts(candidate: Claim, others: Iterable[Claim], policy: Policy) -> list[Conflict]:
    mine = candidate.patterns(policy)
    conflicts: list[Conflict] = []
    for other in others:
        reasons = [
            f"cùng giữ làn độc quyền `{lane}`" for lane in sorted(set(candidate.exclusive) & set(other.exclusive))
        ]
        reasons += [
            f"cùng giữ vùng bảo vệ `{zone}`" for zone in sorted(set(candidate.protected) & set(other.protected))
        ]
        theirs = other.patterns(policy)
        reasons += [f"`{a}` chồng `{b}`" for a in mine for b in theirs if may_overlap(a, b)]
        if reasons:
            unique = tuple(dict.fromkeys(reasons))
            conflicts.append(Conflict(other, unique[:_MAX_REASONS]))
    return conflicts


def new_lease(moment: datetime, hours: int, policy: Policy) -> str:
    if hours <= 0 or hours > policy.lease_max_hours:
        raise AgentctlError(f"lease phải trong khoảng 1..{policy.lease_max_hours} giờ (chính sách), nhận {hours}")
    return iso(moment + timedelta(hours=hours))


class ClaimRegistry:
    def __init__(self, repo: Path, policy: Policy) -> None:
        self.repo = repo
        self.policy = policy
        self.tracking_ref = f"refs/remotes/{policy.remote}/{policy.claims_branch}"

    def fetch(self) -> str | None:
        """Kéo sổ mới nhất. Trả về commit đầu sổ, hoặc `None` nếu sổ chưa từng được tạo."""
        branch = self.policy.claims_branch
        result = run_git(
            self.repo, ["fetch", "--no-tags", self.policy.remote, f"+refs/heads/{branch}:{self.tracking_ref}"]
        )
        if result.returncode != 0:
            if "couldn't find remote ref" in result.stderr.lower():
                return None
            raise GitError(f"không kéo được sổ claim `{branch}`: {result.stderr.strip()}")
        return resolve(self.repo, self.tracking_ref)

    def local_tip(self) -> str | None:
        """Đầu sổ theo lần kéo gần nhất — dùng khi không được phép gọi mạng (hook)."""
        return resolve(self.repo, self.tracking_ref)

    def read(self, tip: str | None) -> dict[str, Claim]:
        if tip is None:
            return {}
        claims: dict[str, Claim] = {}
        # `full_tree`: sổ claim nằm ở GỐC nhánh mồ côi, không phụ thuộc dự án nằm ở thư mục nào.
        for path in list_files(self.repo, tip, f"{CLAIMS_DIR}/", full_tree=True):
            if path.endswith(".json"):
                claim = Claim.from_json(git(self.repo, "show", f"{tip}:{path}"), source=path)
                claims[claim.ticket] = claim
        return claims

    def _commit(self, parent: str | None, changes: Mapping[str, str | None], message: str) -> str:
        handle, index_file = tempfile.mkstemp(prefix="agentctl-index-")
        os.close(handle)
        os.unlink(index_file)  # git tự tạo index; một file rỗng sẵn có sẽ bị coi là index hỏng
        env = {"GIT_INDEX_FILE": index_file, **identity_env(self.repo)}
        try:
            git(self.repo, "read-tree", *([parent] if parent else ["--empty"]), env=env)
            for path, content in sorted(changes.items()):
                if content is None:
                    git(self.repo, "update-index", "--force-remove", "--", path, env=env)
                    continue
                blob = git(self.repo, "hash-object", "-w", "--stdin", input_text=content).strip()
                git(self.repo, "update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
            tree = git(self.repo, "write-tree", env=env).strip()
            return git(
                self.repo, "commit-tree", tree, *(["-p", parent] if parent else []), "-m", message, env=env
            ).strip()
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(index_file)

    def _push(self, commit: str) -> bool:
        """`True` nếu ghi được; `False` nếu bị từ chối vì có người vừa ghi trước (cần đọc lại)."""
        target = f"refs/heads/{self.policy.claims_branch}"
        result = run_git(self.repo, ["push", "--quiet", self.policy.remote, f"{commit}:{target}"])
        if result.returncode == 0:
            git(self.repo, "update-ref", self.tracking_ref, commit)
            return True
        if "rejected" in result.stderr or "fetch first" in result.stderr or "non-fast-forward" in result.stderr:
            return False
        raise GitError(f"không đẩy được sổ claim: {result.stderr.strip()}")

    def update(self, decide: Callable[[dict[str, Claim]], Update | None]) -> Update | None:
        """Đọc sổ → quyết định → ghi. Bị từ chối vì ghi đồng thời thì đọc lại và QUYẾT ĐỊNH LẠI từ đầu.

        `decide` được gọi lại mỗi lần thử, trên sổ mới nhất — nên một quyết định "không chồng" không
        bao giờ được ghi dựa trên một bản sổ đã cũ.
        """
        for _attempt in range(_MAX_ATTEMPTS):
            tip = self.fetch()
            update = decide(self.read(tip))
            if update is None or not update.changes:
                return update
            if self._push(self._commit(tip, update.changes, update.message)):
                return update
        raise AgentctlError(f"không ghi được sổ claim sau {_MAX_ATTEMPTS} lần — sổ đang bị ghi liên tục, thử lại sau")
