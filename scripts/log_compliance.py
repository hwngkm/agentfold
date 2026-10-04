"""Đếm tuân thủ nhật ký/bàn giao trên lịch sử git đã merge. CHỈ ĐỌC git: không mạng, không ghi gì.

Ticket "đã merge" = có commit merge kiểu `Merge pull request #N from <owner>/<nhánh>` (hoặc `Merge branch '<nhánh>'`)
mà tên nhánh chứa mã ticket. Với mỗi ticket:
  - in_branch: các commit của nhánh đã merge (P1..P2) có THÊM tệp trong docs/work/log/ hoặc docs/work/handoffs/;
  - anywhere: in_branch, hoặc có commit nào trong lịch sử có mã ticket ở tiêu đề mà thêm tệp ở hai thư mục đó
    (nhật ký nằm ở PR "docs" riêng).
Ghép theo mã ticket, không theo PR. Tách agent/người theo mẫu tác giả (`--agent-author`, regex) nếu người dùng cung cấp.

Dùng: python scripts/log_compliance.py [--repo .] [--ref HEAD] [--agent-author REGEX]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LOG_DIRS = ("docs/work/log/", "docs/work/handoffs/")
TICKET_RE = re.compile(r"\b[A-Z][A-Z0-9]*-\d+\b")
MERGE_RE = re.compile(r"^Merge (?:pull request #\d+ from \S+?/(?P<pr>\S+)|branch '(?P<br>[^']+)')")
SEP = "\x1f"


@dataclass
class TicketRow:
    ticket: str
    prs: int = 0
    in_branch: bool = False
    anywhere: bool = False
    by: str = "khong-ro"


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, encoding="utf-8")
    return out.stdout


def _is_log(path: str) -> bool:
    return path.startswith(LOG_DIRS)


def _merges(repo: Path, ref: str) -> list[tuple[str, str, str]]:
    """(P1, P2, mã ticket-từ-nhánh) cho từng merge PR."""
    found: list[tuple[str, str, str]] = []
    text = _git(repo, "log", "--merges", f"--format=%P{SEP}%s", ref)
    for line in text.splitlines():
        parents, _, subject = line.partition(SEP)
        match = MERGE_RE.match(subject)
        ps = parents.split()
        if not match or len(ps) < 2:
            continue
        for ticket in dict.fromkeys(TICKET_RE.findall(match.group("pr") or match.group("br"))):
            found.append((ps[0], ps[1], ticket))
    return found


def _added_in_range(repo: Path, rng: str) -> set[str]:
    out = _git(repo, "log", "--diff-filter=A", "--name-only", "--format=", rng, "--", *LOG_DIRS)
    return {line for line in out.splitlines() if line and _is_log(line)}


def _log_commits_by_subject(repo: Path, ref: str) -> set[str]:
    """Mã ticket nằm ở tiêu đề của commit có thêm tệp nhật ký/bàn giao."""
    out = _git(repo, "log", "--diff-filter=A", "--name-only", "--format=%x1e%s", ref, "--", *LOG_DIRS)
    tickets: set[str] = set()
    for chunk in out.split("\x1e"):
        if not chunk.strip():
            continue
        subject, _, files = chunk.partition("\n")
        if any(_is_log(f) for f in files.split()):
            tickets.update(TICKET_RE.findall(subject))
    return tickets


def collect(repo: Path, ref: str = "HEAD", agent_author: str | None = None) -> list[TicketRow]:
    rows: dict[str, TicketRow] = {}
    pattern = re.compile(agent_author) if agent_author else None
    by_subject = _log_commits_by_subject(repo, ref)
    agent_seen: dict[str, bool] = {}
    for p1, p2, ticket in _merges(repo, ref):
        row = rows.setdefault(ticket, TicketRow(ticket))
        row.prs += 1
        rng = f"{p1}..{p2}"
        if _added_in_range(repo, rng):
            row.in_branch = True
        if pattern:
            authors = _git(repo, "log", "--format=%an <%ae>", rng).splitlines()
            agent_seen[ticket] = agent_seen.get(ticket, False) or any(pattern.search(a) for a in authors)
    for ticket, row in rows.items():
        row.anywhere = row.in_branch or ticket in by_subject
        if pattern:
            row.by = "agent" if agent_seen.get(ticket) else "nguoi"
    return sorted(rows.values(), key=lambda r: r.ticket)


def _rate(num: int, den: int) -> float | None:
    return num / den if den else None


def summarize(rows: list[TicketRow]) -> dict[str, Any]:
    total = len(rows)
    in_branch = sum(r.in_branch for r in rows)
    anywhere = sum(r.anywhere for r in rows)
    out: dict[str, Any] = {
        "total": total,
        "in_branch": in_branch,
        "anywhere": anywhere,
        "rate_in_branch": _rate(in_branch, total),
        "rate_anywhere": _rate(anywhere, total),
    }
    for who in ("agent", "nguoi", "khong-ro"):
        sub = [r for r in rows if r.by == who]
        out[who] = {
            "total": len(sub),
            "in_branch": sum(r.in_branch for r in sub),
            "anywhere": sum(r.anywhere for r in sub),
        }
    return out


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def render(rows: list[TicketRow]) -> str:
    lines = ["| Ticket | PR | Nhật ký trong nhánh | Nhật ký ở đâu đó | Làm bởi |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r.ticket} | {r.prs} | {'có' if r.in_branch else 'không'} | {'có' if r.anywhere else 'không'} | {r.by} |"
        )
    s = summarize(rows)
    lines += [
        "",
        f"Cỡ mẫu: {s['total']} ticket đã merge.",
        f"Tuân thủ trong nhánh: {s['in_branch']}/{s['total']} ({_pct(s['rate_in_branch'])})",
        f"Tuân thủ tính cả PR docs riêng: {s['anywhere']}/{s['total']} ({_pct(s['rate_anywhere'])})",
    ]
    for who in ("agent", "nguoi"):
        sub = s[who]
        if sub["total"]:
            lines.append(
                f"  {who}: trong nhánh {sub['in_branch']}/{sub['total']}, tính cả PR docs {sub['anywhere']}/{sub['total']}"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--agent-author", default=None, help="regex khớp 'tên <email>' của tác giả agent")
    args = ap.parse_args(argv)
    rows = collect(Path(args.repo), args.ref, args.agent_author)
    print(render(rows) if rows else "Không có ticket đã merge nào trong lịch sử.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
