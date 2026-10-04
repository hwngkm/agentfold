"""Xác thực JWT và phân quyền theo vai trò.

Phân quyền kiểm HAI lần: ở route (`require_role`) và ở truy vấn (lọc theo chủ sở hữu). Route đúng
vai trò vẫn không được đọc bản ghi của người khác — trả 404 thay vì 403 để không lộ bản ghi tồn tại.
Luồng đăng nhập/cấp token là việc của từng dự án; `issue_access_token` chỉ là mẫu tối thiểu.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.settings import AppSettings, get_settings

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str


def issue_access_token(subject: str, role: str, settings: AppSettings, *, now: datetime | None = None) -> str:
    issued = now or datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role,
        "iat": issued,
        "exp": issued + timedelta(minutes=settings.jwt_access_ttl_min),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: AppSettings) -> Principal:
    unauthorized = status.HTTP_401_UNAUTHORIZED
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(unauthorized, "token đã hết hạn") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(unauthorized, "token không hợp lệ") from exc
    role = payload.get("role")
    if not isinstance(role, str) or not role:
        raise HTTPException(unauthorized, "token thiếu vai trò")
    return Principal(subject=str(payload["sub"]), role=role)


def current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[AppSettings, Depends(get_settings)],
) -> Principal:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "thiếu token")
    return decode_access_token(credentials.credentials, settings)


def require_role(*roles: str) -> Callable[[Principal], Principal]:
    allowed = frozenset(roles)

    def dependency(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
        if principal.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "không đủ quyền")
        return principal

    return dependency
