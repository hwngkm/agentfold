"""Hook cổng bằng chứng — `start` ở SessionStart, `stop` ở Stop. Logic: tools/agentctl/evidence.py."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.agentctl.evidence import hook_main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(hook_main())
