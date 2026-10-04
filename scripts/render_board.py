"""Bảng việc dạng HTML TĨNH cho người duyệt — chỉ đọc, mở bằng nhấp đúp, không máy chủ, không tải gì từ mạng.

    python scripts/render_board.py                 # ghi board/index.html (git bỏ qua tệp này)
    python scripts/render_board.py --out bang.html # ghi chỗ khác
    python scripts/render_board.py --offline       # không kéo nhánh mới từ remote

CÙNG nguồn dữ liệu với `python -m tools.agentctl board`: cả hai gọi `collect_board` (tools/agentctl/board.py), chỉ khác cách hiển thị
(văn bản / HTML). Không có logic dựng bảng thứ hai ở đây. HTML thêm một mục mà bảng văn bản không in: thư AGENT-LOG gần nhất.

An toàn: mọi chuỗi đi qua `html.escape`; CSS nội tuyến, không `<script>`, `<link>`, `url()` hay tài nguyên ngoài. Muốn đổi trạng thái việc:
làm qua PR/ticket như thường — bảng này không sửa gì.
"""

from __future__ import annotations

import argparse
import html
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.agentctl.board import Board, BoardItem, collect_board  # noqa: E402
from tools.agentctl.clock import now  # noqa: E402
from tools.agentctl.errors import AgentctlError  # noqa: E402
from tools.agentctl.gitutil import project_root  # noqa: E402

DEFAULT_OUT = "board/index.html"

#: Bảng màu sáng/tối. Mọi cặp chữ/nền đạt WCAG AA 4.5:1 (có test; đo bằng `scripts/check_design.py`).
PALETTE: dict[str, dict[str, str]] = {
    "light": {
        "bg": "#f7f7f5",
        "surface": "#ffffff",
        "text": "#1c1c1a",
        "muted": "#55554f",
        "accent": "#1f5fbf",
        "accent-text": "#ffffff",
        "line": "#cfcfc8",
    },
    "dark": {
        "bg": "#121211",
        "surface": "#1c1c1a",
        "text": "#ecece8",
        "muted": "#b4b4ac",
        "accent": "#8ab4f8",
        "accent-text": "#0b1b33",
        "line": "#3a3a35",
    },
}


def _vars(scheme: str) -> str:
    return " ".join(f"--{name}: {value};" for name, value in PALETTE[scheme].items())


STYLE = f"""
:root {{ color-scheme: light dark; {_vars("light")} }}
@media (prefers-color-scheme: dark) {{ :root {{ {_vars("dark")} }} }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font: 16px/1.5 system-ui, sans-serif; color: var(--text); background: var(--bg); }}
main {{ max-width: 60rem; margin: 0 auto; padding: 1rem; }}
h1 {{ font-size: 1.4rem; margin: .5rem 0 .25rem; }}
h2 {{ font-size: 1.05rem; margin: 0 0 .5rem; }}
.meta {{ color: var(--muted); font-size: .9rem; margin: 0 0 1rem; }}
.chips {{ display: flex; flex-wrap: wrap; gap: .5rem; margin: 0 0 1rem; padding: 0; list-style: none; }}
.chip {{ background: var(--accent); color: var(--accent-text); border-radius: 999px; padding: .15rem .7rem; font-size: .85rem; }}
section {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: .9rem 1rem; margin: 0 0 .9rem; }}
ul.items {{ margin: 0; padding: 0; list-style: none; }}
ul.items li {{ padding: .4rem 0; border-top: 1px solid var(--line); overflow-wrap: anywhere; }}
ul.items li:first-child {{ border-top: 0; }}
.empty {{ color: var(--muted); }}
.sep {{ color: var(--muted); }}
code {{ font: .9em ui-monospace, monospace; }}
"""


def _e(value: str) -> str:
    return html.escape(value, quote=True)


def _item_html(item: BoardItem) -> str:
    first, *rest = item.parts
    tail = "".join(f' <span class="sep">·</span> <span>{_e(part)}</span>' for part in rest)
    return f"<li><strong>{_e(first)}</strong>{tail}</li>"


def _section(title: str, items: list[BoardItem]) -> str:
    body = "".join(_item_html(item) for item in items) or '<li class="empty">(trống)</li>'
    return f'<section><h2>{_e(title)} ({len(items)})</h2><ul class="items">{body}</ul></section>'


def render_html(board: Board, *, moment: datetime) -> str:
    """HTML tự chứa từ một `Board` — cùng dữ liệu `agentctl board` in ra, thêm thư AGENT-LOG."""
    sections = [_section(title, items) for title, items in board.tickets.items()]
    sections += [
        _section("Câu hỏi đang mở", board.questions),
        _section("Kế hoạch chờ duyệt (chưa viết mã khi chưa approved)", board.plans),
        _section("Bàn giao đang chờ người nhận", board.handoffs),
        _section("Thư AGENT-LOG gần đây", board.mail),
    ]
    if board.broken:
        sections.append(_section("Ticket hỏng — sửa trước khi ai claim", [BoardItem((text,)) for text in board.broken]))
    chips = "".join(
        f'<li class="chip">{_e(title)}: {len(items)}</li>'
        for title, items in (*board.tickets.items(), ("câu hỏi", board.questions), ("kế hoạch", board.plans))
    )
    stamp = moment.strftime("%Y-%m-%d %H:%M UTC")
    fetched = "" if board.fetched else " (chưa kéo mới)"
    return (
        "<!doctype html>\n"
        '<html lang="vi">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Bảng việc</title>\n"
        f"<style>{STYLE}</style>\n</head>\n<body>\n<main>\n"
        "<h1>Bảng việc</h1>\n"
        f'<p class="meta">Tại <code>{_e(board.base_ref)}</code>{fetched} · tạo lúc {stamp} · chỉ đọc</p>\n'
        f'<ul class="chips">{chips}</ul>\n' + "\n".join(sections) + "\n</main>\n</body>\n</html>\n"
    )


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", help="thư mục dự án (mặc định thư mục hiện tại)")
    parser.add_argument("--offline", action="store_true", help="không gọi mạng, dùng bản đã kéo về")
    parser.add_argument("--out", help=f"nơi ghi tệp HTML (mặc định {DEFAULT_OUT} trong dự án)")
    args = parser.parse_args(argv)
    try:
        repo = project_root(Path(args.repo) if args.repo else Path.cwd())
        moment = now()
        board = collect_board(repo, fetch=not args.offline, moment=moment, with_mail=True)
    except AgentctlError as exc:
        print(f"🔴 {exc}", file=sys.stderr)
        return exc.exit_code
    out = Path(args.out) if args.out else repo / DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(board, moment=moment), encoding="utf-8", newline="\n")
    print(f"✅ Đã ghi {out} — mở bằng nhấp đúp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
