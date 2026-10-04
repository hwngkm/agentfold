"""Nhánh do nền tảng đặt tên (`claude/...`) vẫn được kiểm đúng phạm vi ticket nhờ CLAIM của nhánh đó.

Nguồn gắn duy nhất ngoài tên nhánh là claim còn hạn trong sổ `agent-claims` do `agentctl start` ghi. Bên bị kiểm không tự khai
được: trailer trong commit KHÔNG được tính (quyết định của chủ dự án).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.tools.helpers import Workspace, run_git, ticket_text
from tools.agentctl.cli import main
from tools.agentctl.lifecycle import ClaimRequest, claim_ticket

Build = Callable[[Mapping[str, str]], tuple[Workspace, Path]]
PLATFORM_BRANCH = "claude/pensive-test"


def _setup(workspace: Build, *, claim_branch: str | None, files: Mapping[str, str], trailer: bool = False) -> Path:
    ws, repo = workspace({"API-01": ticket_text("API-01", allow=["src/api/orders.py"])})
    if claim_branch is not None:
        claim_ticket(repo, ClaimRequest("API-01", "R3", "agent-a", branch=claim_branch), datetime.now(UTC))
    run_git(repo, "switch", "--quiet", "-c", PLATFORM_BRANCH)
    Workspace.write(repo, files)
    run_git(repo, "add", "-A")
    message = "feat(api): don hang\n\nTicket: API-01" if trailer else "feat(api): don hang"
    run_git(repo, "commit", "--quiet", "-m", message)
    return repo


def _scope(repo: Path, *extra: str) -> int:
    return main(["--repo", str(repo), "check-scope", "--base", "origin/main", *extra])


def test_nhanh_nen_tang_co_claim_hoat_dong_duoc_kiem_theo_ticket_cua_claim(
    workspace: Build, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _setup(workspace, claim_branch=PLATFORM_BRANCH, files={"src/api/orders.py": "x = 1\n"})
    assert _scope(repo) == 0, capsys.readouterr().out


def test_nhanh_nen_tang_co_claim_van_bi_bat_file_ngoai_pham_vi(
    workspace: Build, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _setup(workspace, claim_branch=PLATFORM_BRANCH, files={"src/api/users.py": "y = 2\n"})
    assert _scope(repo) == 1
    assert "src/api/users.py — ngoài `scope.allow`" in capsys.readouterr().out


def test_khong_co_claim_thi_van_la_nhanh_khong_gan_ticket(workspace: Build, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _setup(workspace, claim_branch=None, files={"src/api/orders.py": "x = 1\n"})
    assert _scope(repo) == 1
    assert "nhánh không gắn ticket" in capsys.readouterr().out


def test_trailer_tu_khai_khong_thay_duoc_claim(workspace: Build, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _setup(workspace, claim_branch=None, files={"src/api/orders.py": "x = 1\n"}, trailer=True)
    assert _scope(repo) == 1
    assert "nhánh không gắn ticket" in capsys.readouterr().out


def test_claim_cua_nhanh_khac_khong_gan_nhanh_nay(workspace: Build, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _setup(workspace, claim_branch="claude/nhanh-khac", files={"src/api/orders.py": "x = 1\n"})
    assert _scope(repo) == 1
    assert "nhánh không gắn ticket" in capsys.readouterr().out


def test_claim_het_han_khong_gan_nhanh(
    workspace: Build, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _setup(workspace, claim_branch=PLATFORM_BRANCH, files={"src/api/orders.py": "x = 1\n"})
    monkeypatch.setenv("AGENTCTL_NOW", (datetime.now(UTC) + timedelta(days=30)).isoformat())
    assert _scope(repo) == 1
    assert "nhánh không gắn ticket" in capsys.readouterr().out


def test_offline_khong_co_so_claim_cuc_bo_thi_bo_qua_khong_do(
    workspace: Build, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _setup(workspace, claim_branch=None, files={"src/api/orders.py": "x = 1\n"})
    assert _scope(repo, "--offline") == 1
    assert "nhánh không gắn ticket" in capsys.readouterr().out
