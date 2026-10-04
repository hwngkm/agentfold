"""Bản chụp hợp đồng API (`contracts/openapi.json`) phải khớp ứng dụng đang chạy.

Vì sao: agent làm backend đổi một trường, agent làm frontend (khác nhà cung cấp, khác phiên) vẫn đọc
hợp đồng cũ — không lớp nào báo cho tới khi người dùng bấm. Buộc bản chụp đi cùng thay đổi làm mọi
đổi hợp đồng hiện ra trong diff, và làn `api-contract` bảo đảm không hai ticket cùng đổi nó.
Sửa khi đỏ: `python scripts/export_openapi.py`, đọc diff, commit cùng thay đổi API.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.export_openapi import CONTRACT, render_contract

ROOT = Path(__file__).resolve().parents[2]


def test_ban_chup_hop_dong_khop_ung_dung() -> None:
    assert CONTRACT.is_file(), "thiếu contracts/openapi.json — chạy `python scripts/export_openapi.py`"
    assert render_contract() == CONTRACT.read_text(encoding="utf-8"), (
        "Hợp đồng API đã đổi mà bản chụp chưa cập nhật. Chạy `python scripts/export_openapi.py`, đọc diff, "
        "và bảo đảm ticket có khai làn `api-contract`."
    )


def test_ban_chup_that_su_chua_endpoint() -> None:
    """Lưới cho chính lưới: bản chụp rỗng cũng 'khớp' một ứng dụng rỗng."""
    paths = json.loads(CONTRACT.read_text(encoding="utf-8"))["paths"]
    assert {"/health", "/api/v1/me"} <= set(paths)
