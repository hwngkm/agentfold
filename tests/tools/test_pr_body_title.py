"""`pr-body` chọn tiêu đề từ commit TÍNH NĂNG gần nhất, không phải commit cuối (thường là nhật ký hay docs(work)).

Hạn chế đã ghi từ bản đầu: `build_title` lấy chủ đề của commit cuối nên PR có tiêu đề là dòng nhật ký, không mô tả thay đổi.
Test cũ (tests/tools/test_pr_body.py) giữ nguyên và vẫn phải xanh.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from tests.tools.helpers import Workspace, run_git, ticket_text
from tools.agentctl.cli import main
from tools.agentctl.commitmsg import check_commit_message

Build = Callable[[Mapping[str, str]], tuple[Workspace, Path]]
TICKET = ticket_text("API-01", allow=["src/api/orders.py"], title="Thêm đơn hàng")


def _branch(workspace: Build, *subjects: str) -> Path:
    """Nhánh feature với mỗi chủ đề là một commit (cũ → mới)."""
    _, repo = workspace({"API-01": TICKET})
    run_git(repo, "switch", "--quiet", "-c", "feature/API-01-don-hang")
    for index, subject in enumerate(subjects):
        Workspace.write(repo, {"src/api/orders.py": f"x = {index}\n"})
        run_git(repo, "add", "-A")
        run_git(repo, "commit", "--quiet", "-m", subject)
    return repo


def _title(repo: Path, capsys: pytest.CaptureFixture[str]) -> str:
    assert main(["--repo", str(repo), "pr-body", "--ticket", "API-01", "--title-only"]) == 0
    title = capsys.readouterr().out.strip()
    assert check_commit_message(title, "API-01") == [], f"tiêu đề `{title}` phải qua kiểm thông điệp commit"
    return title


def test_commit_cuoi_la_docs_work_thi_lay_commit_tinh_nang(
    workspace: Build, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _branch(workspace, "feat(api): them don hang (API-01)", "docs(work): nhat ky API-01 (API-01)")
    assert _title(repo, capsys) == "feat(api): them don hang (API-01)"


def test_lay_commit_tinh_nang_gan_nhat_trong_cac_loai_cho_phep(
    workspace: Build, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _branch(
        workspace,
        "feat(api): them don hang (API-01)",
        "fix(api): sua loi bien (API-01)",
        "docs(work): nhat ky (API-01)",
    )
    assert _title(repo, capsys) == "fix(api): sua loi bien (API-01)"


@pytest.mark.parametrize("kind", ["refactor", "perf", "test", "chore"])
def test_chap_nhan_moi_loai_tinh_nang(kind: str, workspace: Build, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _branch(workspace, f"{kind}(api): viec nho (API-01)", "docs(work): nhat ky (API-01)")
    assert _title(repo, capsys) == f"{kind}(api): viec nho (API-01)"


def test_nhanh_chi_co_docs_work_van_ra_tieu_de_hop_le(workspace: Build, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _branch(workspace, "docs(work): ke hoach va cau hoi (API-01)")
    assert _title(repo, capsys) == "docs(work): ke hoach va cau hoi (API-01)"


def test_khong_co_commit_hop_le_thi_quay_ve_tieu_de_tu_ticket(
    workspace: Build, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _branch(workspace, "wip", "lam tiep")
    title = _title(repo, capsys)
    assert title.startswith("feat(api): ") and "Thêm đơn hàng" in title and title.endswith("(API-01)")


def test_commit_gop_khong_lam_hong_viec_chon(workspace: Build, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _branch(workspace, "feat(api): them don hang (API-01)")
    run_git(repo, "commit", "--quiet", "--allow-empty", "-m", "Merge origin/main into branch (API-01)")
    assert _title(repo, capsys) == "feat(api): them don hang (API-01)"


def test_chi_xet_commit_cua_nhanh_khong_lay_commit_cu_tu_main(
    workspace: Build, capsys: pytest.CaptureFixture[str]
) -> None:
    """Commit tính năng đã nằm trên main (không thuộc PR này) không được chọn làm tiêu đề PR."""
    _, repo = workspace({"API-01": TICKET})
    Workspace.write(repo, {"src/api/cu.py": "y = 1\n"})
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "--quiet", "-m", "feat(api): viec cu da tren main (API-00)")
    run_git(repo, "switch", "--quiet", "-c", "feature/API-01-don-hang")
    Workspace.write(repo, {"src/api/orders.py": "x = 1\n"})
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "--quiet", "-m", "docs(work): ke hoach (API-01)")
    assert _title(repo, capsys) == "docs(work): ke hoach (API-01)"
