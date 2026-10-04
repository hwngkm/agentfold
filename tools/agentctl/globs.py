"""Ngôn ngữ mẫu đường dẫn dùng chung cho scope ticket, vùng bảo vệ và làn độc quyền.

Quy ước (đường dẫn POSIX, tương đối với gốc repo):

- `**`  khớp mọi chuỗi, kể cả `/` (không hoặc nhiều thư mục).
- `*`   khớp mọi chuỗi không chứa `/`.
- `?`   khớp đúng một ký tự khác `/`.
- Mẫu kết thúc bằng `/` nghĩa là mọi thứ bên dưới thư mục đó (tương đương `dir/**`).

`may_overlap` trả lời "hai mẫu có THỂ cùng khớp một file không". Nó **bảo thủ**: có thể báo chồng
khi thật ra không chồng, nhưng **không bao giờ** báo không chồng khi tồn tại một đường dẫn khớp cả
hai. Chiều sai được chọn là chiều an toàn — một claim bị từ chối oan tốn một câu hỏi thu hẹp phạm
vi; một claim chồng lọt qua tốn một buổi gỡ xung đột merge. Tính chất này có test hồi quy trên một
tập đường dẫn mẫu (`tests/tools/test_globs.py`).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache

_WILDCARDS = ("*", "?")


def normalize(path: str) -> str:
    """Đưa đường dẫn về dạng POSIX tương đối, bỏ `./` ở đầu."""
    result = path.replace("\\", "/")
    while result.startswith("./"):
        result = result[2:]
    return result


def _expand(pattern: str) -> str:
    result = normalize(pattern)
    return result + "**" if result.endswith("/") else result


def _skeleton(pattern: str) -> str:
    """Bỏ dấu `/` tuỳ chọn sau `**` để tính tiền tố/hậu tố literal cho đúng.

    `**/x.py` khớp cả `x.py` ở gốc — nên hậu tố bắt buộc là `x.py`, không phải `/x.py`.
    """
    return _expand(pattern).replace("**/", "**")


@lru_cache(maxsize=2048)
def _regex(pattern: str) -> re.Pattern[str]:
    source = _expand(pattern)
    parts: list[str] = []
    i = 0
    while i < len(source):
        if source.startswith("**/", i):
            parts.append("(?:.*/)?")
            i += 3
        elif source.startswith("**", i):
            parts.append(".*")
            i += 2
        elif source[i] == "*":
            parts.append("[^/]*")
            i += 1
        elif source[i] == "?":
            parts.append("[^/]")
            i += 1
        else:
            parts.append(re.escape(source[i]))
            i += 1
    return re.compile("^" + "".join(parts) + "$")


def matches(path: str, pattern: str) -> bool:
    return _regex(pattern).match(normalize(path)) is not None


def matches_any(path: str, patterns: Iterable[str]) -> bool:
    return any(matches(path, pattern) for pattern in patterns)


def is_literal(pattern: str) -> bool:
    candidate = normalize(pattern)
    return not candidate.endswith("/") and not any(w in candidate for w in _WILDCARDS)


def matches_everything(pattern: str) -> bool:
    """Mẫu phủ toàn repo (`**`, `*`, `**/*`...) — vô hiệu hoá mọi phép điều phối."""
    return _literal_prefix(pattern) == "" and _literal_suffix(pattern) == "" and "**" in _expand(pattern)


def _literal_prefix(pattern: str) -> str:
    skeleton = _skeleton(pattern)
    cut = min((skeleton.index(w) for w in _WILDCARDS if w in skeleton), default=len(skeleton))
    return skeleton[:cut]


def _literal_suffix(pattern: str) -> str:
    skeleton = _skeleton(pattern)
    cut = max((skeleton.rindex(w) for w in _WILDCARDS if w in skeleton), default=-1)
    return skeleton[cut + 1 :]


def _slash_range(pattern: str) -> tuple[int, int | None]:
    """Số dấu `/` tối thiểu/tối đa mà một đường dẫn khớp mẫu phải có (`None` = không giới hạn)."""
    source = _expand(pattern)
    minimum = source.replace("**/", "").count("/")
    return minimum, (None if "**" in source else minimum)


def may_overlap(a: str, b: str) -> bool:
    if is_literal(a) and is_literal(b):
        return normalize(a) == normalize(b)
    if is_literal(a):
        return matches(a, b)
    if is_literal(b):
        return matches(b, a)
    prefix_a, prefix_b = _literal_prefix(a), _literal_prefix(b)
    if not (prefix_a.startswith(prefix_b) or prefix_b.startswith(prefix_a)):
        return False
    suffix_a, suffix_b = _literal_suffix(a), _literal_suffix(b)
    if not (suffix_a.endswith(suffix_b) or suffix_b.endswith(suffix_a)):
        return False
    (min_a, max_a), (min_b, max_b) = _slash_range(a), _slash_range(b)
    return (max_a is None or max_a >= min_b) and (max_b is None or max_b >= min_a)
