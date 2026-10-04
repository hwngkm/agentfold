"""Dự án tạo bằng `bootstrap.py --apply` không kế thừa danh tính chủ template.

Đã gặp thật khi audit trên bản clone mới: sau bootstrap, CODEOWNERS vẫn trỏ mọi đường dẫn tới tài khoản chủ
template (dự án mới vô tình bắt người lạ duyệt), và lệnh cài skill trong README bị đổi thành `<chủ>/<slug-mới>` —
một repo không tồn tại.

Khoá gì: sau `--apply`, `github_handles` trong team-profile rỗng, CODEOWNERS chỉ còn handle giữ chỗ `@rN-...`, và
các dòng lệnh cài từ template trong README giữ nguyên.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.agentctl.team_profile import load_team_profile

ROOT = Path(__file__).resolve().parents[2]
HANDLE = "@template-owner"
INSTALL = (
    "npx skills add template-owner/agentfold --list --full-depth\n"
    "/plugin marketplace add template-owner/agentfold\n"
    "/plugin install core@agentfold\n"
)


def _template_copy(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for rel in (
        "scripts/bootstrap.py",
        "tools",
        "docs/design/presets",
        "coordination/policy.yaml",
        "docs/design/team-profile.yaml",
    ):
        src = ROOT / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, dst)
    profile = root / "docs/design/team-profile.yaml"
    text = profile.read_text(encoding="utf-8")
    text = re.sub(r"(?ms)^github_handles:.*", f'github_handles:\n  R1: "{HANDLE}" # chủ template\n', text)
    profile.write_text(text, encoding="utf-8")
    (root / ".github").mkdir()
    (root / ".github/CODEOWNERS").write_text(f"*  {HANDLE}\n", encoding="utf-8")
    (root / "README.md").write_text(f"# Agentfold\n\n```bash\n{INSTALL}```\n", encoding="utf-8")
    return root


@pytest.fixture()
def bootstrapped(tmp_path: Path) -> Path:
    root = _template_copy(tmp_path)
    result = subprocess.run(
        [sys.executable, "scripts/bootstrap.py", "--name", "Du An Moi", "--slug", "du-an-moi", "--apply"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return root


def test_profile_moi_khong_con_handle_cua_chu_template(bootstrapped: Path) -> None:
    text = (bootstrapped / "docs/design/team-profile.yaml").read_text(encoding="utf-8")
    assert HANDLE not in text
    profile = load_team_profile(bootstrapped)
    assert re.match(r"@r1-", profile.role("R1").handle), "chưa khai handle thì phải về handle giữ chỗ"


def test_codeowners_moi_chi_con_handle_giu_cho(bootstrapped: Path) -> None:
    text = (bootstrapped / ".github/CODEOWNERS").read_text(encoding="utf-8")
    rules = [line for line in text.splitlines() if line.strip() and not line.startswith("#")]
    assert rules, "CODEOWNERS phải được sinh lại, không bị xoá trắng"
    assert HANDLE not in text
    assert all(re.search(r"@r\d+-", line) for line in rules)


def test_lenh_cai_tu_template_trong_readme_giu_nguyen(bootstrapped: Path) -> None:
    text = (bootstrapped / "README.md").read_text(encoding="utf-8")
    assert text.startswith("# Du An Moi"), "tên dự án vẫn phải được đổi"
    assert INSTALL in text, "lệnh cài skill trỏ tới template, không tới repo mới chưa tồn tại"
