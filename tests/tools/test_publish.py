"""Phát hành skill qua marketplace plugin của Claude Code (`.claude-plugin/marketplace.json`).

Manifest được SINH từ `packs/registry.yaml` (`python scripts/packs.py --sync-marketplace`); các test này giữ ba điều:
khớp bản sinh, mọi skill nó khai có thật và đúng tên, và không skill nào bị bỏ sót (mồ côi).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from scripts import packs as packs_mod

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / ".claude-plugin" / "marketplace.json"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _manifest() -> dict:
    assert MANIFEST.is_file(), (
        "thiếu .claude-plugin/marketplace.json — chạy `python scripts/packs.py --sync-marketplace`"
    )
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _frontmatter(path: Path) -> dict:
    parts = path.read_text(encoding="utf-8").split("---\n", 2)
    assert len(parts) == 3, f"{path}: thiếu frontmatter"
    data = yaml.safe_load(parts[1])
    assert isinstance(data, dict), f"{path}: frontmatter phải là mapping"
    return data


def _skill_dirs(plugin: dict) -> list[Path]:
    """Thư mục skill mà một plugin trong manifest nạp: danh sách `skills` hoặc thư mục `skills/` của nguồn."""
    source = ROOT / str(plugin["source"])
    if plugin.get("skills"):
        return [ROOT / str(p) for p in plugin["skills"]]
    return sorted(p for p in (source / "skills").iterdir() if p.is_dir())


def test_manifest_khop_ban_sinh_tu_so_dang_ky() -> None:
    expected = packs_mod.marketplace_manifest(packs_mod.load_registry())
    assert _manifest() == expected, "chạy `python scripts/packs.py --sync-marketplace`"
    assert MANIFEST.read_text(encoding="utf-8") == packs_mod.render_marketplace(expected)


def test_cau_truc_manifest_theo_dac_ta_claude_code() -> None:
    data = _manifest()
    assert data["owner"]["name"] and data["description"]
    assert NAME_RE.match(data["name"]) and data["name"] == "agentfold"
    names = [p["name"] for p in data["plugins"]]
    assert len(names) == len(set(names)), "tên plugin trùng"
    assert "core" in names
    for plugin in data["plugins"]:
        assert NAME_RE.match(plugin["name"]) and plugin["description"].strip()
        source = str(plugin["source"])
        assert source == "." or (source.startswith("./") and ".." not in source), source
        assert (ROOT / source).is_dir(), f"nguồn plugin không tồn tại: {source}"


def test_moi_skill_khai_trong_manifest_co_that_va_dung_ten() -> None:
    registry = packs_mod.load_registry()
    for plugin in _manifest()["plugins"]:
        dirs = _skill_dirs(plugin)
        assert dirs, f"plugin {plugin['name']} không có skill nào"
        pack = plugin["name"]
        want = set(registry["core"]) if pack == "core" else {s["name"] for s in registry["packs"][pack]["skills"]}
        assert {d.name for d in dirs} == want, f"plugin {pack}: skill trong manifest lệch sổ đăng ký"
        for d in dirs:
            meta = _frontmatter(d / "SKILL.md")
            assert meta.get("name") == d.name, f"{d}: frontmatter name phải trùng tên thư mục"
            assert str(meta.get("description", "")).strip(), f"{d}: thiếu description"


def test_khong_skill_mo_coi() -> None:
    claimed = {d.resolve() for plugin in _manifest()["plugins"] for d in _skill_dirs(plugin)}
    found = {p.parent.resolve() for p in (ROOT / "packs").glob("*/skills/*/SKILL.md")}
    registry = packs_mod.load_registry()
    found |= {(ROOT / ".claude" / "skills" / str(n)).resolve() for n in registry["core"]}
    assert found - claimed == set(), f"skill không plugin nào khai: {sorted(str(p) for p in found - claimed)}"


def test_chi_pack_ready_co_plugin() -> None:
    registry = packs_mod.load_registry()
    plugin_names = {p["name"] for p in _manifest()["plugins"]} - {"core"}
    ready = {n for n, p in registry["packs"].items() if p.get("status") == "ready"}
    assert plugin_names == ready
