"""Sổ khai báo hành động của agent sản phẩm, theo mức rủi ro — mặc định FAIL CLOSED.

| Mức    | Nghĩa                                                         | Cổng                          |
|--------|---------------------------------------------------------------|-------------------------------|
| LOW    | Chỉ đọc hoặc tính toán thuần                                  | không                         |
| MEDIUM | Ghi dữ liệu của chính người dùng                              | ghi `audit_log`               |
| HIGH   | Tới tay người dùng cuối, ra ngoài hệ thống, đổi dữ liệu dùng chung | BẮT BUỘC vai trò người duyệt |

Hành động CHƯA KHAI BÁO được coi là HIGH: thêm tính năng mà quên khai thì nó bị chặn, chứ không lặng
lẽ chạy với quyền cao nhất. Mọi hành động HIGH phải nói RÕ vai trò nào được duyệt — HIGH mà không có
người duyệt thì cổng vô nghĩa (có test ép điều này).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class AgentAction:
    name: str
    risk: RiskLevel
    description: str
    requires_role: str | None = None


class ApprovalRequiredError(PermissionError):
    """Hành động cần người có vai trò phù hợp duyệt."""


ACTIONS: dict[str, AgentAction] = {
    action.name: action
    for action in (
        AgentAction("read_catalog", RiskLevel.LOW, "Tra cứu danh mục, chỉ đọc"),
        AgentAction("compute_quote", RiskLevel.LOW, "Tính báo giá tất định, không ghi gì"),
        AgentAction("create_quote_draft", RiskLevel.MEDIUM, "Lưu bản nháp — luôn ở trạng thái chờ duyệt"),
        AgentAction("publish_quote", RiskLevel.HIGH, "Gửi báo giá tới khách hàng", requires_role="reviewer"),
        AgentAction(
            "edit_catalog_price", RiskLevel.HIGH, "Đổi đơn giá dùng chung cho mọi báo giá", requires_role="admin"
        ),
        AgentAction(
            "send_external_message",
            RiskLevel.HIGH,
            "Gửi ra ngoài hệ thống — không thu hồi được",
            requires_role="reviewer",
        ),
    )
}


def action_risk(name: str) -> RiskLevel:
    action = ACTIONS.get(name)
    if action is None:
        logger.warning("Hành động chưa khai báo %r — coi là HIGH", name)
        return RiskLevel.HIGH
    return action.risk


def require_approval(name: str, *, actor_role: str) -> None:
    """Ném `ApprovalRequiredError` nếu hành động HIGH mà người thực hiện không có vai trò duyệt."""
    if action_risk(name) is not RiskLevel.HIGH:
        return
    action = ACTIONS.get(name)
    required = action.requires_role if action else None
    if required is None or actor_role != required:
        raise ApprovalRequiredError(
            f"`{name}` là hành động rủi ro cao — cần vai trò `{required or 'chưa khai báo'}` duyệt"
        )
