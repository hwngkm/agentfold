"""`agentctl prime`: MỘT lệnh cho agent mới vào phiên — bất kể công cụ — biết đủ để làm tiếp.

Vì sao: trước đây agent phải nhớ chạy 4–5 lệnh (git log, status, board, mail inbox, đọc SKILLS.md); agent hết hạn mức
được thay bằng agent khác nhà cung cấp thì thường bỏ sót một trong số đó và làm lại việc đã làm. Ý tưởng mượn từ
`bd prime` của gastownhall/beads.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

from tests.tools.helpers import Workspace, run_git, ticket_text
from tools.agentctl.mail import Mailbox, new_message
from tools.agentctl.prime import render_prime

MOMENT = datetime(2026, 10, 4, 9, 0, tzinfo=UTC)
Build = Callable[[Mapping[str, str]], tuple[Workspace, Path]]
AGENTS_MD = """# AGENTS.md
## 2. Tám luật tối cao

1. **Thiết kế do người chốt là luật.** chi tiết…
2. **Một ticket · một claim · một nhánh · một worktree.** chi tiết…

## 3. Khác
"""


def test_prime_gom_luat_viec_thu_va_buoc_tiep(workspace: Build) -> None:
    ws, seed = workspace({"API-01": ticket_text("API-01", allow=["src/x.py"], title="Thêm đơn hàng")})
    ws.commit_push(seed, {"AGENTS.md": AGENTS_MD}, "docs: luật")
    box = Mailbox(seed, remote="origin", branch="agent-mail")
    box.send(
        new_message(
            sender="human",
            to=["codex-1"],
            thread="API-01",
            kind="request",
            subject="Ưu tiên API-01",
            body=".",
            moment=MOMENT,
            ack_required=True,
        )
    )
    run_git(seed, "checkout", "--quiet", "-b", "feature/API-01-them-don-hang")
    ws.write(seed, {"src/x.py": "x = 1\n"})

    text = render_prime(seed, agent="codex-1", fetch=True, moment=MOMENT)
    assert "Thiết kế do người chốt là luật." in text and "Một ticket · một claim" in text
    assert "feature/API-01-them-don-hang" in text and "1 tệp chưa commit" in text
    assert "API-01 — Thêm đơn hàng" in text and "có test" in text, "ticket + tiêu chí nghiệm thu"
    assert "chưa có claim" in text
    assert "Ưu tiên API-01" in text and "cần xác nhận" in text
    assert "agentctl start API-01" in text, "bước tiếp theo nói đúng lệnh"


def test_prime_khong_co_dinh_danh_va_khong_remote_van_chay(tmp_path: Path, git_isolated: None) -> None:
    repo = tmp_path / "solo"
    run_git(tmp_path, "init", "--quiet", "--initial-branch=main", str(repo))
    (repo / "AGENTS.md").write_text(AGENTS_MD, encoding="utf-8")
    text = render_prime(repo, agent=None, fetch=True, moment=MOMENT)
    assert "AGENTCTL_AGENT" in text, "nhắc đặt định danh để đọc hộp thư"
    assert "Thiết kế do người chốt là luật." in text


def test_prime_cho_biet_vi_tri_trong_doi_va_uu_tien_thu_giao_viec(workspace: Build) -> None:
    from tests.tools.test_team import TEAM

    ws, seed = workspace({"API-01": ticket_text("API-01", allow=["src/x.py"], title="Thêm đơn hàng")})
    ws.commit_push(seed, {"AGENTS.md": AGENTS_MD, "coordination/team.yaml": TEAM}, "docs: luật + đội")
    box = Mailbox(seed, remote="origin", branch="agent-mail")
    sent = box.send(
        new_message(
            sender="boss",
            to=["coder"],
            thread="API-01",
            kind="request",
            subject="Giao API-01",
            body=".",
            moment=MOMENT,
            ack_required=True,
        )
    )
    text = render_prime(seed, agent="coder", fetch=True, moment=MOMENT)
    assert "specialist" in text and "báo cáo cho `boss`" in text, "agent biết mình là ai và báo cho ai"
    assert "đặt ticket `ready`" in text, "nhắc việc chỉ người làm"
    next_step = text.split("## Bước tiếp theo", 1)[1]
    assert f"mail read {sent.id}" in next_step, "thư giao việc đi trước mọi việc khác"
