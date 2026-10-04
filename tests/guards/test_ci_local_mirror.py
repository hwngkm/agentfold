"""`scripts/ci_local.py` phải phủ MỌI lệnh mà CI chạy.

Vì sao: script "chạy giống CI" mà lệch CI thì tệ hơn không có — nó nói "sạch", người ta đẩy, CI đỏ đúng ở bước
script bỏ sót. Đã có dự án đỏ CI sáu lần liên tiếp vì kiểm cục bộ khác CI.
Khoá gì: mỗi dòng `run:` của ci.yml hoặc có Y HỆT trong `CI_COMMANDS`, hoặc nằm trong danh sách miễn có lý do.
Sửa khi đỏ: thêm lệnh vào `CI_COMMANDS`, hoặc thêm vào `EXEMPT` kèm lý do đọc được — không để trống.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.ci_local import CI_COMMANDS

ROOT = Path(__file__).resolve().parents[2]

#: Tiền tố lệnh CI mà script CỐ Ý không chạy — mỗi mục là một quyết định có lý do.
EXEMPT = {
    "python -m pip install": "cài phụ thuộc — máy đã có môi trường",
    "npm ci": "cài phụ thuộc frontend — máy đã có node_modules",
    "docker build": "dựng image mất nhiều phút và cần Docker đang chạy",
    "alembic upgrade head": "cần CSDL trống; máy dev không được chạy migration vào CSDL dùng chung",
    "python scripts/check_migration_matches_models.py": "cần PostgreSQL trống; lưới SQLite rẻ đã có trong tests/guards",
    "python -m uvicorn": "khởi động backend cho e2e, không phải phép kiểm",
    "trap ": "dọn tiến trình e2e",
    "for attempt": "vòng chờ backend sẵn sàng",
    "cd web": "đổi thư mục trong bước e2e",
    "npx playwright install": "tải trình duyệt (~150 MB), cài một lần",
    "npx playwright test": "cần backend + frontend đang chạy",
}


def _run_lines() -> list[str]:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    lines: list[str] = []
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            for line in str(step.get("run", "")).splitlines():
                if line.strip() and not line.strip().startswith("#"):
                    lines.append(line.strip())
    return lines


def test_script_phu_moi_lenh_cua_ci() -> None:
    lines = _run_lines()
    assert len(lines) >= 10, "đọc được quá ít lệnh từ ci.yml — lưới đang không kiểm gì"
    mirrored = set(CI_COMMANDS.values())
    missing = [line for line in lines if line not in mirrored and not line.startswith(tuple(EXEMPT))]
    assert not missing, (
        "CI chạy những lệnh mà scripts/ci_local.py không phủ:\n  "
        + "\n  ".join(missing)
        + "\nThêm vào CI_COMMANDS, hoặc vào EXEMPT kèm lý do."
    )


def test_khong_mien_nham_lenh_kiem_tra() -> None:
    """Chiều ngược lại: lệnh script phản chiếu phải thật sự còn trong CI — nếu không, `CI_COMMANDS` nói dối."""
    stale = set(CI_COMMANDS.values()) - set(_run_lines())
    assert not stale, f"CI_COMMANDS còn lệnh CI không chạy nữa: {stale}"


def test_script_chay_duoi_utc_va_kiem_cay_git_sach() -> None:
    source = (ROOT / "scripts/ci_local.py").read_text(encoding="utf-8")
    assert '"TZ": "UTC"' in source, "CI chạy UTC — script phải ép TZ=UTC để tái hiện CI chứ không tái hiện máy"
    assert "--porcelain" in source, "script phải kiểm cây git sạch: CI checkout repo, không checkout đĩa của bạn"
