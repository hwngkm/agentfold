"""Sinh lại các sơ đồ/bảng suy ra được trong `docs/design/ARCHITECTURE.md` — cùng mẫu với
`scripts/generate_team_docs.py` và `scripts/export_openapi.py`.

    python scripts/generate_diagrams.py            # sinh lại, ghi vào tài liệu
    python scripts/generate_diagrams.py --check    # CI: đỏ nếu tài liệu lệch nguồn sự thật

Sinh cái gì, từ đâu:

| Vùng trong ARCHITECTURE.md | Nguồn sự thật |
|---|---|
| `GENERATED:layers`    | `contracts/boundaries.yaml` |
| `GENERATED:ownership` | `coordination/policy.yaml` (chủ vùng do `team-profile.yaml` sinh ra) |

KHÔNG sinh: §2 bối cảnh và §4 luồng găng — người vẽ, vì chúng mã hoá quyết định phạm vi. Lưới canh
`tests/guards/test_diagrams_dong_bo.py` chỉ kiểm chúng có mặt.

⚠️ Đổi team-size/complexity thì chạy `generate_team_docs.py` TRƯỚC (nó viết lại `owners:` trong
policy.yaml), rồi mới chạy file này — nếu không sơ đồ quyền sở hữu sẽ mang chủ cũ.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.agentctl.errors import AgentctlError  # noqa: E402
from tools.agentctl.policy import load_policy  # noqa: E402
from tools.diagrams import (  # noqa: E402
    load_boundaries,
    render_layers_mermaid,
    render_layers_table,
    render_zones_mermaid,
    replace_region,
)

ARCHITECTURE_PATH = ROOT / "docs" / "design" / "ARCHITECTURE.md"


def _rendered(root: Path) -> str:
    """Nội dung ARCHITECTURE.md sau khi ghi đè mọi vùng sinh tự động."""
    boundaries = load_boundaries(root)
    policy = load_policy(root, None)
    text = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    layers_body = render_layers_table(boundaries) + "\n\n" + render_layers_mermaid(boundaries)
    text = replace_region(text, "layers", layers_body)
    text = replace_region(text, "ownership", render_zones_mermaid(policy))
    return text


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="chỉ so, không ghi (dùng trong CI)")
    args = parser.parse_args()

    try:
        rendered = _rendered(ROOT)
    except AgentctlError as exc:
        print(f"🔴 {exc}", file=sys.stderr)
        return 1

    current = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    rel = ARCHITECTURE_PATH.relative_to(ROOT).as_posix()

    if args.check:
        if current != rendered:
            print(
                f"🔴 Lệch nguồn sự thật: {rel}\n"
                "   Sơ đồ/bảng trong tài liệu không còn khớp contracts/boundaries.yaml hoặc "
                "coordination/policy.yaml.\n"
                "   Chạy `python scripts/generate_diagrams.py` rồi commit diff.",
                file=sys.stderr,
            )
            return 1
        print(f"✅ {rel} khớp boundaries.yaml + policy.yaml.")
        return 0

    if current == rendered:
        print(f"✅ {rel} đã khớp — không có gì để ghi.")
        return 0
    ARCHITECTURE_PATH.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"✅ Đã sinh lại vùng `layers` và `ownership` trong {rel}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
