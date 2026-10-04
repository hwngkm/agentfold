"""Hook SAU KHI GHI FILE (Claude Code `PostToolUse`): kiểm nhanh đúng loại file vừa sửa, báo lại cho agent.

- `.py` → `ruff check` riêng file đó (vài trăm mili giây).
- `docs/work/**.md`, `coordination/policy.yaml` → kiểm cấu trúc mục công việc và chính sách.

Không chặn được gì (file đã ghi). Có vấn đề thì thoát mã 2 để Claude Code đưa stderr cho agent đọc
và tự sửa ngay, thay vì phát hiện ở CI 20 phút sau. Môi trường trục trặc ⇒ im lặng, thoát 0.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.hooks.guard_write import target_paths  # noqa: E402

FEEDBACK = 2


def _ruff(path: Path) -> list[str]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--quiet", "--output-format", "concise", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return [line for line in result.stdout.splitlines() if line.strip()] if result.returncode == 1 else []


def _work_items() -> list[str]:
    try:
        from tools.agentctl.errors import AgentctlError
        from tools.agentctl.policy import load_policy
        from tools.agentctl.workcheck import validate_work_items
    except ImportError:
        return []
    try:
        return validate_work_items(ROOT, load_policy(ROOT, None))
    except AgentctlError as exc:
        return [str(exc)]


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 0
    if not isinstance(payload, dict):
        return 0
    problems: list[str] = []
    check_work = False
    for raw in target_paths(payload):
        path = Path(raw)
        path = path if path.is_absolute() else ROOT / path
        try:
            rel = path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            continue
        if rel.endswith(".py") and path.is_file():
            problems += _ruff(path)
        check_work = check_work or rel.startswith("docs/work/") or rel == "coordination/policy.yaml"
    if check_work:
        problems += _work_items()
    if not problems:
        return 0
    print("🟡 Kiểm nhanh sau khi sửa:\n" + "\n".join(f"  - {p}" for p in problems[:20]), file=sys.stderr)
    return FEEDBACK


if __name__ == "__main__":
    raise SystemExit(main())
