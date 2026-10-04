"""Skill được cài cho MỌI agent: `.agents/skills/` là bản sao đúng từng byte của `.claude/skills/`.

Vì sao: `.agents/skills/` là thư mục skill dùng chung mà Codex, Cursor, Antigravity, Gemini CLI, GitHub Copilot,
OpenCode tự nạp (bảng "Supported Agents" của vercel-labs/skills, kiểm 04/10/2026); Claude Code đọc `.claude/skills/`.
Chỉ cài một nơi thì nửa số công cụ không thấy skill nào; hai nơi sửa tay thì lệch nhau âm thầm — agent này làm theo
bản cũ, agent kia theo bản mới. Bản sao (không symlink) vì symlink trong git hỏng trên Windows không bật Developer Mode.

Khoá gì: (1) trong repo, hai thư mục khớp từng byte; (2) cơ chế đồng bộ thêm/xoá/sửa đúng và chạy lại không đổi gì.
"""

from __future__ import annotations

from pathlib import Path

from scripts import packs as packs_mod


def test_agents_skills_khop_tung_byte_voi_claude_skills() -> None:
    assert packs_mod.agents_skills_drift() == [], "chạy `python scripts/packs.py --sync-index` để đồng bộ"


def _skill(root: Path, name: str, body: str) -> None:
    (root / name).mkdir(parents=True, exist_ok=True)
    (root / name / "SKILL.md").write_bytes(body.encode("utf-8"))


def test_dong_bo_them_xoa_sua_va_chay_lai_khong_doi(tmp_path: Path) -> None:
    src, dst = tmp_path / ".claude" / "skills", tmp_path / ".agents" / "skills"
    _skill(src, "a", "---\nname: a\n---\nmới\n")
    _skill(src, "b", "---\nname: b\n---\nb\n")
    (src / "b" / "ref.md").write_bytes(b"tai lieu kem\n")
    _skill(dst, "a", "---\nname: a\n---\ncũ\n")
    _skill(dst, "c", "---\nname: c\n---\nskill đã gỡ\n")

    changed = packs_mod.mirror_skills(src, dst)
    assert changed == {"a", "b", "c"}
    assert packs_mod.skills_tree_drift(src, dst) == []
    assert not (dst / "c").exists(), "skill đã gỡ khỏi .claude/skills phải biến mất khỏi .agents/skills"
    assert (dst / "b" / "ref.md").read_bytes() == b"tai lieu kem\n", "chép cả tệp đi kèm, không chỉ SKILL.md"
    assert packs_mod.mirror_skills(src, dst) == set(), "chạy lại không đổi gì"


def test_bo_kiem_bat_lech(tmp_path: Path) -> None:
    src, dst = tmp_path / "s", tmp_path / "d"
    _skill(src, "a", "x\n")
    _skill(dst, "a", "x\r\n")
    assert any("a/SKILL.md" in p for p in packs_mod.skills_tree_drift(src, dst)), "CRLF cũng là lệch"
