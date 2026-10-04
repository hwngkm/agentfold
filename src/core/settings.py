"""Cấu hình cấp ứng dụng — nơi DUY NHẤT phần lõi đọc biến môi trường.

Quy ước (chi tiết: `docs/rules/20-backend.md`):

- Mỗi miền có lớp settings riêng với `env_prefix` riêng, đặt trong gói của miền đó (vd.
  `src/llm/settings.py`, tiền tố `LLM_`). Không dồn mọi biến vào một lớp: file cấu
  hình một-lớp thành điểm nóng xung đột vì tính năng nào cũng thêm trường.
- Không `os.getenv()` rải rác. Thêm biến ⇒ sửa `.env.example` trong cùng PR.
- Bí mật dùng `SecretStr` để không lọt vào log hay `repr`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Mặc định cho máy dev và test. Cổng production (`production_gate.py`) từ chối khởi động nếu gặp nó.
DEV_JWT_SECRET = "dev-only-insecure-secret-change-me"
DEFAULT_CORS_ORIGIN = "http://localhost:3000"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Agentfold"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    cors_origins: str = DEFAULT_CORS_ORIGIN
    #: Chỉ dùng cho preview deployment đổi hostname mỗi lần đẩy. Mặc định RỖNG = tắt; mẫu quá rộng
    #: (vd. `.*\.vercel\.app`) cho trang của người khác gọi API kèm credential — cổng production chặn.
    cors_origin_regex: str = ""

    database_url: str = "sqlite:///./data/app.db"
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=5, ge=0, le=50)
    db_pool_timeout_sec: int = Field(default=10, ge=1, le=120)
    db_connect_timeout_sec: int = Field(default=10, ge=1, le=120)

    jwt_secret: SecretStr = SecretStr(DEV_JWT_SECRET)
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_access_ttl_min: int = Field(default=15, ge=1, le=1440)

    @property
    def cors_origin_list(self) -> list[str]:
        # `.strip()` từng mục: biến môi trường trên dashboard hay có khoảng trắng sau dấu phẩy, và
        # origin kèm khoảng trắng không bao giờ khớp — lỗi CORS rất khó truy.
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return AppSettings()
