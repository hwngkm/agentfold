"""scope-guard chạy lại được trên runner tự host đã có worktree cũ.

Lỗi gốc (PR cloud đầu tiên): `git worktree add "$RUNNER_TEMP/base"` chết với "missing but already registered worktree"
vì lần chạy trước để lại đăng ký worktree mà thư mục `_temp` đã bị dọn. Job chết trước khi kiểm phạm vi; re-run vẫn đỏ.
Test chạy ĐÚNG đoạn `run` của workflow trên một repo thật có worktree mồ côi.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts import skill_evals as se

ROOT = Path(__file__).resolve().parents[2]


def _steps() -> list[dict]:
    workflow = yaml.safe_load((ROOT / ".github/workflows/scope-guard.yml").read_text(encoding="utf-8"))
    return workflow["jobs"]["scope-guard"]["steps"]


def _step_with(text: str) -> dict:
    return next(step for step in _steps() if text in str(step.get("run", "")))


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "a.txt").write_text("x", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "chore(x): khoi tao")
    return repo


def _path_for_step(bash: str) -> str:
    """PATH tối thiểu cho đoạn `run`: bash chạy được thật + git (trên Windows cả hai nằm ngoài `/usr/bin`) cộng các thư mục POSIX quen thuộc."""
    dirs = [str(Path(bash).parent)]
    git = shutil.which("git")
    if git:
        dirs.append(str(Path(git).parent))
    return os.pathsep.join([*dirs, "/usr/bin", "/bin", "/usr/local/bin"])


def _run(step: dict, repo: Path, runner_temp: Path, base_sha: str) -> subprocess.CompletedProcess[str]:
    bash = se.find_bash()  # `bash` đầu PATH trên Windows có thể là launcher WSL không distro
    assert bash is not None, "máy chạy test cần một bash chạy được (Linux/CI có sẵn, Windows cần Git Bash)"
    env = {
        "PATH": _path_for_step(bash),
        "HOME": str(repo),
        "RUNNER_TEMP": str(runner_temp),
        "BASE_SHA": base_sha,
    }
    return subprocess.run([bash, "-e", "-c", step["run"]], cwd=repo, env=env, capture_output=True, text=True)


def test_dung_worktree_goc_chay_lai_duoc_khi_con_dang_ky_mo_coi(repo: Path, tmp_path: Path) -> None:
    runner_temp = tmp_path / "temp"
    runner_temp.mkdir()
    sha = _git(repo, "rev-parse", "HEAD").strip()
    step = _step_with("git worktree add")
    first = _run(step, repo, runner_temp, sha)
    assert first.returncode == 0, first.stderr
    # runner dọn _temp nhưng đăng ký worktree trong .git còn nguyên → đúng hiện trường của lần chạy hỏng
    for path in (runner_temp / "base").iterdir():
        path.unlink() if path.is_file() else None
    (runner_temp / "base" / ".git").unlink(missing_ok=True)
    (runner_temp / "base").rmdir()
    second = _run(step, repo, runner_temp, sha)
    assert second.returncode == 0, second.stderr
    assert (runner_temp / "base" / "a.txt").is_file()


def test_dung_worktree_goc_chay_lai_duoc_khi_thu_muc_con_nguyen(repo: Path, tmp_path: Path) -> None:
    runner_temp = tmp_path / "temp"
    runner_temp.mkdir()
    sha = _git(repo, "rev-parse", "HEAD").strip()
    step = _step_with("git worktree add")
    assert _run(step, repo, runner_temp, sha).returncode == 0
    again = _run(step, repo, runner_temp, sha)
    assert again.returncode == 0, again.stderr


def test_buoc_cuoi_don_worktree_ke_ca_khi_job_loi() -> None:
    steps = _steps()
    cleanup = [s for s in steps if "git worktree remove" in str(s.get("run", ""))]
    assert cleanup, "thiếu bước dọn worktree gốc"
    assert str(cleanup[-1].get("if", "")).strip() == "always()", "bước dọn phải chạy cả khi job lỗi"
    assert steps.index(cleanup[-1]) == len(steps) - 1, "bước dọn phải là bước cuối"


def test_nguyen_tac_bo_kiem_lay_tu_nhanh_goc_khong_doi() -> None:
    add = _step_with("git worktree add")
    assert "BASE_SHA" in add["run"] and "RUNNER_TEMP" in add["run"]
    checker = _step_with("check-scope")
    assert "runner.temp" in str(checker.get("working-directory", ""))
