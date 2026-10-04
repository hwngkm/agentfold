"""Cổng production: mặc định dev không được lên production, và mọi lỗi được báo trong MỘT lần."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from src.core.production_gate import ProductionConfigError, enforce_production_settings, production_problems
from src.core.settings import DEFAULT_CORS_ORIGIN, DEV_JWT_SECRET, AppSettings


def _settings(**overrides: object) -> AppSettings:
    base: dict[str, object] = {
        "app_env": "production",
        "jwt_secret": SecretStr("p" * 48),
        "database_url": "postgresql+psycopg2://app:secret@db.example:5432/app",
        "cors_origins": "https://app.example.vn",
        "cors_origin_regex": "",
    }
    return AppSettings(**(base | overrides))  # type: ignore[arg-type]


def test_cau_hinh_production_day_du_thi_qua() -> None:
    enforce_production_settings(_settings())


def test_mac_dinh_dev_bi_chan_va_bao_du_moi_loi_mot_lan() -> None:
    settings = _settings(
        jwt_secret=SecretStr(DEV_JWT_SECRET), database_url="sqlite:///./data/app.db", cors_origins=DEFAULT_CORS_ORIGIN
    )
    with pytest.raises(ProductionConfigError) as error:
        enforce_production_settings(settings)
    message = str(error.value)
    assert "3 chỗ" in message
    for fragment in ("JWT_SECRET", "DATABASE_URL", "CORS_ORIGINS"):
        assert fragment in message


@pytest.mark.parametrize(
    "regex", [r".*\.vercel\.app", r"^https://.*\.vercel\.app$", r"^https://app-[^.]+\.vercel\.app$"]
)
def test_regex_cors_qua_rong_bi_chan(regex: str) -> None:
    assert any("CORS_ORIGIN_REGEX" in p for p in production_problems(_settings(cors_origin_regex=regex)))


def test_regex_cors_neo_ten_du_an_thi_qua() -> None:
    assert production_problems(_settings(cors_origin_regex=r"^https://app-[a-z0-9]+-team\.vercel\.app$")) == []


def test_khong_phai_production_thi_khong_chan() -> None:
    assert production_problems(AppSettings(app_env="development")) == []


def test_khoa_ngan_bi_chan() -> None:
    assert any("tối thiểu" in p for p in production_problems(_settings(jwt_secret=SecretStr("ngan"))))
