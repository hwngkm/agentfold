"""Pack `infra` khai container-use là tích hợp MCP tuỳ chọn + skill `container-isolation`.

Không chạm `.mcp.json` / `.claude/skills` thật của repo: mọi thao tác bật/tắt chạy trên thư mục tạm.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts import packs as packs_mod

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "packs" / "infra" / "skills" / "container-isolation" / "SKILL.md"


def _item() -> dict:
    items = packs_mod.pack_integrations(packs_mod.load_registry(), "infra")
    found = [i for i in items if i.get("kind") == "mcp" and i.get("name") == "container-use"]
    assert found, "pack infra phải khai MCP `container-use`"
    return found[0]


def test_tich_hop_mcp_container_use_co_why_va_fallback_worktree() -> None:
    item = _item()
    assert item["config"] == {"command": "container-use", "args": ["stdio"]}
    assert str(item["why"]).strip()
    assert "worktree" in str(item["fallback"]).lower(), "không có container-use thì quay về worktree hiện có"
    assert packs_mod.integration_problems(packs_mod.load_registry()) == []


def test_cli_container_use_co_cach_cai_de_nguoi_tu_cai() -> None:
    items = packs_mod.pack_integrations(packs_mod.load_registry(), "infra")
    cli = [i for i in items if i.get("kind") == "cli" and i.get("name") == "container-use"]
    assert cli and str(cli[0].get("install", "")).startswith("https://"), "cài phần mềm hệ thống là việc của người"


def test_skill_container_isolation_khai_bao_va_co_noi_dung() -> None:
    names = packs_mod.pack_skills(packs_mod.load_registry(), "infra")
    assert "container-isolation" in names
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\nname: container-isolation\n")
    assert "Dùng khi" in text.split("---")[1], "description phải có câu 'Dùng khi'"
    for phrase in ("worktree", "không tin cậy", "mạng", "fallback"):
        assert phrase in text, f"skill phải nói về: {phrase}"


def test_bat_tat_pack_giu_mcp_json_va_agents_skills_dong_bo(tmp_path: Path) -> None:
    registry = packs_mod.load_registry()
    mcp = tmp_path / ".mcp.json"
    mcp.write_text(json.dumps({"mcpServers": {"cua-toi": {"command": "x"}}}), "utf-8")

    packs_mod.sync_mcp(registry, ["infra"], mcp)
    servers = json.loads(mcp.read_text(encoding="utf-8"))["mcpServers"]
    assert servers["container-use"] == {"command": "container-use", "args": ["stdio"]}
    assert "cua-toi" in servers and "terraform" in servers
    assert packs_mod.mcp_drift(registry, ["infra"], mcp) == []

    src = tmp_path / "claude-skills"
    (src / "container-isolation").mkdir(parents=True)
    (src / "container-isolation" / "SKILL.md").write_bytes(SKILL.read_bytes())
    dst = tmp_path / "agents-skills"
    packs_mod.mirror_skills(src, dst)
    assert packs_mod.skills_tree_drift(src, dst) == []

    packs_mod.sync_mcp(registry, [], mcp)
    after = json.loads(mcp.read_text(encoding="utf-8"))["mcpServers"]
    assert set(after) == {"cua-toi"}, "tắt pack phải gỡ container-use, giữ server của người dùng"
