"""Dụng cụ dựng repo git thật cho test agentctl: chính sách mẫu, ticket mẫu, remote + bản clone."""

from __future__ import annotations

import subprocess
import textwrap
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

POLICY = textwrap.dedent(
    """\
    version: 1
    remote: origin
    base_branch: main
    claims_branch: agent-claims
    tickets_dir: docs/work/tickets
    human_approval_label: human-approved
    lease: {default_hours: 24, max_hours: 72}
    always_allowed: [docs/work/log/**, docs/work/questions/**]
    protected:
      - id: design
        owners: [R1]
        why: thiết kế do người chốt
        paths: [docs/design/**, AGENTS.md]
      - id: guard-nets
        owners: [R1]
        why: lưới canh là thiết kế chạy được
        allow_additions: true
        paths: [tests/guards/**]
      - id: work-plan
        owners: [R1]
        why: kế hoạch đã duyệt
        allow_additions: true
        paths: [docs/work/tickets/**]
    exclusive:
      - id: db-migrations
        why: hai nhánh cùng thêm migration sinh nhiều head
        paths: [alembic/versions/**]
    """
)


def ticket_text(
    ticket_id: str,
    *,
    state: str = "ready",
    allow: Iterable[str] = (),
    exclusive: Iterable[str] = (),
    protected: Iterable[str] = (),
    depends_on: Iterable[str] = (),
    title: str = "Việc mẫu",
) -> str:
    def block(items: Iterable[str]) -> str:
        return "[" + ", ".join(f'"{item}"' for item in items) + "]"

    return textwrap.dedent(
        f"""\
        ---
        id: {ticket_id}
        title: {title}
        state: {state}
        owner_role: R1
        design_refs: []
        depends_on: {block(depends_on)}
        scope:
          allow: {block(allow)}
          exclusive: {block(exclusive)}
          protected: {block(protected)}
        acceptance:
          - có test
        ---
        # {ticket_id}
        """
    )


def run_git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False)
    assert result.returncode == 0, f"git {' '.join(args)} thất bại: {result.stderr}"
    return result.stdout


@dataclass
class Workspace:
    root: Path
    remote: Path

    def clone(self, name: str) -> Path:
        target = self.root / name
        run_git(self.root, "clone", "--quiet", str(self.remote), str(target))
        return target

    @staticmethod
    def write(repo: Path, files: Mapping[str, str]) -> None:
        for rel, content in files.items():
            path = repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def commit_push(self, repo: Path, files: Mapping[str, str], message: str, branch: str = "main") -> None:
        self.write(repo, files)
        run_git(repo, "add", "-A")
        run_git(repo, "commit", "--quiet", "-m", message)
        run_git(repo, "push", "--quiet", "origin", f"HEAD:{branch}")
