"""Fixture dùng chung. Biến môi trường PHẢI đặt trước mọi `import src.*`.

`get_settings()` được cache ngay lần import đầu. Máy phát triển thường có `.env` trỏ `DATABASE_URL`
sang CSDL thật — có dự án, đó là CSDL DÙNG CHUNG với bản deploy. Trỏ URL vào một cổng chết ở
loopback biến mọi đường vô tình chạm CSDL thật thành lỗi TO ngay lập tức, thay vì âm thầm ghi vào
dữ liệu người dùng. Test cần CSDL thì dùng `db_session` (SQLite trong bộ nhớ).
"""

from __future__ import annotations

import os

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "postgresql+psycopg2://test:test@127.0.0.1:1/khong-duoc-cham-csdl-that"
os.environ["JWT_SECRET"] = "test-only-secret-with-enough-length-0123456789"
os.environ["LLM_PROVIDER"] = "offline"

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from src.db.base import get_db  # noqa: E402
from src.db.models import Base  # noqa: E402
from src.main import app  # noqa: E402


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
