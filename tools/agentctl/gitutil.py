"""Gọi git bằng danh sách đối số ở chế độ nhị phân — không qua shell, không dịch xuống dòng.

- Không `shell=True`: nó từng "chạy được" trên Windows (nối argv thành chuỗi) mà không chạy gì trên
  POSIX — một lỗi chỉ CI thấy (đã gặp thật).
- Nhị phân: ở chế độ text, Python trên Windows đổi `\\n` thành `\\r\\n` khi ghi vào stdin, nên cùng
  một claim sẽ băm ra blob khác nhau tuỳ hệ điều hành của agent ghi nó.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from tools.agentctl.errors import AgentctlEnvironmentError, AgentctlError

#: Đường dẫn chính sách, tương đối với gốc dự án — dấu hiệu nhận ra gốc dự án.
POLICY_PATH = "coordination/policy.yaml"


class GitError(AgentctlError):
    """Một lệnh git thất bại."""


@dataclass(frozen=True)
class GitResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class Change:
    """Một file đổi trong diff. `status` là một ký tự: A (thêm), M (sửa), D (xoá), T (đổi kiểu)."""

    status: str
    path: str


def run_git(
    repo: Path,
    args: Sequence[str],
    *,
    input_text: str | None = None,
    env: Mapping[str, str] | None = None,
) -> GitResult:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo,
            input=input_text.encode("utf-8") if input_text is not None else None,
            capture_output=True,
            env={**os.environ, **(env or {})},
            check=False,
        )
    except FileNotFoundError as exc:
        raise AgentctlEnvironmentError("không tìm thấy lệnh `git` trên PATH") from exc
    except OSError as exc:
        raise AgentctlEnvironmentError(f"không chạy được git: {exc}") from exc
    return GitResult(
        proc.returncode,
        proc.stdout.decode("utf-8", errors="replace"),
        proc.stderr.decode("utf-8", errors="replace"),
    )


def git(
    repo: Path,
    *args: str,
    input_text: str | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    result = run_git(repo, args, input_text=input_text, env=env)
    if result.returncode != 0:
        raise GitError(f"`git {' '.join(args)}` thất bại (mã {result.returncode}): {result.stderr.strip()}")
    return result.stdout


def repo_root(start: Path) -> Path:
    result = run_git(start, ["rev-parse", "--show-toplevel"])
    if result.returncode != 0:
        raise AgentctlError(f"`{start}` không nằm trong một repo git")
    return Path(result.stdout.strip())


def project_root(start: Path) -> Path:
    """Gốc DỰ ÁN: thư mục gần nhất (từ `start` đi lên, không vượt gốc git) có chính sách điều phối.

    Dự án có thể nằm trong thư mục con của một monorepo. Mọi hàm đọc đường dẫn trong module này làm việc
    tương đối với thư mục chúng được gọi (`ref:./đường-dẫn`, `diff --relative`), nên chạy từ gốc dự án là đủ.
    """
    top = repo_root(start).resolve()
    current = start.resolve()
    current = current if current.is_dir() else current.parent
    for candidate in [current, *current.parents]:
        if (candidate / POLICY_PATH).is_file():
            return candidate
        if candidate == top:
            break
    return top


def resolve(repo: Path, ref: str) -> str | None:
    result = run_git(repo, ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"])
    return result.stdout.strip() if result.returncode == 0 else None


def show_file(repo: Path, ref: str, path: str) -> str | None:
    """Nội dung `path` (tương đối với `repo`) tại `ref`, hoặc `None` nếu file/ref không tồn tại."""
    result = run_git(repo, ["show", f"{ref}:./{path}"])
    return result.stdout if result.returncode == 0 else None


def list_files(repo: Path, ref: str, prefix: str, *, full_tree: bool = False) -> list[str]:
    """File dưới `prefix` tại `ref`. Mặc định tương đối với `repo`; `full_tree` tính từ gốc cây (nhánh mồ côi)."""
    args = ["ls-tree", "-r", "--name-only", *(["--full-tree"] if full_tree else []), ref, "--", prefix]
    result = run_git(repo, args)
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def current_branch(repo: Path) -> str | None:
    result = run_git(repo, ["symbolic-ref", "--quiet", "--short", "HEAD"])
    return result.stdout.strip() if result.returncode == 0 else None


def _parse_name_status(output: str) -> list[Change]:
    fields = [field for field in output.split("\0") if field]
    return [Change(fields[i][0], fields[i + 1]) for i in range(0, len(fields) - 1, 2)]


def diff_changes(repo: Path, base: str, head: str) -> list[Change]:
    """Thay đổi của `head` kể từ điểm tách khỏi `base` (ba chấm), không gộp đổi tên.

    `--relative`: chỉ thay đổi trong thư mục dự án, đường dẫn tính từ đó — dự án trong monorepo không bị
    phân xử theo file của dự án khác.
    """
    return _parse_name_status(
        git(repo, "diff", "--relative", "--name-status", "--no-renames", "-z", f"{base}...{head}")
    )


def staged_changes(repo: Path) -> list[Change]:
    return _parse_name_status(git(repo, "diff", "--cached", "--relative", "--name-status", "--no-renames", "-z"))


def commit_subjects(repo: Path, ref: str) -> list[str]:
    result = run_git(repo, ["log", "--format=%s", ref])
    return result.stdout.splitlines() if result.returncode == 0 else []


def identity_env(repo: Path) -> dict[str, str]:
    """Danh tính cho commit plumbing khi máy chưa cấu hình `user.name`/`user.email` (vd. CI).

    Chỉ điền chỗ trống — không bao giờ ghi đè danh tính người dùng đã cấu hình.
    """
    env: dict[str, str] = {}
    if not run_git(repo, ["config", "user.name"]).stdout.strip():
        env |= {"GIT_AUTHOR_NAME": "agentctl", "GIT_COMMITTER_NAME": "agentctl"}
    if not run_git(repo, ["config", "user.email"]).stdout.strip():
        env |= {"GIT_AUTHOR_EMAIL": "agentctl@localhost", "GIT_COMMITTER_EMAIL": "agentctl@localhost"}
    return env
