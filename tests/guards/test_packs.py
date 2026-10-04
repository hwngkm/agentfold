"""Bộ kỹ năng đã cài phải khớp `docs/design/project-profile.yaml` — cùng mẫu với `test_team_profile.py`.

Vì sao: mô tả của mọi skill được nạp vào ngữ cảnh ở mọi phiên của mọi agent. Skill mồ côi (cài rồi nhưng
không pack nào bật) là thuế ngữ cảnh vĩnh viễn mà không ai cố ý trả; skill thiếu (profile bật nhưng chưa
cài) là agent đọc hướng dẫn nói "dùng skill X" rồi không tìm thấy X. Cả hai đều trôi âm thầm vì không ai
đọc lại `.claude/skills/` sau khi đổi profile.

Khoá gì: (1) skill đã cài == lõi + skill của các pack đang bật; (2) mọi skill có frontmatter hợp lệ và
`name` trùng tên thư mục — sai tên thì công cụ không gọi được skill đó; (3) sổ đăng ký tự nhất quán;
(4) cài/gỡ thật sự chép và xoá file, không phải chỉ sửa profile.

Sửa khi đỏ: `python scripts/packs.py --install <pack>` hoặc `--remove <pack>`. Đừng sửa tay
`project-profile.yaml` rồi quên chép file (hoặc ngược lại) — đó chính là ca lưới này bắt.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from scripts import packs as packs_mod

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / ".claude" / "skills"


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name} thiếu frontmatter mở đầu bằng `---`"
    _, block, _ = text.split("---\n", 2)
    data = yaml.safe_load(block)
    assert isinstance(data, dict), f"{path.name}: frontmatter phải là mapping"
    return data


def test_skill_da_cai_khop_profile() -> None:
    registry = packs_mod.load_registry()
    profile = packs_mod.load_profile()
    expected = packs_mod.expected_skills(registry, profile)
    installed = packs_mod.installed_skills()
    assert installed == expected, (
        f"thiếu: {sorted(expected - installed)} · thừa: {sorted(installed - expected)} — "
        "chạy `python scripts/packs.py --install/--remove`"
    )


def test_moi_skill_co_frontmatter_hop_le() -> None:
    """`name` sai tên thư mục thì công cụ không gọi được skill; `description` rỗng thì không ai gọi đúng lúc."""
    for skill_dir in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        data = _frontmatter(skill_dir / "SKILL.md")
        assert data.get("name") == skill_dir.name, f"{skill_dir.name}: frontmatter `name` phải trùng tên thư mục"
        mô_tả = str(data.get("description") or "")
        assert len(mô_tả) > 40, f"{skill_dir.name}: `description` quá ngắn để agent biết khi nào nên dùng"
        assert "ùng khi" in mô_tả or "ùng cho" in mô_tả, (
            f"{skill_dir.name}: `description` phải nói RÕ DÙNG KHI NÀO, không chỉ nói skill làm gì — "
            "đó là câu quyết định agent có gọi đúng lúc hay không"
        )


def test_so_dang_ky_tu_nhat_quan() -> None:
    registry = packs_mod.load_registry()
    tên_skill: dict[str, str] = {}
    for tên_pack, pack in registry["packs"].items():
        assert pack.get("label"), f"pack `{tên_pack}` thiếu `label`"
        assert pack.get("status") in {"ready", "planned"}, f"pack `{tên_pack}`: status phải là ready|planned"
        assert pack.get("skills"), f"pack `{tên_pack}` không khai skill nào"
        for skill in pack["skills"]:
            assert skill.get("summary"), f"{tên_pack}/{skill.get('name')} thiếu `summary`"
            # Một skill nằm ở hai pack là hợp lệ, nhưng phải cố ý — ghi ra để người đọc thấy.
            tên_skill.setdefault(str(skill["name"]), tên_pack)
    trùng_lõi = set(registry["core"]) & set(tên_skill)
    assert not trùng_lõi, f"skill vừa ở lõi vừa ở pack thì gỡ pack sẽ xoá nhầm skill lõi: {sorted(trùng_lõi)}"

    for kind, packs in (registry.get("project_types") or {}).items():
        lạ = [p for p in packs if p not in registry["packs"]]
        assert not lạ, f"project_types.{kind} trỏ tới pack không tồn tại: {lạ}"


def test_pack_chua_viet_thi_tu_choi_cai_chu_khong_cai_rong(monkeypatch: pytest.MonkeyPatch) -> None:
    registry = packs_mod.load_registry()
    profile = packs_mod.load_profile()
    planned = [n for n, p in registry["packs"].items() if p.get("status") == "planned"]
    if not planned:
        pytest.skip("không còn pack `planned` để kiểm")
    with pytest.raises(packs_mod.PackError, match="CHƯA có nội dung"):
        packs_mod._cmd_install(registry, profile, planned[0])


def test_cai_va_go_that_su_chep_va_xoa_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Chứng minh cơ chế chạy thật, không chỉ sửa profile.

    Một `--install` chỉ ghi profile mà không chép file vẫn làm `test_skill_da_cai_khop_profile` ĐỎ, nhưng
    đỏ muộn và khó đọc. Test này dựng một pack `ready` giả trong tmp và đi trọn vòng cài → kiểm → gỡ.
    """
    fake_root = tmp_path
    (fake_root / "packs" / "demo" / "skills" / "demo-skill").mkdir(parents=True)
    (fake_root / "packs" / "demo" / "skills" / "demo-skill" / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: Skill thử. Dùng khi chạy lưới canh test_packs.\n---\n\n# thử\n",
        encoding="utf-8",
    )
    (fake_root / "docs" / "design").mkdir(parents=True)
    profile_path = fake_root / "docs" / "design" / "project-profile.yaml"
    profile_path.write_text("version: 1\nproject_type: prototype\npacks: []\n", encoding="utf-8")
    registry_path = fake_root / "packs" / "registry.yaml"
    registry_path.write_text(
        "version: 1\ncore: []\npacks:\n  demo:\n    label: Demo\n    status: ready\n"
        "    skills:\n      - name: demo-skill\n        summary: thử\n",
        encoding="utf-8",
    )
    skills_dir = fake_root / ".claude" / "skills"

    monkeypatch.setattr(packs_mod, "ROOT", fake_root)
    monkeypatch.setattr(packs_mod, "REGISTRY_PATH", registry_path)
    monkeypatch.setattr(packs_mod, "PROFILE_PATH", profile_path)
    monkeypatch.setattr(packs_mod, "SKILLS_DIR", skills_dir)

    registry = packs_mod.load_registry()
    packs_mod._cmd_install(registry, packs_mod.load_profile(), "demo")
    assert (skills_dir / "demo-skill" / "SKILL.md").is_file(), "cài mà không chép file"
    assert packs_mod.load_profile()["packs"] == ["demo"], "cài mà không ghi profile"
    assert packs_mod._cmd_check(registry, packs_mod.load_profile()) == 0

    packs_mod._cmd_remove(registry, packs_mod.load_profile(), "demo")
    assert not (skills_dir / "demo-skill").exists(), "gỡ mà không xoá file"
    assert packs_mod.load_profile()["packs"] == [], "gỡ mà không ghi profile"

    shutil.rmtree(fake_root, ignore_errors=True)


def test_profile_giu_nguyen_chu_thich_khi_ghi_lai(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`yaml.dump` sẽ xoá sạch chú thích — mất luôn phần giải thích vì sao vùng này cần người duyệt."""
    profile_path = tmp_path / "project-profile.yaml"
    profile_path.write_text(
        "# chú thích quan trọng\nversion: 1\nproject_type: llm-app\npacks: []\n# chú thích cuối\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(packs_mod, "PROFILE_PATH", profile_path)
    packs_mod.write_enabled(["ai-llm", "ops"])
    text = profile_path.read_text(encoding="utf-8")
    assert "# chú thích quan trọng" in text and "# chú thích cuối" in text
    assert "packs: [ai-llm, ops]" in text
    assert "project_type: llm-app" in text
