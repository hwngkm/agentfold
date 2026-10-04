"""Đồ thị migration đúng một head, không revision mồ côi, và mọi bảng trong model đều có migration.

Vì sao:
- Nhiều nhánh cùng thêm migration rồi merge mà không gộp head ⇒ `alembic upgrade head` MƠ HỒ, chỉ lộ
  ra lúc deploy. Từng gặp nhiều lần và phải viết hàng chục revision chỉ để gộp head.
- Bộ test dựng bảng bằng `create_all()`, nên thêm model mà quên migration là XANH tuyệt đối ở local;
  production đổ `UndefinedTable` ở request đầu tiên (đã gặp thật, phát hiện tình cờ).

Sửa khi đỏ: `alembic merge -m "gộp ..." <head1> <head2>` — TUYỆT ĐỐI KHÔNG `alembic stamp`: stamp ghi
đè `alembic_version` mà không chạy DDL, tức nói dối về schema thật.

Đây là lưới RẺ và SỚM. Lưới ĐÚNG là job CI `migration-postgres`: SQLite chấp nhận những schema mà
PostgreSQL từ chối, nên xanh ở đây không thay được xanh ở đó.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from alembic import command
from src.db.models import Base

ROOT = Path(__file__).resolve().parents[2]


def _config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    return config


def test_alembic_ini_chi_chua_ascii() -> None:
    """Alembic đọc `alembic.ini` bằng mã hoá của locale. Một ký tự có dấu làm MỌI lệnh alembic đổ trên
    máy Windows cp1252 (`UnicodeDecodeError`) — phát hiện khi dựng chính template này."""
    raw = (ROOT / "alembic.ini").read_bytes()
    assert raw.isascii(), "alembic.ini chứa ký tự ngoài ASCII — viết chú thích không dấu"


def test_dung_mot_head() -> None:
    heads = ScriptDirectory.from_config(_config()).get_heads()
    assert len(heads) == 1, f"{len(heads)} head {heads} — gộp bằng `alembic merge`, không bằng `alembic stamp`"


def test_khong_revision_mo_coi() -> None:
    script = ScriptDirectory.from_config(_config())
    known = {revision.revision for revision in script.walk_revisions()}
    assert known, "không đọc được revision nào — kiểm alembic.ini/script_location"
    orphans = [
        f"{revision.revision} → {down}"
        for revision in script.walk_revisions()
        for down in (
            [revision.down_revision] if isinstance(revision.down_revision, str) else revision.down_revision or []
        )
        if down not in known
    ]
    assert not orphans, f"revision trỏ vào mã không tồn tại: {orphans}"


def test_upgrade_head_tren_sqlite_dung_du_moi_bang_va_cot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Chạy migration THẬT (nạp `env.py`), rồi hỏi Alembic: schema thu được có thiếu gì so với model?

    `ScriptDirectory.from_config()` không nạp `env.py` — một lưới chỉ đọc đồ thị sẽ xanh cả khi `env.py`
    hỏng. Nên phải chạy `command.upgrade`.
    """
    url = f"sqlite:///{(tmp_path / 'migrate.db').as_posix()}"
    monkeypatch.setitem(os.environ, "ALEMBIC_DATABASE_URL", url)
    command.upgrade(_config(), "head")
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    finally:
        engine.dispose()
    missing = [item for item in diff if isinstance(item, tuple) and item[0] in {"add_table", "add_column"}]
    assert not missing, f"model có mà migration không dựng: {missing}"
    assert Base.metadata.tables, "Base.metadata rỗng — lưới này đang không kiểm gì"
