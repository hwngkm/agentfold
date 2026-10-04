"""`python -m tools.agentctl` — nạp CLI muộn để báo lỗi môi trường (thiếu PyYAML) bằng mã thoát 3."""

from __future__ import annotations

import sys

from tools.agentctl.errors import AgentctlEnvironmentError


def _run() -> int:
    try:
        from tools.agentctl.cli import main
    except AgentctlEnvironmentError as exc:
        print(f"⚠️  {exc}", file=sys.stderr)
        return exc.exit_code
    return main()


if __name__ == "__main__":
    raise SystemExit(_run())
