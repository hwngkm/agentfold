"""Kiểm thông điệp commit: dạng conventional và mang mã ticket khi làm trên nhánh ticket.

Mã ticket trong dòng đầu là cách DUY NHẤT `board` và `claim` biết một ticket đã merge (không ai
ghi `done` bằng tay). Thiếu nó, phụ thuộc giữa các ticket không tự mở khoá được.
"""

from __future__ import annotations

import re

_CONVENTIONAL = re.compile(r"^(feat|fix|docs|test|refactor|chore|perf|ci)(\([a-z0-9][a-z0-9-]*\))?!?: \S")
_EXEMPT_PREFIXES = ("Merge ", 'Revert "', "fixup! ", "squash! ", "amend! ")
MAX_SUBJECT = 100


def check_commit_message(message: str, ticket_id: str | None) -> list[str]:
    lines = [line for line in message.replace("\r\n", "\n").split("\n") if not line.startswith("#")]
    subject = next((line.strip() for line in lines if line.strip()), "")
    if subject.startswith(_EXEMPT_PREFIXES):
        return []
    problems: list[str] = []
    if not _CONVENTIONAL.match(subject):
        problems.append("dòng đầu phải dạng `type(scope): mô tả`, type ∈ feat|fix|docs|test|refactor|chore|perf|ci")
    if ticket_id and f"({ticket_id})" not in subject:
        problems.append(
            f"nhánh gắn ticket `{ticket_id}` — dòng đầu phải chứa `({ticket_id})` để lịch sử truy được ticket"
        )
    if len(subject) > MAX_SUBJECT:
        problems.append(f"dòng đầu dài {len(subject)} ký tự, tối đa {MAX_SUBJECT}")
    return problems
