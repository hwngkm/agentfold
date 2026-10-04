"""Hook chặn ghi: hiểu payload của Claude Code, Codex (`apply_patch`) và Gemini; chặn đúng, không chặn oan."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from scripts.hooks import guard_write
from tests.tools.helpers import run_git, ticket_text

PATCH = """*** Begin Patch
*** Update File: src/api/orders.py
@@
-x = 1
+x = 2
*** Add File: docs/design/NEW.md
+# mới
*** Update File: src/old.py
*** Move to: src/new.py
*** End Patch"""


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"tool_name": "Write", "tool_input": {"file_path": "/r/a.py", "content": "x"}}, ["/r/a.py"]),
        (
            {"tool_name": "MultiEdit", "tool_input": {"file_path": "a.py", "edits": [{"file_path": "b.py"}]}},
            ["a.py", "b.py"],
        ),
        ({"tool_name": "write_file", "tool_input": {"file_path": "c.py"}}, ["c.py"]),
        (
            {"tool_name": "apply_patch", "tool_input": {"command": PATCH}},
            ["src/api/orders.py", "docs/design/NEW.md", "src/old.py", "src/new.py"],
        ),
        (
            {"tool_name": "apply_patch", "tool_input": {"command": ["apply_patch", PATCH]}},
            ["src/api/orders.py", "docs/design/NEW.md", "src/old.py", "src/new.py"],
        ),
        ({"tool_name": "Bash", "tool_input": {"command": "ls -la"}}, []),
    ],
)
def test_doc_duong_dan_tu_payload_moi_cong_cu(payload: dict, expected: list[str]) -> None:
    assert guard_write.target_paths(payload) == expected


@pytest.fixture
def ticket_repo(workspace) -> Path:
    _ws, repo = workspace({"API-01": ticket_text("API-01", allow=["src/api/orders.py"])})
    run_git(repo, "switch", "--quiet", "-c", "feature/API-01-don-hang")
    return repo


def _decide(repo: Path, rel: str, tool: str = "Write") -> int:
    payload = {"tool_name": tool, "tool_input": {"file_path": str(repo / rel)}}
    return guard_write.decide(payload, cwd=repo)[0]


def test_nhanh_ticket_chan_ngoai_scope_va_vung_bao_ve(ticket_repo: Path) -> None:
    assert _decide(ticket_repo, "src/api/orders.py") == 0
    assert _decide(ticket_repo, "docs/work/log/2026/09/x.md") == 0
    assert _decide(ticket_repo, "src/api/users.py") == guard_write.BLOCK
    assert _decide(ticket_repo, "docs/design/ARCHITECTURE.md") == guard_write.BLOCK
    assert _decide(ticket_repo, "tests/guards/test_moi.py") == 0, "thêm lưới canh mới luôn được"


def test_nhanh_khong_ticket_chi_chan_vung_bao_ve(ticket_repo: Path) -> None:
    run_git(ticket_repo, "switch", "--quiet", "-c", "kham-pha")
    assert _decide(ticket_repo, "src/bat/ky.py") == 0
    assert _decide(ticket_repo, "AGENTS.md") == guard_write.BLOCK


def test_ngoai_repo_va_tat_hook_thi_cho_qua(ticket_repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    outside = tmp_path / "ngoai-repo" / "ghi-chu.md"
    outside.parent.mkdir()
    assert guard_write.decide({"tool_input": {"file_path": str(outside)}}, cwd=tmp_path)[0] == 0
    monkeypatch.setenv("AGENTCTL_HOOKS", "off")
    assert _decide(ticket_repo, "docs/design/ARCHITECTURE.md") == 0


def test_payload_hong_khong_lam_dung_phien(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("không phải json"))
    assert guard_write.main() == 0
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(["không", "phải", "mapping"])))
    assert guard_write.main() == 0
