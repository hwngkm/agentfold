"""`agentctl pr-body`: tiêu đề + nội dung PR sinh từ ticket và git, không cần `gh`, MCP hay mạng.

Ca thử cloud: `gh auth status` báo token lỗi nên quy trình `gh pr create` sai trên môi trường đó. Lệnh này chỉ ĐỌC git cục bộ; việc
mở PR vẫn do người/agent làm bằng công cụ có sẵn (gh, GitHub MCP, hoặc dán vào web).
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from tests.tools.helpers import Workspace, run_git, ticket_text
from tools.agentctl.cli import main
from tools.agentctl.commitmsg import check_commit_message

Build = Callable[[Mapping[str, str]], tuple[Workspace, Path]]
TICKET = ticket_text("API-01", allow=["src/api/orders.py"], title="Thêm đơn hàng")


def _branch(workspace: Build, *, subject: str) -> Path:
    ws, repo = workspace({"API-01": TICKET})
    run_git(repo, "switch", "--quiet", "-c", "feature/API-01-don-hang")
    Workspace.write(repo, {"src/api/orders.py": "x = 1\n"})
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "--quiet", "-m", subject)
    return repo


def _run(repo: Path, *extra: str) -> int:
    return main(["--repo", str(repo), "pr-body", "--ticket", "API-01", *extra])


def test_in_tieu_de_va_noi_dung_tu_ticket_va_git(workspace: Build, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _branch(workspace, subject="feat(api): don hang (API-01)")
    assert _run(repo) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "feat(api): don hang (API-01)"
    assert "API-01" in out and "docs/work/tickets/API-01.md" in out
    assert "có test" in out, "tiêu chí nghiệm thu của ticket phải có trong nội dung"
    assert "src/api/orders.py" in out, "file đã đổi và phạm vi phải có trong nội dung"


def test_tieu_de_hop_le_ke_ca_khi_commit_cuoi_khong_theo_quy_uoc(
    workspace: Build, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _branch(workspace, subject="wip")
    assert _run(repo, "--title-only") == 0
    title = capsys.readouterr().out.strip()
    assert check_commit_message(title, "API-01") == [], f"tiêu đề `{title}` phải qua kiểm thông điệp commit"
    assert "\n" not in title


def test_body_only_khong_co_tieu_de(workspace: Build, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _branch(workspace, subject="feat(api): don hang (API-01)")
    assert _run(repo, "--body-only") == 0
    out = capsys.readouterr().out
    assert "feat(api): don hang (API-01)" not in out.splitlines()[0]
    assert "API-01" in out


def test_khong_ghi_cong_ai_trong_noi_dung(workspace: Build, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _branch(workspace, subject="feat(api): don hang (API-01)")
    assert _run(repo) == 0
    out = capsys.readouterr().out.lower()
    for marker in ("co-authored-by", "generated with", "claude", "codex", "chatgpt"):
        assert marker not in out


def test_chi_goi_git_khong_goi_gh_hay_mang(
    workspace: Build, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _branch(workspace, subject="feat(api): don hang (API-01)")
    seen: list[str] = []
    verbs: list[str] = []
    real = subprocess.run

    def spy(args, *a, **k):  # type: ignore[no-untyped-def]
        seen.append(str(args[0]))
        verbs.extend(str(a) for a in args[1:])
        return real(args, *a, **k)

    monkeypatch.setattr(subprocess, "run", spy)
    assert _run(repo) == 0
    assert seen, "phải gọi git để đọc lịch sử"
    assert set(seen) == {"git"}, f"chỉ được gọi git, đã gọi {set(seen)}"
    network = {"fetch", "push", "pull", "clone", "ls-remote"}
    assert not network & set(verbs), f"không được đụng mạng, đã gọi {network & set(verbs)}"
    capsys.readouterr()


def test_ticket_khong_ton_tai_thi_loi_ro_rang(workspace: Build, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _branch(workspace, subject="feat(api): don hang (API-01)")
    assert main(["--repo", str(repo), "pr-body", "--ticket", "NOPE-99"]) != 0


def test_commit_merge_khong_duoc_lam_tieu_de(workspace: Build, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _branch(workspace, subject="feat(api): don hang (API-01)")
    run_git(repo, "commit", "--quiet", "--allow-empty", "-m", "Merge pull request #1 from x/y")
    assert _run(repo, "--title-only") == 0
    title = capsys.readouterr().out.strip()
    assert not title.startswith("Merge"), "dòng Merge được miễn kiểm commit nhưng không phải tiêu đề PR"
    assert title.endswith("(API-01)") and ": " in title
