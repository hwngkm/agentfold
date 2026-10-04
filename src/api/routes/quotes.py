"""Endpoint xem báo giá nháp — mẫu cho audit đa agent (EXM-01)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["quotes"])


@router.get("/quotes/{quote_id}")
async def get_quote(quote_id: str) -> dict[str, str]:
    return {"quote_id": quote_id}
