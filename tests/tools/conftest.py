"""Fixture cho test agentctl — repo git THẬT + remote bare, cô lập khỏi cấu hình git của máy.

Không giả lập git: cơ chế claim dựa vào việc `git push` từ chối lần đẩy không fast-forward, và chỉ
git thật mới chứng minh được điều đó. Cấu hình git toàn cục/hệ thống bị tách ra để `commit.gpgSign`,
`core.hooksPath` hay `core.autocrlf` của máy người chạy không làm test đổi kết quả.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from tests.tools.helpers import POLICY, Workspace, run_git


@pytest.fixture
def git_isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    empty_config = tmp_path / "gitconfig-rong"
    empty_config.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty_config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for key in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{key}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{key}_EMAIL", "test@example.invalid")
    monkeypatch.delenv("AGENTCTL_NOW", raising=False)


@pytest.fixture
def workspace(tmp_path: Path, git_isolated: None) -> Callable[[Mapping[str, str]], tuple[Workspace, Path]]:
    """Dựng remote bare có `main` chứa policy + ticket; trả về (workspace, bản clone đầu tiên)."""

    def build(tickets: Mapping[str, str]) -> tuple[Workspace, Path]:
        remote = tmp_path / "remote.git"
        run_git(tmp_path, "init", "--quiet", "--bare", "--initial-branch=main", str(remote))
        ws = Workspace(tmp_path, remote)
        seed = tmp_path / "seed"
        run_git(tmp_path, "init", "--quiet", "--initial-branch=main", str(seed))
        run_git(seed, "remote", "add", "origin", str(remote))
        files = {"coordination/policy.yaml": POLICY, "README.md": "# repo thử\n"}
        files |= {f"docs/work/tickets/{tid}.md": text for tid, text in tickets.items()}
        ws.commit_push(seed, files, "chore: khởi tạo")
        run_git(seed, "fetch", "--quiet", "origin")
        return ws, seed

    return build
