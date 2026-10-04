"""Thân lỗi thống nhất và xử lý lỗi hạ tầng có thể thử lại."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


class ErrorBody(BaseModel):
    code: str
    detail: str
    retryable: bool = False


async def _database_unavailable(_request: Request, exc: Exception) -> JSONResponse:
    # Không đưa `exc` ra client: thông điệp của driver có thể chứa host/tên CSDL.
    logger.warning("CSDL tạm thời không kết nối được: %s", type(exc).__name__)
    body = ErrorBody(
        code="database_unavailable", detail="Cơ sở dữ liệu tạm thời mất kết nối, thử lại sau.", retryable=True
    )
    return JSONResponse(
        body.model_dump(), status_code=status.HTTP_503_SERVICE_UNAVAILABLE, headers={"Retry-After": "15"}
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(OperationalError, _database_unavailable)
