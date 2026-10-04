"""Chính sách điều phối và mọi mục công việc đúng cấu trúc; vùng bảo vệ không trỏ vào khoảng không.

Vì sao: ticket hỏng cú pháp phát hiện ở đây rẻ hơn phát hiện lúc một agent claim nó. Và một vùng bảo vệ
trỏ tới file đã đổi tên là vùng RỖNG — nó không bảo vệ gì, mà ai đọc `policy.yaml` vẫn tin là có.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.agentctl.globs import is_literal
from tools.agentctl.policy import load_policy
from tools.agentctl.workcheck import validate_work_items

ROOT = Path(__file__).resolve().parents[2]
POLICY = load_policy(ROOT, None)


def test_moi_muc_cong_viec_dung_cau_truc() -> None:
    assert validate_work_items(ROOT, POLICY) == []


def test_vung_bao_ve_va_lan_doc_quyen_tro_toi_thu_co_that() -> None:
    missing = [
        f"{kind} `{item.id}`: {pattern}"
        for kind, items in (("vùng", POLICY.protected), ("làn", POLICY.exclusive))
        for item in items
        for pattern in item.paths
        if (is_literal(pattern) or pattern.endswith("/")) and not (ROOT / pattern.rstrip("/")).exists()
    ]
    assert not missing, f"mẫu trỏ tới đường dẫn không tồn tại (vùng/làn rỗng): {missing}"


def test_chu_vung_la_vai_tro_co_trong_governance() -> None:
    governance = (ROOT / "docs/GOVERNANCE.md").read_text(encoding="utf-8")
    roles = set(re.findall(r"\*\*(R\d+)\*\*", governance))
    assert roles, "không đọc được vai trò nào trong docs/GOVERNANCE.md"
    unknown = {owner for zone in POLICY.protected for owner in zone.owners} - roles
    assert not unknown, f"chủ vùng không có trong docs/GOVERNANCE.md: {unknown}"


def test_nhanh_so_claim_khong_trung_nhanh_goc() -> None:
    assert POLICY.claims_branch != POLICY.base_branch
