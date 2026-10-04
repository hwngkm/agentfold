"""Router tự khám phá: mỗi module trong gói này có một biến `router` là `APIRouter`.

KHÔNG sửa file này khi thêm endpoint — thêm một module mới (`src/api/routes/<tài-nguyên>.py`).
Một file đăng ký router tập trung là chỗ MỌI nhánh tính năng cùng sửa, tức là xung đột merge được
đảm bảo. Module thiếu `router` làm ứng dụng đổ lúc khởi động thay vì âm thầm mất endpoint.
"""

from __future__ import annotations

import importlib
import pkgutil

from fastapi import APIRouter


def discover_routers() -> list[APIRouter]:
    routers: list[APIRouter] = []
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda module: module.name):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{info.name}")
        router = getattr(module, "router", None)
        if not isinstance(router, APIRouter):
            raise RuntimeError(f"{module.__name__} không có biến `router: APIRouter`")
        routers.append(router)
    return routers
