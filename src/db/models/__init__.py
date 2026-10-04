"""Mọi module trong gói này tự được nạp để `Base.metadata` đầy đủ cho Alembic.

KHÔNG sửa file này khi thêm bảng — thêm một module mới trong gói (`src/db/models/<miền>.py`).
Không có danh sách import tập trung để mọi nhánh cùng sửa: file model một-khối thành
điểm nóng xung đột và là gốc của nhiều lần sinh nhiều head Alembic.
"""

from __future__ import annotations

import importlib
import pkgutil

from src.db.base import Base


def load_all_models() -> list[str]:
    loaded: list[str] = []
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda module: module.name):
        if not info.name.startswith("_"):
            importlib.import_module(f"{__name__}.{info.name}")
            loaded.append(info.name)
    return loaded


load_all_models()

__all__ = ["Base", "load_all_models"]
