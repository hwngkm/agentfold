"""`scripts/render_board.py`: bảng việc HTML tĩnh cho người duyệt, CÙNG nguồn dữ liệu với `agentctl board`.

Tiêu chí 2 của ticket: một hàm dựng dữ liệu (`collect_board`), hai cách hiển thị (văn bản, HTML) — không logic thứ hai. Đầu ra văn bản của
`agentctl board` phải giữ nguyên TỪNG BYTE sau khi tách hàm (GOLDEN dưới đây chụp từ mã TRƯỚC khi tách).
"""

from __future__ import annotations

import html as html_lib
import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts import render_board as rb
from scripts.check_design import contrast_ratio
from tests.tools.helpers import Workspace, run_git, ticket_text
from tools.agentctl.board import Board, BoardItem, collect_board, render_board, render_text
from tools.agentctl.lifecycle import ClaimRequest, claim_ticket
from tools.agentctl.mail import Mailbox, new_message

ROOT = Path(__file__).resolve().parents[2]
MOMENT = datetime(2026, 10, 3, 9, 0, tzinfo=UTC)
Build = Callable[[Mapping[str, str]], tuple[Workspace, Path]]

GOLDEN = """Bảng công việc tại `origin/main` (chưa kéo mới)

## đang làm (1)
- API-04 — Claimed one [R1] · R3 · `feature/API-04-x` · hạn 2026-10-04T09:00:00Z

## claim quá hạn (1)
- API-05 — Stale one [R1] · R3 · hết hạn 2026-10-01T09:00:00Z

## ready (1)
- API-01 — Ready one [R1]

## proposed (1)
- API-02 — Proposed one [R1]

## đã merge (1)
- API-03 — Merged one [R1]

## câu hỏi đang mở (1)
- Q-20261003-x → R1 · chặn ['API-01']

## kế hoạch chờ duyệt (1) — chưa viết mã khi chưa `approved`
- PLAN-API-01 · ticket API-01 · soạn bởi R3

## bàn giao đang chờ người nhận (1) — đọc trước khi làm tiếp
- HND-20261003-h · từ R3 · ticket API-01 · nhánh `feature/API-01-x` @ abc1234"""

QUESTION = (
    "---\nid: Q-20261003-x\nkind: question\nstatus: open\nasked_by: R3\nanswer_by: R1\nblocking: [API-01]\n"
    "created: 2026-10-03\n---\n# q\n"
)
PLAN = (
    "---\nid: PLAN-API-01\nkind: plan\nticket: API-01\nstatus: proposed\nauthor_role: R3\napproved_by: null\n---\n# p\n"
)
HANDOFF = (
    "---\nid: HND-20261003-h\nkind: handoff\nstatus: open\nfrom_role: R3\nticket: API-01\nbranch: feature/API-01-x\n"
    "head: abc1234\n---\n# h\n"
)


def _repo(workspace: Build, *, title: str = "Ready one") -> Path:
    """Kho thử đủ mọi nhóm của bảng: ready, proposed, đã merge, đang làm, claim quá hạn, câu hỏi, kế hoạch, bàn giao."""
    ws, _unused = workspace({})
    seed = ws.root / "seed2"
    run_git(ws.root, "init", "--quiet", "--initial-branch=main", str(seed))
    run_git(seed, "remote", "add", "origin", str(ws.remote))
    rows = [("API-01", title, "ready"), ("API-02", "Proposed one", "proposed"), ("API-03", "Merged one", "ready")]
    rows += [("API-04", "Claimed one", "ready"), ("API-05", "Stale one", "ready")]
    tickets = {
        f"docs/work/tickets/{i}.md": ticket_text(i, allow=[f"src/{i.lower()}.py"], title=t, state=s) for i, t, s in rows
    }
    run_git(seed, "pull", "--quiet", "origin", "main")
    ws.commit_push(seed, tickets, "chore: them ticket")
    ws.commit_push(seed, {"src/api-03.py": "x=1\n"}, "feat(x): xong (API-03)")
    files = {
        "docs/work/questions/Q-1.md": QUESTION,
        "docs/work/plans/PLAN-API-01.md": PLAN,
        "docs/work/handoffs/HND-1.md": HANDOFF,
    }
    ws.commit_push(seed, files, "docs: muc cong viec")
    run_git(seed, "fetch", "--quiet", "origin")
    claim_ticket(seed, ClaimRequest("API-04", "R3", "agent-a", branch="feature/API-04-x"), MOMENT)
    stale = MOMENT - timedelta(days=3)
    claim_ticket(seed, ClaimRequest("API-05", "R3", "agent-b", branch="feature/API-05-x"), stale)
    return seed


def _all_items(board: Board) -> list[BoardItem]:
    groups = [*board.tickets.values(), board.questions, board.plans, board.handoffs, board.mail]
    return [item for group in groups for item in group]


# --- tiêu chí 2: một hàm dựng dữ liệu, hai cách hiển thị ---------------------------------------------------------------


def test_dau_ra_van_ban_cua_agentctl_board_giu_nguyen_tung_byte(workspace: Build) -> None:
    repo = _repo(workspace)
    assert render_board(repo, fetch=False, moment=MOMENT) == GOLDEN


def test_bo_hien_thi_van_ban_chi_la_cach_hien_thi_cua_du_lieu_dung_chung(workspace: Build) -> None:
    repo = _repo(workspace)
    board = collect_board(repo, fetch=False, moment=MOMENT)
    assert render_text(board) == GOLDEN
    assert {k: len(v) for k, v in board.tickets.items()} == {
        "đang làm": 1,
        "claim quá hạn": 1,
        "ready": 1,
        "proposed": 1,
        "đã merge": 1,
    }
    assert [i.text for i in board.questions] == ["Q-20261003-x → R1 · chặn ['API-01']"]


def test_html_dung_cung_ham_dung_du_lieu_va_moi_muc_deu_co_trong_html(
    workspace: Build, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(workspace)
    calls: list[bool] = []
    real = rb.collect_board

    def spy(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(kwargs.get("with_mail", False))
        return real(*args, **kwargs)

    monkeypatch.setattr(rb, "collect_board", spy)
    monkeypatch.setenv("AGENTCTL_NOW", MOMENT.isoformat())
    out = tmp_path / "bang.html"
    assert rb.main(["--repo", str(repo), "--offline", "--out", str(out)]) == 0
    assert calls == [True], "bộ HTML phải gọi đúng hàm dựng dữ liệu dùng chung một lần (có kèm thư AGENT-LOG)"
    page = out.read_text(encoding="utf-8")
    for item in _all_items(real(repo, fetch=False, moment=MOMENT, with_mail=True)):
        for part in item.parts:  # HTML tách mỗi mảnh vào một thẻ; mọi mảnh của mọi mục phải có mặt
            assert html_lib.escape(part, quote=True) in page, part


def test_hop_thu_agent_log_hien_o_html_nhung_khong_lam_doi_dau_ra_van_ban(workspace: Build, tmp_path: Path) -> None:
    repo = _repo(workspace)
    Mailbox(repo, remote="origin", branch="agent-mail").send(
        new_message(
            sender="claude-cloud-q1",
            to=["human"],
            thread="API-01",
            kind="request",
            subject="Cần duyệt kế hoạch API-01",
            body="x",
            moment=MOMENT,
        )
    )
    assert render_board(repo, fetch=False, moment=MOMENT) == GOLDEN
    board = collect_board(repo, fetch=False, moment=MOMENT, with_mail=True)
    assert any("Cần duyệt kế hoạch API-01" in i.text for i in board.mail)
    assert "Cần duyệt kế hoạch API-01" in rb.render_html(board, moment=MOMENT)


def test_chua_co_hop_thu_thi_van_ra_html_khong_do(workspace: Build, tmp_path: Path) -> None:
    repo = _repo(workspace)
    board = collect_board(repo, fetch=False, moment=MOMENT, with_mail=True)
    assert board.mail == []
    assert "(trống)" in rb.render_html(board, moment=MOMENT)


# --- tiêu chí 1 + 3: tự chứa, đọc được ở 360px và chế độ tối --------------------------------------------------------


def _sample_page(workspace: Build) -> str:
    repo = _repo(workspace)
    return rb.render_html(collect_board(repo, fetch=False, moment=MOMENT, with_mail=True), moment=MOMENT)


def test_html_tu_chua_khong_tai_gi_tu_mang(workspace: Build) -> None:
    page = _sample_page(workspace)
    assert re.search(r"https?://", page) is None, "không URL ngoài"
    for forbidden in ("<script", "<link", "@import", "url(", "<img", "<iframe", "src="):
        assert forbidden not in page, forbidden


def test_html_co_khung_nhin_thich_ung_va_che_do_toi(workspace: Build) -> None:
    page = _sample_page(workspace)
    assert '<html lang="vi"' in page
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in page
    assert "prefers-color-scheme: dark" in page
    assert "overflow-wrap: anywhere" in page, "mã nhánh dài không được gây cuộn ngang"


def test_html_thoat_ky_tu_dac_biet(workspace: Build) -> None:
    repo = _repo(workspace, title="<script>alert(1)</script>")
    page = rb.render_html(collect_board(repo, fetch=False, moment=MOMENT), moment=MOMENT)
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_bang_mau_dat_wcag_aa(scheme: str) -> None:
    palette = rb.PALETTE[scheme]
    pairs = [("text", "bg"), ("text", "surface"), ("muted", "surface"), ("muted", "bg"), ("accent-text", "accent")]
    for foreground, background in pairs:
        ratio = contrast_ratio(palette[foreground], palette[background])
        assert ratio is not None and ratio >= 4.5, f"{scheme}: {foreground} trên {background} = {ratio}"


# --- ghi tệp: mặc định board/, bỏ qua bằng .gitignore, không làm bẩn cây git ----------------------------------------


def test_mac_dinh_ghi_vao_board_va_gitignore_bo_qua_tep_sinh_ra() -> None:
    assert rb.DEFAULT_OUT == "board/index.html"
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "board/" in [line.strip() for line in ignored], "tệp sinh ra không được làm cây git bẩn"


def test_main_ghi_tep_o_noi_chon_va_in_duong_dan(
    workspace: Build, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo = _repo(workspace)
    out = tmp_path / "nho" / "bang.html"
    assert rb.main(["--repo", str(repo), "--offline", "--out", str(out)]) == 0
    assert out.is_file() and "<!doctype html>" in out.read_text(encoding="utf-8").lower()
    assert str(out) in capsys.readouterr().out


def test_main_mac_dinh_ghi_board_index_trong_repo_va_khong_lam_ban_cay_git(workspace: Build) -> None:
    repo = _repo(workspace)
    (repo / ".gitignore").write_text("board/\n", encoding="utf-8")
    run_git(repo, "add", ".gitignore")
    run_git(repo, "commit", "--quiet", "-m", "chore: gitignore")
    assert rb.main(["--repo", str(repo), "--offline"]) == 0
    assert (repo / "board" / "index.html").is_file()
    assert run_git(repo, "status", "--porcelain").strip() == "", "tệp board/ phải bị bỏ qua"
