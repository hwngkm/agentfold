"""Bàn giao giữa agent: git điền sẵn sự thật, bộ kiểm cấu trúc bắt mục hỏng.

Vì sao: agent hết hạn mức dừng giữa chừng, đúng lúc không còn sức ghi chú. Phần máy đo được phải tự có.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path

from tests.tools.helpers import POLICY, Workspace, run_git
from tools.agentctl.entries import create_entry
from tools.agentctl.handoff import MAX_DIRTY_LINES, collect_facts
from tools.agentctl.policy import parse_policy
from tools.agentctl.tickets import split_front_matter
from tools.agentctl.workcheck import validate_work_items

MOMENT = datetime(2026, 10, 3, 9, 0, tzinfo=UTC)
Build = Callable[[Mapping[str, str]], tuple[Workspace, Path]]


def test_bao_cao_git_that_cua_cay_lam_viec(workspace: Build) -> None:
    ws, seed = workspace({})
    run_git(seed, "checkout", "--quiet", "-b", "feature/API-01-don-hang")
    ws.write(seed, {"src/moi.py": "x = 1\n", "README.md": "# sửa dở\n"})
    facts = collect_facts(seed)
    assert facts["branch"] == "feature/API-01-don-hang"
    assert facts["ticket"] == "API-01"
    assert facts["dirty_count"] == "2"
    assert "src/moi.py" in facts["dirty"] and "README.md" in facts["dirty"]
    assert facts["subject"] == "chore: khởi tạo"
    assert facts["unpushed"].startswith("không rõ")  # nhánh mới chưa có upstream — nói thật, không bịa


def test_cay_sach_va_danh_sach_dai_duoc_cat(workspace: Build) -> None:
    ws, seed = workspace({})
    assert collect_facts(seed)["dirty"] == "(cây làm việc sạch)"
    ws.write(seed, {f"rac/{i}.txt": "x" for i in range(MAX_DIRTY_LINES + 5)})
    facts = collect_facts(seed)
    assert facts["dirty_count"] == str(MAX_DIRTY_LINES + 5)
    assert "và 5 dòng nữa" in facts["dirty"]


def test_muc_ban_giao_sinh_ra_qua_kiem_cau_truc_va_giu_nguyen_kieu(tmp_path: Path) -> None:
    """`head` toàn chữ số (vd. `1234567`) mà không đặt trong ngoặc kép thì YAML hiểu thành số nguyên."""
    policy = parse_policy(POLICY)
    facts = {"branch": "feature/API-01-x", "head": "1234567", "ticket": "API-01", "dirty": "(cây làm việc sạch)"}
    path = create_entry(tmp_path, "handoff", title="Hết hạn mức", role="R3", moment=MOMENT, facts=facts)
    assert path.as_posix().endswith("docs/work/handoffs/HND-20261003-het-han-muc.md")
    data, body = split_front_matter(path.read_text(encoding="utf-8"))
    assert data["head"] == "1234567" and data["ticket"] == "API-01" and data["status"] == "open"
    assert "Còn dở" in body and "Đã thử và SAI" in body
    assert validate_work_items(tmp_path, policy) == []


def test_ban_giao_khong_ticket_van_hop_le(tmp_path: Path) -> None:
    create_entry(tmp_path, "handoff", title="Dừng ở main", role="R2", moment=MOMENT, facts={"branch": "main"})
    assert validate_work_items(tmp_path, parse_policy(POLICY)) == []


def test_kiem_cau_truc_bat_ban_giao_hong(tmp_path: Path) -> None:
    folder = tmp_path / "docs/work/handoffs"
    folder.mkdir(parents=True)
    (folder / "HND-20261003-a.md").write_text("---\nid: HND-20261003-a\nstatus: pending\nticket: abc\n---\n", "utf-8")
    problems = validate_work_items(tmp_path, parse_policy(POLICY))
    assert any("`status` phải thuộc" in p for p in problems)
    assert any("`ticket` phải là mã ticket hoặc null" in p for p in problems)
