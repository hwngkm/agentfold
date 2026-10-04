"""Agent điền được kế hoạch của CHÍNH MÌNH, nhưng không tự duyệt.

Lỗi gốc (ca thử cloud 04/10/2026): `agentctl new plan` tạo `docs/work/plans/PLAN-<ID>.md` (vùng `work-plan`, cho THÊM mới), rồi hook
`guard_write.py` coi tệp đã có trên đĩa là SỬA và chặn — agent không điền được kế hoạch vừa tạo. Cổng thật (`check-scope`) so với nhánh
gốc nên tệp đó vẫn là THÊM. Sửa: hook phân xử theo nhánh gốc như cổng thật, cho điền kế hoạch `proposed` của ticket đang làm, và
CHẶN mọi nội dung tự đặt `status: approved` (duyệt là việc của người).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from scripts.hooks import guard_write
from tests.tools.helpers import POLICY, Workspace, run_git, ticket_text
from tools.agentctl.cli import main
from tools.agentctl.entries import create_plan

Build = Callable[[Mapping[str, str]], tuple[Workspace, Path]]
PLAN = "docs/work/plans/PLAN-API-01.md"
OTHER = "docs/work/plans/PLAN-API-02.md"
TICKETS = {
    "API-01": ticket_text("API-01", allow=["src/api/orders.py"]),
    "API-02": ticket_text("API-02", allow=["src/api/users.py"]),
}


# Chính sách thật có `docs/work/plans/` trong vùng `work-plan`; chính sách mẫu của helpers chỉ có `tickets/`.
POLICY_WITH_PLANS = POLICY.replace("paths: [docs/work/tickets/**]", "paths: [docs/work/tickets/**, docs/work/plans/**]")


def _plan_text(ticket: str, status: str = "proposed", approved_by: str = "null") -> str:
    return (
        f"---\nid: PLAN-{ticket}\nkind: plan\nticket: {ticket}\nstatus: {status}\nauthor_role: R3\n"
        f"approved_by: {approved_by}\n---\n# Kế hoạch {ticket}\n"
    )


def _repo(workspace: Build, *, on_main: Mapping[str, str] | None = None) -> Path:
    ws, repo = workspace(TICKETS)
    assert POLICY_WITH_PLANS != POLICY
    ws.commit_push(
        repo, {"coordination/policy.yaml": POLICY_WITH_PLANS, **(on_main or {})}, "chore: chinh sach co plans"
    )
    run_git(repo, "switch", "--quiet", "-c", "feature/API-01-don-hang")
    return repo


def _write(repo: Path, rel: str, content: str) -> int:
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(repo / rel), "content": content}}
    return guard_write.decide(payload, cwd=repo)[0]


def _edit(repo: Path, rel: str, new: str) -> int:
    payload = {"tool_name": "Edit", "tool_input": {"file_path": str(repo / rel), "old_string": "x", "new_string": new}}
    return guard_write.decide(payload, cwd=repo)[0]


def test_dien_duoc_ke_hoach_vua_tao_bang_new_plan(workspace: Build) -> None:
    """Tái hiện lỗi gốc: tạo kế hoạch bằng lệnh của repo rồi điền nó."""
    repo = _repo(workspace)
    create_plan(repo, ticket_id="API-01", title="Kế hoạch", role="R3")
    assert (repo / PLAN).is_file()
    assert _write(repo, PLAN, _plan_text("API-01") + "## Các bước\n1. test đỏ\n") == 0


def test_khong_cho_tu_duyet_ke_hoach_vua_tao(workspace: Build) -> None:
    repo = _repo(workspace)
    create_plan(repo, ticket_id="API-01", title="Kế hoạch", role="R3")
    assert _write(repo, PLAN, _plan_text("API-01", "approved", "R1")) == guard_write.BLOCK
    assert _edit(repo, PLAN, "status: approved") == guard_write.BLOCK
    assert _edit(repo, PLAN, "approved_by: R1") == guard_write.BLOCK


def test_ke_hoach_proposed_tren_main_cua_ticket_dang_lam_thi_dien_duoc(workspace: Build) -> None:
    repo = _repo(workspace, on_main={PLAN: _plan_text("API-01")})
    assert _write(repo, PLAN, _plan_text("API-01") + "## Rủi ro\n- ...\n") == 0
    assert _write(repo, PLAN, _plan_text("API-01", "approved", "R1")) == guard_write.BLOCK


def test_ke_hoach_da_duyet_tren_main_bi_chan_nhu_cu(workspace: Build) -> None:
    repo = _repo(workspace, on_main={PLAN: _plan_text("API-01", "approved", "R1")})
    assert _write(repo, PLAN, _plan_text("API-01", "approved", "R1") + "sửa lén\n") == guard_write.BLOCK


def test_khong_sua_ke_hoach_cua_ticket_khac_da_co_tren_main(workspace: Build) -> None:
    repo = _repo(workspace, on_main={OTHER: _plan_text("API-02")})
    assert _write(repo, OTHER, _plan_text("API-02") + "chen vào\n") == guard_write.BLOCK


def test_van_chan_ngoai_ke_hoach_nhu_cu(workspace: Build) -> None:
    repo = _repo(workspace)
    assert _write(repo, "docs/design/ARCHITECTURE.md", "x") == guard_write.BLOCK
    assert _write(repo, "docs/work/tickets/API-01.md", ticket_text("API-01", allow=["src/**"])) == guard_write.BLOCK


def test_check_scope_doi_tu_duyet_phai_co_nhan_cua_nguoi(workspace: Build, capsys: pytest.CaptureFixture[str]) -> None:
    repo = _repo(workspace)
    Workspace.write(repo, {PLAN: _plan_text("API-01", "approved", "R1")})
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "--quiet", "-m", "docs(work): ke hoach tu duyet (API-01)")
    assert main(["--repo", str(repo), "check-scope", "--base", "origin/main"]) == 1
    assert "approved" in capsys.readouterr().out
    labelled = ["--repo", str(repo), "check-scope", "--base", "origin/main", "--labels", json.dumps(["human-approved"])]
    assert main(labelled) == 0, "người gắn nhãn thì được"


def test_check_scope_ke_hoach_proposed_moi_thi_qua(workspace: Build) -> None:
    repo = _repo(workspace)
    Workspace.write(repo, {PLAN: _plan_text("API-01")})
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "--quiet", "-m", "docs(work): ke hoach de xuat (API-01)")
    assert main(["--repo", str(repo), "check-scope", "--base", "origin/main"]) == 0
