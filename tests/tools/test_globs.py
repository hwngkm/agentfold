"""Mẫu đường dẫn: khớp đúng, và `may_overlap` KHÔNG BAO GIỜ bỏ sót một chồng lấn có thật."""

from __future__ import annotations

from itertools import product

import pytest

from tools.agentctl.globs import matches, matches_everything, may_overlap

CORPUS = [
    "README.md",
    "x.py",
    "src/main.py",
    "src/api/routes/orders.py",
    "src/api/routes/users.py",
    "src/api/routes/nested/deep.py",
    "src/domain/pricing/totals.py",
    "src/db/models/orders.py",
    "tests/unit/test_orders.py",
    "tests/unit/test_users.py",
    "tests/guards/test_boundaries.py",
    "docs/design/ARCHITECTURE.md",
    "docs/work/log/2026/09/2026-09-15-r2-a.md",
    "web/src/app/orders/page.tsx",
    "web/src/app/admin/page.tsx",
    "alembic/versions/20260915_0001_init.py",
]

PATTERNS = [
    "**",
    "*.md",
    "**/*.md",
    "**/*.py",
    "src/",
    "src/**",
    "src/*.py",
    "src/api/routes/*.py",
    "src/api/routes/orders.py",
    "src/api/**/deep.py",
    "src/**/orders.py",
    "tests/unit/test_orders*.py",
    "tests/**/test_*.py",
    "docs/design/**",
    "docs/work/log/**",
    "web/src/app/orders/**",
    "web/src/app/admin/**",
    "alembic/versions/**",
    "x.py",
]


@pytest.mark.parametrize(
    ("path", "pattern", "expected"),
    [
        ("src/api/routes/orders.py", "src/api/routes/*.py", True),
        ("src/api/routes/nested/deep.py", "src/api/routes/*.py", False),
        ("src/api/routes/nested/deep.py", "src/api/**", True),
        ("src/main.py", "src/", True),
        ("x.py", "**/x.py", True),
        ("src/x.py", "**/x.py", True),
        ("docs/design/ARCHITECTURE.md", "*.md", False),
        ("docs\\design\\ARCHITECTURE.md", "docs/design/**", True),
        ("./src/main.py", "src/*.py", True),
    ],
)
def test_matches(path: str, pattern: str, expected: bool) -> None:
    assert matches(path, pattern) is expected


def test_may_overlap_khong_bao_gio_bo_sot_chong_that() -> None:
    """Tính chất an toàn: có đường dẫn khớp cả hai mẫu ⇒ `may_overlap` phải trả `True`."""
    bo_sot = [
        (a, b)
        for a, b in product(PATTERNS, PATTERNS)
        if any(matches(p, a) and matches(p, b) for p in CORPUS) and not may_overlap(a, b)
    ]
    assert not bo_sot, f"báo không chồng trong khi có file khớp cả hai: {bo_sot}"


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("web/src/app/orders/**", "web/src/app/admin/**"),
        ("src/*.py", "src/api/**"),
        ("**/*.md", "src/**/*.py"),
        ("tests/unit/test_orders*.py", "tests/unit/test_users.py"),
        ("src/api/routes/orders.py", "src/api/routes/users.py"),
    ],
)
def test_may_overlap_tach_duoc_ca_pho_bien(a: str, b: str) -> None:
    """Độ chính xác: phạm vi rời nhau thì không bị từ chối oan — nếu không, người ta sẽ tắt claim."""
    assert not may_overlap(a, b)
    assert not may_overlap(b, a)


def test_mau_phu_ca_repo_bi_nhan_dien() -> None:
    assert matches_everything("**")
    assert matches_everything("**/*")
    assert not matches_everything("src/**")
    assert not matches_everything("**/*.py")
