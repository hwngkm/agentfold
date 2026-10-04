"""Bộ kiểm phạm vi: phân xử từng file đổi theo chính sách + ticket ĐỌC TỪ NHÁNH GỐC."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.tools.helpers import POLICY, Workspace, run_git, ticket_text
from tools.agentctl.claims import Claim
from tools.agentctl.cli import main
from tools.agentctl.gitutil import Change
from tools.agentctl.lifecycle import ClaimRequest, claim_ticket, create_worktree
from tools.agentctl.policy import parse_policy
from tools.agentctl.scope import Verdict, claim_findings, evaluate
from tools.agentctl.tickets import Ticket, parse_ticket

POLICY_OBJ = parse_policy(POLICY)


def _ticket(**kwargs) -> Ticket:
    return parse_ticket(ticket_text("API-01", **kwargs), source="API-01.md")


def _verdict(changes: list[Change], **ticket_kwargs) -> Verdict:
    return evaluate(changes, policy=POLICY_OBJ, ticket_id="API-01", ticket=_ticket(**ticket_kwargs), approved=False)


def test_file_ngoai_scope_bi_bat() -> None:
    verdict = _verdict(
        [Change("M", "src/api/orders.py"), Change("M", "src/api/users.py")],
        allow=["src/api/orders.py"],
    )
    assert verdict.errors == ("src/api/users.py — ngoài `scope.allow` của `API-01`",)


def test_always_allowed_khong_can_scope() -> None:
    verdict = _verdict([Change("A", "docs/work/log/2026/09/x.md")], allow=["src/api/orders.py"])
    assert verdict.ok


def test_them_luoi_canh_moi_duoc_sua_luoi_cu_can_duyet() -> None:
    verdict = _verdict(
        [Change("A", "tests/guards/test_moi.py"), Change("M", "tests/guards/test_cu.py")],
        allow=["src/api/orders.py"],
    )
    assert not verdict.errors
    assert verdict.approvals_needed == ("tests/guards/test_cu.py — vùng bảo vệ guard-nets",)


def test_ticket_duyet_truoc_vung_bao_ve_thi_khong_can_nhan() -> None:
    verdict = _verdict([Change("M", "docs/design/ARCHITECTURE.md")], allow=["src/x.py"], protected=["design"])
    assert verdict.ok


def test_nhan_duyet_mo_vung_bao_ve_nhung_van_ghi_canh_bao() -> None:
    ticket = _ticket(allow=["src/x.py"])
    verdict = evaluate([Change("M", "AGENTS.md")], policy=POLICY_OBJ, ticket_id="API-01", ticket=ticket, approved=True)
    assert verdict.ok and verdict.warnings


def test_lan_doc_quyen_phai_khai_trong_ticket() -> None:
    change = [Change("A", "alembic/versions/20260915_0002_orders.py")]
    assert _verdict(change, allow=["src/db/models/orders.py"]).errors
    assert _verdict(change, allow=["src/db/models/orders.py"], exclusive=["db-migrations"]).ok


def test_ticket_chua_ready_chan_moi_thu() -> None:
    verdict = _verdict([Change("M", "src/api/orders.py")], allow=["src/api/orders.py"], state="proposed")
    assert verdict.errors and "proposed" in verdict.errors[0]


def test_nhanh_khong_ticket_chi_duoc_them_ticket_de_xuat_va_always_allowed() -> None:
    verdict = evaluate(
        [
            Change("A", "docs/work/tickets/API-09.md"),
            Change("A", "docs/work/questions/Q-1.md"),
            Change("M", "src/api/orders.py"),
        ],
        policy=POLICY_OBJ,
        ticket_id=None,
        ticket=None,
        approved=False,
    )
    assert len(verdict.errors) == 1 and verdict.errors[0].startswith("src/api/orders.py")


def test_claim_findings_bat_thieu_claim_sai_nhanh_va_het_han() -> None:
    now = datetime(2026, 9, 15, tzinfo=UTC)
    claim = Claim("API-01", "R3", "s", "feature/API-01-x", "2026-09-14T00:00:00Z", "2026-09-15T12:00:00Z")
    assert claim_findings({}, "API-01", "feature/API-01-x", now)[0]
    assert claim_findings({"API-01": claim}, "API-01", "feature/API-01-khac", now)[0]
    assert claim_findings({"API-01": claim}, "API-01", "feature/API-01-x", now) == ([], [])
    assert claim_findings({"API-01": claim}, "API-01", "feature/API-01-x", now + timedelta(days=1))[1]


def test_cli_doc_ticket_tu_base_nen_nhanh_tu_noi_scope_van_bi_bat(
    workspace, capsys: pytest.CaptureFixture[str]
) -> None:
    """Đầu-cuối trên git thật: nhánh sửa ticket để nới scope rồi thêm file vào vùng vừa nới.

    Bộ kiểm đọc ticket từ BASE, nên (1) file mới vẫn ngoài scope và (2) việc sửa ticket bị đòi duyệt.
    """
    ws, repo = workspace({"API-01": ticket_text("API-01", allow=["src/api/orders.py"])})
    run_git(repo, "switch", "--quiet", "-c", "feature/API-01-don-hang")
    Workspace.write(
        repo,
        {
            "docs/work/tickets/API-01.md": ticket_text("API-01", allow=["src/api/**"]),
            "src/api/orders.py": "x = 1\n",
            "src/api/users.py": "y = 2\n",
        },
    )
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "--quiet", "-m", "feat(api): don hang (API-01)")

    code = main(["--repo", str(repo), "check-scope", "--base", "origin/main"])
    output = capsys.readouterr().out
    assert code == 1
    assert "src/api/users.py — ngoài `scope.allow`" in output
    assert "docs/work/tickets/API-01.md — vùng bảo vệ work-plan" in output
    assert "src/api/orders.py —" not in output

    labelled = main(["--repo", str(repo), "check-scope", "--base", "origin/main", "--labels", '["human-approved"]'])
    assert labelled == 1, "nhãn duyệt mở vùng bảo vệ nhưng KHÔNG hợp thức hoá file ngoài scope"


def test_cli_pre_commit_bo_qua_khi_chua_co_base(tmp_path: Path, git_isolated: None) -> None:
    run_git(tmp_path, "init", "--quiet", "--initial-branch=main")
    assert main(["--repo", str(tmp_path), "check-scope", "--staged"]) == 0


def test_du_an_nam_trong_thu_muc_con_cua_monorepo(
    tmp_path: Path, git_isolated: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """Dự án ở `app/` của monorepo: gốc dự án nhận theo `coordination/policy.yaml`, không theo gốc git.

    Phân xử chỉ tính file trong `app/` và đường dẫn tính TỪ `app/` — dự án khác trong cùng repo không bị
    ràng buộc bởi chính sách này.
    """
    remote = tmp_path / "remote.git"
    run_git(tmp_path, "init", "--quiet", "--bare", "--initial-branch=main", str(remote))
    seed = tmp_path / "seed"
    run_git(tmp_path, "init", "--quiet", "--initial-branch=main", str(seed))
    run_git(seed, "remote", "add", "origin", str(remote))
    Workspace.write(
        seed,
        {
            "app/coordination/policy.yaml": POLICY,
            "app/docs/work/tickets/API-01.md": ticket_text("API-01", allow=["src/api/orders.py"]),
            "du-an-khac/readme.md": "dự án khác trong monorepo\n",
        },
    )
    run_git(seed, "add", "-A")
    run_git(seed, "commit", "--quiet", "-m", "chore: khoi tao")
    run_git(seed, "push", "--quiet", "origin", "HEAD:main")
    run_git(seed, "fetch", "--quiet", "origin")

    run_git(seed, "switch", "--quiet", "-c", "feature/API-01-don-hang")
    Workspace.write(
        seed,
        {
            "app/src/api/orders.py": "x = 1\n",
            "app/src/api/users.py": "y = 2\n",
            "du-an-khac/readme.md": "sửa dự án khác\n",
        },
    )
    run_git(seed, "add", "-A")
    run_git(seed, "commit", "--quiet", "-m", "feat(api): don hang (API-01)")

    app = seed / "app"
    assert main(["--repo", str(app), "check-scope", "--base", "origin/main"]) == 1
    output = capsys.readouterr().out
    assert "src/api/users.py — ngoài `scope.allow`" in output
    assert "du-an-khac" not in output, "dự án khác trong monorepo không bị phân xử theo chính sách này"

    claim, _notes = claim_ticket(app, ClaimRequest("API-01", "R3", "a"), datetime(2026, 9, 15, tzinfo=UTC))
    project_dir, created = create_worktree(app, claim, "origin/main")
    assert created and (project_dir / "coordination" / "policy.yaml").is_file()
