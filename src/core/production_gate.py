"""Cổng cấu hình production — chạy lúc KHỞI ĐỘNG. Thiếu hoặc sai thì dịch vụ không lên.

Mặc định của `AppSettings` giúp test và máy dev chạy không cần `.env`. Ở production, chính các mặc
định ấy là bẫy im lặng:

| Biến bị quên   | Hậu quả nếu dịch vụ vẫn lên                                                         |
|----------------|--------------------------------------------------------------------------------------|
| `JWT_SECRET`   | Token ký bằng một chuỗi nằm trong source control — ai đọc repo cũng tự cấp quyền admin |
| `DATABASE_URL` | Chạy SQLite trong container — dữ liệu mất sạch mỗi lần deploy                        |
| `CORS_ORIGINS` | Không trình duyệt nào ngoài máy dev gọi được API                                     |

Không log lỗi, không 500, không dấu hiệu nào trên giao diện. Một dịch vụ không lên thì ai cũng thấy
trong năm phút; một dịch vụ lên với khoá công khai thì không ai thấy (đã gặp thật).
Gom MỌI lỗi rồi báo một lần, để người vận hành không phải deploy lại ba lần mới biết thiếu ba biến.
"""

from __future__ import annotations

import re

from src.core.settings import DEFAULT_CORS_ORIGIN, DEV_JWT_SECRET, AppSettings

MIN_JWT_SECRET_LENGTH = 32
_TOO_BROAD_REGEX = re.compile(r"\.\*|\.\+|\[\^")


class ProductionConfigError(RuntimeError):
    """Cấu hình production thiếu hoặc còn giá trị mặc định của môi trường phát triển."""


def production_problems(settings: AppSettings) -> list[str]:
    if settings.app_env != "production":
        return []
    problems: list[str] = []
    secret = settings.jwt_secret.get_secret_value()
    if secret == DEV_JWT_SECRET:
        problems.append(
            "JWT_SECRET vẫn là mặc định dev (nằm trong source control). "
            'Sinh khoá: python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    elif len(secret) < MIN_JWT_SECRET_LENGTH:
        problems.append(f"JWT_SECRET dài {len(secret)} ký tự, cần tối thiểu {MIN_JWT_SECRET_LENGTH}")
    if settings.database_url.startswith("sqlite"):
        problems.append("DATABASE_URL trỏ SQLite — trong container, dữ liệu mất sạch mỗi lần deploy")
    regex = settings.cors_origin_regex.strip()
    if settings.cors_origin_list in ([], [DEFAULT_CORS_ORIGIN]) and not regex:
        problems.append("CORS_ORIGINS vẫn là mặc định localhost và không có CORS_ORIGIN_REGEX")
    if regex and (not regex.startswith("^https://") or not regex.endswith("$") or _TOO_BROAD_REGEX.search(regex)):
        problems.append(
            "CORS_ORIGIN_REGEX quá rộng: phải neo `^https://...$` vào tên dự án + team, không chứa `.*`/`.+`/`[^`"
        )
    return problems


def enforce_production_settings(settings: AppSettings) -> None:
    problems = production_problems(settings)
    if problems:
        numbered = "\n".join(f"  {index}. {problem}" for index, problem in enumerate(problems, 1))
        raise ProductionConfigError(
            f"Cấu hình production sai ở {len(problems)} chỗ — dịch vụ KHÔNG khởi động:\n{numbered}\n"
            "Hướng dẫn đặt biến: docs/DEPLOY.md"
        )
