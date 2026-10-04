"""Test cho EXM-01 — mẫu audit, không phải đặc tả sản phẩm thật."""

from __future__ import annotations


def test_route_ton_tai() -> None:
    from src.api.routes.quotes import router

    assert any(r.path == "/api/v1/quotes/{quote_id}" for r in router.routes)
