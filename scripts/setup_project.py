"""Cấu hình dự án từ tệp `project-setup.json` do giao diện `wizard/index.html` tạo — an toàn cho người không chuyên.

    python scripts/setup_project.py project-setup.json            # CHẠY THỬ: kiểm tệp + in kế hoạch, không đổi gì
    python scripts/setup_project.py project-setup.json --apply    # làm thật (cây git phải sạch)
    python scripts/setup_project.py --write-wizard                # sinh lại danh mục nhúng trong wizard/index.html
    python scripts/setup_project.py --check-wizard                # CI: đỏ nếu danh mục trong wizard lệch nguồn

An toàn: tệp chỉ chứa lựa chọn (tên, loại dự án, cỡ đội, pack) — không bí mật nào. Làm thật chỉ khi cây git sạch, để
mọi thay đổi xem lại được bằng `git diff` và hoàn tác được bằng `git checkout -- .`. Mỗi bước là một script có sẵn của
template (bootstrap, generate_team_docs, packs) — không có đường ghi riêng nào khác.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import check_design as design_mod  # noqa: E402
from scripts import packs as packs_mod  # noqa: E402
from tools.agentctl.team_profile import COMPLEXITIES, TEAM_SIZES, TeamProfileError, build_profile  # noqa: E402

WIZARD = ROOT / "wizard" / "index.html"
_BEGIN, _END = "<!-- CATALOG:BEGIN — sinh bởi scripts/setup_project.py, đừng sửa tay -->", "<!-- CATALOG:END -->"
_SLUG = re.compile(r"^[a-z][a-z0-9-]{2,40}$")
SETUP_VERSION = 1

#: Nhãn ngôn ngữ thường cho người không chuyên. Khoá phải trùng `project_types` trong packs/registry.yaml (lưới canh).
PROJECT_TYPE_LABELS: dict[str, tuple[str, str]] = {
    "crud-web-app": ("Ứng dụng web quản lý", "Đăng nhập, nhập liệu, tra cứu, báo cáo — như phần mềm quản lý nội bộ."),
    "api-service": ("Dịch vụ cho hệ thống khác gọi (API)", "Không có giao diện riêng; phần mềm khác gửi yêu cầu tới."),
    "llm-app": ("Ứng dụng có dùng AI", "Hỏi đáp trên tài liệu, tóm tắt, trích xuất thông tin bằng mô hình ngôn ngữ."),
    "ai-product": (
        "Sản phẩm AI hoàn chỉnh",
        "Trợ lý/agent có công cụ, có người duyệt, có giao diện, có kế hoạch phát hành và nghiên cứu thị trường.",
    ),
    "ml-training": ("Huấn luyện mô hình", "Tự huấn luyện hoặc tinh chỉnh mô hình học máy trên dữ liệu của mình."),
    "data-pipeline": ("Xử lý dữ liệu tự động", "Thu thập, làm sạch, chuẩn hoá dữ liệu định kỳ."),
    "research": ("Nghiên cứu", "Tìm tài liệu, so sánh mô hình/bộ dữ liệu có sẵn, chạy thí nghiệm, viết ghi chú."),
    "prototype": ("Thử nghiệm nhanh một ý tưởng", "Ít thủ tục nhất; chỉ bộ kỹ năng lõi."),
}
#: Công cụ AI người dùng có thể đang dùng — chỉ để in lời khuyên; mọi công cụ đều đọc AGENTS.md.
AGENT_TOOLS: dict[str, str] = {
    "claude-code": "Claude Code — tự nạp kỹ năng, cài được plugin/MCP.",
    "codex": "Codex — đọc AGENTS.md; kỹ năng qua SKILLS.md.",
    "copilot": "GitHub Copilot — đọc AGENTS.md; kỹ năng qua SKILLS.md.",
    "cursor": "Cursor — đọc AGENTS.md; kỹ năng qua SKILLS.md.",
    "antigravity": "Antigravity — đọc AGENTS.md; kỹ năng qua SKILLS.md.",
    "gemini-cli": "Gemini CLI — đọc AGENTS.md; kỹ năng qua SKILLS.md.",
}


class SetupError(ValueError):
    """Tệp cấu hình sai — thông điệp nói rõ sửa gì."""


def catalog() -> dict[str, Any]:
    """Mọi lựa chọn giao diện được phép hiển thị, sinh từ nguồn thật (sổ pack, preset đội) — nhúng vào wizard."""
    registry = packs_mod.load_registry()
    combos: dict[str, list[str]] = {}
    for team in TEAM_SIZES:
        for level in COMPLEXITIES:
            try:
                build_profile(team, level)
                combos.setdefault(team, []).append(level)
            except TeamProfileError:
                continue
    return {
        "version": SETUP_VERSION,
        "project_types": [
            {"id": key, "label": PROJECT_TYPE_LABELS[key][0], "help": PROJECT_TYPE_LABELS[key][1], "packs": list(packs)}
            for key, packs in registry["project_types"].items()
        ],
        "packs": [
            {
                "id": name,
                "label": pack["label"],
                "skills": [s["name"] for s in pack.get("skills", [])],
                "tools": [str(i.get("id") or i.get("name")) for i in pack.get("integrations") or []],
            }
            for name, pack in registry["packs"].items()
            if pack.get("status") == "ready"
        ],
        "team_sizes": list(TEAM_SIZES),
        "complexities": list(COMPLEXITIES),
        "compatible": combos,
        "agent_tools": AGENT_TOOLS,
    }


DESIGN_KEYS = ("primary", "background", "text")


def _design_problems(design: Any, name: str) -> list[str]:
    """Mục `design` (tuỳ chọn): ba màu hex; chữ/nền phải đạt WCAG AA — kiểm bằng chính bộ sinh DESIGN.md."""
    if not isinstance(design, dict) or set(design) != set(DESIGN_KEYS):
        return [f"`design` phải là đối tượng có đủ {list(DESIGN_KEYS)} (mã màu hex, vd. #0F766E) hoặc bỏ hẳn mục này"]
    try:
        design_mod.starter(name=name or "x", **{key: str(design[key]) for key in DESIGN_KEYS})
    except ValueError as exc:
        return [f"`design`: {exc}"]
    return []


def validate(setup: Any) -> dict[str, Any]:
    if not isinstance(setup, dict):
        raise SetupError("tệp phải là một đối tượng JSON")
    cat = catalog()
    problems: list[str] = []
    if setup.get("version") != SETUP_VERSION:
        problems.append(f"`version` phải là {SETUP_VERSION}")
    name = str(setup.get("name") or "").strip()
    if not 2 <= len(name) <= 80:
        problems.append("`name`: tên dự án 2–80 ký tự")
    if not _SLUG.match(str(setup.get("slug") or "")):
        problems.append("`slug`: chữ thường không dấu, số, gạch nối; bắt đầu bằng chữ; 3–41 ký tự (vd. tro-ly-kho)")
    types = {t["id"] for t in cat["project_types"]}
    if setup.get("project_type") not in types:
        problems.append(f"`project_type` phải thuộc {sorted(types)}")
    team, level = setup.get("team_size"), setup.get("complexity")
    if team not in cat["compatible"] or level not in cat["compatible"].get(team, []):
        problems.append(
            f"cỡ đội `{team}` + mức `{level}` không hợp lệ hoặc không đủ người duyệt — các tổ hợp được phép: {cat['compatible']}"
        )
    ready = {p["id"] for p in cat["packs"]}
    packs = setup.get("packs")
    if not isinstance(packs, list) or not all(isinstance(p, str) for p in packs):
        problems.append("`packs` phải là danh sách tên pack")
    else:
        unknown = sorted(set(packs) - ready)
        if unknown:
            problems.append(f"pack không có hoặc chưa sẵn sàng: {unknown}")
    tools = setup.get("agent_tools", [])
    if not isinstance(tools, list) or not set(tools) <= set(AGENT_TOOLS):
        problems.append(f"`agent_tools` chỉ gồm {sorted(AGENT_TOOLS)}")
    design = setup.get("design")
    if design is not None:
        problems += _design_problems(design, name)
    if problems:
        raise SetupError("tệp cấu hình chưa đúng:\n  - " + "\n  - ".join(problems))
    normalized = {**setup, "name": name, "packs": sorted(dict.fromkeys(packs or []))}
    if design is not None:
        normalized["design"] = {key: design_mod._norm(design[key], key) for key in DESIGN_KEYS}
    return normalized


def plan(setup: dict[str, Any]) -> list[tuple[str, list[str]]]:
    """Các bước (mô tả cho người, lệnh) — chỉ gọi script có sẵn của template."""
    steps: list[tuple[str, list[str]]] = [
        (
            f"Đổi tên template thành “{setup['name']}” ({setup['slug']})",
            ["scripts/bootstrap.py", "--name", setup["name"], "--slug", setup["slug"], "--apply"],
        ),
        (
            f"Cỡ đội `{setup['team_size']}`, mức thủ tục `{setup['complexity']}` → sinh GOVERNANCE.md, CODEOWNERS",
            ["scripts/generate_team_docs.py", "--team-size", setup["team_size"], "--complexity", setup["complexity"]],
        ),
        (f"Ghi loại dự án `{setup['project_type']}`", ["scripts/packs.py", "--set-type", setup["project_type"]]),
    ]
    design = setup.get("design")
    if design:
        steps.append(
            (
                "Sinh DESIGN.md khởi đầu từ màu đã chọn (token giao diện cho agent, đã kiểm tương phản)",
                [
                    "scripts/check_design.py",
                    "--init",
                    "--name",
                    setup["name"],
                    "--primary",
                    design["primary"],
                    "--background",
                    design["background"],
                    "--text",
                    design["text"],
                    "--out",
                    "DESIGN.md",
                ],
            )
        )
    steps += [(f"Bật pack `{p}`", ["scripts/packs.py", "--install", p]) for p in setup["packs"]]
    return steps


def _git_clean() -> bool:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.returncode == 0 and not result.stdout.strip()


Runner = Callable[[Sequence[str]], int]


def _run(argv: Sequence[str]) -> int:
    return subprocess.run([sys.executable, *argv], cwd=ROOT, check=False).returncode


def apply(setup: dict[str, Any], *, runner: Runner = _run, require_clean: bool = True) -> int:
    if require_clean and not _git_clean():
        print(
            "🔴 Cây git đang có thay đổi chưa commit. Commit hoặc cất chúng trước, để mọi thay đổi của bước này xem lại được bằng `git diff`.",
            file=sys.stderr,
        )
        return 1
    for index, (label, argv) in enumerate(plan(setup), start=1):
        print(f"[{index}] {label}", flush=True)
        if runner(argv) != 0:
            print(
                f"🔴 Bước {index} lỗi — dừng. Xem thông báo ở trên; hoàn tác: `git checkout -- . && git clean -fd`.",
                file=sys.stderr,
            )
            return 1
    _advice(setup)
    return 0


def _advice(setup: dict[str, Any]) -> None:
    print("\n✅ Xong. Việc tiếp theo:")
    print("  1. Xem lại thay đổi: git diff --stat   (không ưng thì: git checkout -- . && git clean -fd)")
    print('  2. Commit: git add -A && git commit -m "chore: cấu hình dự án ban đầu"')
    print("  3. Danh sách việc NGƯỜI phải tự làm (bảo vệ nhánh, khoá dịch vụ…) đã in ở bước 1.")
    for tool in setup.get("agent_tools", []):
        print(f"  • {AGENT_TOOLS[tool]}")
    if "claude-code" not in setup.get("agent_tools", []) and setup["packs"]:
        print("  • Công cụ của bạn không cài plugin Claude Code: mở SKILLS.md, cột “Không có thì” cho cách làm thay.")


def _wizard_block() -> str:
    data = json.dumps(catalog(), ensure_ascii=False, indent=1, sort_keys=True)
    return f'{_BEGIN}\n<script id="catalog" type="application/json">\n{data}\n</script>\n{_END}'


def wizard_with_catalog(html: str) -> str:
    start, end = html.find(_BEGIN), html.find(_END)
    if start < 0 or end < 0:
        raise SetupError("wizard/index.html thiếu cặp mốc CATALOG:BEGIN/END")
    return html[:start] + _wizard_block() + html[end + len(_END) :]


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", nargs="?", help="project-setup.json do wizard tạo")
    parser.add_argument("--apply", action="store_true", help="làm thật (mặc định chỉ chạy thử)")
    parser.add_argument("--write-wizard", action="store_true")
    parser.add_argument("--check-wizard", action="store_true")
    args = parser.parse_args(argv)

    if args.write_wizard or args.check_wizard:
        html = WIZARD.read_text(encoding="utf-8")
        wanted = wizard_with_catalog(html)
        if args.check_wizard:
            if wanted != html:
                print(
                    "🔴 wizard/index.html lệch sổ pack/preset — chạy `python scripts/setup_project.py --write-wizard`",
                    file=sys.stderr,
                )
                return 1
            print("✅ Danh mục trong wizard khớp nguồn.")
            return 0
        WIZARD.write_text(wanted, encoding="utf-8", newline="\n")
        print("✅ Đã sinh lại danh mục trong wizard/index.html")
        return 0
    if not args.file:
        parser.error("cần đường dẫn tệp project-setup.json (hoặc --write-wizard / --check-wizard)")
    try:
        setup = validate(json.loads(Path(args.file).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, SetupError) as exc:
        print(f"🔴 {exc}", file=sys.stderr)
        return 1
    if not args.apply:
        print("Kế hoạch (CHẠY THỬ — chưa đổi gì):")
        for index, (label, argv_) in enumerate(plan(setup), start=1):
            print(f"  [{index}] {label}\n      python {shlex.join(argv_)}")
        print("\nĐồng ý thì chạy lại với --apply.")
        return 0
    return apply(setup)


if __name__ == "__main__":
    raise SystemExit(main())
