"""Engine và session dùng chung. PostgreSQL ở production; SQLite cho dev/test nhanh.

⚠️ SQLite "khớp" rộng hơn sự thật: nó không thực thi độ dài `VARCHAR`, phần lớn `CHECK`, và không
có `ALTER COLUMN`. Vì vậy migration luôn được kiểm thêm trên PostgreSQL thật ở CI (job
`migration-postgres`) — xanh trên SQLite không nói gì về production.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.core.settings import get_settings


class Base(DeclarativeBase):
    pass


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    url = make_url(settings.database_url)
    if url.get_backend_name() == "sqlite":
        if url.database and url.database != ":memory:":
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url, connect_args={"check_same_thread": False})
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
        return engine
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_sec,
        connect_args={"connect_timeout": settings.db_connect_timeout_sec},
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency. Test ghi đè nó bằng SQLite trong bộ nhớ (`tests/conftest.py`)."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
