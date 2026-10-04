"""Xuất hợp đồng API ra `contracts/openapi.json`, hoặc kiểm nó còn khớp ứng dụng (`--check`).

Vì sao commit bản chụp hợp đồng: đổi API mà không ai thấy là cách frontend (hay agent làm frontend)
gọi một endpoint không còn tồn tại. Bản chụp nằm trong diff của PR, nên mọi thay đổi hợp đồng HIỆN RA
để người review đọc — và file này là làn độc quyền `api-contract`, không hai ticket nào đổi nó cùng lúc.

    python scripts/export_openapi.py          # ghi lại bản chụp sau khi đổi API có chủ đích
    python scripts/export_openapi.py --check  # CI: đỏ nếu bản chụp lệch ứng dụng
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "openapi.json"


def render_contract() -> str:
    os.environ.setdefault("APP_ENV", "test")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.main import create_app

    schema = create_app().openapi()
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    # Console Windows mặc định cp1252: dòng in tiếng Việt đầu tiên ném UnicodeEncodeError và script chết
    # trước khi kịp báo kết quả — trông hệt một lỗi của công cụ bên dưới.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="chỉ so, không ghi")
    args = parser.parse_args()
    rendered = render_contract()
    current = CONTRACT.read_text(encoding="utf-8") if CONTRACT.is_file() else ""
    if args.check:
        if rendered != current:
            print("🔴 contracts/openapi.json lệch ứng dụng — chạy `python scripts/export_openapi.py` và commit diff.")
            return 1
        print("✅ Hợp đồng API khớp ứng dụng.")
        return 0
    CONTRACT.parent.mkdir(parents=True, exist_ok=True)
    CONTRACT.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"✅ Đã ghi {CONTRACT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
