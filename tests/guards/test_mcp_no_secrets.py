"""`.mcp.json` nằm trong git — không được chứa bí mật ở dạng thô.

Vì sao: cách thêm MCP server phổ biến nhất gắn thẳng khoá vào lệnh
(`claude mcp add ... --header "Authorization: Bearer rnd_..."`). Chạy ở phạm vi project là commit khoá
vào repo, và `git diff` chỉ hiện một dòng JSON trông vô hại. Đã có dự án suýt gặp đúng chuyện này
— lần đó thoát chỉ vì lệnh không chạy được, không phải vì có gì chặn.

Khoá gì: không giá trị nào mang tiền tố khoá đã biết; header xác thực phải là tham chiếu `${TEN_BIEN}`.
Lỡ commit khoá: THU HỒI trước, xoá khỏi file sau — xoá khỏi lịch sử git không rút lại thứ đã đẩy.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.secret_scan import secret_problems

ROOT = Path(__file__).resolve().parents[2]
MCP = ROOT / ".mcp.json"


def test_mcp_json_khong_chua_bi_mat_tho() -> None:
    assert MCP.is_file(), "thiếu .mcp.json — lưới đang không kiểm gì"
    data = json.loads(MCP.read_text(encoding="utf-8"))
    assert "mcpServers" in data
    assert secret_problems(data) == []


def test_bo_do_bat_duoc_khoa_that() -> None:
    leaked = {"mcpServers": {"render": {"headers": {"Authorization": "Bearer rnd_abc123"}}}}
    clean = {"mcpServers": {"render": {"headers": {"Authorization": "Bearer ${RENDER_API_KEY}"}}}}
    assert secret_problems(leaked)
    assert secret_problems(clean) == []
