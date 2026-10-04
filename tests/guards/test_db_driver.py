"""URL PostgreSQL trong cấu hình và fixture phải ghi RÕ driver (`postgresql+psycopg2://`), không để SQLAlchemy tự chọn.

Vì sao: `postgresql://` trần để SQLAlchemy chọn driver mặc định, mà mặc định đã đổi giữa các bản (psycopg2 → psycopg 3 ở 2.1).
`requirements.txt` ghim `psycopg2-binary`, nên trên máy có SQLAlchemy mới và không có `psycopg` v3, `tests/conftest.py` làm
hai test đỏ `ModuleNotFoundError: No module named 'psycopg'` — lỗi chỉ lộ trên máy dev, CI vẫn xanh vì CI ghi rõ driver
(phát hiện 03/10/2026). Ghi rõ driver làm hành vi không phụ thuộc phiên bản SQLAlchemy.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_BARE = re.compile(r"\bpostgres(?:ql)?://")
#: Nơi URL Postgres thật sự được đưa cho engine. Dữ liệu mẫu cho bộ lọc bí mật (tests/unit/test_llm_boundary.py) và danh sách
#: tiền tố khoá (scripts/secret_scan.py) cố ý chứa URL trần nên KHÔNG nằm ở đây.
CONFIG_FILES = (
    "tests/conftest.py",
    "docker-compose.yml",
    "render.yaml",
    ".env.example",
    "alembic.ini",
    *(p.relative_to(ROOT).as_posix() for p in sorted((ROOT / ".github" / "workflows").glob("*.yml"))),
)


def bare_urls(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if _BARE.search(line)]


def test_url_postgres_trong_cau_hinh_ghi_ro_driver() -> None:
    offenders = {
        rel: bare
        for rel in CONFIG_FILES
        if (ROOT / rel).is_file() and (bare := bare_urls((ROOT / rel).read_text(encoding="utf-8")))
    }
    assert offenders == {}, f"URL Postgres không ghi driver — dùng `postgresql+psycopg2://`: {offenders}"


def test_bo_kiem_phan_biet_url_tran_va_url_co_driver() -> None:
    assert bare_urls('os.environ["DATABASE_URL"] = "postgresql://u:p@h:1/d"')
    assert bare_urls("DATABASE_URL=postgres://u:p@h/d")
    assert not bare_urls("DATABASE_URL: postgresql+psycopg2://u:p@h/d")
    assert not bare_urls("DATABASE_URL: sqlite:///./data/x.db")
