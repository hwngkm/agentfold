"""`skill_evals --run` phải tìm một `bash` CHẠY ĐƯỢC THẬT, như `tests/guards/test_cloud_setup.py`.

Lỗi (thấy trên máy Windows sau khi chuyển lệnh agent sang chạy qua shell): `bash` đầu PATH là launcher WSL không có distro nên `bash -c ...` thoát lỗi, `run_agent` ghi `error`
và `tests/guards/test_skill_evals.py` đỏ ở bài kiểm oracle. Ở đây mô phỏng bằng một `bash` giả đầu PATH (thoát mã 1 như launcher đó);
Git Bash được thay bằng đường dẫn bash thật của máy chạy test qua hằng `GIT_BASH`.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from scripts import skill_evals as se

GIT_BASH_DEFAULT = r"C:\Program Files\Git\bin\bash.exe"


def _working_bash() -> str | None:
    """Bash chạy được thật, dò độc lập với mã đang kiểm (như `tests/guards/test_cloud_setup.py`): trên Windows `bash` đầu PATH có thể là launcher WSL."""
    entries = [shutil.which("bash", path=e) for e in os.environ.get("PATH", "").split(os.pathsep) if e]
    for candidate in [*entries, GIT_BASH_DEFAULT]:
        if not candidate:
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "echo ok"], capture_output=True, text=True, check=False, timeout=15
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == "ok":
            return candidate
    return None


REAL_BASH = _working_bash()
needs_bash = pytest.mark.skipif(REAL_BASH is None, reason="máy chạy test không có bash để làm 'Git Bash' giả lập")


def _scenario() -> dict:
    return {
        "id": "bash-lookup",
        "prompt": "tạo out.txt",
        "setup": {"files": {"README.md": "x\n"}},
        "checks": [{"kind": "file_exists", "glob": "out.txt"}],
        "oracle": {"files": {"out.txt": "x"}},
    }


AGENT_OK = 'printf %s "$(cat {prompt_file})" > out.txt'


def _fake_wsl_dir(tmp_path: Path) -> Path:
    """Thư mục chứa một `bash` giả (launcher WSL không distro: thoát mã 1)."""
    fake_dir = tmp_path / "fake-bin"
    fake_dir.mkdir()
    fake = fake_dir / "bash"
    fake.write_text(
        '#!/bin/sh\necho "Windows Subsystem for Linux has no installed distributions." >&2\nexit 1\n', encoding="utf-8"
    )
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    return fake_dir


def _fake_wsl_first_on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *after: str) -> None:
    """Đặt `bash` giả lên ĐẦU PATH; `after` là các thư mục chèn ngay sau nó (vd. nơi có Git Bash chạy được)."""
    parts = [str(_fake_wsl_dir(tmp_path)), *after, os.environ["PATH"]]
    monkeypatch.setenv("PATH", os.pathsep.join(parts))


@needs_bash
def test_bash_dau_path_la_launcher_wsl_thi_dung_git_bash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_wsl_first_on_path(tmp_path, monkeypatch)
    monkeypatch.setattr(se, "GIT_BASH", REAL_BASH)
    assert se.find_bash() == REAL_BASH, "phải bỏ qua bash đầu PATH đã hỏng và dùng Git Bash chạy được"
    status, results = se.run_agent(_scenario(), AGENT_OK, timeout=30)
    assert status == "pass", [r.detail for r in results]


@needs_bash
def test_bash_hong_dau_path_thi_thu_bash_ke_tiep_tren_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows có Git Bash trên PATH sau launcher WSL: phải dùng được mà không cần đường dẫn cài mặc định."""
    assert REAL_BASH is not None
    _fake_wsl_first_on_path(tmp_path, monkeypatch, str(Path(REAL_BASH).parent))
    monkeypatch.setattr(se, "GIT_BASH", str(tmp_path / "khong-co" / "bash.exe"))
    assert se.find_bash() == REAL_BASH


def test_khong_co_bash_chay_duoc_thi_bao_loi_ro_rang(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = str(_fake_wsl_dir(tmp_path) / "bash")
    # Tự ép môi trường: chỉ còn một bash hỏng và một đường dẫn Git Bash không tồn tại, bất kể máy chạy test có gì trên PATH.
    monkeypatch.setattr(se, "_bash_candidates", lambda: [fake, str(tmp_path / "khong-co" / "bash.exe")])
    assert se.find_bash() is None
    with pytest.raises(se.BashNotFoundError) as exc:
        se.build_argv(AGENT_OK, tmp_path / "prompt.txt")
    message = str(exc.value)
    assert "bash" in message and "WSL" in message and "Git Bash" in message, message
    status, results = se.run_agent(_scenario(), AGENT_OK, timeout=30)
    assert status == "error"
    assert any("bash" in r.detail and "Git Bash" in r.detail for r in results), "lỗi phải nói rõ, không im lặng"


def test_run_thieu_bash_thoat_ma_3_va_noi_ro(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(se, "find_bash", lambda: None)
    assert se.main(["--run", "--agent-cmd", "true"]) == 3
    assert "bash" in capsys.readouterr().err


@needs_bash
def test_bash_dau_path_chay_duoc_thi_giu_nguyen_hanh_vi() -> None:
    assert se.find_bash() == REAL_BASH
    argv = se.build_argv(AGENT_OK, Path("/tmp/prompt.txt"))
    assert argv[0] == REAL_BASH and argv[1] == "-c"
    status, results = se.run_agent(_scenario(), AGENT_OK, timeout=30)
    assert status == "pass", [r.detail for r in results]
