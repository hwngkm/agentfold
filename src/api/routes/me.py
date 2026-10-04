"""Mẫu endpoint cần xác thực: trả danh tính trong token (không tra CSDL)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.security import Principal, current_principal

router = APIRouter(prefix="/api/v1", tags=["auth"])


class MeResponse(BaseModel):
    subject: str
    role: str


@router.get("/me")
async def me(principal: Annotated[Principal, Depends(current_principal)]) -> MeResponse:
    return MeResponse(subject=principal.subject, role=principal.role)
