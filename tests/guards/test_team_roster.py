"""Sổ đội agent của repo (`coordination/team.yaml`) luôn dùng được: đúng một điều phối viên, mọi chuỗi báo cáo tới
người, mọi tuyến việc trỏ tới agent có thật, review khác nhà cung cấp, và có danh sách việc chỉ người làm.

Vì sao là lưới canh: `mail assign` và `prime` đọc sổ này từ nhánh gốc ở mọi phiên. Sổ hỏng thì mọi agent mất phân cấp
cùng lúc và quay lại cảnh người dùng chép tay lời nhắn — phải đỏ ở CI trước khi merge, không phải ở phiên kế tiếp.
"""

from __future__ import annotations

from pathlib import Path

from tools.agentctl.team import TEAM_PATH, load_team

ROOT = Path(__file__).resolve().parents[2]


def test_so_doi_cua_repo_hop_le_va_phu_du_viec() -> None:
    team = load_team(ROOT, None)
    assert team is not None, f"thiếu {TEAM_PATH}"
    assert team.coordinator.reports_to == "human", "điều phối viên báo cáo thẳng cho người"
    assert team.human_only, "phải liệt kê việc chỉ người làm"
    assert any("ready" in item for item in team.human_only), "đặt ticket `ready` luôn là việc của người"
    covered = {route.primary for route in team.routes.values()} | {
        route.backup for route in team.routes.values() if route.backup
    }
    idle = set(team.members) - covered
    assert not idle, f"agent không nằm trong tuyến việc nào: {sorted(idle)}"
    for member in team.members.values():
        assert member.id in member.wake or member.rank == "coordinator", (
            f"câu đánh thức của `{member.id}` phải gọi `prime --as {member.id}` để agent đọc đúng hộp thư"
        )
