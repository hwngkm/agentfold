"""Đọc và kiểm `coordination/policy.yaml` — nguồn sự thật về vùng bảo vệ và làn độc quyền.

Khi phân xử (claim, check-scope trên CI), chính sách luôn được đọc từ NHÁNH GỐC (`origin/main`),
không từ nhánh đang làm. Một PR tự nới chính sách của mình không có hiệu lực cho chính nó: bên bị
kiểm không được cầm bộ kiểm.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.agentctl.errors import AgentctlEnvironmentError, AgentctlError
from tools.agentctl.gitutil import POLICY_PATH, show_file
from tools.agentctl.globs import matches_any, matches_everything, may_overlap

try:
    import yaml
except ImportError as exc:  # phụ thuộc môi trường, không phải lỗi logic
    raise AgentctlEnvironmentError("thiếu PyYAML — chạy `python -m pip install -r requirements-dev.txt`") from exc

_ID = re.compile(r"^[a-z][a-z0-9-]{1,40}$")
#: Bẫy YAML hay gặp nhất khi viết mẫu đường dẫn: `*` đứng đầu giá trị là cú pháp alias.
YAML_STAR_HINT = 'mẫu bắt đầu bằng `*` phải đặt trong ngoặc kép, vd. `- "**/*.md"`'


def yaml_error_message(where: str, exc: Exception) -> str:
    hint = f" — gợi ý: {YAML_STAR_HINT}" if "alias" in str(exc) else ""
    return f"{where} không phải YAML hợp lệ{hint}: {exc}"


class PolicyError(AgentctlError):
    """`policy.yaml` sai cấu trúc hoặc tự mâu thuẫn."""


@dataclass(frozen=True)
class ProtectedZone:
    """Vùng do con người sở hữu: sửa phải được duyệt (nhãn PR hoặc ticket đã duyệt trước)."""

    id: str
    paths: tuple[str, ...]
    owners: tuple[str, ...]
    why: str
    allow_additions: bool

    def covers(self, path: str) -> bool:
        return matches_any(path, self.paths)


@dataclass(frozen=True)
class ExclusiveLane:
    """Tài nguyên chỉ một ticket được giữ tại một thời điểm (migration, lockfile, hợp đồng API...)."""

    id: str
    paths: tuple[str, ...]
    why: str

    def covers(self, path: str) -> bool:
        return matches_any(path, self.paths)


@dataclass(frozen=True)
class Policy:
    remote: str
    base_branch: str
    claims_branch: str
    tickets_dir: str
    human_approval_label: str
    lease_default_hours: int
    lease_max_hours: int
    always_allowed: tuple[str, ...]
    protected: tuple[ProtectedZone, ...]
    exclusive: tuple[ExclusiveLane, ...]
    #: Nhánh mồ côi chứa hộp thư AGENT-LOG (docs/AGENT-LOG.md). Mặc định khi policy không khai.
    mail_branch: str = "agent-mail"

    @property
    def base_ref(self) -> str:
        return f"{self.remote}/{self.base_branch}"

    def zones_for(self, path: str) -> list[ProtectedZone]:
        return [zone for zone in self.protected if zone.covers(path)]

    def lanes_for(self, path: str) -> list[ExclusiveLane]:
        return [lane for lane in self.exclusive if lane.covers(path)]

    def zone(self, zone_id: str) -> ProtectedZone | None:
        return next((zone for zone in self.protected if zone.id == zone_id), None)

    def lane(self, lane_id: str) -> ExclusiveLane | None:
        return next((lane for lane in self.exclusive if lane.id == lane_id), None)

    def paths_of(self, *, lanes: Iterable[str] = (), zones: Iterable[str] = ()) -> tuple[str, ...]:
        found: list[str] = []
        for lane_id in lanes:
            lane = self.lane(lane_id)
            found.extend(lane.paths if lane else ())
        for zone_id in zones:
            zone = self.zone(zone_id)
            found.extend(zone.paths if zone else ())
        return tuple(found)


def _text(data: dict[str, Any], key: str, where: str, problems: list[str], default: str | None = None) -> str:
    value = data.get(key, default)
    if not isinstance(value, str) or not value.strip():
        problems.append(f"{where}.{key}: cần chuỗi không rỗng")
        return ""
    return value.strip()


def _texts(value: Any, where: str, problems: list[str], *, allow_empty: bool = True) -> tuple[str, ...]:
    if value is None:
        value = []
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        problems.append(f"{where}: cần danh sách chuỗi không rỗng")
        return ()
    if not allow_empty and not value:
        problems.append(f"{where}: không được rỗng")
    return tuple(item.strip() for item in value)


def _positive_int(value: Any, where: str, problems: list[str]) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        problems.append(f"{where}: cần số nguyên dương")
        return 1
    return value


def _zones(raw: Any, problems: list[str]) -> tuple[ProtectedZone, ...]:
    zones: list[ProtectedZone] = []
    for index, item in enumerate(raw if isinstance(raw, list) else []):
        where = f"protected[{index}]"
        if not isinstance(item, dict):
            problems.append(f"{where}: cần mapping")
            continue
        additions = item.get("allow_additions", False)
        if not isinstance(additions, bool):
            problems.append(f"{where}.allow_additions: cần true/false")
        zones.append(
            ProtectedZone(
                id=_text(item, "id", where, problems),
                paths=_texts(item.get("paths"), f"{where}.paths", problems, allow_empty=False),
                owners=_texts(item.get("owners"), f"{where}.owners", problems, allow_empty=False),
                why=_text(item, "why", where, problems),
                allow_additions=additions is True,
            )
        )
    return tuple(zones)


def _lanes(raw: Any, problems: list[str]) -> tuple[ExclusiveLane, ...]:
    lanes: list[ExclusiveLane] = []
    for index, item in enumerate(raw if isinstance(raw, list) else []):
        where = f"exclusive[{index}]"
        if not isinstance(item, dict):
            problems.append(f"{where}: cần mapping")
            continue
        lanes.append(
            ExclusiveLane(
                id=_text(item, "id", where, problems),
                paths=_texts(item.get("paths"), f"{where}.paths", problems, allow_empty=False),
                why=_text(item, "why", where, problems),
            )
        )
    return tuple(lanes)


def _check_consistency(policy: Policy, problems: list[str]) -> None:
    ids = [zone.id for zone in policy.protected] + [lane.id for lane in policy.exclusive]
    for duplicate in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append(f"id `{duplicate}` bị dùng hai lần (id vùng và id làn phải khác nhau)")
    for item_id in ids:
        if item_id and not _ID.match(item_id):
            problems.append(f"id `{item_id}` phải dạng chữ thường-gạch-nối")
    if len({policy.base_branch, policy.claims_branch, policy.mail_branch}) < 3:
        problems.append("base_branch, claims_branch, mail_branch phải là ba nhánh khác nhau")
    if policy.lease_default_hours > policy.lease_max_hours:
        problems.append("lease.default_hours lớn hơn lease.max_hours")
    everything = [p for p in policy.always_allowed if matches_everything(p)]
    if everything:
        problems.append(f"always_allowed chứa mẫu phủ cả repo {everything} — vô hiệu hoá mọi kiểm phạm vi")
    # Một đường dẫn vừa thuộc làn độc quyền vừa thuộc vùng bảo vệ thì không rõ luật nào áp — cấm luôn.
    for lane in policy.exclusive:
        for zone in policy.protected:
            pairs = [(a, b) for a in lane.paths for b in zone.paths if may_overlap(a, b)]
            if pairs:
                problems.append(f"làn `{lane.id}` chồng vùng bảo vệ `{zone.id}` ở {pairs[:3]}")


def parse_policy(text: str) -> Policy:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PolicyError(yaml_error_message(POLICY_PATH, exc)) from exc
    if not isinstance(data, dict):
        raise PolicyError(f"{POLICY_PATH} phải là một mapping")

    problems: list[str] = []
    if data.get("version") != 1:
        problems.append("version: chỉ hỗ trợ 1")
    raw_lease = data.get("lease")
    lease: dict[str, Any] = raw_lease if isinstance(raw_lease, dict) else {}
    policy = Policy(
        remote=_text(data, "remote", "policy", problems, "origin"),
        base_branch=_text(data, "base_branch", "policy", problems, "main"),
        claims_branch=_text(data, "claims_branch", "policy", problems, "agent-claims"),
        tickets_dir=_text(data, "tickets_dir", "policy", problems, "docs/work/tickets").rstrip("/"),
        human_approval_label=_text(data, "human_approval_label", "policy", problems, "human-approved"),
        lease_default_hours=_positive_int(lease.get("default_hours", 24), "lease.default_hours", problems),
        lease_max_hours=_positive_int(lease.get("max_hours", 72), "lease.max_hours", problems),
        always_allowed=_texts(data.get("always_allowed"), "always_allowed", problems),
        protected=_zones(data.get("protected"), problems),
        exclusive=_lanes(data.get("exclusive"), problems),
        mail_branch=_text(data, "mail_branch", "policy", problems, "agent-mail"),
    )
    _check_consistency(policy, problems)
    if problems:
        raise PolicyError(f"{POLICY_PATH} sai ở {len(problems)} chỗ:\n  - " + "\n  - ".join(problems))
    return policy


def load_policy(repo: Path, ref: str | None = None) -> Policy:
    """Đọc chính sách tại `ref` (vd. `origin/main`); `ref=None` đọc cây làm việc."""
    if ref is None:
        path = repo / POLICY_PATH
        if not path.is_file():
            raise PolicyError(f"không thấy {POLICY_PATH} trong cây làm việc")
        return parse_policy(path.read_text(encoding="utf-8"))
    text = show_file(repo, ref, POLICY_PATH)
    if text is None:
        raise PolicyError(f"không thấy {POLICY_PATH} tại `{ref}` — đã `git fetch` chưa?")
    return parse_policy(text)
