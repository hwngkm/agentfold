"""`board` thấy bàn giao còn mở nằm trên nhánh CHƯA merge.

Vì sao: agent hết hạn mức dừng giữa chừng trên nhánh feature của mình; bàn giao nằm ở đó. Nếu `board` chỉ đọc
`origin/main`, agent kế tiếp chạy `board`, thấy "(trống)" và làm lại từ đầu — đúng điều bàn giao sinh ra để tránh.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

from tests.tools.helpers import Workspace, run_git
from tools.agentctl.board import render_board
from tools.agentctl.entries import create_entry

MOMENT = datetime(2026, 10, 3, 9, 0, tzinfo=UTC)
Build = Callable[[Mapping[str, str]], tuple[Workspace, Path]]


def _handoff_file(tmp: Path, title: str, status: str = "open") -> dict[str, str]:
    path = create_entry(
        tmp, "handoff", title=title, role="R3", moment=MOMENT, facts={"branch": "feature/API-01-x", "head": "abc1234"}
    )
    text = path.read_text(encoding="utf-8").replace("status: open", f"status: {status}", 1)
    return {path.relative_to(tmp).as_posix(): text}


def _push_branch(ws: Workspace, agent: Path, branch: str, files: Mapping[str, str]) -> None:
    run_git(agent, "checkout", "--quiet", "-b", branch)
    ws.commit_push(agent, files, f"chore: {branch}", branch=branch)


def test_ban_giao_mo_tren_nhanh_chua_merge_hien_o_bang(workspace: Build, tmp_path: Path) -> None:
    ws, seed = workspace({})
    agent = ws.clone("agent-a")
    _push_branch(ws, agent, "feature/API-01-x", _handoff_file(tmp_path / "gen", "Het quota"))
    run_git(seed, "fetch", "--quiet", "origin")
    board = render_board(seed, fetch=False, moment=MOMENT)
    assert "HND-20261003-het-quota" in board
    assert "origin/feature/API-01-x" in board


def test_ban_giao_da_dong_tren_nhanh_khong_hien(workspace: Build, tmp_path: Path) -> None:
    ws, seed = workspace({})
    agent = ws.clone("agent-a")
    _push_branch(ws, agent, "feature/API-01-x", _handoff_file(tmp_path / "gen", "Da xong", status="closed"))
    run_git(seed, "fetch", "--quiet", "origin")
    assert "HND-20261003-da-xong" not in render_board(seed, fetch=False, moment=MOMENT)


def test_ban_sao_tren_nhanh_khong_ghi_de_ket_qua_da_dong_tren_main(workspace: Build, tmp_path: Path) -> None:
    """Đã `closed` trên main mà nhánh cũ còn bản `open` thì KHÔNG báo — main là sự thật đã duyệt."""
    ws, seed = workspace({})
    agent = ws.clone("agent-a")
    _push_branch(ws, agent, "feature/API-01-x", _handoff_file(tmp_path / "gen1", "Cu"))
    main_copy = _handoff_file(tmp_path / "gen2", "Cu", status="closed")
    ws.commit_push(seed, main_copy, "docs: dong ban giao")
    run_git(seed, "fetch", "--quiet", "origin")
    assert "HND-20261003-cu" not in render_board(seed, fetch=False, moment=MOMENT)


def test_fetch_keo_ca_nhanh_feature_khong_chi_main(workspace: Build, tmp_path: Path) -> None:
    """Lỗi gốc: `board` chỉ fetch đúng `main`, nên nhánh của agent khác chưa bao giờ về máy này."""
    ws, seed = workspace({})
    agent = ws.clone("agent-a")
    _push_branch(ws, agent, "feature/API-01-x", _handoff_file(tmp_path / "gen", "Chua fetch"))
    assert "HND-20261003-chua-fetch" in render_board(seed, fetch=True, moment=MOMENT)
