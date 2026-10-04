"""Mục công việc một-file-một-mục và thông điệp commit mang mã ticket."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.tools.helpers import POLICY, ticket_text
from tools.agentctl.commitmsg import check_commit_message
from tools.agentctl.entries import create_entry, create_ticket, slugify
from tools.agentctl.errors import AgentctlError
from tools.agentctl.policy import PolicyError, parse_policy
from tools.agentctl.tickets import TicketError, parse_ticket, policy_problems, ticket_id_from_branch
from tools.agentctl.workcheck import validate_work_items

MOMENT = datetime(2026, 9, 15, 9, 30, tzinfo=UTC)


def test_slug_tieng_viet_on_dinh() -> None:
    assert slugify("Đổi ngưỡng đường huyết — bản nháp #2") == "doi-nguong-duong-huyet-ban-nhap-2"
    assert slugify("!!!") == "khong-ten"


def test_hai_agent_ghi_cung_tieu_de_ra_hai_file_khac_nhau(tmp_path: Path) -> None:
    first = create_entry(tmp_path, "decision", title="Chọn hàng đợi", role="R1", moment=MOMENT)
    second = create_entry(tmp_path, "decision", title="Chọn hàng đợi", role="R3", moment=MOMENT)
    assert first != second and first.exists() and second.exists()
    assert second.stem == "DEC-20260915-chon-hang-doi-2"
    assert "id: DEC-20260915-chon-hang-doi-2" in second.read_text(encoding="utf-8")


def test_muc_sinh_ra_qua_duoc_kiem_cau_truc(tmp_path: Path) -> None:
    policy = parse_policy(POLICY)
    create_entry(tmp_path, "question", title="Ngưỡng nào?", role="R2", moment=MOMENT, blocking=["API-01"])
    create_entry(tmp_path, "incident", title="CI đỏ", role="R3", moment=MOMENT)
    create_entry(tmp_path, "log", title="Buổi sáng", role="R2", moment=MOMENT)
    create_ticket(tmp_path, policy.tickets_dir, ticket_id="API-01", title="Đơn hàng", role="R3")
    assert validate_work_items(tmp_path, policy) == []
    with pytest.raises(AgentctlError, match="đã tồn tại"):
        create_ticket(tmp_path, policy.tickets_dir, ticket_id="API-01", title="Trùng", role="R3")


def test_kiem_cau_truc_bat_ticket_hong_va_phu_thuoc_ma(tmp_path: Path) -> None:
    policy = parse_policy(POLICY)
    tickets = tmp_path / policy.tickets_dir
    tickets.mkdir(parents=True)
    (tickets / "API-01.md").write_text(ticket_text("API-01", allow=["src/x.py"], depends_on=["API-99"]), "utf-8")
    (tickets / "API-02.md").write_text(ticket_text("API-03", allow=["src/y.py"]), "utf-8")
    problems = validate_work_items(tmp_path, policy)
    assert any("API-99" in p for p in problems)
    assert any("tên file phải là `API-03.md`" in p for p in problems)


@pytest.mark.parametrize(
    ("kwargs", "fragment"),
    [
        ({"allow": ["**"]}, "phủ cả repo"),
        ({"allow": ["src/x.py"], "state": "done"}, "được suy ra"),
        ({}, "scope` rỗng"),
    ],
)
def test_ticket_sai_bi_tu_choi(kwargs: dict, fragment: str) -> None:
    with pytest.raises(TicketError, match=fragment):
        parse_ticket(ticket_text("API-01", **kwargs), source="API-01.md")


@pytest.mark.parametrize(
    ("allow", "fragment"),
    [
        (["alembic/versions/20260915_x.py"], "lấn làn `db-migrations`"),
        (["docs/**"], "lấn vùng bảo vệ `design`"),
        (["**/*.py"], "lấn vùng bảo vệ `guard-nets`"),
    ],
)
def test_allow_khong_duoc_lan_lan_hay_vung_ma_khong_khai_ten(allow: list[str], fragment: str) -> None:
    """Không có luật này, hai ticket cùng chạm `alembic/versions/**` mà sổ claim không biết chúng tranh một làn."""
    ticket = parse_ticket(ticket_text("API-01", allow=allow), source="API-01.md")
    assert any(fragment in problem for problem in policy_problems(ticket, parse_policy(POLICY)))


def test_mau_bat_dau_bang_sao_khong_ngoac_kep_duoc_chi_cach_sua() -> None:
    """`**/*.md` không ngoặc kép là alias YAML — lỗi gốc của PyYAML không nói gì về đường dẫn."""
    text = ticket_text("API-01", allow=["src/x.py"]).replace('"src/x.py"', "**/*.md")
    with pytest.raises(TicketError, match="ngoặc kép"):
        parse_ticket(text, source="API-01.md")


def test_policy_cam_lan_chong_vung_bao_ve() -> None:
    broken = POLICY.replace("paths: [alembic/versions/**]", "paths: [docs/design/adr/**]")
    with pytest.raises(PolicyError, match="chồng vùng bảo vệ"):
        parse_policy(broken)


@pytest.mark.parametrize(
    ("message", "branch", "ok"),
    [
        ("feat(api): thêm đơn hàng (API-01)", "feature/API-01-don-hang", True),
        ("feat(api): thêm đơn hàng", "feature/API-01-don-hang", False),
        ("sửa lung tung", "main", False),
        ("docs: cập nhật README", "main", True),
        ("Merge branch 'main' into feature/API-01-x", "feature/API-01-x", True),
    ],
)
def test_thong_diep_commit(message: str, branch: str, ok: bool) -> None:
    assert (check_commit_message(message, ticket_id_from_branch(branch)) == []) is ok
