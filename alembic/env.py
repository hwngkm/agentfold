"""Môi trường Alembic: URL lấy từ cấu hình ứng dụng, metadata lấy từ mọi model tự khám phá."""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.settings import get_settings  # noqa: E402
from src.db.models import Base  # noqa: E402

config = context.config

# `disable_existing_loggers=False` là BẮT BUỘC. Mặc định `True` tắt vĩnh viễn mọi logger đã tạo mà
# ini không khai báo — chạy migration trong cùng tiến trình với ứng dụng/test sẽ bịt miệng toàn bộ log
# của `src.*`. Trong thực tế, đó là gốc của chuỗi "test đỏ ngẫu nhiên, chạy riêng lại xanh" vì `caplog`
# rỗng sau khi một test chạy migration.
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

config.set_main_option("sqlalchemy.url", os.environ.get("ALEMBIC_DATABASE_URL") or get_settings().database_url)
target_metadata = Base.metadata


def _is_sqlite() -> bool:
    return config.get_main_option("sqlalchemy.url", "").startswith("sqlite")


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        render_as_batch=_is_sqlite(),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        # `render_as_batch` trên SQLite: SQLite không có `ALTER COLUMN`; batch mode dựng lại bảng.
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True, render_as_batch=_is_sqlite()
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
