"""AGENT-LOG: agent (mọi nhà cung cấp) và người nhắn cho nhau qua git, không cần MCP, không cần copy-paste.

Vì sao: trong thực tế, hai agent thay phiên nhau (hết hạn mức) và một người duyệt chỉ giao tiếp được bằng cách người
dùng chép tay lời nhắn từ cửa sổ này sang cửa sổ kia. Hộp thư nằm trên nhánh git mồ côi: ai có `git` là đọc/ghi được.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.tools.helpers import Workspace, run_git
from tools.agentctl.errors import AgentctlError
from tools.agentctl.mail import AgentCard, Mailbox, new_message, parse_message

MOMENT = datetime(2026, 10, 3, 9, 30, tzinfo=UTC)
Build = Callable[[Mapping[str, str]], tuple[Workspace, Path]]


def _box(repo: Path) -> Mailbox:
    return Mailbox(repo, remote="origin", branch="agent-mail")


def _card(agent: str, role: str = "R3", tool: str = "codex") -> AgentCard:
    return AgentCard(id=agent, tool=tool, on_behalf_of=role, registered_at="2026-10-03T09:00:00Z")


def test_gui_nhan_xac_nhan_qua_hai_ban_clone(workspace: Build) -> None:
    ws, seed = workspace({})
    other = ws.clone("agent-b")
    sender, receiver = _box(seed), _box(other)
    sender.register(_card("codex-1"))
    receiver.register(_card("claude-1", tool="claude-code"))

    sent = sender.send(
        new_message(
            sender="codex-1",
            to=["claude-1"],
            thread="API-02",
            kind="request",
            subject="Review migration",
            body="Nhờ xem `alembic/versions/x.py`.",
            moment=MOMENT,
            ack_required=True,
        )
    )
    inbox = receiver.inbox("claude-1")
    assert [m.id for m in inbox] == [sent.id]
    assert inbox[0].body.strip() == "Nhờ xem `alembic/versions/x.py`."
    assert sender.inbox("codex-1") == [], "người gửi không nhận lại thư của chính mình"

    receiver.ack(sent.id, "claude-1", note="đã xem", moment=MOMENT)
    assert receiver.inbox("claude-1") == []
    assert sender.acks(sent.id) == {"claude-1"}


def test_hai_agent_gui_cung_luc_khong_mat_thu(workspace: Build) -> None:
    """Bản clone B gửi trên đầu nhánh CŨ (chưa thấy thư của A): CAS bị từ chối, đọc lại, ghi đè lên — không mất thư."""
    ws, seed = workspace({})
    a, b = _box(seed), _box(ws.clone("agent-b"))
    a.register(_card("codex-1"))
    stale = b.fetch()  # B thấy hộp thư lúc này, rồi A ghi tiếp
    first = a.send(
        new_message(sender="codex-1", to=["all"], thread="T", kind="inform", subject="1", body="a", moment=MOMENT)
    )

    real_fetch, calls = b.fetch, []

    def fetch_stale_once() -> str | None:
        calls.append(1)
        return stale if len(calls) == 1 else real_fetch()

    b.fetch = fetch_stale_once  # type: ignore[method-assign]
    second = b.send(
        new_message(sender="cursor-1", to=["all"], thread="T", kind="inform", subject="2", body="b", moment=MOMENT)
    )
    assert len(calls) >= 2, "lần ghi đầu trên đầu nhánh cũ phải bị từ chối và làm lại"
    assert {m.id for m in a.thread("T")} == {first.id, second.id}


def test_gui_theo_vai_tro_va_toan_bo(workspace: Build) -> None:
    ws, seed = workspace({})
    box = _box(seed)
    box.register(_card("codex-1", role="R3"))
    box.register(_card("gemini-1", role="R2"))
    to_role = box.send(
        new_message(sender="human", to=["role:R3"], thread="T", kind="request", subject="x", body="y", moment=MOMENT)
    )
    to_all = box.send(
        new_message(sender="human", to=["all"], thread="T", kind="inform", subject="x", body="y", moment=MOMENT)
    )
    assert {m.id for m in box.inbox("codex-1")} == {to_role.id, to_all.id}
    assert {m.id for m in box.inbox("gemini-1")} == {to_all.id}


def test_trang_thai_yeu_cau_theo_thu_tra_loi_moi_nhat(workspace: Build) -> None:
    ws, seed = workspace({})
    box = _box(seed)
    req = box.send(
        new_message(
            sender="human",
            to=["codex-1"],
            thread="API-02",
            kind="request",
            subject="Làm API-02",
            body=".",
            moment=MOMENT,
        )
    )
    assert box.request_state(req.id) == "submitted"
    box.send(
        new_message(
            sender="codex-1",
            to=["human"],
            thread="API-02",
            kind="status",
            subject="bắt đầu",
            body=".",
            state="working",
            in_reply_to=req.id,
            moment=MOMENT,
        )
    )
    box.send(
        new_message(
            sender="codex-1",
            to=["human"],
            thread="API-02",
            kind="status",
            subject="cần quyết",
            body=".",
            state="input-required",
            in_reply_to=req.id,
            moment=MOMENT.replace(minute=40),
        )
    )
    assert box.request_state(req.id) == "input-required"


def test_nhat_ky_hoat_dong_jsonl_moi_agent_mot_file(workspace: Build) -> None:
    ws, seed = workspace({})
    box = _box(seed)
    box.log_event("codex-1", "session_start", moment=MOMENT, ticket="API-02")
    box.log_event("codex-1", "test_run", moment=MOMENT.replace(minute=45), detail="pytest tests/unit -q: 12 passed")
    events = box.events(agent="codex-1")
    assert [e["event"] for e in events] == ["session_start", "test_run"]
    assert events[0]["ticket"] == "API-02" and events[1]["ts"] == "2026-10-03T09:45:00Z"


def test_che_do_cuc_bo_khi_khong_co_remote(tmp_path: Path, git_isolated: None) -> None:
    """Máy không có remote (hoặc agent không có quyền push): hộp thư vẫn chạy trên nhánh cục bộ, worktree dùng chung."""
    repo = tmp_path / "solo"
    run_git(tmp_path, "init", "--quiet", "--initial-branch=main", str(repo))
    box = _box(repo)
    assert box.mode == "local"
    msg = box.send(
        new_message(sender="human", to=["codex-1"], thread="T", kind="request", subject="s", body="b", moment=MOMENT)
    )
    assert [m.id for m in box.inbox("codex-1")] == [msg.id]
    tip = subprocess.run(["git", "rev-parse", "agent-mail"], cwd=repo, capture_output=True, text=True, check=True)
    assert tip.stdout.strip()


@pytest.mark.parametrize(
    ("kwargs", "fragment"),
    [
        ({"kind": "lạ"}, "`kind`"),
        ({"kind": "status", "state": "xong"}, "`state`"),
        ({"sender": "Codex 1"}, "định danh"),
        ({"to": []}, "người nhận"),
    ],
)
def test_thu_sai_bi_tu_choi(kwargs: dict, fragment: str) -> None:
    base = {"sender": "codex-1", "to": ["claude-1"], "thread": "T", "kind": "inform", "subject": "s", "body": "b"}
    with pytest.raises(AgentctlError, match=fragment):
        new_message(**{**base, **kwargs}, moment=MOMENT)


def test_thu_doc_lai_dung_nhu_khi_ghi() -> None:
    msg = new_message(
        sender="codex-1",
        to=["role:R1", "human"],
        thread="API-02",
        kind="question",
        subject="Làm tròn theo dòng hay tổng?",
        body="Chi tiết: …\n\n- a\n- b\n",
        moment=MOMENT,
        refs=["docs/work/tickets/API-02.md", "abc1234"],
    )
    again = parse_message(msg.render(), source="x.md")
    assert again == msg


def test_dong_lenh_tu_dau_den_cuoi(
    workspace: Build, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Agent không có MCP chỉ cần shell: đăng ký → gửi → người nhận thấy trong inbox → xác nhận."""
    from tools.agentctl.cli import main

    ws, seed = workspace({})
    other = ws.clone("agent-b")
    assert main(["--repo", str(seed), "mail", "register", "--as", "codex-1", "--tool", "codex", "--role", "R3"]) == 0
    assert (
        main(
            [
                "--repo",
                str(seed),
                "mail",
                "send",
                "--as",
                "codex-1",
                "--to",
                "human",
                "--thread",
                "API-02",
                "--kind",
                "question",
                "--subject",
                "Làm tròn theo dòng?",
                "--body",
                "Chi tiết...",
                "--ack",
            ]
        )
        == 0
    )
    capsys.readouterr()
    monkeypatch.setenv("AGENTCTL_AGENT", "human")
    assert main(["--repo", str(other), "mail", "inbox"]) == 0
    out = capsys.readouterr().out
    assert "Làm tròn theo dòng?" in out and "cần xác nhận" in out
    msg_id = out.split()[1]
    assert main(["--repo", str(other), "mail", "ack", msg_id, "--note", "theo dòng"]) == 0
    capsys.readouterr()
    assert main(["--repo", str(other), "mail", "inbox"]) == 0
    assert "Không có thư mới" in capsys.readouterr().out


def test_che_do_offline_khong_goi_mang(workspace: Build) -> None:
    """Hook đầu phiên đọc hộp thư offline: chỉ thấy bản đã kéo về, không treo khi mất mạng."""
    ws, seed = workspace({})
    other = ws.clone("agent-b")
    sent = _box(seed).send(
        new_message(sender="human", to=["codex-1"], thread="T", kind="inform", subject="s", body="b", moment=MOMENT)
    )
    offline = Mailbox(other, remote="origin", branch="agent-mail", offline=True)
    assert offline.inbox("codex-1") == [], "chưa kéo về thì offline không thấy"
    assert [m.id for m in _box(other).inbox("codex-1")] == [sent.id], "bản online kéo về"
    assert [m.id for m in offline.inbox("codex-1")] == [sent.id], "sau khi kéo, offline thấy"
