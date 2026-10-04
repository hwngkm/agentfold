"""Repo không chứa bí mật, CSDL, phụ thuộc, bảng theo dõi nhị phân; có đủ file của mặt phẳng điều phối.

Vì sao: một `git add -A` là đẩy nguyên `.env.bak` (khoá thật) lên remote — từng phải chặn thêm cả họ
`.env.*` sau một lần xoay khoá. Bảng Excel theo dõi việc bị 45 commit chạm trong 4 tuần và không
merge được.
"""

from __future__ import annotations

from scripts.check_structure import FORBIDDEN, REQUIRED, candidate_files, problems


def test_repo_sach() -> None:
    files = candidate_files()
    assert len(files) >= 50, "quét được quá ít file — lưới đang không kiểm gì"
    assert problems(files) == []


def test_du_lieu_khong_vao_git_nhung_seed_nho_va_gitkeep_thi_duoc() -> None:
    """Dữ liệu nhạy cảm thật nằm ở `data/` và kho riêng; một lần `git add .` không được mang nó lên remote."""

    def flagged(path: str) -> bool:
        return any(pattern.search(path) for pattern, _ in FORBIDDEN)

    for blocked in (
        "data/corpus/chunks.jsonl",
        "data/eval/gold.csv",
        "data/x/y.json",
        "snapshots/model.parquet",
        "a/b.pkl",
    ):
        assert flagged(blocked), blocked
    for allowed in ("data/.gitkeep", "seeds/foods.csv", "tests/fixtures/mau.jsonl", "docs/data/README.md"):
        assert not flagged(allowed), allowed


def test_bo_do_bat_duoc_file_cam_that() -> None:
    samples = [".env", "backend/.env.production", "docs/work/tien-do.xlsx", "data/app.db", "home/claude/x.py"]
    flagged = [path for path in samples if any(pattern.search(path) for pattern, _ in FORBIDDEN)]
    assert flagged == samples
    assert not any(pattern.search(".env.example") for pattern, _ in FORBIDDEN)
    assert "AGENTS.md" in REQUIRED
