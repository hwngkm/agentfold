"""Cổng đẩy tùy chọn: tắt mặc định, bật thì chặn, nhưng không bao giờ chặn sổ claim của chính agentctl.

Vì sao: chế độ "agent commit cục bộ, người chủ repo duyệt rồi tự đẩy" (dự án thực tế) cần một chốt cục bộ; chốt đó mà
chặn cả nhánh `agent-claims` thì `agentctl start` hỏng — đúng lỗi dễ mắc khi viết hook mà không thử.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "scripts/githooks/pre-push"
SHA = "0" * 40


def _working_bash() -> str | None:
    """Bash chạy được thật. Trên Windows `bash` đầu PATH thường là launcher WSL (System32) không có distro —
    `shutil.which` thấy nó nhưng nó không chạy được gì; phải thử chạy, và thử cả Git Bash."""
    candidates = [shutil.which("bash"), r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"]
    for candidate in filter(None, candidates):
        probe = subprocess.run([candidate, "-c", "echo ok"], capture_output=True, text=True, check=False)
        if probe.returncode == 0 and probe.stdout.strip() == "ok":
            return candidate
    return None


BASH = _working_bash()

pytestmark = pytest.mark.skipif(BASH is None, reason="cần bash để chạy hook")


def _run(repo: Path, stdin: str, env_extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if key != "ALLOW_PUSH"} | (env_extra or {})
    return subprocess.run(
        [BASH or "bash", str(HOOK)],
        cwd=repo,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    return tmp_path


def _gate(repo: Path, value: str) -> None:
    subprocess.run(["git", "config", "agentctl.pushGate", value], cwd=repo, check=True)


MAIN_PUSH = f"refs/heads/feature/X-1 {SHA} refs/heads/feature/X-1 {SHA}\n"
CLAIMS_PUSH = f"refs/heads/agent-claims {SHA} refs/heads/agent-claims {SHA}\n"
MAIL_PUSH = f"refs/heads/agent-mail {SHA} refs/heads/agent-mail {SHA}\n"


def test_tat_mac_dinh_thi_im_lang(repo: Path) -> None:
    assert _run(repo, MAIN_PUSH).returncode == 0


def test_bat_thi_chan_va_noi_cach_mo(repo: Path) -> None:
    _gate(repo, "on")
    result = _run(repo, MAIN_PUSH)
    assert result.returncode == 1
    assert "ALLOW_PUSH=1" in result.stderr


def test_bat_nhung_nguoi_chu_cho_qua(repo: Path) -> None:
    _gate(repo, "on")
    assert _run(repo, MAIN_PUSH, {"ALLOW_PUSH": "1"}).returncode == 0


def test_bat_van_cho_so_claim_di_qua(repo: Path) -> None:
    _gate(repo, "on")
    assert _run(repo, CLAIMS_PUSH).returncode == 0
    mixed = _run(repo, CLAIMS_PUSH + MAIN_PUSH)
    assert mixed.returncode == 1, "đẩy lẫn nhánh khác cùng sổ claim vẫn phải bị chặn"


def test_cong_tat_hook_chung_khong_mo_duoc_cong_day(repo: Path) -> None:
    _gate(repo, "on")
    assert _run(repo, MAIN_PUSH, {"AGENTCTL_HOOKS": "off"}).returncode == 1


def test_bat_van_cho_hop_thu_agent_log_di_qua(repo: Path) -> None:
    """Hộp thư AGENT-LOG (`agent-mail`) là đường giao tiếp giữa agent — chặn nó là cắt liên lạc khi cổng bật."""
    _gate(repo, "on")
    assert _run(repo, MAIL_PUSH).returncode == 0
    assert _run(repo, MAIL_PUSH + CLAIMS_PUSH).returncode == 0
    assert _run(repo, MAIL_PUSH + MAIN_PUSH).returncode == 1
