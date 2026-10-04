"""Tài liệu agent đọc không được trỏ tới đường dẫn không tồn tại.

Vì sao: agent làm theo tài liệu như đặc tả. Một đường dẫn chết ("xem `docs/rules/xx.md`") khiến agent
hoặc bỏ qua luật, hoặc tự bịa nội dung cho file nó không tìm thấy. Đã có trường hợp comment "đang chờ
`TênModule`, chưa merge" tồn tại nhiều tuần sau khi module đó đã chạy thật — mọi người đọc code,
kể cả người phụ trách, kết luận sai rằng tính năng còn bị chặn.

Khoá gì: mọi đoạn mã nội tuyến trông như đường dẫn (có `/`, không có ký tự giữ chỗ) phải tồn tại, tính
từ gốc repo hoặc từ thư mục của tài liệu. Ticket được miễn — chúng nói về file SẼ tạo.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXEMPT_DIRS = ("docs/work/tickets/",)
_CODE_SPAN = re.compile(r"(?<!`)`([^`\s]+)`(?!`)")
_PLACEHOLDER = re.compile(r"[<>*{}$|=:…]|YYYY|NNNN|\.\.\.")


def _docs() -> list[Path]:
    files = [ROOT / name for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", "README.md", "web/AGENTS.md")]
    files += sorted((ROOT / "docs").rglob("*.md")) + sorted((ROOT / "coordination").rglob("*.md"))
    return [f for f in files if f.is_file() and not f.relative_to(ROOT).as_posix().startswith(EXEMPT_DIRS)]


def _strip_fenced_blocks(text: str) -> str:
    """Khối lệnh ``` chứa ví dụ và đầu ra minh hoạ, không phải tham chiếu — bỏ trước khi quét."""
    return re.sub(r"^```.*?^```", "", text, flags=re.MULTILINE | re.DOTALL)


def dangling(text: str, doc_dir: Path) -> list[str]:
    missing: list[str] = []
    for token in _CODE_SPAN.findall(_strip_fenced_blocks(text)):
        # `/health`, `/api/v1`: đường dẫn URL của API, không phải file trong repo.
        if "/" not in token or _PLACEHOLDER.search(token) or token.startswith(("/", "http", "git@", "refs/")):
            continue
        clean = token.split("#", 1)[0].rstrip("/")
        # Chỉ bỏ tiền tố `./` — `lstrip(".")` sẽ cắt luôn dấu chấm của `.github/`, `.claude/`.
        first = re.sub(r"^(?:\./)+", "", clean).split("/", 1)[0]
        bases = [base for base in (ROOT, doc_dir) if (base / first).exists() or clean.startswith("..")]
        if not bases:
            continue  # không bắt đầu bằng thứ gì có trong repo: nhánh git, ref, ví dụ tên
        if not any((base / clean).exists() for base in bases):
            missing.append(token)
    return missing


def test_co_tai_lieu_de_quet() -> None:
    assert len(_docs()) >= 15, "quét được quá ít tài liệu — lưới đang không kiểm gì"


@pytest.mark.parametrize("doc", _docs(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_khong_tro_toi_duong_dan_chet(doc: Path) -> None:
    assert dangling(doc.read_text(encoding="utf-8"), doc.parent) == []


def test_bo_do_bat_duoc_duong_dan_chet_that() -> None:
    text = (
        "Xem `src/khong/ton-tai.py` và `docs/rules/99-bia.md`, nhưng `feature/ABC-01-x`, `<ID>/x` và "
        "`/api/v1` không phải file."
    )
    assert dangling(text, ROOT) == ["src/khong/ton-tai.py", "docs/rules/99-bia.md"]
