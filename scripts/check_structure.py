"""Vệ sinh repo: thứ không được có trong git, và thứ bắt buộc phải có để mặt phẳng điều phối chạy được.

Đọc danh sách file mà git sẽ commit (đã theo dõi + chưa theo dõi nhưng không bị ignore), nên chạy được như
một bước kiểm TRƯỚC khi commit.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 5 * 1024 * 1024

REQUIRED = [
    "AGENTS.md",
    "coordination/policy.yaml",
    "contracts/boundaries.yaml",
    "docs/design/invariants.yaml",
    "docs/design/ARCHITECTURE.md",
    ".github/workflows/ci.yml",
    ".github/workflows/scope-guard.yml",
    "scripts/githooks/pre-commit",
]

#: (mẫu regex trên đường dẫn POSIX, lý do)
FORBIDDEN: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(^|/)\.env($|\.(?!example$)[^/]*$)"), "file môi trường chứa bí mật — chỉ commit .env.example"),
    (re.compile(r"\.(pem|key|p12|pfx)$"), "khoá/chứng chỉ"),
    (re.compile(r"(^|/)(node_modules|\.venv|venv|__pycache__)/"), "phụ thuộc/cache không commit"),
    (re.compile(r"\.(db|sqlite3?)$"), "file CSDL — có thể chứa dữ liệu người dùng"),
    (
        re.compile(r"^data/(?!\.gitkeep$)"),
        "dữ liệu không vào git — `data/` chỉ giữ `.gitkeep`; đồng bộ qua kho dữ liệu riêng (docs/rules/40-data.md R40.10)",
    ),
    (
        re.compile(r"\.(parquet|feather|arrow|h5|hdf5|npy|npz|pkl|pickle)$"),
        "tệp dữ liệu nhị phân/cột — không diff, không review, dễ chứa dữ liệu thật (R40.10)",
    ),
    (
        re.compile(r"^docs/work/.*\.(xlsx|xls|docx|numbers)$"),
        "bảng theo dõi nhị phân không merge được — dùng file Markdown",
    ),
    (re.compile(r"^(mnt|home|Users)/"), "đường dẫn sandbox/máy cá nhân của agent lọt vào repo"),
    (re.compile(r"(^|/)\.worktrees/"), "worktree của agent"),
]


def candidate_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode == 0:
        return [line for line in result.stdout.splitlines() if line and (ROOT / line).exists()]
    skip = {".git", ".venv", "node_modules", ".worktrees", "__pycache__"}
    return [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and not skip.intersection(path.relative_to(ROOT).parts)
    ]


def problems(files: list[str]) -> list[str]:
    found = [f"thiếu `{rel}` — mặt phẳng điều phối cần file này" for rel in REQUIRED if not (ROOT / rel).is_file()]
    for rel in files:
        for pattern, reason in FORBIDDEN:
            if pattern.search(rel):
                found.append(f"{rel} — {reason}")
                break
        else:
            if (ROOT / rel).stat().st_size > MAX_FILE_BYTES:
                found.append(f"{rel} — lớn hơn {MAX_FILE_BYTES // (1024 * 1024)} MB, không để trong git")
    return found


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    files = candidate_files()
    found = problems(files)
    if found:
        print(f"🔴 {len(found)} vấn đề trong {len(files)} file:")
        print("\n".join(f"  - {item}" for item in found))
        return 1
    print(f"✅ Repo sạch ({len(files)} file).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
