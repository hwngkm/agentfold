"""Đếm tuân thủ nhật ký/bàn giao trên lịch sử git (chỉ đọc)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("log_compliance", ROOT / "scripts" / "log_compliance.py")
assert _spec and _spec.loader
lc = importlib.util.module_from_spec(_spec)
sys.modules["log_compliance"] = lc
_spec.loader.exec_module(lc)

LOG = "docs/work/log/2026/10/x.md"


def git(repo: Path, *args: str, author: str = "Nguoi <nguoi@example.com>") -> str:
    name, email = author.rstrip(">").split(" <")
    env = {
        "GIT_AUTHOR_NAME": name,
        "GIT_AUTHOR_EMAIL": email,
        "GIT_COMMITTER_NAME": name,
        "GIT_COMMITTER_EMAIL": email,
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "HOME": str(repo),
    }
    out = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env)
    return out.stdout


def commit(repo: Path, rel: str, msg: str, author: str = "Nguoi <nguoi@example.com>") -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(msg + "\n", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg, author=author)


def init(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    commit(tmp_path, "README.md", "chore: khoi dau")
    return tmp_path


def merge_branch(repo: Path, ticket: str, files: dict[str, str], author: str = "Nguoi <nguoi@example.com>") -> None:
    branch = f"feature/{ticket}-lam-gi-do"
    git(repo, "checkout", "-q", "-b", branch)
    for rel, msg in files.items():
        commit(repo, rel, msg, author=author)
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", branch, "-m", f"Merge pull request #1 from o/{branch}")


def rows(repo: Path, **kw: Any) -> dict[str, Any]:
    return {r.ticket: r for r in lc.collect(repo, **kw)}


def test_ticket_co_va_khong_co_nhat_ky(tmp_path: Path) -> None:
    repo = init(tmp_path)
    merge_branch(repo, "ABC-01", {"src/a.py": "feat: a (ABC-01)", LOG: "docs(work): nhat ky (ABC-01)"})
    merge_branch(repo, "ABC-02", {"src/b.py": "feat: b (ABC-02)"})
    got = rows(repo)
    assert got["ABC-01"].in_branch is True and got["ABC-02"].in_branch is False
    summary = lc.summarize(list(got.values()))
    assert summary["total"] == 2 and summary["in_branch"] == 1 and summary["rate_in_branch"] == 0.5


def test_ticket_chua_merge_bi_bo_qua(tmp_path: Path) -> None:
    repo = init(tmp_path)
    git(repo, "checkout", "-q", "-b", "feature/ABC-09-dang-lam")
    commit(repo, LOG, "docs(work): nhat ky (ABC-09)")
    git(repo, "checkout", "-q", "main")
    assert rows(repo) == {}


def test_nhat_ky_o_pr_docs_rieng_tinh_la_o_noi_khac(tmp_path: Path) -> None:
    repo = init(tmp_path)
    merge_branch(repo, "ABC-03", {"src/c.py": "feat: c (ABC-03)"})
    commit(repo, "docs/work/handoffs/HND-1.md", "docs(work): ban giao cho ABC-03")
    row = rows(repo)["ABC-03"]
    assert row.in_branch is False and row.anywhere is True


def test_repo_khong_co_ticket_khong_do(tmp_path: Path, capsys: object) -> None:
    repo = init(tmp_path)
    assert lc.collect(repo) == []
    assert lc.summarize([])["rate_in_branch"] is None
    assert lc.main(["--repo", str(repo)]) == 0


def test_nhieu_pr_cung_ticket_gop_lai(tmp_path: Path) -> None:
    repo = init(tmp_path)
    merge_branch(repo, "ABC-04", {"src/d.py": "feat: d (ABC-04)"})
    git(repo, "checkout", "-q", "-b", "feature/ABC-04-tiep")
    commit(repo, LOG, "docs(work): nhat ky (ABC-04)")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "feature/ABC-04-tiep", "-m", "Merge pull request #2 from o/feature/ABC-04-tiep")
    row = rows(repo)["ABC-04"]
    assert row.prs == 2 and row.in_branch is True


def test_tach_agent_va_nguoi_theo_mau_tac_gia(tmp_path: Path) -> None:
    repo = init(tmp_path)
    merge_branch(repo, "ABC-05", {"src/e.py": "feat: e (ABC-05)"}, author="Bot <bot@agent.invalid>")
    merge_branch(repo, "ABC-06", {"src/f.py": "feat: f (ABC-06)"})
    got = rows(repo, agent_author="agent\\.invalid")
    assert got["ABC-05"].by == "agent" and got["ABC-06"].by == "nguoi"
    assert rows(repo)["ABC-05"].by == "khong-ro"


def test_chi_doc_khong_ghi_gi(tmp_path: Path) -> None:
    repo = init(tmp_path)
    merge_branch(repo, "ABC-07", {"src/g.py": "feat: g (ABC-07)"})
    before = git(repo, "status", "--porcelain=v1"), git(repo, "rev-parse", "HEAD"), git(repo, "reflog")
    lc.main(["--repo", str(repo)])
    assert (git(repo, "status", "--porcelain=v1"), git(repo, "rev-parse", "HEAD"), git(repo, "reflog")) == before


def test_merge_pr_nam_ngoai_duong_first_parent_van_duoc_tinh(tmp_path: Path) -> None:
    """PR merge có thể tới main qua một merge khác (vd. nhánh nền tảng merge main rồi PR); không được bỏ sót."""
    repo = init(tmp_path)
    git(repo, "checkout", "-q", "-b", "side")
    merge_branch_on(repo, "side", "ABC-08", {LOG: "docs(work): nhat ky (ABC-08)"})
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "side", "-m", "chore: merge side")
    assert rows(repo)["ABC-08"].in_branch is True


def merge_branch_on(repo: Path, base: str, ticket: str, files: dict[str, str]) -> None:
    branch = f"feature/{ticket}-lam-gi-do"
    git(repo, "checkout", "-q", "-b", branch)
    for rel, msg in files.items():
        commit(repo, rel, msg)
    git(repo, "checkout", "-q", base)
    git(repo, "merge", "-q", "--no-ff", branch, "-m", f"Merge pull request #3 from o/{branch}")
