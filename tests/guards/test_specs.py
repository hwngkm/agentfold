"""Đặc tả sống trong repo hợp lệ: mỗi yêu cầu có SHALL, kịch bản WHEN/THEN và test CÓ THẬT; delta chờ gộp thuộc ticket tồn tại.

Vì sao: đặc tả mà test nó trỏ tới đã bị đổi tên hay xoá là lời hứa không còn ai canh — đọc thì tin, thực tế trống.
Lưới này đỏ ngay lúc test bị đổi tên/xoá, buộc người đổi cập nhật đặc tả cùng PR (R00.4: không tính năng ẩn).
"""

from __future__ import annotations

from pathlib import Path

from tools.agentctl.policy import load_policy
from tools.agentctl.spec import CHANGES_DIR, SPECS_DIR, pending_deltas, repo_problems
from tools.agentctl.tickets import TICKET_ID

ROOT = Path(__file__).resolve().parents[2]


def test_dac_ta_va_delta_hop_le() -> None:
    assert repo_problems(ROOT) == []


def test_co_it_nhat_mot_dac_ta_mau() -> None:
    """Lưới rỗng nghĩa: thư mục đặc tả còn nhưng không ai đọc được gì thì `repo_problems` vẫn xanh."""
    specs = [p for p in (ROOT / SPECS_DIR).glob("*.md") if p.name != "README.md"]
    assert len(specs) >= 2, "template phải giữ ít nhất hai đặc tả mẫu (handoff, agent-log) làm ví dụ sống"


def test_delta_cho_gop_thuoc_ve_ticket_ton_tai() -> None:
    tickets_dir = ROOT / load_policy(ROOT, None).tickets_dir
    for delta in pending_deltas(ROOT):
        ticket = delta.name.split("-", 2)
        ticket_id = "-".join(ticket[:2])
        assert TICKET_ID.match(ticket_id), f"{CHANGES_DIR}/{delta.name}: tên phải bắt đầu bằng mã ticket"
        assert (tickets_dir / f"{ticket_id}.md").is_file(), f"{delta.name}: ticket {ticket_id} không tồn tại"
