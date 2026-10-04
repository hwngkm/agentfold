"""Mọi skill của mọi pack `ready` đúng khuôn NGAY TRONG `packs/`, không chỉ khi đã cài.

Vì sao: `test_packs.py` kiểm frontmatter của skill ĐÃ CÀI trong `.claude/skills/`. Template mặc định không bật pack
nào, nên CI không bao giờ đọc nội dung pack — một skill có `description` thiếu câu "Dùng khi" lọt qua CI và chỉ đỏ
ở máy người đầu tiên bật pack. Lỗi đó đã xảy ra khi viết pack `data` (03/10/2026): lưới chỉ bắt được vì người viết
tình cờ cài thử.

Khoá gì: với mỗi pack `status: ready`, mỗi skill khai trong `registry.yaml` có `SKILL.md`, frontmatter có `name`
trùng tên thư mục và `description` nói rõ dùng khi nào; không có thư mục skill thừa không khai trong sổ.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from scripts import packs as packs_mod

ROOT = Path(__file__).resolve().parents[2]


def skill_problems(skill_dir: Path) -> list[str]:
    """Cùng tiêu chí với `test_packs.test_moi_skill_co_frontmatter_hop_le`, trả danh sách thay vì assert."""
    path = skill_dir / "SKILL.md"
    if not path.is_file():
        return [f"{skill_dir.name}: thiếu SKILL.md"]
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or text.count("---\n") < 2:
        return [f"{skill_dir.name}: thiếu frontmatter mở đầu bằng `---`"]
    data = yaml.safe_load(text.split("---\n", 2)[1])
    if not isinstance(data, dict):
        return [f"{skill_dir.name}: frontmatter phải là mapping"]
    problems = []
    if data.get("name") != skill_dir.name:
        problems.append(f"{skill_dir.name}: `name` phải trùng tên thư mục")
    description = str(data.get("description") or "")
    if len(description) <= 40 or not ("ùng khi" in description or "ùng cho" in description):
        problems.append(f"{skill_dir.name}: `description` phải đủ dài và nói rõ DÙNG KHI NÀO")
    body = text.split("---\n", 2)[2]
    if _NAMES_TOOL.search(body) and not _FALLBACK.search(body):
        problems.append(
            f'{skill_dir.name}: nhắc MCP/plugin cụ thể mà không có dòng "Không có MCP/plugin…" — agent không có kết nối '
            "đó (Codex, Copilot, Cursor, Antigravity…) phải biết làm cách khác"
        )
    return problems


#: Skill nhắc một MCP/plugin CỤ THỂ (`MCP \`playwright\``, `plugin \`figma\``) phải có đường khác khi thiếu nó.
_NAMES_TOOL = re.compile(r"(?:MCP|plugin) `[^`]+`|MCP Figma|MCP `", re.IGNORECASE)
_FALLBACK = re.compile(r"Không có (?:MCP|plugin|Figma|kết nối)", re.IGNORECASE)


def test_moi_skill_cua_pack_ready_dung_khuon() -> None:
    registry = packs_mod.load_registry()
    problems: list[str] = []
    for name, pack in registry["packs"].items():
        if pack.get("status") != "ready":
            continue
        source = ROOT / "packs" / name / "skills"
        declared = set(packs_mod.pack_skills(registry, name))
        on_disk = {p.name for p in source.iterdir() if p.is_dir()} if source.is_dir() else set()
        problems += [f"{name}/{s}: khai trong sổ nhưng không có thư mục" for s in sorted(declared - on_disk)]
        problems += [f"{name}/{s}: có thư mục nhưng không khai trong sổ" for s in sorted(on_disk - declared)]
        for skill in sorted(declared & on_disk):
            problems += [f"{name}/{p}" for p in skill_problems(source / skill)]
    assert problems == []


def test_bo_kiem_bat_description_thieu_dung_khi(tmp_path: Path) -> None:
    bad = tmp_path / "data-quality"
    bad.mkdir()
    (bad / "SKILL.md").write_text(
        "---\nname: data-quality\ndescription: Kiểm chất lượng dữ liệu đủ dài để qua ngưỡng độ dài. Dùng sau mỗi"
        " lần nạp.\n---\n",
        encoding="utf-8",
    )
    assert any("DÙNG KHI NÀO" in p for p in skill_problems(bad))
    (bad / "SKILL.md").write_text(
        "---\nname: data-quality\ndescription: Kiểm chất lượng dữ liệu đủ dài để qua ngưỡng. Dùng khi vừa nạp.\n---\n",
        encoding="utf-8",
    )
    assert skill_problems(bad) == []
