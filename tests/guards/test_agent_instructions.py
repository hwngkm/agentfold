"""Mọi AI agent — mọi nhà cung cấp — đọc CÙNG MỘT bộ luật: `AGENTS.md`.

Vì sao: mỗi công cụ tự nạp một file khác nhau (CLAUDE.md, GEMINI.md, copilot-instructions.md,
.cursor/rules...). Nếu luật được chép vào từng file, các bản sẽ trôi khỏi nhau và mỗi agent làm theo
một phiên bản luật khác. Đã có trường hợp một cảnh báo "chưa có nguồn" rơi mất khi câu chữ được chép từ
nhật ký sang CLAUDE.md — và vì CLAUDE.md là thứ agent đọc như đặc tả, cảnh báo đó im lặng biến thành
luật (09/09/2026).

Khoá gì: adapter tồn tại, NGẮN, trỏ về AGENTS.md, không chứa danh sách luật riêng; vai trò agent chỉ
định nghĩa một nơi; lệnh hook không phụ thuộc thư mục làm việc của phiên.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]


def _tracked(rel: str) -> bool:
    """`True` nếu `rel` thực sự nằm trong git, không chỉ tồn tại trên đĩa.

    Vì sao đây là bài kiểm bắt buộc, không phải `path.is_file()`: `.gitignore` của một repo CHA (khi
    template nằm lồng trong một thư mục con, hoặc lúc tách bằng `git subtree split`) có thể khớp một mẫu
    KHÔNG neo root như `.cursor/` hay `.gemini/` ở BẤT KỲ độ sâu nào, khiến `git add -A` ÂM THẦM bỏ qua
    những file đó — không cảnh báo, không lỗi. File vẫn nằm nguyên trên đĩa máy đang phát triển (gitignore
    không xoá gì cả), nên `path.is_file()` vẫn xanh, còn bản thật sự đẩy lên remote thì thiếu. Đúng lỗi đã
    xảy ra: `.cursor/rules/agents.mdc` và `.gemini/settings.json` bị nuốt khi tách `agent-project-template`
    ra khỏi repo cha (16/09/2026), chỉ lộ ra khi kiểm trên một bản `git clone` sạch.
    """
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return result.returncode == 0


MAX_AGENTS_LINES = 250
MAX_ADAPTER_LINES = 8
ADAPTERS = [
    "CLAUDE.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
    ".cursor/rules/agents.mdc",
    "web/CLAUDE.md",
]
_RULE_LINE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\S")


def adapter_problems(text: str) -> list[str]:
    body = text.split("\n---", 1)[1] if text.startswith("---") else text
    lines = [line for line in body.splitlines() if line.strip() and not line.strip().startswith("<!--")]
    problems = []
    if "AGENTS.md" not in text:
        problems.append("không trỏ về AGENTS.md")
    if len(lines) > MAX_ADAPTER_LINES:
        problems.append(f"{len(lines)} dòng nội dung — adapter chỉ được trỏ, tối đa {MAX_ADAPTER_LINES}")
    if any(_RULE_LINE.match(line) for line in lines):
        problems.append("có danh sách gạch đầu dòng — luật phải viết trong AGENTS.md")
    return problems


def test_agents_md_ton_tai_va_du_ngan_de_doc_het() -> None:
    lines = (ROOT / "AGENTS.md").read_text(encoding="utf-8").splitlines()
    assert len(lines) <= MAX_AGENTS_LINES, (
        f"AGENTS.md dài {len(lines)} dòng. File luật dài thì agent đọc lướt — tách chi tiết sang docs/rules/"
    )


@pytest.mark.parametrize("rel", ADAPTERS)
def test_adapter_chi_tro_ve_agents_md(rel: str) -> None:
    path = ROOT / rel
    assert path.is_file(), f"thiếu adapter {rel}"
    assert _tracked(rel), f"{rel} tồn tại trên đĩa nhưng KHÔNG được git theo dõi — sẽ biến mất khi clone sạch"
    assert adapter_problems(path.read_text(encoding="utf-8")) == []


def test_bo_do_bat_duoc_adapter_chua_commit() -> None:
    """Chứng minh `_tracked` phân biệt được 'có trên đĩa' và 'có trong git' — hai thứ khác nhau đã gây lỗi thật."""
    assert not _tracked("khong-ton-tai-va-khong-bao-gio-duoc-commit.md")
    assert _tracked("AGENTS.md")


def test_bo_do_adapter_bat_duoc_luat_chep_rieng() -> None:
    forked = "@AGENTS.md\n\n- Luôn dùng tab thay dấu cách\n- Được sửa docs/design khi cần\n"
    assert "có danh sách gạch đầu dòng — luật phải viết trong AGENTS.md" in adapter_problems(forked)
    assert "không trỏ về AGENTS.md" in adapter_problems("Luật riêng của công cụ này.\n")


def test_cau_hinh_cong_cu_nap_agents_md() -> None:
    gemini = json.loads((ROOT / ".gemini/settings.json").read_text(encoding="utf-8"))
    assert "AGENTS.md" in gemini["context"]["fileName"]
    aider = yaml.safe_load((ROOT / ".aider.conf.yml").read_text(encoding="utf-8"))
    assert "AGENTS.md" in aider["read"]


def test_vai_tro_agent_chi_dinh_nghia_mot_noi() -> None:
    roles = {path.stem for path in (ROOT / "coordination/roles").glob("*.md")}
    assert {
        "planner",
        "critic",
        "architect",
        "implementer",
        "reviewer",
        "supervisor",
        "system-designer",
        "red-team",
        "release-engineer",
        "researcher",
    } <= roles
    claude_agents = {path.stem: path.read_text(encoding="utf-8") for path in (ROOT / ".claude/agents").glob("*.md")}
    assert set(claude_agents) == roles, "mỗi vai trò trung lập phải có đúng một adapter Claude và ngược lại"
    for name, text in claude_agents.items():
        assert f"coordination/roles/{name}.md" in text, f".claude/agents/{name}.md không trỏ về vai trò gốc"
        assert f"name: {name}\n" in text
        body = text.split("\n---", 2)[-1]
        assert len([line for line in body.splitlines() if line.strip()]) <= 3, f"adapter {name} đang tự viết vai trò"


def _hook_commands() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for rel in (".claude/settings.json", ".gemini/settings.json", ".codex/hooks.json"):
        data = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        for groups in data.get("hooks", {}).values():
            for group in groups:
                found += [(rel, hook["command"]) for hook in group.get("hooks", []) if "command" in hook]
    return found


def test_lenh_hook_khong_phu_thuoc_thu_muc_lam_viec() -> None:
    """`bash scripts/x.py` hỏng ngay khi phiên agent đổi thư mục làm việc vào thư mục con.

    Gặp thật khi dựng template này: hook của repo gốc báo "can't open file .../scripts/log_hook.py" sau
    mỗi thao tác ghi, vì đường dẫn tương đối được tính từ thư mục con.
    """
    commands = _hook_commands()
    assert commands, "không đọc được lệnh hook nào — lưới rỗng nghĩa"
    relative = [
        f"{rel}: {command}"
        for rel, command in commands
        if "$CLAUDE_PROJECT_DIR" not in command and "git rev-parse --show-toplevel" not in command
    ]
    assert not relative, f"lệnh hook dùng đường dẫn tương đối: {relative}"
    referenced = {m for _, c in commands for m in re.findall(r"scripts/hooks/[a-z_]+\.py", c)}
    assert "scripts/hooks/guard_write.py" in referenced, "hook chặn ghi ngoài phạm vi phải còn"
    missing = sorted(path for path in referenced if not (ROOT / path).is_file())
    assert not missing, f"hook trỏ tới script không tồn tại: {missing}"
    modules = {m for _, c in commands for m in re.findall(r"-m (tools\.[a-z_.]+)", c)}
    assert all(
        (ROOT / (m.replace(".", "/") + ".py")).is_file() or (ROOT / m.replace(".", "/")).is_dir() for m in modules
    )
