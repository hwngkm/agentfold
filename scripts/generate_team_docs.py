"""Sinh `docs/GOVERNANCE.md`, `.github/CODEOWNERS`, và phần `owners:` của `coordination/policy.yaml`
từ `docs/design/team-profile.yaml` — cùng mẫu với `scripts/export_openapi.py`.

    python scripts/generate_team_docs.py                              # sinh lại theo profile hiện có
    python scripts/generate_team_docs.py --check                      # CI: đỏ nếu ba file lệch profile
    python scripts/generate_team_docs.py --team-size small            # đổi team-size, giữ complexity
    python scripts/generate_team_docs.py --team-size solo --complexity strict
    python scripts/generate_team_docs.py --list                       # liệt kê preset có sẵn

Đổi team-size KHÔNG đổi cơ chế `tools/agentctl` — chỉ đổi ai chịu trách nhiệm vùng nào và mức nghi thức
duyệt/ADR. Xem `docs/design/presets/README.md`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.agentctl.errors import AgentctlError  # noqa: E402
from tools.agentctl.policy import POLICY_PATH  # noqa: E402
from tools.agentctl.team_profile import (  # noqa: E402
    COMPLEXITIES,
    TEAM_PROFILE_PATH,
    TEAM_SIZES,
    TeamProfile,
    load_team_profile,
    patch_policy_owners,
    render_codeowners,
    render_governance,
    write_team_profile,
)

GOVERNANCE_PATH = ROOT / "docs" / "GOVERNANCE.md"
CODEOWNERS_PATH = ROOT / ".github" / "CODEOWNERS"
POLICY_FILE = ROOT / POLICY_PATH


def _rendered(profile: TeamProfile) -> dict[Path, str]:
    policy_text = POLICY_FILE.read_text(encoding="utf-8")
    return {
        GOVERNANCE_PATH: render_governance(profile),
        CODEOWNERS_PATH: render_codeowners(profile),
        POLICY_FILE: patch_policy_owners(policy_text, profile),
    }


def _list_presets() -> int:
    print(f"team-size: {', '.join(TEAM_SIZES)}")
    print(f"complexity: {', '.join(COMPLEXITIES)}")
    print("Chi tiết: docs/design/presets/README.md")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="chỉ so, không ghi (dùng trong CI)")
    parser.add_argument("--team-size", choices=TEAM_SIZES, help="đổi team-size trong team-profile.yaml")
    parser.add_argument("--complexity", choices=COMPLEXITIES, help="đổi complexity trong team-profile.yaml")
    parser.add_argument("--list", action="store_true", help="liệt kê preset có sẵn rồi thoát")
    args = parser.parse_args()

    if args.list:
        return _list_presets()
    if args.check and (args.team_size or args.complexity):
        print("🔴 --check không dùng cùng --team-size/--complexity — đổi profile thì bỏ --check.", file=sys.stderr)
        return 2

    try:
        if args.team_size or args.complexity:
            current = load_team_profile(ROOT)
            write_team_profile(ROOT, args.team_size or current.team_size, args.complexity or current.complexity)
            print(f"✅ Đã ghi {TEAM_PROFILE_PATH}")

        profile = load_team_profile(ROOT)
        rendered = _rendered(profile)
    except AgentctlError as exc:
        print(f"🔴 {exc}", file=sys.stderr)
        return 1

    if args.check:
        stale = [
            path
            for path, content in rendered.items()
            if not path.is_file() or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            names = ", ".join(p.relative_to(ROOT).as_posix() for p in stale)
            print(
                f"🔴 Lệch team-profile.yaml: {names}\n   Chạy `python scripts/generate_team_docs.py` rồi commit diff.",
                file=sys.stderr,
            )
            return 1
        print("✅ GOVERNANCE.md, CODEOWNERS, policy.yaml owners khớp team-profile.yaml.")
        return 0

    for path, content in rendered.items():
        path.write_text(content, encoding="utf-8", newline="\n")
    print(f"✅ Đã sinh lại theo team-size=`{profile.team_size}` complexity=`{profile.complexity}`:")
    for path in rendered:
        print(f"   - {path.relative_to(ROOT).as_posix()}")
    print('\n⚠️  docs/GOVERNANCE.md giữ tên người đã điền ở cột "Người" — kiểm lại diff trước khi commit.')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
