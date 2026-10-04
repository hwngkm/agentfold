"""Cấu hình riêng của cửa ngõ LLM (tiền tố `LLM_`) — mẫu cho quy ước "mỗi miền một lớp settings"."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    #: `offline` = không gọi mạng; dùng cho test, CI và máy chưa có khoá.
    provider: Literal["offline", "openai", "anthropic", "gemini", "openai_compatible"] = "offline"
    model: str = ""
    api_key: SecretStr = SecretStr("")
    base_url: str = ""
    #: Mọi lời gọi LLM có timeout tường minh — treo mạng không được thành request treo.
    timeout_sec: float = Field(default=20.0, ge=1.0, le=120.0)
    #: Mọi vòng lặp gọi LLM có trần — không có vòng lặp vô hạn tốn tiền thật.
    max_attempts: int = Field(default=2, ge=1, le=5)


@lru_cache(maxsize=1)
def get_llm_settings() -> LLMSettings:
    return LLMSettings()
