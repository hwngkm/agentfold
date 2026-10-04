"""Ba quy trình chuẩn có ĐẦU RA CỐ ĐỊNH, kiểm được bằng máy: sửa lỗi, thẩm định ý tưởng, duyệt kế hoạch trước khi viết mã.

Vì sao: "đã sửa lỗi" và "ý tưởng này nên làm" là loại khẳng định agent hay đưa ra mà không để lại gì kiểm được. Mỗi quy
trình kết thúc bằng một tệp có kết luận thuộc tập đóng — `verified | partial | failed` cho sửa lỗi, `go | clarify | kill`
cho thẩm định, `proposed | approved | rejected` cho kế hoạch — nên "thiếu bằng chứng" không thể bị diễn đạt thành "xong".
Ý tưởng mượn từ github/spec-kit (bug-fix assess→fix→test; idea assessment) và MrLesk/Backlog.md (duyệt kế hoạch trước mã).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.tools.helpers import POLICY, Workspace, run_git, ticket_text
from tools.agentctl.board import render_board
from tools.agentctl.entries import create_entry, create_plan
from tools.agentctl.errors import AgentctlError
from tools.agentctl.policy import parse_policy
from tools.agentctl.workcheck import validate_work_items

MOMENT = datetime(2026, 10, 4, 9, 0, tzinfo=UTC)
Build = Callable[[Mapping[str, str]], tuple[Workspace, Path]]


def _problems(root: Path) -> list[str]:
    return validate_work_items(root, parse_policy(POLICY))


def test_muc_sua_loi_va_tham_dinh_sinh_ra_qua_kiem_cau_truc(tmp_path: Path) -> None:
    bug = create_entry(tmp_path, "bug", title="Gửi form rỗng làm sập đăng nhập", role="R3", moment=MOMENT)
    asm = create_entry(tmp_path, "assessment", title="Cho phép dùng offline", role="R2", moment=MOMENT)
    assert bug.as_posix().endswith("docs/work/bugs/BUG-20261004-gui-form-rong-lam-sap-dang-nhap.md")
    assert asm.as_posix().endswith("docs/work/assessments/ASM-20261004-cho-phep-dung-offline.md")
    assert "verdict: pending" in bug.read_text(encoding="utf-8")
    assert "decision: pending" in asm.read_text(encoding="utf-8")
    assert _problems(tmp_path) == []


@pytest.mark.parametrize(
    ("kind", "old", "new", "fragment"),
    [
        ("bug", "verdict: pending", "verdict: da-sua", "`verdict` phải thuộc"),
        ("assessment", "decision: pending", "decision: co-le", "`decision` phải thuộc"),
    ],
)
def test_ket_luan_ngoai_tap_dong_bi_bat(tmp_path: Path, kind: str, old: str, new: str, fragment: str) -> None:
    path = create_entry(tmp_path, kind, title="Việc", role="R3", moment=MOMENT)
    path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    assert any(fragment in p for p in _problems(tmp_path))


def test_sua_loi_xac_nhan_phai_co_bang_chung(tmp_path: Path) -> None:
    """`verified` mà không nói lệnh nào đã chạy thì chỉ là tự khai (R00.8)."""
    path = create_entry(tmp_path, "bug", title="Lỗi", role="R3", moment=MOMENT)
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("verdict: pending", "verdict: verified"), encoding="utf-8")
    assert any("verified" in p and "bằng chứng" in p for p in _problems(tmp_path))
    path.write_text(
        text.replace("verdict: pending", "verdict: verified").replace(
            "evidence: []", 'evidence: ["pytest tests/unit/test_login.py -q: 3 passed (đã đỏ trước khi sửa)"]'
        ),
        encoding="utf-8",
    )
    assert _problems(tmp_path) == []


def test_tham_dinh_go_phai_co_ly_do(tmp_path: Path) -> None:
    path = create_entry(tmp_path, "assessment", title="Ý tưởng", role="R2", moment=MOMENT)
    text = path.read_text(encoding="utf-8").replace("decision: pending", "decision: go")
    path.write_text(text, encoding="utf-8")
    assert any("go" in p and "bằng chứng" in p for p in _problems(tmp_path))
    path.write_text(
        text.replace("evidence: []", 'evidence: ["phỏng vấn 5 người: 4 người dùng bảng tính"]'), encoding="utf-8"
    )
    assert _problems(tmp_path) == []


def test_ke_hoach_dung_ma_ticket_va_duyet_phai_co_nguoi(tmp_path: Path) -> None:
    path = create_plan(tmp_path, ticket_id="API-01", title="Thêm đơn hàng", role="R3")
    assert path.name == "PLAN-API-01.md" and _problems(tmp_path) == []
    with pytest.raises(AgentctlError, match="đã tồn tại"):
        create_plan(tmp_path, ticket_id="API-01", title="Trùng", role="R3")
    with pytest.raises(AgentctlError, match="mã ticket"):
        create_plan(tmp_path, ticket_id="sai ma", title="x", role="R3")

    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("status: proposed", "status: approved"), encoding="utf-8")
    assert any("approved_by" in p for p in _problems(tmp_path)), "duyệt mà không ghi ai duyệt"
    path.write_text(
        text.replace("status: proposed", "status: approved").replace("approved_by: null", "approved_by: R1"),
        encoding="utf-8",
    )
    assert _problems(tmp_path) == []
    path.write_text(text.replace("ticket: API-01", "ticket: API-02"), encoding="utf-8")
    assert any("PLAN-API-01" in p or "ticket" in p for p in _problems(tmp_path))


def test_bang_viec_liet_ke_ke_hoach_cho_duyet(workspace: Build, tmp_path: Path) -> None:
    ws, seed = workspace({"API-01": ticket_text("API-01", allow=["src/x.py"])})
    plan = create_plan(tmp_path / "gen", ticket_id="API-01", title="Thêm đơn hàng", role="R3")
    ws.commit_push(seed, {"docs/work/plans/PLAN-API-01.md": plan.read_text(encoding="utf-8")}, "docs: kế hoạch")
    run_git(seed, "fetch", "--quiet", "origin")
    board = render_board(seed, fetch=False, moment=MOMENT)
    assert "kế hoạch chờ duyệt" in board and "PLAN-API-01" in board


def test_ke_hoach_co_san_khong_the_tu_duyet_o_vung_thuong() -> None:
    """CHÍNH SÁCH THẬT của repo: thêm kế hoạch đề xuất thì tự do; ĐỔI kế hoạch có sẵn (= duyệt) thuộc vùng `work-plan`."""
    from tools.agentctl.gitutil import Change
    from tools.agentctl.policy import load_policy
    from tools.agentctl.scope import evaluate

    root = Path(__file__).resolve().parents[2]
    policy = load_policy(root, None)
    added = evaluate(
        [Change("A", "docs/work/plans/PLAN-API-01.md")], policy=policy, ticket_id=None, ticket=None, approved=False
    )
    edited = evaluate(
        [Change("M", "docs/work/plans/PLAN-API-01.md")], policy=policy, ticket_id=None, ticket=None, approved=False
    )
    assert not added.errors and not added.approvals_needed, "thêm kế hoạch mới tự do"
    assert edited.approvals_needed or edited.errors, "sửa kế hoạch có sẵn (duyệt) cần người"
    free = evaluate(
        [Change("A", "docs/work/bugs/BUG-20261004-x.md")], policy=policy, ticket_id=None, ticket=None, approved=False
    )
    assert not free.errors and not free.approvals_needed, "báo cáo sửa lỗi là mục tự do như nhật ký"
