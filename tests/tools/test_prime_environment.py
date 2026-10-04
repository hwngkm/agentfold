"""`prime` phát hiện môi trường chưa dựng và chỉ ĐÚNG MỘT lệnh sửa.

Ca thử cloud 04/10/2026: repo đã clone nhưng Setup script không chạy → `core.hooksPath` rỗng (hook git không hoạt động, phạm vi và
định dạng commit không được kiểm cục bộ) và thiếu pytest/ruff/mypy. Lỗi im lặng nguy hiểm. `prime --offline` (hook SessionStart)
chỉ CẢNH BÁO, không tự cài gì; `--fix-env` mới chạy script, khi người cho phép.
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.tools.helpers import run_git
from tools.agentctl import cli
from tools.agentctl.cli import main
from tools.agentctl.prime import render_prime

MOMENT = datetime(2026, 10, 4, 9, 0, tzinfo=UTC)
FIX = "bash scripts/cloud_setup.sh"


def _repo(tmp_path: Path, git_isolated: None, *, hooks_path: str | None) -> Path:
    run_git(tmp_path, "init", "--quiet", "--initial-branch=main")
    if hooks_path is not None:
        run_git(tmp_path, "config", "core.hooksPath", hooks_path)
    return tmp_path


def _prime(repo: Path) -> str:
    return render_prime(repo, agent=None, fetch=False, moment=MOMENT)


def _tools_present(monkeypatch: pytest.MonkeyPatch, missing: set[str] = frozenset()) -> None:  # type: ignore[assignment]
    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *a, **k: None if name in missing else real("os"))


def test_hooks_path_rong_bi_canh_bao_kem_dung_mot_lenh_sua(
    tmp_path: Path, git_isolated: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _tools_present(monkeypatch)
    out = _prime(_repo(tmp_path, git_isolated, hooks_path=None))
    assert "core.hooksPath" in out
    assert out.count(FIX) == 1, "đúng MỘT lệnh sửa, không liệt kê nhiều cách"


def test_thieu_cong_cu_bi_canh_bao_nhac_ten_cong_cu(
    tmp_path: Path, git_isolated: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _tools_present(monkeypatch, missing={"ruff", "mypy"})
    out = _prime(_repo(tmp_path, git_isolated, hooks_path="scripts/githooks"))
    assert "ruff" in out and "mypy" in out and "pytest" not in out.split("Môi trường")[1].split("##")[0]
    assert out.count(FIX) == 1


def test_moi_truong_du_thi_khong_canh_bao(tmp_path: Path, git_isolated: None, monkeypatch: pytest.MonkeyPatch) -> None:
    _tools_present(monkeypatch)
    out = _prime(_repo(tmp_path, git_isolated, hooks_path="scripts/githooks"))
    assert FIX not in out
    assert "Môi trường" in out


def test_prime_offline_khong_cai_gi_tu_dong(
    tmp_path: Path, git_isolated: None, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _tools_present(monkeypatch)
    repo = _repo(tmp_path, git_isolated, hooks_path=None)
    calls: list[Path] = []
    monkeypatch.setattr(cli, "fix_environment", lambda r: calls.append(r) or 0, raising=False)
    assert main(["--repo", str(repo), "prime", "--offline"]) == 0
    assert calls == [], "không có --fix-env thì không được chạy script"
    assert FIX in capsys.readouterr().out


def test_fix_env_chay_script_khi_nguoi_cho_phep(
    tmp_path: Path, git_isolated: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    _tools_present(monkeypatch)
    repo = _repo(tmp_path, git_isolated, hooks_path=None)
    calls: list[Path] = []
    monkeypatch.setattr(cli, "fix_environment", lambda r: calls.append(r) or 0, raising=False)
    assert main(["--repo", str(repo), "prime", "--offline", "--fix-env"]) == 0
    assert calls == [repo]
