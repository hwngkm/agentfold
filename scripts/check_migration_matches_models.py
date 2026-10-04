"""So schema Alembic dựng trên PostgreSQL THẬT với `Base.metadata` (job CI `migration-postgres`).

Bộ test dựng bảng bằng `create_all()`, nên không bao giờ chạy một dòng migration: thêm cột vào model mà quên
migration thì xanh ở local, xanh ở CI unit test, và đổ ở production với `UndefinedColumn` (đã gặp thật,
phát hiện tình cờ). Phép kiểm này hỏi chính Alembic: "autogenerate bây giờ có sinh thay đổi nào
không?" — kiểm KẾT QUẢ (schema có khớp), không kiểm cơ chế (ai đó có nhớ tạo migration).

PostgreSQL, không SQLite: SQLite không thực thi độ dài VARCHAR, phần lớn CHECK, và nhận những schema mà
PostgreSQL từ chối.

    python scripts/check_migration_matches_models.py --dsn postgresql+psycopg2://...   # CSDL ĐÃ `alembic upgrade head`
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

#: Bảng không do ứng dụng quản lý. Đừng bao giờ thêm bảng của mình vào đây để làm script im lặng.
FOREIGN_TABLES = frozenset({"alembic_version", "spatial_ref_sys"})
#: Khác biệt vô hại: cách viết server_default (`now()` vs `CURRENT_TIMESTAMP`), chú thích cột.
IGNORED_KINDS = frozenset({"modify_default", "modify_comment"})
#: Bậc CHẶN: code tham chiếu thứ CSDL không có — request đầu tiên chạm tới sẽ đổ.
BLOCKING_KINDS = frozenset({"add_table", "add_column"})


def _kind(diff: Any) -> str:
    if isinstance(diff, list):
        return _kind(diff[0]) if diff else ""
    return str(diff[0])


def _table(diff: Any) -> str:
    if isinstance(diff, list):
        return _table(diff[0]) if diff else ""
    kind = diff[0]
    if kind in ("add_table", "remove_table"):
        return str(diff[1].name)
    if kind in ("add_column", "remove_column") or kind.startswith("modify_"):
        return str(diff[2])
    table = getattr(
        diff[1], "table", None
    )  # chỉ mục/ràng buộc; không dùng `and` — mệnh đề SQL không có giá trị chân lý
    return str(table.name) if table is not None else ""


def differences(dsn: str) -> list[Any]:
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine

    from src.db.models import Base

    engine = create_engine(dsn)
    try:
        with engine.connect() as connection:
            raw = compare_metadata(MigrationContext.configure(connection, opts={"compare_type": True}), Base.metadata)
    finally:
        engine.dispose()
    return [d for d in raw if _table(d) not in FOREIGN_TABLES and _kind(d) not in IGNORED_KINDS]


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dsn", required=True, help="PostgreSQL đã chạy `alembic upgrade head`. Chỉ ĐỌC.")
    parser.add_argument("--strict", action="store_true", help="coi mọi lệch (nullable/kiểu/chỉ mục) là lỗi")
    args = parser.parse_args()
    if args.dsn.startswith("sqlite"):
        print("❌ DSN là SQLite — lặp lại đúng điểm mù phép kiểm này sinh ra để bịt.", file=sys.stderr)
        return 2
    found = differences(args.dsn)
    blocking = [d for d in found if _kind(d) in BLOCKING_KINDS]
    minor = [d for d in found if _kind(d) not in BLOCKING_KINDS]
    for diff in minor:
        print(f"⚠️  lệch (không chặn): [{_kind(diff)}] {_table(diff)} → {diff}")
    if blocking:
        for diff in blocking:
            print(f"❌ model có mà migration không dựng: [{_kind(diff)}] {_table(diff)} → {diff}", file=sys.stderr)
        print('Sửa: alembic revision --autogenerate -m "..." rồi ĐỌC LẠI file sinh ra.', file=sys.stderr)
        return 1
    if minor and args.strict:
        return 1
    print("✅ Schema sau `alembic upgrade head` khớp model." if not found else "✅ Không thiếu bảng/cột nào.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
