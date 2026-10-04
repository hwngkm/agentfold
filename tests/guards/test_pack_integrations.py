"""Công cụ ngoài đi kèm pack (plugin, MCP server, CLI) khai một nơi, đồng bộ bằng máy, không mang bí mật.

Vì sao: một pack kỹ năng thường cần công cụ thật mới làm được việc — pack kiểm thử cần trình duyệt điều khiển
được (Playwright MCP), pack hạ tầng cần Terraform. Nếu mỗi người tự `claude mcp add` theo trí nhớ thì: (1) hai
máy chạy hai bộ công cụ khác nhau mà không ai biết; (2) server của pack đã tắt vẫn nằm lại trong `.mcp.json`,
tiếp tục nhận dữ liệu của mọi phiên; (3) lệnh thêm server hay gắn thẳng khoá vào header (xem
`test_mcp_no_secrets.py`).

Khoá gì: (1) mọi khai báo tích hợp trong `packs/registry.yaml` đúng cấu trúc và không chứa khoá thô; (2)
`.mcp.json` chứa ĐÚNG các server của pack đang bật — server do pack quản lý mà pack đã tắt thì phải biến mất,
server người dùng tự thêm (tên không thuộc pack nào) thì giữ nguyên; (3) cơ chế đồng bộ chạy thật.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts import packs as packs_mod

ROOT = Path(__file__).resolve().parents[2]


def _registry(packs_yaml: str) -> dict:
    import yaml

    return yaml.safe_load(f"version: 1\ncore: []\npacks:\n{packs_yaml}")


def test_khai_bao_tich_hop_trong_so_dang_ky_hop_le() -> None:
    assert packs_mod.integration_problems(packs_mod.load_registry()) == []


def test_mcp_json_khop_cac_pack_dang_bat() -> None:
    registry, profile = packs_mod.load_registry(), packs_mod.load_profile()
    assert packs_mod.mcp_drift(registry, profile["packs"]) == [], (
        "chạy `python scripts/packs.py --install <pack>` (hoặc `--remove`) để đồng bộ lại .mcp.json"
    )


def test_bo_kiem_bat_khai_bao_sai() -> None:
    broken = _registry(
        "  a:\n    label: A\n    status: ready\n    skills: [{name: s1, summary: x}]\n    integrations:\n"
        "      - {kind: mcp, name: gh, why: x, config: {type: http, url: 'https://x',"
        " headers: {Authorization: 'Bearer ghp_abc'}}}\n"
        "      - {kind: lạ, name: y, why: x}\n"
        "      - {kind: claude-plugin, id: thieu-marketplace, why: x}\n"
        "      - {kind: cli, name: docker}\n"
        "  b:\n    label: B\n    status: ready\n    skills: [{name: s2, summary: x}]\n    integrations:\n"
        "      - {kind: mcp, name: gh, why: x, config: {command: npx, args: [khac]}}\n"
    )
    problems = "\n".join(packs_mod.integration_problems(broken))
    assert "khoá thô" in problems
    assert "`kind`" in problems
    assert "name@marketplace" in problems
    assert "`why`" in problems
    assert "hai cấu hình khác nhau" in problems


def test_dong_bo_giu_server_cua_nguoi_dung_va_go_server_cua_pack_da_tat(tmp_path: Path) -> None:
    registry = _registry(
        "  testing:\n    label: T\n    status: ready\n    skills: [{name: s1, summary: x}]\n    integrations:\n"
        "      - {kind: mcp, name: playwright, why: x, config: {command: npx, args: ['@playwright/mcp@latest']}}\n"
        "  docs:\n    label: D\n    status: ready\n    skills: [{name: s2, summary: x}]\n    integrations:\n"
        "      - {kind: mcp, name: context7, why: x, config: {type: http, url: 'https://mcp.context7.com/mcp'}}\n"
    )
    mcp = tmp_path / ".mcp.json"
    mcp.write_text(json.dumps({"mcpServers": {"cua-toi": {"command": "x"}, "context7": {"type": "http"}}}), "utf-8")

    added, removed = packs_mod.sync_mcp(registry, ["testing"], mcp)
    servers = json.loads(mcp.read_text(encoding="utf-8"))["mcpServers"]
    assert set(servers) == {"cua-toi", "playwright"}, "server của người dùng giữ; context7 (pack tắt) phải gỡ"
    assert (added, removed) == (["playwright"], ["context7"])
    assert packs_mod.mcp_drift(registry, ["testing"], mcp) == []
    assert packs_mod.mcp_drift(registry, ["testing", "docs"], mcp) != []

    assert packs_mod.sync_mcp(registry, ["testing"], mcp) == ([], []), "chạy lại phải không đổi gì"
    assert mcp.read_bytes().endswith(b"\n") and b"\r\n" not in mcp.read_bytes()
