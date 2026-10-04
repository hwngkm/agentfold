"""`check-work` không kiểm lại ticket ĐÃ MERGE theo chính sách MỚI.

Lỗi gốc: ticket mở rộng một vùng bảo vệ, chính sách đọc từ nhánh gốc, nên ticket cũ đã merge có `allow` lấn
vùng mới tự đỏ ở `check-work` và phải sửa tay. Ở đây vùng `design` là "chính sách mới"; ticket cũ liệt kê thẳng
`docs/design/x.md` trong `allow` — hợp lệ hôm qua, lấn vùng hôm nay.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from tests.tools.helpers import POLICY, Workspace, run_git, ticket_text
from tools.agentctl.policy import parse_policy
from tools.agentctl.tickets import merged_ticket_ids
from tools.agentctl.workcheck import validate_work_items

Build = Callable[[Mapping[str, str]], tuple[Workspace, Path]]

OVERLAP = ("docs/design/x.md",)


def _tickets(*ids: str) -> dict[str, str]:
    return {tid: ticket_text(tid, allow=OVERLAP) for tid in ids}


def _lan(problems: list[str], ticket_id: str) -> list[str]:
    return [p for p in problems if ticket_id in p and "lấn vùng bảo vệ" in p]


def test_ticket_da_merge_khong_bi_bao_lan_vung_theo_chinh_sach_moi(workspace: Build) -> None:
    ws, seed = workspace(_tickets("OLD-01"))
    ws.commit_push(seed, {"src/a.py": "x = 1\n"}, "feat(x): lam xong viec (OLD-01)")
    repo = ws.clone("dev")
    assert "OLD-01" in merged_ticket_ids(repo, "origin/main")
    assert _lan(validate_work_items(repo, parse_policy(POLICY)), "OLD-01") == []


def test_ticket_chua_merge_van_bi_kiem_day_du(workspace: Build) -> None:
    ws, _ = workspace(_tickets("NEW-01"))
    repo = ws.clone("dev")
    assert _lan(validate_work_items(repo, parse_policy(POLICY)), "NEW-01"), "ticket chưa merge phải bị báo lấn vùng"


def test_ma_ticket_chi_co_tren_nhanh_dang_lam_khong_duoc_mien_kiem(workspace: Build) -> None:
    ws, _ = workspace(_tickets("WIP-01"))
    repo = ws.clone("dev")
    run_git(repo, "checkout", "--quiet", "-b", "feature/WIP-01-x")
    (repo / "b.txt").write_text("b", encoding="utf-8")
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "--quiet", "-m", "feat(x): dang lam (WIP-01)")
    assert "WIP-01" not in merged_ticket_ids(repo, "origin/main")
    assert _lan(validate_work_items(repo, parse_policy(POLICY)), "WIP-01"), "chỉ lịch sử nhánh GỐC mới được miễn"


def test_ticket_da_merge_van_bi_kiem_cau_truc(workspace: Build) -> None:
    ws, seed = workspace({"OLD-02": ticket_text("OLD-02", allow=OVERLAP, depends_on=["KHONG-99"])})
    ws.commit_push(seed, {"src/a.py": "x = 1\n"}, "feat(x): xong (OLD-02)")
    repo = ws.clone("dev")
    problems = validate_work_items(repo, parse_policy(POLICY))
    assert _lan(problems, "OLD-02") == []
    assert any("OLD-02" in p and "KHONG-99" in p for p in problems), "miễn kiểm chính sách, không miễn kiểm cấu trúc"


def test_khong_co_git_thi_khong_do_va_van_kiem_day_du(tmp_path: Path) -> None:
    (tmp_path / "docs/work/tickets").mkdir(parents=True)
    (tmp_path / "docs/work/tickets/OLD-01.md").write_text(ticket_text("OLD-01", allow=OVERLAP), encoding="utf-8")
    problems = validate_work_items(tmp_path, parse_policy(POLICY))
    assert _lan(problems, "OLD-01"), "không có lịch sử thì không lọc, vẫn kiểm đầy đủ"


def test_khong_co_lenh_git_thi_khong_do_va_van_kiem_day_du(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "docs/work/tickets").mkdir(parents=True)
    (tmp_path / "docs/work/tickets/OLD-01.md").write_text(ticket_text("OLD-01", allow=OVERLAP), encoding="utf-8")
    monkeypatch.setenv("PATH", str(tmp_path / "khong-co-gi"))
    problems = validate_work_items(tmp_path, parse_policy(POLICY))
    assert _lan(problems, "OLD-01"), "không có git thì không lọc, vẫn kiểm cấu trúc và chính sách đầy đủ"


def test_job_ci_chay_check_work_co_lich_su_de_loc_ticket_da_merge() -> None:
    import yaml

    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    for name, job in workflow["jobs"].items():
        steps = job["steps"]
        if not any("tools.agentctl check-work" in str(step.get("run", "")) for step in steps):
            continue
        checkout = next(step for step in steps if str(step.get("uses", "")).startswith("actions/checkout"))
        assert checkout.get("with", {}).get("fetch-depth") == 0, (
            f"job `{name}` chạy check-work với checkout nông: không thấy `origin/main` nên bộ lọc ticket đã merge vô tác dụng"
        )
        return
    raise AssertionError("không job CI nào chạy `check-work`")
