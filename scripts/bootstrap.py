"""Khởi tạo dự án mới từ template: đổi tên dự án, rồi in danh sách việc NGƯỜI phải tự làm.

Mặc định CHẠY THỬ (chỉ in file sẽ đổi). Ghi thật thêm `--apply`.

    python scripts/bootstrap.py --name "Tên Dự Án" --slug ten-du-an
    python scripts/bootstrap.py --name "Tên Dự Án" --slug ten-du-an --apply
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TEMPLATE_NAME = "Agentfold"
TEMPLATE_SLUG = "agentfold"
SKIP_DIRS = {".git", ".venv", "node_modules", ".next", ".worktrees", "__pycache__", ".mypy_cache", ".ruff_cache"}
TEXT_SUFFIXES = {".md", ".py", ".toml", ".yaml", ".yml", ".json", ".ts", ".tsx", ".mjs", ".txt", ".ini", ".example", ""}
_SLUG = re.compile(r"^[a-z][a-z0-9-]{2,40}$")
# Lệnh cài skill/plugin trỏ tới TEMPLATE (repo đã có); đổi sang slug mới thành repo chưa tồn tại.
_INSTALL_LINE = re.compile(r"^\s*(npx skills add |/plugin )")
# Handle chủ template không được theo sang dự án mới: CODEOWNERS sẽ bắt người lạ duyệt.
_HANDLES_BLOCK = re.compile(r"(?m)^github_handles:[^\n]*\n?(?:[ \t]+[^\n]*\n?)*")
NO_HANDLES = 'github_handles: {}  # khai handle của dự án, vd. R1: "@tai-khoan", rồi chạy generate_team_docs.py\n'
PROFILE = Path("docs/design/team-profile.yaml")
CODEOWNERS = Path(".github/CODEOWNERS")

MANUAL_STEPS = """
Việc NGƯỜI phải làm sau khi khởi tạo (agent không làm thay được):
  1. Chọn hình dạng đội: `python scripts/generate_team_docs.py --team-size <solo|small|standard|large>
     --complexity <lite|standard|strict>` — sinh docs/GOVERNANCE.md + .github/CODEOWNERS + chủ vùng bảo
     vệ. Xem lựa chọn: docs/design/presets/README.md. Bỏ qua bước này = giữ mặc định standard/standard.
  2. Chọn loại dự án và pack kỹ năng: `python scripts/packs.py --set-type <crud-web-app|api-service|
     llm-app|ai-product|ml-training|data-pipeline|research|prototype>` rồi `--list` để xem pack gợi ý, `--install <pack>` để
     bật. Skill lõi luôn có sẵn; pack chỉ bật cái dự án thật dùng — mô tả mọi skill đều tốn ngữ cảnh ở
     MỌI phiên của MỌI agent. Chi tiết: packs/README.md.
  3. docs/GOVERNANCE.md — điền người thật vào cột "Người"; quyết "Ghi công cụ AI: có/không".
  4. .github/CODEOWNERS — bootstrap đã gỡ handle của chủ template về handle giữ chỗ (@rN-...). Khai tài
     khoản thật ở `github_handles` trong docs/design/team-profile.yaml rồi chạy generate_team_docs.py;
     agent dùng tài khoản KHÔNG có trong đó.
  5. docs/design/PRD.md và docs/design/invariants.yaml — phạm vi, không-mục-tiêu, bất biến miền (+ lưới canh).
  6. Tạo repo trên git host; bật branch protection cho `main` (require PR, require status checks,
     require review from Code Owners — số approval theo GOVERNANCE.md §3); KHÔNG bảo vệ nhánh `agent-claims`.
     ⚠️ Repo PRIVATE trên GitHub Free: branch protection và rulesets trả 403 — GitHub sẽ không chặn gì. Chọn:
     nâng gói · chuyển public · hoặc chấp nhận và ghi "CI xanh mới merge" thành kỷ luật trong GOVERNANCE.md.
     Kiểm ngay: `gh api repos/<chủ>/<repo>/branches/main/protection` (403 = không có bảo vệ).
  7. Mỗi bản clone: `make setup` (hoặc `git config core.hooksPath scripts/githooks`).
  8. Render: tạo từ render.yaml, đặt biến `sync: false`, bật "After CI Checks Pass".
  9. Vercel: Root Directory = web, đặt NEXT_PUBLIC_API_BASE_URL cho cả 3 môi trường,
     Deployment Checks chọn đủ job của ci.yml.
 10. Xoá ticket mẫu docs/work/tickets/EXM-01.md và miền mẫu src/domain/catalog khi có miền thật.
 11. Commit đầu tiên, rồi chạy `python scripts/ci_local.py` để xác nhận mọi thứ xanh.
"""


def _files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and not SKIP_DIRS.intersection(path.relative_to(ROOT).parts)
        and (path.suffix in TEXT_SUFFIXES or path.name in {"Dockerfile", "Makefile", "CODEOWNERS"})
        and path.resolve() != Path(__file__).resolve()
    ]


def _rename(text: str, name: str, slug: str) -> str:
    return "".join(
        line if _INSTALL_LINE.match(line) else line.replace(TEMPLATE_NAME, name).replace(TEMPLATE_SLUG, slug)
        for line in text.splitlines(keepends=True)
    )


def _reset_handles(apply: bool) -> list[str]:
    """Gỡ `github_handles` khỏi profile và sinh lại CODEOWNERS bằng handle giữ chỗ."""
    profile_path = ROOT / PROFILE
    if not profile_path.is_file():
        return []
    text = profile_path.read_text(encoding="utf-8")
    updated = _HANDLES_BLOCK.sub(NO_HANDLES, text, count=1)
    if updated == text:
        return []
    changed = [PROFILE.as_posix(), CODEOWNERS.as_posix()]
    if apply:
        from tools.agentctl.team_profile import load_team_profile, render_codeowners

        profile_path.write_text(updated, encoding="utf-8", newline="\n")
        codeowners = render_codeowners(load_team_profile(ROOT))
        (ROOT / CODEOWNERS).write_text(codeowners, encoding="utf-8", newline="\n")
    return changed


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True, help="tên hiển thị của dự án")
    parser.add_argument("--slug", required=True, help="tên máy: chữ thường, số, gạch nối")
    parser.add_argument("--apply", action="store_true", help="ghi thật (mặc định chỉ chạy thử)")
    args = parser.parse_args()
    if not _SLUG.match(args.slug):
        print("🔴 --slug phải khớp ^[a-z][a-z0-9-]{2,40}$", file=sys.stderr)
        return 2

    changed: list[str] = []
    for path in _files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        updated = _rename(text, args.name, args.slug)
        if updated != text:
            changed.append(path.relative_to(ROOT).as_posix())
            if args.apply:
                path.write_text(updated, encoding="utf-8", newline="\n")

    for rel in _reset_handles(args.apply):
        if rel not in changed:
            changed.append(rel)

    verb = "Đã đổi" if args.apply else "Sẽ đổi (chạy thử — thêm --apply để ghi)"
    print(f"{verb} {len(changed)} file:")
    print("\n".join(f"  - {rel}" for rel in changed))
    if args.apply:
        print("\nSau khi đổi tên: `python scripts/export_openapi.py` (tiêu đề API nằm trong hợp đồng).")
    print(MANUAL_STEPS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
