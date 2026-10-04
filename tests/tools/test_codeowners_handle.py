"""CODEOWNERS dùng handle GitHub THẬT khai trong team-profile.yaml, không còn `@rN-...` giữ chỗ.

Bối cảnh: sau khi chuyển sang `team_size: solo`, bộ sinh điền handle giữ chỗ `@r1-nguoi-duy` cho mọi đường dẫn nên GitHub bỏ qua các dòng đó.
Handle là tài khoản chủ repo (chủ dự án chọn). Handle thật nằm ở trường tuỳ chọn
`github_handles` của profile (tương thích ngược: không khai thì vẫn ra handle giữ chỗ như cũ).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tools.agentctl.team_profile import (
    TeamProfileError,
    build_profile,
    load_team_profile,
    render_codeowners,
    write_team_profile,
)

ROOT = Path(__file__).resolve().parents[2]
PLACEHOLDER = re.compile(r"@r\d+-")
PROFILE = "docs/design/team-profile.yaml"


def _root_with_profile(tmp_path: Path, extra: str = "") -> Path:
    target = tmp_path / PROFILE
    target.parent.mkdir(parents=True)
    target.write_text(f"version: 1\nteam_size: solo\ncomplexity: standard\n{extra}", encoding="utf-8")
    return tmp_path


def test_codeowners_that_khong_con_handle_giu_cho_va_khop_profile() -> None:
    text = (ROOT / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    rules = [line for line in text.splitlines() if line.strip() and not line.startswith("#")]
    assert rules, "CODEOWNERS không có dòng quy tắc nào"
    bad = [line for line in rules if PLACEHOLDER.search(line)]
    assert bad == [], f"còn handle giữ chỗ: {bad[:3]}"
    handle = load_team_profile(ROOT).role("R1").handle
    assert all(line.split()[-1] == handle for line in rules), f"solo: mọi đường dẫn thuộc chủ dự án {handle}"


def test_profile_that_khai_handle_cho_vai_tro_r1() -> None:
    profile = load_team_profile(ROOT)
    assert re.fullmatch(r"@[\w.-]+(/[\w.-]+)?", profile.role("R1").handle), (
        "handle phải dạng @tai-khoan hoặc @to-chuc/nhom"
    )
    assert not PLACEHOLDER.search(profile.role("R1").handle)


def test_render_dung_handle_khai_trong_profile(tmp_path: Path) -> None:
    root = _root_with_profile(tmp_path, 'github_handles:\n  R1: "@example-owner"\n')
    text = render_codeowners(load_team_profile(root))
    assert "@example-owner" in text and not any(
        PLACEHOLDER.search(line) for line in text.splitlines() if not line.startswith("#")
    )


def test_khong_khai_handle_thi_van_ra_handle_giu_cho_nhu_cu(tmp_path: Path) -> None:
    root = _root_with_profile(tmp_path)
    profile = load_team_profile(root)
    assert PLACEHOLDER.match(profile.role("R1").handle), (
        "tương thích ngược: không khai thì handle suy từ tiêu đề vai trò"
    )
    assert profile.role("R1").handle == build_profile("solo", "standard").role("R1").handle


@pytest.mark.parametrize(
    "block",
    [
        'github_handles:\n  R1: "example-owner"\n',  # thiếu @
        'github_handles:\n  R1: "@bad handle"\n',  # có dấu cách
        'github_handles:\n  R9: "@example-owner"\n',  # vai trò không tồn tại trong preset solo
        "github_handles: [R1]\n",  # sai kiểu
        'github_handles:\n  R1: "@-bad"\n',  # tên GitHub không được bắt đầu bằng dấu gạch
    ],
)
def test_handle_sai_bi_tu_choi(tmp_path: Path, block: str) -> None:
    root = _root_with_profile(tmp_path, block)
    with pytest.raises(TeamProfileError):
        load_team_profile(root)


def test_ghi_lai_profile_giu_nguyen_handle_da_khai(tmp_path: Path) -> None:
    """`generate_team_docs.py --team-size ...` ghi đè profile; không được làm mất handle thật."""
    root = _root_with_profile(tmp_path, 'github_handles:\n  R1: "@example-owner"\n')
    write_team_profile(root, "solo", "lite")
    profile = load_team_profile(root)
    assert profile.complexity == "lite" and profile.role("R1").handle == "@example-owner"
