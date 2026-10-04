"""Sống (`/health`) và sẵn sàng (`/health/ready`) — tách hai để nền tảng deploy không giết tiến trình
chỉ vì CSDL chập chờn, trong khi người vận hành vẫn thấy được CSDL đang hỏng."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.settings import AppSettings, get_settings
from src.db.base import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(settings: Annotated[AppSettings, Depends(get_settings)]) -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@router.get("/health/ready")
def ready(db: Annotated[Session, Depends(get_db)]) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
