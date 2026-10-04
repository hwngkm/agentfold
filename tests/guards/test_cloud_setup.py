"""`scripts/cloud_setup.sh`: một nơi duy nhất dựng môi trường cho phiên chạy trên cloud (và máy mới).

Vì sao: ô "Setup script" của môi trường cloud là văn bản dán tay trong giao diện web, không nằm trong git — để logic cài đặt ở đó
thì nó trôi khỏi repo (đổi `requirements-dev.txt`, đổi đường dẫn hook mà quên cập nhật) và không ai review được. Script nằm trong
repo, ô cấu hình chỉ gọi nó. Lưới này khoá những điều khiến nó đáng tin: cú pháp bash đúng, cùng đường dẫn hook với `make setup`,
không cài bằng quyền root, không chạy mã tải từ mạng, và chế độ chạy khô in kế hoạch mà không đổi gì.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cloud_setup.sh"


def _bash() -> str | None:
    """Bash chạy được thật (trên Windows `bash` đầu PATH thường là launcher WSL không có distro)."""
    for candidate in filter(None, [shutil.which("bash"), r"C:\Program Files\Git\bin\bash.exe"]):
        probe = subprocess.run([candidate, "-c", "echo ok"], capture_output=True, text=True, check=False)
        if probe.returncode == 0 and probe.stdout.strip() == "ok":
            return candidate
    return None


BASH = _bash()
TEXT = SCRIPT.read_text(encoding="utf-8")


def test_script_la_bash_khong_quyen_root_va_khong_chay_ma_tai_ve() -> None:
    assert TEXT.startswith("#!/usr/bin/env bash\n")
    assert "\r" not in TEXT, "CRLF làm bash hỏng trên Linux"
    code = "\n".join(
        line for line in TEXT.splitlines() if not line.lstrip().startswith("#")
    )  # chú thích được nhắc sudo
    assert not re.search(r"\bsudo\b|apt(-get)?\s+install|\|\s*(ba)?sh\b|curl\b|wget\b", code), (
        "setup không được cần root, và không chạy mã tải từ mạng"
    )
    assert "requirements-dev.txt" in TEXT


def test_cung_duong_dan_hook_voi_make_setup() -> None:
    make = (ROOT / "Makefile").read_text(encoding="utf-8")
    hooks = re.search(r"git config core\.hooksPath (\S+)", make)
    assert hooks and f"core.hooksPath {hooks.group(1)}" in TEXT, "hai nơi cấu hình hook phải giống nhau"


def test_moi_hook_git_duoc_luu_voi_quyen_thuc_thi() -> None:
    """Git bỏ qua hook không có quyền thực thi — hook `100644` trông như đã cài mà không chạy trên bản clone sạch (Linux/cloud)."""
    listing = subprocess.run(
        ["git", "ls-files", "--stage", "scripts/githooks", "scripts/_pyrun.sh", "scripts/cloud_setup.sh"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert listing, "không đọc được hook nào — lưới rỗng nghĩa"
    not_exec = [line.split("\t", 1)[1] for line in listing if not line.startswith("100755")]
    assert not_exec == [], f"thiếu quyền thực thi trong git: {not_exec} — `git update-index --chmod=+x <tệp>`"


@pytest.mark.skipif(BASH is None, reason="cần bash để chạy script")
def test_cu_phap_bash_dung() -> None:
    result = subprocess.run([BASH or "bash", "-n", str(SCRIPT)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(BASH is None, reason="cần bash để chạy script")
def test_chay_kho_in_ke_hoach_va_khong_doi_gi(tmp_path: Path) -> None:
    before = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout
    env = {**os.environ, "CLOUD_SETUP_DRY_RUN": "1", "SETUP_WEB": "1"}
    result = subprocess.run(
        [BASH or "bash", str(SCRIPT)], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", check=False
    )
    assert result.returncode == 0, result.stderr
    for step in ("requirements-dev.txt", "core.hooksPath", "npm ci"):
        assert step in result.stdout, f"kế hoạch chạy khô thiếu bước `{step}`"
    after = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout
    assert after == before, "chạy khô không được đổi cây làm việc"


@pytest.mark.skipif(BASH is None, reason="cần bash để chạy script")
def test_khong_thay_repo_thi_thoat_0_va_noi_ro(tmp_path: Path) -> None:
    """Ô setup chạy TRƯỚC khi repo được clone (chưa kiểm được trên cloud thật) thì không được làm hỏng việc khởi tạo phiên."""
    result = subprocess.run(
        [BASH or "bash", str(SCRIPT)],
        cwd=tmp_path,
        env={**os.environ, "CLOUD_SETUP_ROOT": str(tmp_path)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0
    assert "chưa thấy repo" in result.stdout
