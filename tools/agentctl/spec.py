"""Đặc tả sống — yêu cầu `SHALL`, kịch bản `WHEN/THEN`, test chứng minh; thay đổi đi qua delta rồi gộp vào đặc tả chung.

Bố cục (docs/design/specs/):
    <capability>.md                      đặc tả hiện hành của một năng lực
    changes/<TICKET>-<capability>.md     delta đang chờ: ## ADDED / ## MODIFIED / ## REMOVED Requirements
    changes/archive/<ngày>-<...>.md      delta đã gộp (lịch sử, không sửa)

Khuôn một yêu cầu:
    ### Requirement: <tên duy nhất trong năng lực>
    Hệ thống SHALL <điều kiểm được>.

    #### Scenario: <tên>
    - **WHEN** <điều kiện>
    - **THEN** <kết quả quan sát được>
    - **Test:** đường/dẫn_test.py::tên_hàm   (nhiều test: cách nhau dấu phẩy; chưa có: `planned:TICKET-NN`)

Mọi hàm ở đây trả giá trị MỚI, không sửa đối tượng đầu vào. Ý tưởng mượn từ Fission-AI/OpenSpec (MIT).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path

from tools.agentctl.errors import AgentctlError

SPECS_DIR = "docs/design/specs"
CHANGES_DIR = f"{SPECS_DIR}/changes"
ARCHIVE_DIR = f"{CHANGES_DIR}/archive"

_REQ = re.compile(r"^### Requirement: (.+?)\s*$")
_SCN = re.compile(r"^#### Scenario: (.+?)\s*$")
_STEP = re.compile(r"^- \*\*(WHEN|THEN|AND)\*\* (.+?)\s*$")
_TEST = re.compile(r"^- \*\*Test:\*\* (.+?)\s*$")
_SECTION = re.compile(r"^## (ADDED|MODIFIED|REMOVED) Requirements\s*$")
_PLANNED = re.compile(r"^planned:[A-Z][A-Z0-9]*-\d+$")
_DELTA_NAME = re.compile(r"^([A-Z][A-Z0-9]*-\d+)-(.+)$")


@dataclass(frozen=True)
class Scenario:
    name: str
    steps: tuple[tuple[str, str], ...]
    tests: tuple[str, ...]


@dataclass(frozen=True)
class Requirement:
    name: str
    text: str
    scenarios: tuple[Scenario, ...]


@dataclass(frozen=True)
class Spec:
    capability: str
    requirements: tuple[Requirement, ...]


@dataclass(frozen=True)
class Delta:
    ticket: str
    capability: str
    added: tuple[Requirement, ...]
    modified: tuple[Requirement, ...]
    removed: tuple[str, ...]


@dataclass(frozen=True)
class ArchiveResult:
    spec_path: Path
    archived_path: Path
    requirements_after: int


def _parse_requirements(lines: list[str]) -> tuple[Requirement, ...]:
    requirements: list[Requirement] = []
    name: str | None = None
    text: list[str] = []
    scenarios: list[Scenario] = []
    scn: dict | None = None

    def close_scenario() -> None:
        nonlocal scn
        if scn is not None:
            scenarios.append(Scenario(scn["name"], tuple(scn["steps"]), tuple(scn["tests"])))
            scn = None

    def close_requirement() -> None:
        nonlocal name, text, scenarios
        close_scenario()
        if name is not None:
            requirements.append(Requirement(name, "\n".join(text).strip(), tuple(scenarios)))
        name, text, scenarios = None, [], []

    for line in lines:
        if m := _REQ.match(line):
            close_requirement()
            name = m.group(1)
        elif name is None:
            continue
        elif m := _SCN.match(line):
            close_scenario()
            scn = {"name": m.group(1), "steps": [], "tests": []}
        elif scn is not None and (m := _STEP.match(line)):
            scn["steps"].append((m.group(1), m.group(2)))
        elif scn is not None and (m := _TEST.match(line)):
            scn["tests"] += [part.strip() for part in m.group(1).split(",") if part.strip()]
        elif scn is None:
            text.append(line)
    close_requirement()
    return tuple(requirements)


def parse_spec(capability: str, text: str) -> Spec:
    return Spec(capability, _parse_requirements(text.splitlines()))


def render_requirement(requirement: Requirement) -> list[str]:
    lines = [f"### Requirement: {requirement.name}", requirement.text, ""]
    for scenario in requirement.scenarios:
        lines.append(f"#### Scenario: {scenario.name}")
        lines += [f"- **{keyword}** {body}" for keyword, body in scenario.steps]
        if scenario.tests:
            lines.append(f"- **Test:** {', '.join(scenario.tests)}")
        lines.append("")
    return lines


def render_spec(spec: Spec) -> str:
    lines = [f"# Spec: {spec.capability}", ""]
    for requirement in spec.requirements:
        lines += render_requirement(requirement)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def parse_delta(stem: str, text: str) -> Delta:
    match = _DELTA_NAME.match(stem)
    if not match:
        raise AgentctlError(f"tên delta `{stem}` phải dạng `<MÃ-TICKET>-<năng-lực>`, vd. `ABC-01-handoff`")
    sections: dict[str, list[str]] = {"ADDED": [], "MODIFIED": [], "REMOVED": []}
    current: str | None = None
    for line in text.splitlines():
        if m := _SECTION.match(line):
            current = m.group(1)
        elif current:
            sections[current].append(line)
    return Delta(
        ticket=match.group(1),
        capability=match.group(2),
        added=_parse_requirements(sections["ADDED"]),
        modified=_parse_requirements(sections["MODIFIED"]),
        removed=tuple(m.group(1) for line in sections["REMOVED"] if (m := _REQ.match(line))),
    )


def apply_delta(spec: Spec, delta: Delta) -> Spec:
    """Gộp delta vào đặc tả, trả đặc tả MỚI. Thêm trùng, sửa/bỏ thứ không có ⇒ từ chối, không đoán."""
    by_name = {r.name: r for r in spec.requirements}
    order = [r.name for r in spec.requirements]
    for requirement in delta.added:
        if requirement.name in by_name:
            raise AgentctlError(
                f"ADDED: yêu cầu “{requirement.name}” đã tồn tại trong `{spec.capability}` — dùng MODIFIED"
            )
        by_name[requirement.name] = requirement
        order.append(requirement.name)
    for requirement in delta.modified:
        if requirement.name not in by_name:
            raise AgentctlError(
                f"MODIFIED: yêu cầu “{requirement.name}” không tồn tại trong `{spec.capability}` — dùng ADDED"
            )
        by_name[requirement.name] = requirement
    for name in delta.removed:
        if name not in by_name:
            raise AgentctlError(f"REMOVED: yêu cầu “{name}” không tồn tại trong `{spec.capability}`")
        del by_name[name]
        order.remove(name)
    return replace(spec, requirements=tuple(by_name[name] for name in order))


def _test_problem(ref: str, repo: Path) -> str | None:
    if _PLANNED.match(ref):
        return None
    path, _, function = ref.partition("::")
    if not function:
        return f"test `{ref}` phải dạng `đường/dẫn.py::tên_hàm` hoặc `planned:TICKET-NN`"
    file = repo / path
    if not file.is_file():
        return f"test `{ref}`: tệp không tồn tại"
    name = function.split("[", 1)[0]
    if not re.search(rf"\bdef {re.escape(name)}\b", file.read_text(encoding="utf-8")):
        return f"test `{ref}`: tệp không có hàm `{name}`"
    return None


def spec_problems(spec: Spec, repo: Path) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    for requirement in spec.requirements:
        where = f"{spec.capability} / “{requirement.name}”"
        if requirement.name in seen:
            problems.append(f"{where}: trùng tên yêu cầu")
        seen.add(requirement.name)
        if not re.search(r"\bSHALL\b", requirement.text):
            problems.append(f"{where}: câu yêu cầu phải có `SHALL` (điều kiểm được, không phải ý định)")
        if not requirement.scenarios:
            problems.append(f"{where}: thiếu kịch bản (`#### Scenario:` với WHEN/THEN)")
        for scenario in requirement.scenarios:
            at = f"{where} / kịch bản “{scenario.name}”"
            keywords = {keyword for keyword, _ in scenario.steps}
            problems += [f"{at}: thiếu bước {need}" for need in ("WHEN", "THEN") if need not in keywords]
            if not scenario.tests:
                problems.append(f"{at}: thiếu dòng `**Test:**` (tên test, hoặc `planned:TICKET-NN` nếu chưa có)")
            problems += [f"{at}: {p}" for ref in scenario.tests if (p := _test_problem(ref, repo))]
    return problems


def specs_dir(repo: Path) -> Path:
    return repo / SPECS_DIR


def load_spec(repo: Path, capability: str) -> Spec:
    path = specs_dir(repo) / f"{capability}.md"
    return parse_spec(capability, path.read_text(encoding="utf-8")) if path.is_file() else Spec(capability, ())


def archive_delta(repo: Path, stem: str, *, today: str) -> ArchiveResult:
    """Gộp delta vào đặc tả chung rồi chuyển delta vào archive. Kết quả hỏng ⇒ từ chối và KHÔNG đụng tệp nào."""
    changes = repo / CHANGES_DIR
    source = changes / f"{stem}.md"
    if not source.is_file():
        raise AgentctlError(f"không thấy delta `{CHANGES_DIR}/{stem}.md` (đã archive rồi, hoặc sai tên?)")
    delta = parse_delta(stem, source.read_text(encoding="utf-8"))
    merged = apply_delta(load_spec(repo, delta.capability), delta)
    problems = spec_problems(merged, repo)
    if problems:
        raise AgentctlError("đặc tả sau khi gộp chưa hợp lệ, không ghi gì:\n  - " + "\n  - ".join(problems))
    target = specs_dir(repo) / f"{delta.capability}.md"
    archived = repo / ARCHIVE_DIR / f"{today}-{stem}.md"
    archived.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(render_spec(merged).encode("utf-8"))
    archived.write_bytes(source.read_bytes())
    source.unlink()
    return ArchiveResult(target, archived, len(merged.requirements))


def pending_deltas(repo: Path) -> list[Path]:
    folder = repo / CHANGES_DIR
    return sorted(p for p in folder.glob("*.md") if p.name != "README.md") if folder.is_dir() else []


def repo_problems(repo: Path) -> list[str]:
    """Mọi đặc tả hiện hành hợp lệ; mọi delta chờ gộp đúng tên, đúng cú pháp và gộp thử được."""
    problems: list[str] = []
    folder = specs_dir(repo)
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        if path.name == "README.md":
            continue
        problems += spec_problems(parse_spec(path.stem, path.read_text(encoding="utf-8")), repo)
    for path in pending_deltas(repo):
        try:
            delta = parse_delta(path.stem, path.read_text(encoding="utf-8"))
            merged = apply_delta(load_spec(repo, delta.capability), delta)
        except AgentctlError as exc:
            problems.append(f"{path.name}: {exc}")
            continue
        problems += [f"{path.name} (sau khi gộp): {p}" for p in spec_problems(merged, repo)]
    return problems
