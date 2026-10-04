"""Tầng HTTP: sống/sẵn sàng, xác thực, lỗi hạ tầng không lộ chi tiết."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from src.api.errors import install_error_handlers
from src.api.security import Principal, issue_access_token, require_role
from src.core.settings import get_settings
from src.db.base import get_db
from src.main import app


def test_health_va_ready(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok", "env": "test"}
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_ready_tra_503_co_the_thu_lai_khi_csdl_mat_ket_noi() -> None:
    class BrokenSession:
        def execute(self, *_args: object) -> None:
            raise OperationalError("SELECT 1", {}, Exception("could not connect to host db.internal"))

    def broken_db() -> Iterator[BrokenSession]:
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    try:
        response = TestClient(app).get("/health/ready")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json()["retryable"] is True
    assert "db.internal" not in response.text, "thông điệp driver (host CSDL) không được lộ ra client"


def test_me_can_token_hop_le(client: TestClient) -> None:
    settings = get_settings()
    assert client.get("/api/v1/me").status_code == 401
    token = issue_access_token("u-1", "reviewer", settings)
    assert client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"}).json() == {
        "subject": "u-1",
        "role": "reviewer",
    }
    expired = issue_access_token("u-1", "reviewer", settings, now=datetime.now(UTC) - timedelta(days=1))
    assert client.get("/api/v1/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}x"}).status_code == 401


def test_require_role_chan_sai_vai_tro() -> None:
    mini = FastAPI()
    install_error_handlers(mini)

    @mini.get("/duyet")
    def duyet(principal: Principal = Depends(require_role("reviewer"))) -> dict[str, str]:  # noqa: B008
        return {"ok": principal.subject}

    settings = get_settings()
    test_client = TestClient(mini)
    staff = issue_access_token("u-2", "staff", settings)
    reviewer = issue_access_token("u-3", "reviewer", settings)
    assert test_client.get("/duyet", headers={"Authorization": f"Bearer {staff}"}).status_code == 403
    assert test_client.get("/duyet", headers={"Authorization": f"Bearer {reviewer}"}).status_code == 200


@pytest.mark.parametrize("path", ["/health", "/health/ready", "/api/v1/me"])
def test_moi_route_mau_duoc_tu_kham_pha(path: str) -> None:
    # Đọc qua OpenAPI thay vì `app.routes`: cấu trúc nội bộ của router đổi giữa các bản FastAPI.
    assert path in app.openapi()["paths"]
