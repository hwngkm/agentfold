"""Đồng hồ duy nhất của agentctl.

Mọi phép so lease đi qua `now()` để test tua được thời gian bằng biến `AGENTCTL_NOW` mà không cần
chờ thật hay vá `datetime`. Biến này chỉ dành cho test — đặt nó trong phiên làm việc thật là tự
lừa mình về hạn lease.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime


def now() -> datetime:
    override = os.environ.get("AGENTCTL_NOW", "").strip()
    return parse_iso(override) if override else datetime.now(UTC)


def parse_iso(text: str) -> datetime:
    parsed = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
