"""Cổng bằng chứng — agent đã đổi tệp thì không dừng phiên khi chưa có lần kiểm nào ĐẠT trên đúng cây đó.

Sự thật dùng để chặn (không phán đoán): **dấu vân tay** của cây làm việc = HEAD + mọi thay đổi chưa commit (kể cả tệp
chưa theo dõi, không tính tệp bị ignore).
- Đầu phiên (`SessionStart`): ghi dấu vân tay ban đầu.
- Mỗi lần `scripts/ci_local.py` có mọi bước kiểm mã ĐẠT: ghi dấu vân tay "đã kiểm".
- Lúc dừng (`Stop`): cây không đổi so với đầu phiên → cho qua; đổi rồi mà khác lần "đã kiểm" → chặn, nói lệnh cần chạy.

Chặn tối đa `MAX_BLOCKS` lần mỗi phiên rồi nhường người (không để agent kẹt vòng lặp); tắt bằng
`git config agentctl.evidenceGate off`. Trạng thái nằm trong thư mục `.git` của worktree — không vào repo.
Ý tưởng mượn từ qkal/Canny. Hiện nối với Claude Code (`SessionStart`, `Stop`); công cụ khác: luật R00.8 + supervisor.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from tools.agentctl.clock import iso, now
from tools.agentctl.gitutil import run_git

MAX_BLOCKS = 3
CHECK_COMMAND = "python scripts/ci_local.py --fast"


def _state_path(repo: Path) -> Path:
    git_dir = run_git(repo, ["rev-parse", "--absolute-git-dir"]).stdout.strip()
    return Path(git_dir) / "agentctl" / "evidence.json"


def _load(repo: Path) -> dict[str, Any]:
    path = _state_path(repo)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save(repo: Path, data: dict[str, Any]) -> None:
    path = _state_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def fingerprint(repo: Path) -> str:
    digest = hashlib.sha256()
    digest.update(run_git(repo, ["rev-parse", "--verify", "--quiet", "HEAD"]).stdout.encode())
    digest.update(run_git(repo, ["diff", "HEAD", "--binary", "--no-ext-diff"]).stdout.encode())
    untracked = run_git(repo, ["ls-files", "--others", "--exclude-standard", "-z"]).stdout.split("\0")
    for rel in sorted(p for p in untracked if p):
        digest.update(rel.encode())
        path = repo / rel
        if path.is_file():
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def record_session_start(repo: Path, session_id: str) -> None:
    data = _load(repo)
    sessions = data.setdefault("sessions", {})
    sessions[session_id] = {"start": fingerprint(repo), "blocks": 0, "at": iso(now())}
    data["sessions"] = dict(list(sessions.items())[-20:])  # giữ gọn: 20 phiên gần nhất
    _save(repo, data)


def record_pass(repo: Path, command: str) -> None:
    data = _load(repo)
    data["last_pass"] = {"fingerprint": fingerprint(repo), "command": command, "at": iso(now())}
    _save(repo, data)


def _gate_off(repo: Path) -> bool:
    return run_git(repo, ["config", "--get", "agentctl.evidenceGate"]).stdout.strip() == "off"


def stop_verdict(repo: Path, session_id: str) -> str | None:
    """`None` = cho dừng; chuỗi = lý do chặn (đã tăng bộ đếm chặn của phiên)."""
    if _gate_off(repo):
        return None
    data = _load(repo)
    session = data.get("sessions", {}).get(session_id)
    current = fingerprint(repo)
    if session is not None and session.get("start") == current:
        return None
    if (data.get("last_pass") or {}).get("fingerprint") == current:
        return None
    session = session or {"start": None, "blocks": 0}
    if session.get("blocks", 0) >= MAX_BLOCKS:
        return None
    session["blocks"] = session.get("blocks", 0) + 1
    data.setdefault("sessions", {})[session_id] = session
    _save(repo, data)
    last = data.get("last_pass")
    since = (
        f" (lần kiểm đạt gần nhất: {last['at']}, trên một cây KHÁC)"
        if last
        else " (phiên này chưa có lần kiểm nào đạt)"
    )
    return (
        f"Cổng bằng chứng: tệp đã đổi nhưng chưa có lần kiểm nào ĐẠT trên đúng cây hiện tại{since}.\n"
        f"   Chạy `{CHECK_COMMAND}` (hoặc `make check-fast`), sửa hết bước đỏ, rồi mới báo xong.\n"
        f"   Không chạy được (thiếu môi trường…)? Nói thẳng trong báo cáo là CHƯA kiểm — đừng báo xong. "
        f"(lần chặn {session['blocks']}/{MAX_BLOCKS})"
    )


def hook_main(argv: Sequence[str] | None = None) -> int:
    """`start` (SessionStart) hoặc `stop` (Stop). Payload JSON qua stdin; hỏng gì cũng cho qua."""
    if os.environ.get("AGENTCTL_HOOKS", "on") == "off":
        return 0
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    args = list(argv if argv is not None else sys.argv[1:])
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        if not isinstance(payload, dict):
            return 0
        repo = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or Path.cwd())
        session_id = str(payload.get("session_id") or "khong-ro")
        if args[:1] == ["start"]:
            record_session_start(repo, session_id)
            return 0
        reason = stop_verdict(repo, session_id)
    except (json.JSONDecodeError, OSError, ValueError):
        return 0
    if reason:
        print(f"🔴 {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(hook_main())
