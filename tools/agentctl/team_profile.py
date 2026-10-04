"""Team-size × complexity: một trục chọn số người thật đứng sau các vai trò, một trục chọn mức nghi thức.

`docs/design/team-profile.yaml` là nguồn sự thật. `docs/GOVERNANCE.md`, `.github/CODEOWNERS`, và phần
`owners:` trong `coordination/policy.yaml` là SINH RA từ profile đó bằng module này — cùng mẫu với
`contracts/openapi.json` (`scripts/export_openapi.py`): sửa nguồn mà quên sinh lại thì lưới canh đỏ.

Team-size KHÔNG đổi cơ chế `tools/agentctl` (claim/worktree/kiểm phạm vi chạy y hệt dù 1 hay 20 người —
chúng ngăn chính bạn qua nhiều phiên agent, không chỉ ngăn đồng đội). Nó chỉ đổi: ai chịu trách nhiệm
cho vùng nào, và mức nghi thức duyệt/ADR (trục complexity).

Bảy "hạng mục trách nhiệm" cố định, mọi dự án đều có, bất kể bao nhiêu người giữ chúng:

- ARCH     kiến trúc, luật, điều phối, agent/LLM gateway
- DOMAIN   miền nghiệp vụ, dữ liệu, đánh giá
- BACKEND  API, CSDL, migration
- OPS      CI, deploy, Docker, bí mật
- FRONTEND giao diện
- RELEASE  tài liệu phát hành (README, video, pitch deck)
- SECURITY (tuỳ chọn) đồng duyệt các đường chạm agent/bí mật — chỉ có ở team-size `large` hoặc khi
  complexity `strict` bật `security_lane` mà chưa có vai trò riêng (khi đó rơi về chủ ARCH).
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from tools.agentctl.entries import slugify
from tools.agentctl.errors import AgentctlError
from tools.agentctl.policy import yaml, yaml_error_message

TEAM_PROFILE_PATH = "docs/design/team-profile.yaml"
PRESETS_DIR = "docs/design/presets"
TEAM_SIZES = ("solo", "small", "standard", "large")
COMPLEXITIES = ("lite", "standard", "strict")
#: Handle GitHub hợp lệ cho CODEOWNERS: `@user` hoặc `@org/team` (tên người dùng không bắt đầu/kết thúc bằng `-`, không có `--`).
GITHUB_HANDLE = re.compile(r"^@[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}(?:/[A-Za-z0-9][A-Za-z0-9._-]*)?$")
#: Thứ tự cố định — quyết định thứ tự cột/dòng khi hiển thị, không phải thứ tự ưu tiên.
CATEGORIES = ("ARCH", "DOMAIN", "BACKEND", "OPS", "FRONTEND", "RELEASE", "SECURITY")
_REQUIRED_CATEGORIES = frozenset(CATEGORIES) - {"SECURITY"}

#: Mô tả "sở hữu" cho bảng vai trò ở GOVERNANCE.md §1.
CATEGORY_OWNERSHIP_TEXT: dict[str, str] = {
    "ARCH": "`docs/design/`, `docs/rules/`, `coordination/`, `tests/guards/`, `src/agents/`, `src/llm/`",
    "DOMAIN": "`src/domain/`, dữ liệu nghiệp vụ và nguồn, bộ đánh giá, bất biến miền",
    "BACKEND": "`src/api/`, `src/db/`, `alembic/`",
    "OPS": "CI, deploy, Docker, bí mật",
    "FRONTEND": "`web/`, trải nghiệm người dùng",
    "RELEASE": "tài liệu phát hành (README, video, pitch deck)",
    "SECURITY": "bảo mật agent (`docs/rules/60-agent-security.md`, `src/llm/safety.py`, `src/agents/actions.py`), xoay khoá",
}

#: Mẫu đường dẫn CODEOWNERS theo hạng mục — KHÔNG gồm hạng mục co-owned (`contracts/openapi.json`) và
#: `SECURITY` (lớp đồng duyệt thêm), hai thứ đó xử lý riêng trong `render_codeowners`.
_CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "ARCH": (
        "/docs/design/",
        "/contracts/boundaries.yaml",
        "/docs/rules/",
        "/docs/GOVERNANCE.md",
        "/coordination/",
        "/tools/",
        "/scripts/githooks/",
        "/scripts/hooks/",
        "/tests/guards/",
        "/docs/work/tickets/",
        "/src/agents/",
        "/src/llm/",
        "/AGENTS.md",
        "/CLAUDE.md",
        "/GEMINI.md",
        "/.github/copilot-instructions.md",
        "/.cursor/",
        "/.claude/",
        "/.gemini/",
        "/.codex/",
    ),
    "DOMAIN": ("/src/domain/",),
    "BACKEND": ("/src/api/", "/src/db/", "/alembic/"),
    "OPS": ("/.github/workflows/", "/render.yaml", "/Dockerfile", "/docker-compose.yml"),
    "FRONTEND": ("/web/",),
    "RELEASE": (),
}
#: Đường dẫn hai hạng mục cùng sở hữu — thứ tự vai trò trong handle theo (BACKEND, FRONTEND).
_SHARED_BACKEND_FRONTEND = "/contracts/openapi.json"
#: `/web/AGENTS.md` phải LUÔN thắng `/web/` (rộng hơn) — CODEOWNERS lấy pattern khớp CUỐI CÙNG trong
#: file, nên toàn bộ danh sách được sắp theo độ dài mẫu tăng dần (đặc điểm chung, không riêng dòng này).
_WEB_CONSTITUTION_OVERRIDE = "/web/AGENTS.md"
#: Đồng duyệt thêm khi có hạng mục SECURITY — không thay chủ sở hữu gốc của các đường dẫn này.
_SECURITY_PATTERNS = ("/docs/rules/60-agent-security.md", "/src/llm/safety.py", "/src/agents/actions.py")

#: Zone id trong `coordination/policy.yaml` → hạng mục quyết định ai sở hữu (khớp marker `# OWNER:<cat>`).
POLICY_ZONE_CATEGORY: dict[str, str] = {
    "constitution": "ARCH",
    "design": "ARCH",
    "rules": "ARCH",
    "coordination": "ARCH",
    "work-plan": "ARCH",
    "guard-nets": "ARCH",
    "delivery": "OPS",
}


class TeamProfileError(AgentctlError):
    """`team-profile.yaml` hoặc preset sai cấu trúc."""


@dataclass(frozen=True)
class Role:
    id: str
    title: str
    backup: str | None
    github: str | None = None  # handle GitHub thật khai ở `github_handles` trong profile; None = suy handle giữ chỗ

    @property
    def number(self) -> str:
        return self.id[1:]

    @property
    def handle(self) -> str:
        """Handle GitHub thật nếu profile khai (`github_handles`); không thì `@r<n>-<slug>` giữ chỗ suy từ đoạn đầu tiêu đề (trước dấu `·`)."""
        if self.github:
            return self.github
        head = self.title.split("·", 1)[0].strip()
        words = slugify(head, max_length=64).split("-")[:2]
        return f"@r{self.number}-{'-'.join(w for w in words if w)}"


@dataclass(frozen=True)
class TeamProfile:
    team_size: str
    complexity: str
    roles: tuple[Role, ...]
    category_owner: dict[str, str]
    self_merge_allowed: bool
    min_approvals_protected: int
    adr_required_note: str | None
    security_lane: bool
    team_notes: str
    complexity_description: str

    def owner(self, category: str) -> str:
        return self.category_owner[category]

    def role(self, role_id: str) -> Role:
        return next(r for r in self.roles if r.id == role_id)

    def owners_of(self, categories: tuple[str, ...], *, exclude: str | None = None) -> list[str]:
        """Vai trò sở hữu ≥1 hạng mục trong `categories`, thứ tự xuất hiện, không trùng, trừ `exclude`."""
        seen: list[str] = []
        for category in categories:
            owner = self.category_owner.get(category)
            if owner and owner != exclude and owner not in seen:
                seen.append(owner)
        return seen


def _preset(kind: str, name: str, allowed: tuple[str, ...]) -> dict[str, Any]:
    if name not in allowed:
        raise TeamProfileError(f"`{kind}` phải thuộc {allowed}, nhận `{name}`")
    path = Path(__file__).resolve().parents[2] / PRESETS_DIR / kind / f"{name}.yaml"
    if not path.is_file():
        raise TeamProfileError(f"thiếu preset `{path}`")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TeamProfileError(yaml_error_message(str(path), exc)) from exc
    if not isinstance(data, dict):
        raise TeamProfileError(f"{path}: preset phải là mapping")
    return data


def _roles(raw: Any, *, source: str) -> tuple[Role, ...]:
    if not isinstance(raw, list) or not raw:
        raise TeamProfileError(f"{source}: `roles` phải là danh sách không rỗng")
    roles: list[Role] = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not isinstance(item.get("title"), str):
            raise TeamProfileError(f"{source}: mỗi role cần `id` và `title` dạng chuỗi")
        backup = item.get("backup")
        if backup is not None and not isinstance(backup, str):
            raise TeamProfileError(f"{source}: `backup` phải là chuỗi hoặc null")
        roles.append(Role(item["id"], item["title"], backup))
    ids = [r.id for r in roles]
    if len(ids) != len(set(ids)):
        raise TeamProfileError(f"{source}: trùng id vai trò")
    return tuple(roles)


def _category_owner(raw: Any, roles: tuple[Role, ...], *, source: str) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise TeamProfileError(f"{source}: `category_owner` phải là mapping")
    known = {r.id for r in roles}
    missing = _REQUIRED_CATEGORIES - set(raw)
    if missing:
        raise TeamProfileError(f"{source}: `category_owner` thiếu {sorted(missing)}")
    unknown_cat = set(raw) - set(CATEGORIES)
    if unknown_cat:
        raise TeamProfileError(f"{source}: hạng mục không hợp lệ {sorted(unknown_cat)}")
    unknown_role = {v for v in raw.values() if v not in known}
    if unknown_role:
        raise TeamProfileError(f"{source}: `category_owner` trỏ tới vai trò không tồn tại {sorted(unknown_role)}")
    return dict(raw)


def _apply_handles(roles: tuple[Role, ...], raw: Any, *, source: str) -> tuple[Role, ...]:
    """Gắn handle GitHub thật (`github_handles: {R1: "@tai-khoan"}`) vào vai trò. Sai kiểu, sai dạng handle hay vai trò lạ đều bị từ chối."""
    if raw is None:
        return roles
    if not isinstance(raw, Mapping):
        raise TeamProfileError(f'{source}: `github_handles` phải là mapping vai trò → handle (vd. R1: "@tai-khoan")')
    known = {r.id for r in roles}
    unknown = sorted(str(k) for k in raw if k not in known)
    if unknown:
        raise TeamProfileError(
            f"{source}: `github_handles` trỏ tới vai trò không có trong preset: {unknown} (có: {sorted(known)})"
        )
    for role_id, handle in raw.items():
        if not isinstance(handle, str) or not GITHUB_HANDLE.match(handle):
            raise TeamProfileError(
                f"{source}: handle của {role_id} phải dạng `@tai-khoan` hoặc `@to-chuc/nhom`, nhận {handle!r}"
            )
    return tuple(replace(r, github=raw[r.id]) if r.id in raw else r for r in roles)


def build_profile(team_size: str, complexity: str, github_handles: Any = None) -> TeamProfile:
    team = _preset("team-size", team_size, TEAM_SIZES)
    comp = _preset("complexity", complexity, COMPLEXITIES)
    source = f"preset team-size/{team_size}.yaml"
    roles = _roles(team.get("roles"), source=source)
    category_owner = _category_owner(team.get("category_owner"), roles, source=source)
    roles = _apply_handles(roles, github_handles, source=TEAM_PROFILE_PATH)
    raw_review = team.get("review")
    review: dict[str, Any] = raw_review if isinstance(raw_review, dict) else {}

    security_lane = bool(comp.get("security_lane", False))
    if security_lane and "SECURITY" not in category_owner:
        # `strict` mà preset đội chưa có vai trò bảo mật riêng: rơi về chủ ARCH, đọc lại lần hai.
        category_owner = {**category_owner, "SECURITY": category_owner["ARCH"]}

    self_merge_allowed = bool(review.get("self_merge_allowed", False))
    min_approvals = int(comp.get("min_approvals_protected", 1))
    if not self_merge_allowed and len(roles) <= min_approvals:
        raise TeamProfileError(
            f"team-size `{team_size}` ({len(roles)} vai trò) không đủ người cho complexity `{complexity}` "
            f"(cần {min_approvals} người duyệt KHÁC tác giả, tức tối thiểu {min_approvals + 1} vai trò). "
            f"Chọn team-size lớn hơn, hoặc complexity nhẹ hơn."
        )

    return TeamProfile(
        team_size=team_size,
        complexity=complexity,
        roles=roles,
        category_owner=category_owner,
        self_merge_allowed=self_merge_allowed,
        min_approvals_protected=min_approvals,
        adr_required_note=comp.get("adr_required_note"),
        security_lane=security_lane,
        team_notes=str(team.get("notes", "")).strip(),
        complexity_description=str(comp.get("description", "")).strip(),
    )


def load_team_profile(root: Path) -> TeamProfile:
    path = root / TEAM_PROFILE_PATH
    if not path.is_file():
        raise TeamProfileError(f"thiếu {TEAM_PROFILE_PATH}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TeamProfileError(yaml_error_message(TEAM_PROFILE_PATH, exc)) from exc
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("team_size"), str)
        or not isinstance(data.get("complexity"), str)
    ):
        raise TeamProfileError(f"{TEAM_PROFILE_PATH}: cần `team_size` và `complexity` dạng chuỗi")
    return build_profile(data["team_size"], data["complexity"], data.get("github_handles"))


def _existing_handles(root: Path) -> dict[str, str]:
    """Handle đã khai trong profile hiện có (nếu đọc được và hợp lệ) — để ghi lại profile không làm mất chúng."""
    path = root / TEAM_PROFILE_PATH
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return {}
    raw = data.get("github_handles") if isinstance(data, dict) else None
    if not isinstance(raw, Mapping):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, str) and GITHUB_HANDLE.match(v)}


def write_team_profile(root: Path, team_size: str, complexity: str) -> None:
    """Xác thực rồi ghi `team-profile.yaml` — không bao giờ ghi một tổ hợp không dựng được profile. Giữ nguyên `github_handles` đã khai."""
    handles = _existing_handles(root)
    build_profile(team_size, complexity)  # ném lỗi sớm nếu tổ hợp/preset sai, trước khi ghi gì
    handle_block = ""
    if handles:
        known = {r.id for r in build_profile(team_size, complexity).roles}
        kept = {
            k: v for k, v in handles.items() if k in known
        }  # preset mới không còn vai trò đó thì bỏ handle tương ứng
        if kept:
            handle_block = "github_handles:\n" + "".join(f"  {k}: {json.dumps(v)}\n" for k, v in sorted(kept.items()))
    content = (
        "# Profile đang áp dụng cho DỰ ÁN NÀY — nguồn sự thật cho docs/GOVERNANCE.md, .github/CODEOWNERS, và\n"
        "# phần `owners:` trong coordination/policy.yaml. Ba file đó là SINH RA, không sửa tay — sửa profile này\n"
        "# rồi chạy: python scripts/generate_team_docs.py --apply\n"
        "#\n"
        "# 🔒 Vùng bảo vệ `design`. Đổi team_size/complexity là quyết định của người (docs/GOVERNANCE.md §3).\n"
        "# Xem lựa chọn và ý nghĩa từng preset: docs/design/presets/README.md\n"
        "version: 1\n"
        f"team_size: {team_size} # {' | '.join(TEAM_SIZES)}\n"
        f"complexity: {complexity} # {' | '.join(COMPLEXITIES)}\n"
        + (
            "#\n# Handle GitHub THẬT cho CODEOWNERS (vai trò → tài khoản). Không khai thì CODEOWNERS dùng handle giữ chỗ `@rN-...`.\n"
            + handle_block
            if handle_block
            else ""
        )
    )
    (root / TEAM_PROFILE_PATH).write_text(content, encoding="utf-8", newline="\n")


# --------------------------------------------------------------------- GOVERNANCE.md


def _role_row(role: Role, profile: TeamProfile) -> str:
    owns = "; ".join(CATEGORY_OWNERSHIP_TEXT[c] for c in CATEGORIES if profile.category_owner.get(c) == role.id)
    backup = f"R{profile.role(role.backup).number}" if role.backup else "—"
    return f"| **{role.id}** | {role.title} | `…` | {owns} | {backup} |"


def _raci_row(label: str, a: str, c: str, agent: str) -> str:
    return f"| {label} | {a} | {c} | {agent} |"


def render_governance(profile: TeamProfile) -> str:
    role_rows = "\n".join(_role_row(role, profile) for role in profile.roles)
    role_count_note = f"Preset team-size `{profile.team_size}` ({len(profile.roles)} vai trò)."
    team_notes_block = f"\n> {profile.team_notes}\n" if profile.team_notes else ""

    merge_agent = (
        "được, sau khi CI xanh VÀ đã tự đọc diff — không có người thứ hai (profile `solo`)"
        if profile.self_merge_allowed
        else "merge PR của mình **chỉ** khi governance cho phép và không chạm vùng bảo vệ"
    )
    raci_rows = [
        _raci_row(
            "Kiến trúc, ranh giới lớp, ADR",
            profile.owner("ARCH"),
            ", ".join(profile.owners_of(CATEGORIES, exclude=profile.owner("ARCH"))) or "—",
            "soạn ADR `Proposed`",
        ),
        _raci_row(
            "Bất biến sản phẩm (`invariants.yaml`)",
            " + ".join(dict.fromkeys([profile.owner("ARCH"), profile.owner("DOMAIN")])),
            "cả đội",
            "đề xuất qua câu hỏi",
        ),
        _raci_row(
            "Ngưỡng, hệ số, nguồn số liệu nghiệp vụ",
            profile.owner("DOMAIN"),
            ", ".join(profile.owners_of(("ARCH",), exclude=profile.owner("DOMAIN"))) or "—",
            "**không** — chỉ trích nguồn có sẵn",
        ),
        _raci_row("Ticket `ready`, phạm vi ticket", profile.owner("ARCH"), "chủ module", "soạn ticket `proposed`"),
        _raci_row(
            "Schema CSDL, migration",
            profile.owner("BACKEND"),
            ", ".join(profile.owners_of(("ARCH", "DOMAIN"), exclude=profile.owner("BACKEND"))) or "—",
            "viết migration trong ticket có làn `db-migrations`",
        ),
        _raci_row(
            "Hợp đồng API",
            profile.owner("BACKEND"),
            ", ".join(profile.owners_of(("FRONTEND",), exclude=profile.owner("BACKEND"))) or "—",
            "đổi trong ticket có làn `api-contract`",
        ),
        _raci_row(
            "CI, deploy, bí mật",
            profile.owner("OPS"),
            ", ".join(profile.owners_of(("ARCH",), exclude=profile.owner("OPS"))) or "—",
            "đề xuất; không đổi cổng an toàn",
        ),
    ]
    if "SECURITY" in profile.category_owner:
        raci_rows.append(
            _raci_row(
                "Bảo mật agent (egress, sổ hành động rủi ro cao)",
                profile.owner("SECURITY"),
                ", ".join(profile.owners_of(("ARCH", "OPS"), exclude=profile.owner("SECURITY"))) or "—",
                "đề xuất qua câu hỏi; không tự nới sổ hành động",
            )
        )
    raci_rows += [
        _raci_row("Merge vào `main`", "chủ module, sau CI xanh", "—", merge_agent),
        _raci_row("Nhãn `human-approved`", "chủ vùng bảo vệ", "—", "**không bao giờ**"),
    ]

    approvals_note = (
        f"\n\nComplexity `{profile.complexity}`: vùng bảo vệ cần **{profile.min_approvals_protected} người duyệt** "
        f"— bật branch protection *Require approvals* = {profile.min_approvals_protected}."
        if profile.min_approvals_protected > 1 and not profile.self_merge_allowed
        else ""
    )
    adr_note = (
        f"\n\n> **Complexity `{profile.complexity}`:** {profile.adr_required_note}" if profile.adr_required_note else ""
    )

    return f"""# GOVERNANCE — Ai quyết gì, và AI agent đứng ở đâu

> Vùng bảo vệ `rules`. File này SINH RA từ `docs/design/team-profile.yaml` bằng
> `python scripts/generate_team_docs.py` — sửa profile rồi sinh lại, đừng sửa tay bảng vai trò dưới đây.
> Điền tên người thật vào cột "Người" rồi commit (PR có người duyệt) — sinh lại không xoá tên đã điền.

## 1. Vai trò con người

{role_count_note}

| Mã | Vai trò | Người | Sở hữu | Dự phòng |
|---|---|---|---|---|
{role_rows}
{team_notes_block}
## 2. AI agent trong mô hình trách nhiệm

- **Mỗi phiên agent làm thay đúng một vai trò** (`--role Rn` khi claim). Người giữ vai trò đó chịu trách
  nhiệm cho mọi thứ agent merge — như với commit của chính họ.
- **Agent không có quyền quyết định** ở các hạng mục trong bảng §3. Agent đề xuất (ticket `proposed`,
  ADR `Proposed`, câu hỏi); người quyết.
- **Agent của nhà cung cấp nào cũng theo cùng luật** (`AGENTS.md`). Không có agent "tin cậy hơn" theo thương hiệu.
- **Ghi nhận tác giả:** commit, PR, nhật ký ghi vai trò con người (`R2`). Dự án muốn ghi thêm công cụ/mô
  hình AI để thống kê thì quyết ở đây, bằng một dòng: *Ghi công cụ AI: không*.
- **Tài khoản của agent:** khuyến nghị agent dùng token/tài khoản **không** có quyền duyệt PR hay gắn nhãn
  `human-approved`. Nếu agent dùng tài khoản của người, cổng duyệt chỉ còn là kỷ luật quy trình — ghi rõ.

## 3. Quyền quyết định

| Hạng mục | Quyết (A) | Hỏi ý kiến (C) | Agent được |
|---|---|---|---|
{chr(10).join(raci_rows)}

Không ô nào có hai người **A**. Hạng mục hỏng thì hỏi người **A**.{approvals_note}

## 4. Quyết định kiến trúc (ADR)

ADR bắt buộc khi: thêm/thay framework, CSDL, nhà cung cấp mô hình, dịch vụ cloud · đổi ranh giới giữa mô
hình ngôn ngữ và lõi tất định · đổi schema/API ảnh hưởng từ hai module · đổi luồng duyệt, phân quyền, kiểm
toán · thêm chi phí vận hành định kỳ · chấp nhận một rủi ro an toàn/bảo mật chưa xử lý.{adr_note}

1. Người đề xuất (người hoặc agent `architect`) tạo `docs/design/adr/NNNN-slug.md` từ `0000-template.md`, `Status: Proposed`.
2. {profile.owner("ARCH")} kiểm ít nhất hai phương án có bằng chứng; mời người hỏi ý kiến theo §3.
3. {profile.owner("ARCH")} chuyển `Accepted`/`Rejected`/`Deferred` trong PR có người duyệt.
4. ADR không sửa để che lịch sử — quyết định mới thay quyết định cũ bằng ADR mới ghi `Supersedes`.

## 5. Thang đánh giá kiến trúc (trước mỗi mốc phát hành)

Mỗi tiêu chí 0–5; điểm = `điểm/5 × trọng số`. Thiếu bằng chứng (test/log/báo cáo) thì tối đa 2/5.

| Tiêu chí | Trọng số | Bằng chứng tối thiểu |
|---|---:|---|
| An toàn miền & fail-closed | 25% | lưới canh bất biến xanh và từng được chứng minh đỏ |
| Tính đúng & truy vết nguồn | 15% | test tính toán; mọi con số truy được về nguồn |
| Bảo mật & riêng tư | 15% | test phân quyền/IDOR; không bí mật trong repo; egress guard |
| Độ tin cậy & khôi phục | 10% | health/ready; timeout/retry có trần; đường khôi phục migration |
| Khả năng kiểm thử | 10% | unit/integration/e2e; kiểm cục bộ = CI |
| Bảo trì & đơn giản | 10% | ranh giới lớp giữ được; phụ thuộc có lý do |
| Quan sát & kiểm toán | 5% | audit log cho hành động MEDIUM/HIGH; trace id |
| Hiệu năng & chi phí | 5% | p95; số lời gọi mô hình/request |
| Triển khai | 3% | Docker tái lập; deploy chờ CI; rollback |
| Vận hành giao diện/API | 2% | trạng thái tải/rỗng/lỗi; hợp đồng API cập nhật |

**Qua** ≥ 80 · **Qua có điều kiện** 75–79 (có người chịu rủi ro và hạn) · **Không qua** < 75.
Không qua ngay nếu: an toàn miền, tính đúng hoặc bảo mật dưới 3/5; có đường vòng qua cổng duyệt; có
con số không nguồn tới người dùng; migration production không có đường khôi phục.

## 6. Nhịp

| Khi | Việc | Ai |
|---|---|---|
| Đầu mỗi chu kỳ | lập kế hoạch: ticket `ready`, chia nhóm song song/tuần tự | {profile.owner("ARCH")} + cả đội |
| Hằng ngày | `python -m tools.agentctl board`; dọn claim quá hạn; trả lời câu hỏi mở | {profile.owner("ARCH")} |
| Mỗi PR | review theo `coordination/roles/reviewer.md`; nhãn duyệt nếu chạm vùng bảo vệ | chủ module |
| Cuối chu kỳ | thang đánh giá §5; sự cố → lưới canh mới | {profile.owner("ARCH")} |
"""


# --------------------------------------------------------------------- CODEOWNERS


def render_codeowners(profile: TeamProfile) -> str:
    lines = [
        "# CODEOWNERS — SINH RA từ docs/design/team-profile.yaml bằng `python scripts/generate_team_docs.py`.",
        "# Sửa ở đó, đừng sửa tay file này. Handle thật khai ở `github_handles` trong profile; chưa khai thì ra handle giữ chỗ (@rN-...) — GitHub bỏ qua.",
        '# Chỉ có hiệu lực chặn khi branch protection bật "Require review from Code Owners" — không có nó,',
        "# file này chỉ là gợi ý reviewer. Agent nên dùng tài khoản KHÔNG nằm trong file này.",
        "#",
        "# GitHub áp dụng pattern KHỚP CUỐI CÙNG trong file. Patterns dưới được sắp theo ĐỘ DÀI TĂNG DẦN",
        "# (không phải theo chủ đề) để một pattern hẹp (vd. /web/AGENTS.md) luôn đứng sau, và luôn thắng,",
        "# một pattern rộng hơn (vd. /web/) đứng trước nó — bất kể ai thêm mục mới vào giữa.",
        "",
        f"*{' ' * 35}{profile.role(profile.owner('ARCH')).handle}",
        "",
    ]

    entries: list[tuple[str, tuple[str, ...]]] = []
    for category, patterns in _CATEGORY_PATTERNS.items():
        handle = profile.role(profile.owner(category)).handle
        entries += [(pattern, (handle,)) for pattern in patterns]
    backend_handle = profile.role(profile.owner("BACKEND")).handle
    frontend_handle = profile.role(profile.owner("FRONTEND")).handle
    entries.append((_SHARED_BACKEND_FRONTEND, tuple(dict.fromkeys([backend_handle, frontend_handle]))))
    if "SECURITY" in profile.category_owner:
        security_handle = profile.role(profile.owner("SECURITY")).handle
        arch_handle = profile.role(profile.owner("ARCH")).handle
        entries += [(pattern, tuple(dict.fromkeys([arch_handle, security_handle]))) for pattern in _SECURITY_PATTERNS]
    entries.append(
        (
            _WEB_CONSTITUTION_OVERRIDE,
            tuple(dict.fromkeys([profile.role(profile.owner("ARCH")).handle, frontend_handle])),
        )
    )

    entries.sort(key=lambda entry: len(entry[0]))
    for pattern, handles in entries:
        padding = " " * max(1, 37 - len(pattern))
        lines.append(f"{pattern}{padding}{' '.join(handles)}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------- coordination/policy.yaml owners

_OWNER_LINE = "owners: ["


def patch_policy_owners(text: str, profile: TeamProfile) -> str:
    """Thay nội dung `owners: [...]  # OWNER:<hạng mục>` theo `category_owner` của profile.

    Chỉ đổi các dòng có marker — mọi nội dung khác của policy.yaml (bao gồm mọi comment giải thích) giữ
    nguyên, vì đây là điều KHÔNG được đánh đổi lấy việc tự động hoá bảng vai trò.
    """
    lines = text.split("\n")
    patched: list[str] = []
    for line in lines:
        marker_at = line.find("# OWNER:")
        if marker_at == -1 or _OWNER_LINE not in line:
            patched.append(line)
            continue
        category = line[marker_at + len("# OWNER:") :].strip()
        if category not in profile.category_owner:
            raise TeamProfileError(f"policy.yaml: marker `# OWNER:{category}` không khớp hạng mục nào trong profile")
        indent = line[: len(line) - len(line.lstrip())]
        patched.append(f"{indent}owners: [{profile.owner(category)}]  # OWNER:{category}")
    return "\n".join(patched)
