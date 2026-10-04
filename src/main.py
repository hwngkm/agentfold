"""Gốc lắp ráp ứng dụng. Cổng production chạy TRƯỚC khi FastAPI nhận request nào."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.errors import install_error_handlers
from src.api.routes import discover_routers
from src.core.production_gate import enforce_production_settings
from src.core.settings import AppSettings, get_settings
from src.db.base import get_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info("Khởi động %s", app.title)
    yield
    get_engine().dispose()


def create_app(settings: AppSettings | None = None) -> FastAPI:
    settings = settings or get_settings()
    enforce_production_settings(settings)
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex.strip() or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    for router in discover_routers():
        app.include_router(router)
    return app


app = create_app()
