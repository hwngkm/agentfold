"""Bật/tắt pack kỹ năng cho dự án — trục thứ ba bên cạnh team-size × complexity.

    python scripts/packs.py --list              # pack nào có, pack nào đang bật, gợi ý theo loại dự án
    python scripts/packs.py --install ai-llm    # cài skill của pack vào .claude/skills/ + ghi profile
    python scripts/packs.py --remove ai-llm     # gỡ
    python scripts/packs.py --check             # CI: đỏ nếu .claude/skills/ lệch project-profile.yaml
    python scripts/packs.py --sync-marketplace  # sinh .claude-plugin/marketplace.json (phát hành qua /plugin marketplace)

Vì sao có trục này: mô tả của MỌI skill được nạp vào ngữ cảnh ở MỌI phiên. Cài hết cho mọi dự án là bắt
dự án CRUD trả giá ngữ cảnh cho kỹ năng finetune nó không bao giờ dùng. Xem `packs/README.md`.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.secret_scan import secret_problems  # noqa: E402
from tools.agentctl.errors import AgentctlError  # noqa: E402
from tools.agentctl.policy import yaml_error_message  # noqa: E402

REGISTRY_PATH = ROOT / "packs" / "registry.yaml"
PROFILE_PATH = ROOT / "docs" / "design" / "project-profile.yaml"
SKILLS_DIR = ROOT / ".claude" / "skills"


def mcp_path() -> Path:
    """Tính từ `ROOT` LÚC GỌI: test dựng repo giả bằng cách đổi `ROOT` — hằng số tính sẵn sẽ ghi vào repo thật."""
    return ROOT / ".mcp.json"


def skills_index_path() -> Path:
    return ROOT / "SKILLS.md"


class PackError(AgentctlError):
    """Sổ đăng ký hoặc hồ sơ dự án sai cấu trúc, hoặc pack không cài được."""


def _load_yaml(path: Path, ten: str) -> Any:
    """YAML hỏng phải thành thông điệp đọc được, không phải traceback — cùng cách `policy.py` làm."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PackError(yaml_error_message(ten, exc)) from exc


def load_registry() -> dict[str, Any]:
    if not REGISTRY_PATH.is_file():
        raise PackError("không thấy packs/registry.yaml")
    data = _load_yaml(REGISTRY_PATH, "packs/registry.yaml")
    if not isinstance(data, dict) or not isinstance(data.get("packs"), dict):
        raise PackError("packs/registry.yaml phải có mapping `packs`")
    if not isinstance(data.get("core"), list):
        raise PackError("packs/registry.yaml phải có danh sách `core`")
    return data


def load_profile() -> dict[str, Any]:
    if not PROFILE_PATH.is_file():
        raise PackError("không thấy docs/design/project-profile.yaml")
    data = _load_yaml(PROFILE_PATH, "docs/design/project-profile.yaml")
    if not isinstance(data, dict):
        raise PackError("project-profile.yaml phải là mapping")
    data.setdefault("packs", [])
    if not isinstance(data["packs"], list):
        raise PackError("project-profile.yaml: `packs` phải là danh sách")
    return data


def write_enabled(packs: list[str]) -> None:
    """Ghi lại danh sách pack, GIỮ NGUYÊN chú thích trong file (yaml.dump sẽ xoá sạch chúng)."""
    text = PROFILE_PATH.read_text(encoding="utf-8")
    value = "[]" if not packs else "[" + ", ".join(sorted(packs)) + "]"
    new_text, count = re.subn(r"(?m)^packs:.*$", f"packs: {value}", text, count=1)
    if count != 1:
        raise PackError("project-profile.yaml thiếu dòng `packs:` — thêm lại rồi chạy lệnh này")
    PROFILE_PATH.write_text(new_text, encoding="utf-8", newline="\n")


def write_project_type(kind: str) -> None:
    """Ghi loại dự án, giữ nguyên chú thích. Chỉ ghi loại — KHÔNG tự bật pack: bật pack là quyết định người."""
    text = PROFILE_PATH.read_text(encoding="utf-8")
    new_text, count = re.subn(r"(?m)^project_type:.*$", f"project_type: {kind}", text, count=1)
    if count != 1:
        raise PackError("project-profile.yaml thiếu dòng `project_type:`")
    PROFILE_PATH.write_text(new_text, encoding="utf-8", newline="\n")


def pack_skills(registry: dict[str, Any], name: str) -> list[str]:
    pack = registry["packs"].get(name)
    if pack is None:
        có = ", ".join(sorted(registry["packs"]))
        raise PackError(f"không có pack `{name}` — pack hiện có: {có}")
    return [str(s["name"]) for s in pack.get("skills", [])]


def expected_skills(registry: dict[str, Any], profile: dict[str, Any]) -> set[str]:
    names = {str(s) for s in registry["core"]}
    for pack in profile["packs"]:
        names |= set(pack_skills(registry, str(pack)))
    return names


INTEGRATION_KINDS = ("claude-plugin", "mcp", "cli")


def pack_integrations(registry: dict[str, Any], name: str) -> list[dict[str, Any]]:
    return list(registry["packs"].get(name, {}).get("integrations") or [])


def integration_problems(registry: dict[str, Any]) -> list[str]:
    """Kiểm khai báo `integrations:` của mọi pack: đúng loại, có lý do, không khoá thô, không trùng tên lệch cấu hình."""
    problems: list[str] = []
    mcp_seen: dict[str, tuple[str, Any]] = {}
    for pack_name, pack in registry["packs"].items():
        for index, item in enumerate(pack.get("integrations") or []):
            where = f"{pack_name}.integrations[{index}]"
            if not isinstance(item, dict) or item.get("kind") not in INTEGRATION_KINDS:
                problems.append(f"{where}: `kind` phải thuộc {INTEGRATION_KINDS}")
                continue
            if not str(item.get("why") or "").strip():
                problems.append(
                    f"{where}: thiếu `why` — người bật pack phải biết công cụ này để làm gì, gửi gì ra ngoài"
                )
            kind = item["kind"]
            if kind in ("mcp", "claude-plugin") and not str(item.get("fallback") or "").strip():
                problems.append(
                    f"{where}: thiếu `fallback` — cách làm cùng việc KHÔNG cần MCP/plugin (CLI, HTTP, skill khác), "
                    "để agent không có kết nối đó (Codex, Copilot, Cursor, Antigravity…) vẫn làm được"
                )
            if kind == "claude-plugin" and "@" not in str(item.get("id") or ""):
                problems.append(f"{where}: `id` của plugin phải dạng name@marketplace")
            if kind == "cli" and not item.get("name"):
                problems.append(f"{where}: CLI thiếu `name`")
            if kind == "mcp":
                name, config = item.get("name"), item.get("config")
                if not name or not isinstance(config, dict):
                    problems.append(f"{where}: MCP cần `name` và `config` dạng mapping")
                    continue
                problems += [f"{where}: {p}" for p in secret_problems(config)]
                previous = mcp_seen.setdefault(str(name), (pack_name, config))
                if previous[1] != config:
                    problems.append(
                        f"{where}: MCP `{name}` có hai cấu hình khác nhau ({previous[0]} và {pack_name}) — "
                        "hai pack cùng bật thì không biết lấy bản nào"
                    )
    return problems


def managed_mcp(registry: dict[str, Any]) -> set[str]:
    """Tên MỌI server do pack quản lý — server nằm ngoài tập này là của người dùng, không bao giờ bị đụng."""
    return {
        str(item["name"])
        for pack in registry["packs"]
        for item in pack_integrations(registry, pack)
        if item.get("kind") == "mcp" and item.get("name")
    }


def expected_mcp(registry: dict[str, Any], enabled: list[str]) -> dict[str, Any]:
    servers: dict[str, Any] = {}
    for pack in enabled:
        for item in pack_integrations(registry, str(pack)):
            if item.get("kind") == "mcp":
                servers[str(item["name"])] = item["config"]
    return servers


def _read_mcp(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"mcpServers": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PackError(f"{path.name} không phải JSON hợp lệ: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.setdefault("mcpServers", {}), dict):
        raise PackError(f"{path.name}: `mcpServers` phải là mapping")
    return data


def _desired_servers(registry: dict[str, Any], enabled: list[str], current: dict[str, Any]) -> dict[str, Any]:
    managed, expected = managed_mcp(registry), expected_mcp(registry, enabled)
    kept = {name: cfg for name, cfg in current.items() if name not in managed}
    return {**kept, **expected}


def mcp_drift(registry: dict[str, Any], enabled: list[str], path: Path | None = None) -> list[str]:
    current = _read_mcp(path or mcp_path())["mcpServers"]
    desired = _desired_servers(registry, enabled, current)
    drift = [f"thiếu MCP `{n}` của pack đang bật" for n in sorted(set(desired) - set(current))]
    drift += [f"MCP `{n}` của pack đã tắt vẫn còn" for n in sorted(set(current) - set(desired))]
    drift += [
        f"MCP `{n}` lệch cấu hình trong sổ đăng ký"
        for n in sorted(set(current) & set(desired))
        if current[n] != desired[n]
    ]
    return drift


def sync_mcp(registry: dict[str, Any], enabled: list[str], path: Path | None = None) -> tuple[list[str], list[str]]:
    """Ghi `.mcp.json` = server của người dùng + server của pack đang bật. Trả (thêm, gỡ). Chạy lại không đổi gì."""
    target = path or mcp_path()
    data = _read_mcp(target)
    current = data["mcpServers"]
    desired = _desired_servers(registry, enabled, current)
    added = sorted(n for n in desired if current.get(n) != desired[n])
    removed = sorted(set(current) - set(desired))
    if added or removed or not target.is_file():
        data["mcpServers"] = dict(sorted(desired.items()))
        target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return added, removed


def _integration_line(item: dict[str, Any]) -> str:
    kind = item.get("kind")
    if kind == "claude-plugin":
        market = f"/plugin marketplace add {item['marketplace']} rồi " if item.get("marketplace") else ""
        return f"plugin Claude Code `{item['id']}` — {market}/plugin install {item['id']} · {item.get('why', '')}"
    if kind == "mcp":
        return f"MCP `{item['name']}` (ghi vào .mcp.json) · {item.get('why', '')}"
    found = "có" if shutil.which(str(item.get("name"))) else "CHƯA có trên PATH"
    hint = f" — cài: {item['install']}" if item.get("install") and found != "có" else ""
    return f"CLI `{item['name']}` ({found}){hint} · {item.get('why', '')}"


def _print_integrations(registry: dict[str, Any], name: str, indent: str = "   ") -> None:
    for item in pack_integrations(registry, name):
        print(f"{indent}→ {_integration_line(item)}")


def _skill_meta(name: str, pack: str) -> dict[str, Any]:
    """Frontmatter của skill: bản đã cài nếu có, không thì bản nguồn trong packs/ (để sinh mục lục trước khi cài)."""
    skill_dir = SKILLS_DIR / name
    if not (skill_dir / "SKILL.md").is_file() and pack != "lõi":
        skill_dir = ROOT / "packs" / pack / "skills" / name
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    parts = text.split("---\n", 2)
    data = yaml.safe_load(parts[1]) if len(parts) == 3 else {}
    return data if isinstance(data, dict) else {}


def render_skills_index(registry: dict[str, Any], enabled: list[str]) -> str:
    """Mục lục skill + công cụ đi kèm cho MỌI agent — kể cả công cụ không tự nạp `.claude/skills/`."""
    owner = {str(s): "lõi" for s in registry["core"]}
    for pack in sorted(enabled):
        owner.update({s: str(pack) for s in pack_skills(registry, str(pack))})
    lines = [
        "# SKILLS.md — mục lục kỹ năng đang bật (SINH TỰ ĐỘNG, đừng sửa tay)",
        "",
        "> Sinh bởi `python scripts/packs.py --install/--remove`; CI kiểm khớp (`--check`). Skill được cài ở HAI nơi giống",
        "> hệt nhau: `.claude/skills/` (Claude Code tự nạp) và `.agents/skills/` (Codex, Cursor, Antigravity, Gemini CLI,",
        '> GitHub Copilot, OpenCode tự nạp). Công cụ không tự nạp ở đâu cả (Aider…): khi việc khớp cột "Dùng khi", MỞ',
        "> file SKILL.md tương ứng và làm theo — nội dung là Markdown thuần, không cần kết nối gì.",
        "",
        "| Skill | Pack | Dùng khi (trích mô tả) | File |",
        "|---|---|---|---|",
    ]
    for name in sorted(owner, key=lambda n: (owner[n] != "lõi", owner[n], n)):
        description = " ".join(str(_skill_meta(name, owner[name]).get("description", "")).split())
        when = description[description.find("Dùng ") :] if "Dùng " in description else description
        lines.append(f"| `{name}` | {owner[name]} | {when.replace('|', '/')} | `.claude/skills/{name}/SKILL.md` |")
    tools = [(str(p), i) for p in sorted(enabled) for i in pack_integrations(registry, str(p))]
    if tools:
        lines += [
            "",
            "## Công cụ đi kèm — và cách làm khi KHÔNG có kết nối đó",
            "",
            "| Pack | Công cụ | Không có thì |",
            "|---|---|---|",
        ]
        for pack, item in tools:
            label = item.get("id") or item.get("name")
            fallback = item.get("fallback") or f"cài: {item.get('install', 'xem why')}"
            lines.append(f"| {pack} | {item['kind']} `{label}` | {' '.join(str(fallback).split()).replace('|', '/')} |")
    return "\n".join(lines) + "\n"


def write_skills_index(registry: dict[str, Any], enabled: list[str]) -> None:
    skills_index_path().write_text(render_skills_index(registry, enabled), encoding="utf-8", newline="\n")
    mirror_skills(SKILLS_DIR, agents_skills_dir())


MARKETPLACE_NAME = "agentfold"


def marketplace_path() -> Path:
    return ROOT / ".claude-plugin" / "marketplace.json"


def marketplace_manifest(registry: dict[str, Any]) -> dict[str, Any]:
    """Manifest marketplace của Claude Code, SINH từ sổ đăng ký: plugin `core` (skill lõi ở `.claude/skills/`, nguồn là gốc repo)
    và mỗi pack `ready` một plugin (nguồn là thư mục pack, thư mục con `skills/` được nhận tự động).
    Cấu trúc theo https://code.claude.com/docs/en/plugins/marketplace-reference (kiểm 2026-10-04)."""
    plugins: list[dict[str, Any]] = [
        {
            "name": "core",
            "source": ".",
            "description": "Bộ lõi của template: lưới canh, sơ đồ, ADR, vòng đời ticket, đa agent, sửa lỗi, thẩm định ý tưởng.",
            "skills": [f"./.claude/skills/{name}" for name in registry["core"]],
        }
    ]
    for name, pack in registry["packs"].items():
        if pack.get("status") != "ready":
            continue
        skills = ", ".join(str(s["name"]) for s in pack.get("skills", []))
        plugins.append(
            {
                "name": str(name),
                "source": f"./packs/{name}",
                "description": f"{pack.get('label', name)} — skill: {skills}.",
            }
        )
    return {
        "name": MARKETPLACE_NAME,
        "description": "Kỹ năng cho dự án AI agent: bộ lõi và các pack theo loại việc (backend, dữ liệu, kiểm thử, hạ tầng…).",
        "owner": {"name": "hwngkm"},
        "plugins": plugins,
    }


def render_marketplace(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"


def write_marketplace(registry: dict[str, Any]) -> None:
    target = marketplace_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_marketplace(marketplace_manifest(registry)), encoding="utf-8", newline="\n")


def agents_skills_dir() -> Path:
    """Thư mục skill chung của Codex, Cursor, Antigravity, Gemini CLI, Copilot, OpenCode. Tính từ ROOT lúc gọi."""
    return ROOT / ".agents" / "skills"


def _skill_files(root: Path) -> dict[str, bytes]:
    """Mọi tệp thuộc các thư mục skill (có SKILL.md) dưới `root`, khoá là đường dẫn tương đối POSIX."""
    if not root.is_dir():
        return {}
    files: dict[str, bytes] = {}
    for skill in sorted(p for p in root.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()):
        for path in sorted(skill.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def skills_tree_drift(src: Path, dst: Path) -> list[str]:
    want, have = _skill_files(src), _skill_files(dst)
    drift = [f"thiếu {p}" for p in sorted(set(want) - set(have))]
    drift += [f"thừa {p}" for p in sorted(set(have) - set(want))]
    drift += [f"khác nội dung {p}" for p in sorted(set(want) & set(have)) if want[p] != have[p]]
    return drift


def mirror_skills(src: Path, dst: Path) -> set[str]:
    """Đưa `dst` về đúng bản sao từng byte của `src` (chỉ thư mục skill). Trả tên skill đã đổi; chạy lại không đổi gì."""
    want, have = _skill_files(src), _skill_files(dst)
    changed: set[str] = set()
    for rel in sorted(set(have) - set(want)):
        (dst / rel).unlink()
        changed.add(rel.split("/", 1)[0])
    for rel, content in want.items():
        if have.get(rel) != content:
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            changed.add(rel.split("/", 1)[0])
    if dst.is_dir():
        for folder in sorted((p for p in dst.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            if not any(folder.iterdir()):
                folder.rmdir()
    return changed


def agents_skills_drift() -> list[str]:
    return [f".agents/skills: {p}" for p in skills_tree_drift(SKILLS_DIR, agents_skills_dir())]


def installed_skills() -> set[str]:
    if not SKILLS_DIR.is_dir():
        return set()
    return {p.name for p in SKILLS_DIR.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()}


def _cmd_list(registry: dict[str, Any], profile: dict[str, Any]) -> int:
    enabled = set(profile["packs"])
    print(f"Loại dự án: {profile.get('project_type', 'unspecified')}")
    print(f"Skill lõi (luôn cài): {', '.join(registry['core'])}\n")
    for name, pack in registry["packs"].items():
        mark = "✅ đang bật" if name in enabled else ("· sẵn sàng" if pack.get("status") == "ready" else "· chưa viết")
        print(f"{name:<10} {mark:<14} {pack.get('label', '')}")
        for skill in pack.get("skills", []):
            print(f"             - {skill['name']}: {skill.get('summary', '')}")
        _print_integrations(registry, name, indent="             ")
    suggestions = registry.get("project_types") or {}
    current = profile.get("project_type")
    if current in suggestions:
        print(f"\nGợi ý cho `{current}`: {', '.join(suggestions[current]) or '(chỉ lõi)'}")
    else:
        print("\nGợi ý theo loại dự án:")
        for kind, packs in suggestions.items():
            print(f"  {kind:<14} {', '.join(packs) or '(chỉ lõi)'}")
    return 0


def _cmd_install(registry: dict[str, Any], profile: dict[str, Any], name: str) -> int:
    pack = registry["packs"].get(name)
    if pack is None:
        raise PackError(f"không có pack `{name}` — pack hiện có: {', '.join(sorted(registry['packs']))}")
    if pack.get("status") != "ready":
        raise PackError(
            f"pack `{name}` mới chốt phạm vi, CHƯA có nội dung (status: {pack.get('status')}).\n"
            f"   Viết nội dung trước: packs/README.md nói cách thêm, rồi đổi status thành `ready`."
        )
    source = ROOT / "packs" / name / "skills"
    if not source.is_dir():
        raise PackError(f"pack `{name}` khai `ready` nhưng thiếu thư mục {source.relative_to(ROOT).as_posix()}")
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    for skill in pack_skills(registry, name):
        src = source / skill
        if not (src / "SKILL.md").is_file():
            raise PackError(f"pack `{name}` khai skill `{skill}` nhưng thiếu {skill}/SKILL.md")
        shutil.copytree(src, SKILLS_DIR / skill, dirs_exist_ok=True)
        print(f"   + {skill}")
    enabled = profile["packs"] if name in profile["packs"] else [*profile["packs"], name]
    if name not in profile["packs"]:
        write_enabled(enabled)
    added, _removed = sync_mcp(registry, enabled)
    write_skills_index(registry, enabled)
    print(f"✅ Đã bật pack `{name}`. Ghi vào docs/design/project-profile.yaml.")
    if added:
        print(f"   .mcp.json: thêm {', '.join(added)} — server ngoài nhận dữ liệu phiên làm việc, xem `why` bên dưới.")
    if pack_integrations(registry, name):
        print("   Công cụ đi kèm (plugin/CLI người tự cài một lần mỗi máy; MCP đã ghi sẵn):")
        _print_integrations(registry, name)
    return 0


def _cmd_remove(registry: dict[str, Any], profile: dict[str, Any], name: str) -> int:
    if name not in profile["packs"]:
        raise PackError(f"pack `{name}` không đang bật")
    core = {str(s) for s in registry["core"]}
    còn_lại = [p for p in profile["packs"] if p != name]
    # Skill mà pack KHÁC vẫn cần thì giữ lại — hai pack chia nhau một skill là hợp lệ.
    giữ = core | {s for p in còn_lại for s in pack_skills(registry, p)}
    for skill in pack_skills(registry, name):
        if skill in giữ:
            continue
        target = SKILLS_DIR / skill
        if target.is_dir():
            shutil.rmtree(target)
            print(f"   - {skill}")
    write_enabled(còn_lại)
    _added, removed = sync_mcp(registry, còn_lại)
    write_skills_index(registry, còn_lại)
    print(f"✅ Đã tắt pack `{name}`." + (f" .mcp.json: gỡ {', '.join(removed)}." if removed else ""))
    return 0


def _cmd_check(registry: dict[str, Any], profile: dict[str, Any]) -> int:
    expected = expected_skills(registry, profile)
    installed = installed_skills()
    thiếu = sorted(expected - installed)
    thừa = sorted(installed - expected)
    lỗi_tích_hợp = integration_problems(registry) + mcp_drift(registry, profile["packs"]) + agents_skills_drift()
    if thiếu or thừa:
        pass  # báo ở dưới; mục lục chỉ so khi bộ skill đã khớp
    elif not skills_index_path().is_file() or skills_index_path().read_text(encoding="utf-8") != render_skills_index(
        registry, profile["packs"]
    ):
        lỗi_tích_hợp.append("SKILLS.md lệch skill đang bật — chạy `python scripts/packs.py --sync-index`")
    if lỗi_tích_hợp:
        print("🔴 Công cụ đi kèm pack sai khai báo hoặc .mcp.json lệch profile:", file=sys.stderr)
        print("\n".join(f"   - {p}" for p in lỗi_tích_hợp), file=sys.stderr)
        return 1
    if thiếu or thừa:
        print("🔴 .claude/skills/ lệch docs/design/project-profile.yaml:", file=sys.stderr)
        if thiếu:
            print(f"   thiếu (profile bật nhưng chưa cài): {', '.join(thiếu)}", file=sys.stderr)
        if thừa:
            print(f"   thừa (đã cài nhưng profile không bật): {', '.join(thừa)}", file=sys.stderr)
        print("   Sửa: python scripts/packs.py --install <pack> / --remove <pack>", file=sys.stderr)
        return 1
    print(f"✅ {len(installed)} skill khớp project-profile.yaml.")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="liệt kê pack và trạng thái")
    group.add_argument("--install", metavar="PACK", help="bật một pack")
    group.add_argument("--remove", metavar="PACK", help="tắt một pack")
    group.add_argument("--check", action="store_true", help="CI: đỏ nếu skill đã cài lệch profile")
    group.add_argument("--sync-index", action="store_true", help="sinh lại SKILLS.md từ skill đang bật")
    group.add_argument(
        "--sync-marketplace", action="store_true", help="sinh lại .claude-plugin/marketplace.json từ sổ đăng ký"
    )
    group.add_argument("--set-type", metavar="LOẠI", help="ghi loại dự án (không tự bật pack)")
    args = parser.parse_args()

    try:
        registry = load_registry()
        if args.set_type:
            hợp_lệ = set(registry.get("project_types") or {})
            if args.set_type not in hợp_lệ:
                raise PackError(f"loại dự án `{args.set_type}` không có — chọn: {', '.join(sorted(hợp_lệ))}")
            write_project_type(args.set_type)
            print(f"✅ project_type = `{args.set_type}`")
            gợi_ý = registry["project_types"][args.set_type]
            print(f"   Pack gợi ý: {', '.join(gợi_ý) or '(chỉ lõi)'} — bật bằng `--install <pack>` khi cần.")
            return 0
        if args.sync_marketplace:
            write_marketplace(registry)
            print("✅ Đã sinh lại .claude-plugin/marketplace.json")
            return 0
        profile = load_profile()
        if args.list:
            return _cmd_list(registry, profile)
        if args.install:
            return _cmd_install(registry, profile, args.install)
        if args.remove:
            return _cmd_remove(registry, profile, args.remove)
        if args.sync_index:
            write_skills_index(registry, profile["packs"])
            print("✅ Đã sinh lại SKILLS.md")
            return 0
        return _cmd_check(registry, profile)
    except AgentctlError as exc:
        print(f"🔴 {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
