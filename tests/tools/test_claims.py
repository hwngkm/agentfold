"""Sổ claim trên git thật: nhiều bản clone = nhiều agent làm song song trên các máy khác nhau."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.tools.helpers import Workspace, run_git, ticket_text
from tools.agentctl.claims import ClaimRefusedError, ClaimRegistry
from tools.agentctl.errors import AgentctlError
from tools.agentctl.lifecycle import (
    ClaimRequest,
    claim_ticket,
    create_worktree,
    load_context,
    reap_expired,
    release_claim,
)

T0 = datetime(2026, 9, 15, 8, 0, tzinfo=UTC)


def _claims_on_remote(repo: Path) -> dict[str, str]:
    policy, _ = load_context(repo, fetch=True)
    registry = ClaimRegistry(repo, policy)
    return {tid: claim.branch for tid, claim in registry.read(registry.fetch()).items()}


def test_hai_agent_khong_giu_duoc_hai_pham_vi_chong_nhau(workspace) -> None:
    ws, a = workspace(
        {
            "API-01": ticket_text("API-01", allow=["src/api/orders/**"]),
            "API-02": ticket_text("API-02", allow=["src/api/orders/models.py"]),
            "WEB-01": ticket_text("WEB-01", allow=["web/src/app/orders/**"]),
        }
    )
    b = ws.clone("agent-b")

    claim_ticket(a, ClaimRequest("API-01", "R3", "agent-a"), T0)
    with pytest.raises(ClaimRefusedError) as refused:
        claim_ticket(b, ClaimRequest("API-02", "R1", "agent-b"), T0)
    assert "API-01" in str(refused.value) and "src/api/orders/models.py" in str(refused.value)

    claim_ticket(b, ClaimRequest("WEB-01", "R4", "agent-b"), T0)
    assert set(_claims_on_remote(ws.clone("nguoi-xem"))) == {"API-01", "WEB-01"}


def test_lan_doc_quyen_chi_mot_ticket_giu(workspace) -> None:
    ws, a = workspace(
        {
            "DB-01": ticket_text("DB-01", allow=["src/db/models/orders.py"], exclusive=["db-migrations"]),
            "DB-02": ticket_text("DB-02", allow=["src/db/models/users.py"], exclusive=["db-migrations"]),
        }
    )
    claim_ticket(a, ClaimRequest("DB-01", "R3", "a"), T0)
    with pytest.raises(ClaimRefusedError, match="db-migrations"):
        claim_ticket(ws.clone("b"), ClaimRequest("DB-02", "R3", "b"), T0)


def test_chi_claim_duoc_ticket_ready_tren_nhanh_goc(workspace) -> None:
    ws, a = workspace({"API-01": ticket_text("API-01", state="proposed", allow=["src/api/x.py"])})
    with pytest.raises(ClaimRefusedError, match="proposed"):
        claim_ticket(a, ClaimRequest("API-01", "R3", "a"), T0)


def test_sua_ticket_cuc_bo_khong_noi_duoc_pham_vi(workspace) -> None:
    """Agent tự đổi ticket trong bản clone (chưa merge) để nới scope — claim vẫn đọc bản trên `origin/main`."""
    ws, a = workspace(
        {
            "API-01": ticket_text("API-01", allow=["src/api/orders.py"]),
            "API-02": ticket_text("API-02", allow=["src/api/users.py"]),
        }
    )
    claim_ticket(a, ClaimRequest("API-01", "R3", "a"), T0)
    b = ws.clone("b")
    Workspace.write(b, {"docs/work/tickets/API-02.md": ticket_text("API-02", allow=["src/api/**"])})
    claim = claim_ticket(b, ClaimRequest("API-02", "R1", "b"), T0)[0]
    assert claim.allow == ("src/api/users.py",)


def test_phu_thuoc_chua_merge_bi_chan_tru_khi_xac_nhan(workspace) -> None:
    ws, a = workspace(
        {
            "API-01": ticket_text("API-01", allow=["src/api/a.py"]),
            "API-02": ticket_text("API-02", allow=["src/api/b.py"], depends_on=["API-01"]),
        }
    )
    with pytest.raises(ClaimRefusedError, match="phụ thuộc"):
        claim_ticket(a, ClaimRequest("API-02", "R3", "a"), T0)
    claim_ticket(a, ClaimRequest("API-02", "R3", "a", allow_unmerged_deps=True), T0)

    ws.commit_push(ws.clone("merge"), {"src/api/a.py": "x = 1\n"}, "feat(api): a (API-01)")
    b = ws.clone("b")
    release_claim(b, "API-02", None, "dọn để thử lại")
    claim_ticket(b, ClaimRequest("API-02", "R3", "b"), T0)


def test_claim_het_han_thi_duoc_tiep_quan_va_reap_don_duoc(workspace) -> None:
    ws, a = workspace(
        {
            "API-01": ticket_text("API-01", allow=["src/api/orders/**"]),
            "API-02": ticket_text("API-02", allow=["src/api/orders/models.py"]),
        }
    )
    claim_ticket(a, ClaimRequest("API-01", "R3", "a", hours=2), T0)
    later = T0 + timedelta(hours=3)
    b = ws.clone("b")
    claim_ticket(b, ClaimRequest("API-02", "R1", "b"), later)
    assert [c.ticket for c in reap_expired(b, later)] == ["API-01"]
    assert set(_claims_on_remote(b)) == {"API-02"}


def test_release_chi_tu_dung_nhanh_hoac_override_co_ly_do(workspace) -> None:
    ws, a = workspace({"API-01": ticket_text("API-01", allow=["src/api/x.py"])})
    claim, _ = claim_ticket(a, ClaimRequest("API-01", "R3", "a"), T0)
    b = ws.clone("b")
    with pytest.raises(ClaimRefusedError, match="override"):
        release_claim(b, "API-01", "main", None)
    released = release_claim(b, "API-01", claim.branch, None)
    assert released.on_behalf_of == "R3"
    with pytest.raises(AgentctlError, match="không có claim"):
        release_claim(b, "API-01", claim.branch, None)


def test_ghi_dong_thoi_bi_tu_choi_roi_quyet_dinh_lai_tren_so_moi(workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    """Hai agent đọc sổ cùng lúc, cùng thấy phạm vi trống. Chỉ một lần ghi được thắng.

    Agent B đọc sổ CŨ (trước khi A ghi). Lần đẩy của B phải bị git từ chối; B đọc lại sổ mới, quyết
    định lại, và lần này thấy claim của A — nên từ chối thay vì ghi đè.
    """
    ws, a = workspace(
        {
            "API-01": ticket_text("API-01", allow=["src/api/orders/**"]),
            "API-02": ticket_text("API-02", allow=["src/api/orders/models.py"]),
        }
    )
    b = ws.clone("b")
    claim_ticket(a, ClaimRequest("API-01", "R3", "a"), T0)

    real_fetch = ClaimRegistry.fetch
    calls: list[str | None] = []

    def stale_first(self: ClaimRegistry) -> str | None:
        tip = None if not calls else real_fetch(self)
        calls.append(tip)
        return tip

    monkeypatch.setattr(ClaimRegistry, "fetch", stale_first)
    with pytest.raises(ClaimRefusedError, match="API-01"):
        claim_ticket(b, ClaimRequest("API-02", "R1", "b"), T0)
    assert len(calls) == 2, "lần đẩy dựa trên sổ cũ phải bị từ chối và buộc đọc lại đúng một lần"
    assert calls[1] is not None


def test_worktree_moi_khong_nhan_main_lam_upstream(workspace) -> None:
    ws, a = workspace({"API-01": ticket_text("API-01", allow=["src/api/x.py"], title="Thêm đơn hàng")})
    claim, _ = claim_ticket(a, ClaimRequest("API-01", "R3", "a"), T0)
    assert claim.branch == "feature/API-01-them-don-hang"
    path, created = create_worktree(a, claim, "origin/main")
    assert created and (path / "coordination" / "policy.yaml").is_file()
    upstream = run_git(path, "for-each-ref", "--format=%(upstream)", f"refs/heads/{claim.branch}")
    assert upstream.strip() == "", "nhánh ticket không được theo dõi `main` — `git push` trần có thể đẩy vào main"
