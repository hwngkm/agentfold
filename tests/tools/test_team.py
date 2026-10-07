"""Đội agent (`coordination/team.yaml`): ai điều phối, ai làm gì, giao việc và báo lại qua AGENT-LOG.

Vì sao: hộp thư đã có, nhưng trong thực tế người điều phối vẫn gõ tay một prompt dài vào cửa sổ từng agent, và
agent nhận việc không biết mình được làm gì, báo cho ai, việc nào phải chờ người. Sổ đội ghi phân cấp một lần; lệnh
`mail assign` dựng thư giao việc tự đủ bối cảnh từ ticket đã duyệt; `mail reply` và `mail pending` cho mọi bên thấy
ai đang chờ ai mà không cần người dùng chép lời nhắn.
"""

from __future__ import annotations

import argparse
import textwrap
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from tests.tools.helpers import Workspace, ticket_text
from tools.agentctl import mail_cli
from tools.agentctl.errors import AgentctlError
from tools.agentctl.mail import Mailbox
from tools.agentctl.team import load_team, parse_team

Build = Callable[[Mapping[str, str]], tuple[Workspace, Path]]

TEAM = textwrap.dedent(
    """\
    version: 1
    human_only:
      - đặt ticket `ready`
      - gắn nhãn duyệt
    ranks:
      coordinator: [giao việc, review, merge sau CI xanh]
      specialist: [làm ticket được giao, hỏi, đề xuất]
      generalist: [làm ticket được giao, hỏi, đề xuất]
    agents:
      boss:
        tool: claude-code
        vendor: anthropic
        rank: coordinator
        on_behalf_of: R1
        reports_to: human
        strengths: [điều phối]
        wake: tự đọc hộp thư đầu phiên
      coder:
        tool: codex
        vendor: openai
        rank: specialist
        on_behalf_of: R1
        reports_to: boss
        strengths: [backend, nghiên cứu]
        wake: "gõ: chạy `python -m tools.agentctl prime --as coder` rồi làm theo hộp thư"
      designer:
        tool: antigravity
        vendor: google
        rank: specialist
        on_behalf_of: R1
        reports_to: boss
        strengths: [UI/UX, prototype]
        wake: "gõ: chạy `python -m tools.agentctl prime --as designer` rồi làm theo hộp thư"
    routes:
      backend: {primary: coder, backup: boss, review: boss}
      ui: {primary: designer, backup: coder, review: boss}
    """
)


def test_so_doi_hop_le_cho_biet_dieu_phoi_tuyen_viec_va_nguoi_review() -> None:
    team = parse_team(TEAM, source="team.yaml")
    assert team.coordinator.id == "boss"
    assert team.route("ui").primary == "designer"
    assert team.route("backend").review == "boss"
    assert team.members["coder"].reports_to == "boss"
    with pytest.raises(AgentctlError, match="không có tuyến"):
        team.route("deploy")


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        ("rank: coordinator", "rank: specialist", "đúng một agent `coordinator`"),
        ("reports_to: boss\n    strengths: [backend", "reports_to: ma\n    strengths: [backend", "reports_to"),
        ("primary: designer", "primary: ai-do", "agent không có trong đội"),
        ("tool: codex", "tool: notepad", "tool"),
        ("reports_to: human", "reports_to: coder", "không tới `human`"),
        ("review: boss}\n  ui", "review: coder}\n  ui", "khác nhà cung cấp"),
    ],
)
def test_so_doi_sai_bi_tu_choi(old: str, new: str, problem: str) -> None:
    assert old in TEAM
    with pytest.raises(AgentctlError, match=problem):
        parse_team(TEAM.replace(old, new, 1), source="team.yaml")


def test_so_doi_doc_tu_nhanh_goc_khong_tu_ban_cuc_bo(workspace: Build) -> None:
    ws, seed = workspace({})
    ws.commit_push(seed, {"coordination/team.yaml": TEAM}, "docs: đội")
    swapped = TEAM.replace("rank: coordinator", "rank: X", 1).replace("rank: specialist", "rank: coordinator", 1)
    ws.write(seed, {"coordination/team.yaml": swapped.replace("rank: X", "rank: specialist")})
    assert load_team(seed, None).coordinator.id == "coder"
    assert load_team(seed, "origin/main").coordinator.id == "boss", "agent sửa sổ đội cục bộ không tự nâng quyền được"


def _mail(repo: Path, argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    mail_cli.add_parser(sub)
    return mail_cli.handle(repo, parser.parse_args(["mail", *argv]))


def _setup(workspace: Build, state: str = "ready") -> tuple[Workspace, Path]:
    ws, seed = workspace({"API-01": ticket_text("API-01", state=state, allow=["src/x.py"], title="Thêm đơn hàng")})
    ws.commit_push(seed, {"coordination/team.yaml": TEAM}, "docs: đội")
    return ws, seed


def test_giao_viec_dung_thu_tu_du_boi_canh_tu_ticket_da_duyet(workspace: Build) -> None:
    ws, seed = _setup(workspace)
    assert _mail(seed, ["assign", "API-01", "--to", "coder", "--as", "boss", "--note", "Ưu tiên phần API"]) == 0

    coder = ws.clone("coder")
    inbox = Mailbox(coder, remote="origin", branch="agent-mail").inbox("coder")
    assert len(inbox) == 1
    msg = inbox[0]
    assert (msg.kind, msg.state, msg.thread, msg.sender, msg.ack_required) == (
        "request",
        "submitted",
        "API-01",
        "boss",
        True,
    )
    body = msg.body
    for must in (
        "docs/work/tickets/API-01.md",
        "`src/x.py`",
        "có test",
        "agentctl start API-01 --role R1",
        "đặt ticket `ready`",
        "Ưu tiên phần API",
        f"mail reply {msg.id} --state working",
        f"mail reply {msg.id} --state completed",
        "--as coder",
        "boss",
    ):
        assert must in body, f"thư giao việc thiếu `{must}`"


def test_khong_giao_ticket_chua_ready(workspace: Build) -> None:
    _ws, seed = _setup(workspace, state="proposed")
    with pytest.raises(AgentctlError, match="ready"):
        _mail(seed, ["assign", "API-01", "--to", "coder", "--as", "boss"])


def test_chi_dieu_phoi_hoac_nguoi_moi_giao_viec(workspace: Build) -> None:
    _ws, seed = _setup(workspace)
    with pytest.raises(AgentctlError, match="không có trong đội"):
        _mail(seed, ["assign", "API-01", "--to", "ai-do", "--as", "boss"])
    with pytest.raises(AgentctlError, match="điều phối"):
        _mail(seed, ["assign", "API-01", "--to", "designer", "--as", "coder"])
    assert _mail(seed, ["assign", "API-01", "--to", "coder", "--as", "human"]) == 0


def test_tra_loi_cap_nhat_trang_thai_va_viec_dang_cho(workspace: Build, capsys: pytest.CaptureFixture[str]) -> None:
    ws, seed = _setup(workspace)
    _mail(seed, ["assign", "API-01", "--to", "coder", "--as", "boss"])
    box = Mailbox(seed, remote="origin", branch="agent-mail")
    request = box.inbox("coder")[0]

    capsys.readouterr()
    _mail(seed, ["pending"])
    out = capsys.readouterr().out
    assert "coder" in out and "submitted" in out and "API-01" in out

    coder = ws.clone("coder")
    _mail(coder, ["reply", request.id, "--state", "working", "--as", "coder", "--subject", "Bắt đầu"])
    assert box.request_state(request.id) == "working"
    reply = [m for m in box.thread("API-01") if m.in_reply_to == request.id][0]
    assert (reply.to, reply.kind) == (("boss",), "status"), "trả lời đi về người giao, đúng thread"
    assert box.inbox("coder"), "đang làm thì thư giao việc vẫn nằm trong hộp thư"

    _mail(coder, ["reply", request.id, "--state", "completed", "--as", "coder", "--subject", "Xong, commit abc1234"])
    assert box.request_state(request.id) == "completed"
    assert box.inbox("coder") == [], "hoàn tất thì tự xác nhận thư giao việc"
    assert [m.subject for m in box.inbox("boss")][-1] == "Xong, commit abc1234"
    capsys.readouterr()
    _mail(seed, ["pending"])
    assert "API-01" not in capsys.readouterr().out, "việc đã xong không còn trong danh sách chờ"


def test_lenh_team_in_doi_va_tuyen_viec(workspace: Build, capsys: pytest.CaptureFixture[str]) -> None:
    from tools.agentctl.cli import main

    _ws, seed = _setup(workspace)
    assert main(["--repo", str(seed), "team"]) == 0
    out = capsys.readouterr().out
    assert "boss" in out and "coordinator" in out and "ui" in out and "designer" in out
    assert main(["--repo", str(seed), "team", "--route", "ui"]) == 0
    out = capsys.readouterr().out
    assert "designer" in out and "review" in out and "boss" in out
