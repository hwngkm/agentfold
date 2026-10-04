"""Mọi pack, skill và công cụ đi kèm dùng được bởi agent KHÔNG có MCP/plugin (Codex, Copilot, Cursor, Antigravity…).

Vì sao: một dự án thường dùng nhiều công cụ AI khác nhau; chỉ Claude Code tự nạp `.claude/skills/` và cài được plugin
Claude Code, và không phải công cụ nào cũng nói MCP. Nếu một kỹ năng chỉ làm được qua MCP, agent khác hoặc bỏ qua bước
đó, hoặc tự đoán — cả hai đều lặng lẽ. Mọi công cụ đều đọc `AGENTS.md` và chạy được shell/git: đó là mẫu số chung.

Khoá gì: (1) mỗi plugin/MCP khai trong sổ có `fallback` (cách làm bằng CLI/HTTP/skill khác); (2) `SKILLS.md` — mục lục
skill đang bật + công cụ kèm `fallback` — tồn tại, khớp skill đang bật, và `AGENTS.md` trỏ tới nó; (3) mục lục liệt kê
fallback của pack khi pack bật.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts import packs as packs_mod

ROOT = Path(__file__).resolve().parents[2]


def test_moi_plugin_va_mcp_trong_so_co_fallback() -> None:
    missing = [
        f"{pack}: {item.get('id') or item.get('name')}"
        for pack, data in packs_mod.load_registry()["packs"].items()
        for item in data.get("integrations") or []
        if item.get("kind") in ("mcp", "claude-plugin") and not str(item.get("fallback") or "").strip()
    ]
    assert missing == []


def test_bo_kiem_bat_mcp_thieu_fallback() -> None:
    registry = yaml.safe_load(
        "version: 1\ncore: []\npacks:\n  a:\n    label: A\n    status: ready\n    skills: [{name: s, summary: x}]\n"
        "    integrations:\n      - {kind: mcp, name: x, why: y, config: {command: npx, args: [x]}}\n"
    )
    assert any("thiếu `fallback`" in p for p in packs_mod.integration_problems(registry))


def test_skills_md_khop_skill_dang_bat_va_agents_md_tro_toi() -> None:
    index = ROOT / "SKILLS.md"
    assert index.is_file(), "thiếu SKILLS.md — chạy `python scripts/packs.py --sync-index`"
    registry, profile = packs_mod.load_registry(), packs_mod.load_profile()
    assert index.read_text(encoding="utf-8") == packs_mod.render_skills_index(registry, profile["packs"]), (
        "SKILLS.md lệch skill đang bật — chạy `python scripts/packs.py --sync-index`"
    )
    assert "SKILLS.md" in (ROOT / "AGENTS.md").read_text(encoding="utf-8"), "AGENTS.md phải trỏ tới SKILLS.md"


def test_muc_luc_liet_ke_fallback_khi_pack_bat() -> None:
    registry = packs_mod.load_registry()
    text = packs_mod.render_skills_index(registry, ["testing"])
    assert "`e2e-browser`" in text and ".claude/skills/e2e-browser/SKILL.md" in text
    assert "npx playwright codegen" in text, "mục lục phải nói cách làm khi không có MCP playwright"


def test_muc_luc_khong_phu_thuoc_thu_tu_bat_pack() -> None:
    """Bật `research` rồi `market` và ngược lại phải ra cùng một SKILLS.md — profile lưu danh sách đã sắp xếp."""
    registry = packs_mod.load_registry()
    assert packs_mod.render_skills_index(registry, ["research", "market"]) == packs_mod.render_skills_index(
        registry, ["market", "research"]
    )
