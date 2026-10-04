"""Hook chặn lệnh phá huỷ và đọc bí mật NGAY LÚC agent định chạy — không đợi pre-push hay CI.

Vì sao: luật cấm (`push --force`, `--no-verify`, `reset --hard`, đẩy thẳng `main`, `alembic stamp`, AGENTS.md luật 8 và
R70.12) trước đây chỉ là chữ; một lệnh `git reset --hard` hay `git clean -fdx` xoá việc chưa commit của phiên khác
ngay lập tức, CI không cứu được. Đọc `.env` hay in biến môi trường đưa khoá vào ngữ cảnh mô hình (và vào log của nhà
cung cấp). Ý tưởng và danh mục mượn từ kenryu42/cc-safety-net (MIT); bản này không cần Node, chạy cho Claude Code,
Codex và Gemini CLI qua cùng một script.
"""

from __future__ import annotations

import io
import json

import pytest

from scripts.hooks import guard_shell as gs

BLOCKED = [
    "git push --force origin feature/x",
    "git push -f",
    "git push --force-with-lease origin HEAD",
    "git push origin +feature/x",
    "git commit -m 'x' --no-verify",
    "git reset --hard HEAD~1",
    "git clean -fdx",
    "git checkout -- .",
    "git restore .",
    "git push origin main",
    "git push origin HEAD:main",
    "alembic stamp head",
    "rm -rf /",
    "rm -rf ~",
    "rm -rf .",
    "rm -rf .git",
    "sudo rm -fr / --no-preserve-root",
    "cat .env",
    "type .env.production",
    "Get-Content .env",
    "grep KEY backend/.env",
    "cat ~/.ssh/id_ed25519",
    "cat ~/.aws/credentials",
    "printenv",
    "gh auth token",
    "bash -c 'cd /repo && git reset --hard'",
    'powershell -Command "git push --force"',
    "echo ok && git clean -fd",
    "python -c \"import os; os.system('git push -f')\"",
]

ALLOWED = [
    "git push -u origin HEAD",
    "git push origin feature/ABC-01-guard",
    "git push origin agent-claims",
    "git commit -m 'fix: x'",
    "git reset HEAD file.py",
    "git checkout -- src/x.py",
    "git status && git diff",
    "rm -rf build/",
    "rm -rf .pytest_cache",
    "cp .env.example .env",
    "cat .env.example",
    "grep -rn environment src/",
    "export GITHUB_TOKEN=$(gh auth token)",
    "python -m pytest -q",
    "alembic upgrade head",
    'grep -rn "git push --force" docs/',
    'rg "reset --hard" coordination/',
]


@pytest.mark.parametrize("command", BLOCKED)
def test_chan_lenh_nguy_hiem(command: str) -> None:
    assert gs.reason_for_command(command), f"phải chặn: {command}"


@pytest.mark.parametrize("command", ALLOWED)
def test_cho_qua_lenh_thuong(command: str) -> None:
    assert gs.reason_for_command(command) is None, f"không được chặn: {command}"


@pytest.mark.parametrize(
    ("payload", "blocked"),
    [
        ({"tool_name": "Bash", "tool_input": {"command": "git reset --hard"}}, True),  # Claude Code
        ({"tool_name": "shell", "tool_input": {"command": ["bash", "-lc", "git push -f"]}}, True),  # Codex (danh sách)
        ({"tool_name": "run_shell_command", "tool_input": {"command": "rm -rf ."}}, True),  # Gemini CLI
        ({"tool_name": "Read", "tool_input": {"file_path": "/repo/.env"}}, True),
        ({"tool_name": "read_file", "tool_input": {"absolute_path": "/home/u/.ssh/id_rsa"}}, True),
        ({"tool_name": "Read", "tool_input": {"file_path": "/repo/.env.example"}}, False),
        ({"tool_name": "Bash", "tool_input": {"command": "pytest -q"}}, False),
    ],
)
def test_doc_payload_cua_ba_cong_cu(payload: dict, blocked: bool) -> None:
    assert (gs.reason_for_payload(payload) is not None) is blocked


def test_main_thoat_ma_2_va_noi_ly_do(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    payload = {"tool_name": "Bash", "tool_input": {"command": "git push --force"}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.delenv("AGENTCTL_HOOKS", raising=False)
    assert gs.main() == 2
    err = capsys.readouterr().err
    assert "push --force" in err and "người" in err.lower(), "nói vì sao và ai được làm"


def test_json_hong_thi_cho_qua(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hook hỏng không được làm đứng phiên làm việc (cùng nguyên tắc với guard_write)."""
    monkeypatch.setattr("sys.stdin", io.StringIO("không phải json"))
    assert gs.main() == 0
