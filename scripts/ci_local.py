"""Chạy đúng những gì CI chạy, trên máy, trước khi đẩy — chạy HẾT rồi mới tổng kết.

Vì sao tồn tại: từng có dự án đỏ CI sáu lần liên tiếp, mỗi lần một lỗi khác, cả sáu cùng
một gốc — phép kiểm cục bộ khác phép kiểm CI: chỉ chạy `ruff check` mà quên `ruff format --check`; không chạy
mypy; lệch múi giờ (máy UTC+7, CI UTC); file có trên đĩa mà chưa từng commit. Mỗi lượt đẩy chỉ lộ một lỗi.

    python scripts/ci_local.py          # đủ bước (trước khi mở/cập nhật PR)
    python scripts/ci_local.py --fast   # bỏ bước chậm (trước mỗi commit)

⚠️ Mọi lệnh `run:` trong `.github/workflows/ci.yml` phải có trong `CI_COMMANDS` (hoặc được miễn có lý do) —
lưới canh `tests/guards/test_ci_local_mirror.py` đỏ khi CI thêm bước mà script chưa có. Một script nói
"sạch" cho một CI đã đổi còn tệ hơn không có script.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

#: Lệnh CI được phản chiếu, viết Y HỆT dòng `run:` trong ci.yml. `python`/`npm` được đổi sang trình chạy của máy.
CI_COMMANDS: dict[str, str] = {
    "ruff lint": "python -m ruff check .",
    "ruff format": "python -m ruff format --check .",
    "mypy": "python -m mypy",
    "vệ sinh repo": "python scripts/check_structure.py",
    "mục công việc": "python -m tools.agentctl check-work",
    "đặc tả sống": "python -m tools.agentctl spec check",
    "bộ chấm hành vi skill": "python scripts/skill_evals.py --check",
    "lưới canh + công cụ": "python -m pytest tests/guards tests/tools -q",
    "unit test": "python -m pytest tests/unit -q",
    "hợp đồng API": "python scripts/export_openapi.py --check",
    "team-profile": "python scripts/generate_team_docs.py --check",
    "sơ đồ kiến trúc": "python scripts/generate_diagrams.py --check",
    "pack kỹ năng": "python scripts/packs.py --check",
    "DESIGN.md": "python scripts/check_design.py DESIGN.md",
    "lint frontend": "npm run lint",
    "dựng frontend": "npm run build",
    "bức tường env Vercel": "npm run check:env-wall",
}
SLOW = {"dựng frontend"}
WEB_STEPS = {"lint frontend", "dựng frontend", "bức tường env Vercel"}


@dataclass(frozen=True)
class Outcome:
    name: str
    status: str
    seconds: float = 0.0


def _argv(command: str) -> list[str]:
    parts = shlex.split(command)
    if parts[0] == "python":
        return [sys.executable, *parts[1:]]
    if parts[0] == "npm":
        # `npm` trên Windows là `npm.cmd`; subprocess không qua shell sẽ không tìm ra tên trần.
        return [shutil.which("npm") or "npm", *parts[1:]]
    return parts


def _git_clean() -> tuple[bool, str]:
    """CI checkout REPO, không checkout đĩa của bạn: file chưa commit làm máy xanh mà CI đỏ."""
    # `-- .`: chỉ xét thư mục dự án (dự án có thể nằm trong thư mục con của một monorepo).
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", "."], cwd=ROOT, capture_output=True, text=True, check=False
    )
    dirty = [line for line in result.stdout.splitlines() if line.strip()]
    return not dirty, "\n".join(f"    {line}" for line in dirty[:20])


def _record_evidence(command: str) -> None:
    """Ghi dấu vân tay cây đã kiểm đạt. Lỗi ghi (repo lạ, không quyền) không được làm đỏ lượt kiểm."""
    try:
        sys.path.insert(0, str(ROOT))
        from tools.agentctl.evidence import record_pass

        record_pass(ROOT, command)
    except Exception as exc:  # noqa: BLE001 — chỉ là bằng chứng phụ, không phải bước kiểm
        print(f"⚠️  không ghi được bằng chứng cho cổng Stop: {exc}", file=sys.stderr)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Chạy đúng những gì CI chạy.")
    parser.add_argument("--fast", action="store_true", help="bỏ bước chậm (build frontend)")
    args = parser.parse_args()

    env = {**os.environ, "TZ": "UTC", "APP_ENV": "test", "PYTHONIOENCODING": "utf-8"}
    outcomes: list[Outcome] = []
    for name, command in CI_COMMANDS.items():
        if args.fast and name in SLOW:
            outcomes.append(Outcome(name, "BỎ QUA (--fast)"))
            continue
        if name in WEB_STEPS and (shutil.which("npm") is None or not (WEB / "node_modules").is_dir()):
            outcomes.append(Outcome(name, "BỎ QUA (chưa cài web/node_modules)"))
            continue
        print(f"\n───── {name}: {command} ─────", flush=True)
        started = time.monotonic()
        cwd = WEB if name in WEB_STEPS else ROOT
        code = subprocess.run(_argv(command), cwd=cwd, env=env, check=False).returncode
        outcomes.append(Outcome(name, "ĐẠT" if code == 0 else f"ĐỎ (mã {code})", time.monotonic() - started))

    clean, dirty = _git_clean()
    outcomes.append(Outcome("cây git sạch", "ĐẠT" if clean else "ĐỎ"))

    print("\n" + "═" * 64 + "\nTỔNG KẾT — chạy hết rồi mới báo, để thấy MỌI lỗi trong một lượt\n" + "═" * 64)
    for outcome in outcomes:
        timing = f"{outcome.seconds:6.1f}s" if outcome.seconds else "       "
        print(f"  {outcome.status:<36} {timing}  {outcome.name}")
    if not clean:
        print("\nCây làm việc còn thay đổi chưa commit — CI sẽ kiểm một cây KHÁC:\n" + dirty)
    failed = sum(outcome.status.startswith("ĐỎ") for outcome in outcomes)
    code_failed = sum(o.status.startswith("ĐỎ") for o in outcomes if o.name != "cây git sạch")
    if not code_failed:
        # Bằng chứng cho cổng `Stop` (tools/agentctl/evidence.py): mọi bước kiểm mã đạt trên ĐÚNG cây hiện tại.
        _record_evidence("python scripts/ci_local.py" + (" --fast" if args.fast else ""))
    skipped = sum(outcome.status.startswith("BỎ QUA") for outcome in outcomes)
    if skipped:
        print(f"\n⚠️  {skipped} bước bị bỏ qua — CI vẫn chạy chúng.")
    print("\n✅ Sạch, đẩy được." if not failed else f"\n🔴 {failed} bước đỏ. Sửa hết rồi hãy đẩy.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
