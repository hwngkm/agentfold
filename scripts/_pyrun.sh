#!/usr/bin/env bash
# Chạy Python cho hook, đa nền tảng. Thứ tự: venv đang bật → .venv của repo → .venv của checkout CHÍNH
# (khi đang ở worktree, venv thường nằm ở checkout chính) → python3 → python → py -3.
# Không tìm thấy Python thì thoát 0 im lặng: hook không bao giờ được làm đứng công cụ AI hay git.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
common="$(git -C "$here" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
main_root=""
[ -n "$common" ] && main_root="$(dirname "$common")"

candidates=()
if [ -n "${VIRTUAL_ENV:-}" ]; then
  candidates+=("$VIRTUAL_ENV/bin/python" "$VIRTUAL_ENV/Scripts/python.exe")
fi
candidates+=("$here/.venv/bin/python" "$here/.venv/Scripts/python.exe")
if [ -n "$main_root" ]; then
  candidates+=("$main_root/.venv/bin/python" "$main_root/.venv/Scripts/python.exe")
fi

for candidate in "${candidates[@]}"; do
  if [ -x "$candidate" ]; then
    exec "$candidate" "$@"
  fi
done

# `python3` trên Windows có thể là cửa hàng ứng dụng giả — thử chạy thật trước khi tin.
for launcher in python3 python; do
  if command -v "$launcher" >/dev/null 2>&1 && "$launcher" -c "import sys" >/dev/null 2>&1; then
    exec "$launcher" "$@"
  fi
done
if command -v py >/dev/null 2>&1 && py -3 -c "import sys" >/dev/null 2>&1; then
  exec py -3 "$@"
fi
exit 0
