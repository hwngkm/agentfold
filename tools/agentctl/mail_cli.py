"""Lệnh `python -m tools.agentctl mail ...` — giao diện dòng lệnh của AGENT-LOG (docs/AGENT-LOG.md).

Định danh của phiên: `--as <id>` hoặc biến `AGENTCTL_AGENT`. Mọi lệnh in dạng người đọc; thêm `--json` cho máy đọc.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

from tools.agentctl.clock import iso, now
from tools.agentctl.errors import AgentctlError
from tools.agentctl.mail import KINDS, PRIORITIES, STATES, TOOLS, AgentCard, Mailbox, Message, new_message
from tools.agentctl.policy import POLICY_PATH, load_policy


def mailbox(repo: Path, *, offline: bool = False) -> Mailbox:
    policy = load_policy(repo, None) if (repo / POLICY_PATH).is_file() else None
    remote = policy.remote if policy else "origin"
    branch = policy.mail_branch if policy else "agent-mail"
    return Mailbox(repo, remote=remote, branch=branch, offline=offline)


def _me(args: argparse.Namespace) -> str:
    agent = (getattr(args, "as_agent", None) or os.environ.get("AGENTCTL_AGENT", "")).strip()
    if not agent:
        raise AgentctlError("cần định danh: `--as <id>` hoặc đặt biến AGENTCTL_AGENT (vd. codex-1, human)")
    return agent


def _line(msg: Message) -> str:
    state = f" [{msg.state}]" if msg.state else ""
    ack = " ✋cần xác nhận" if msg.ack_required else ""
    return f"{msg.created}  {msg.id}  {msg.sender} → {', '.join(msg.to)}  ({msg.kind}{state}, {msg.thread}){ack}\n    {msg.subject}"


def _print_messages(msgs: list[Message], as_json: bool, empty: str) -> None:
    if as_json:
        print(json.dumps([asdict(m) for m in msgs], ensure_ascii=False, indent=2))
    else:
        print("\n".join(_line(m) for m in msgs) if msgs else empty)


def _body(args: argparse.Namespace) -> str:
    if args.body_file == "-":
        return sys.stdin.read()
    if args.body_file:
        return Path(args.body_file).read_text(encoding="utf-8")
    return args.body or ""


def handle(repo: Path, args: argparse.Namespace) -> int:
    box = mailbox(repo)
    action = args.mail_action
    if action == "register":
        card = AgentCard(
            id=_me(args),
            tool=args.tool,
            on_behalf_of=args.role,
            registered_at=iso(now()),
            model=args.model or "",
            note=args.note or "",
        )
        box.register(card)
        print(
            f"✅ Đã đăng ký `{card.id}` ({card.tool}, thay mặt {card.on_behalf_of}) trên nhánh `{box.branch}` [{box.mode}]"
        )
    elif action == "send":
        msg = new_message(
            sender=_me(args),
            to=args.to,
            thread=args.thread,
            kind=args.kind,
            subject=args.subject,
            body=_body(args),
            moment=now(),
            state=args.state,
            in_reply_to=args.reply_to,
            ack_required=args.ack,
            priority=args.priority,
            refs=args.ref,
        )
        box.send(msg)
        print(f"✅ Đã gửi {msg.id} [{box.mode}]")
    elif action == "inbox":
        _print_messages(box.inbox(_me(args)), args.json, "📭 Không có thư mới.")
    elif action == "read":
        msg = box.get(args.id)
        print(json.dumps(asdict(msg), ensure_ascii=False, indent=2) if args.json else _line(msg) + "\n\n" + msg.body)
    elif action == "ack":
        box.ack(args.id, _me(args), note=args.note or "", moment=now())
        print(f"✅ `{_me(args)}` đã xác nhận {args.id}")
    elif action == "thread":
        _print_messages(box.thread(args.thread), args.json, "(thread trống)")
    elif action == "state":
        print(box.request_state(args.id))
    elif action == "log":
        fields = {k: v for k, v in {"ticket": args.ticket, "detail": args.detail}.items() if v}
        box.log_event(_me(args), args.event, moment=now(), **fields)
        print(f"✅ Ghi nhật ký `{args.event}`")
    elif action == "events":
        rows = box.events(agent=args.agent)
        print(
            json.dumps(rows, ensure_ascii=False, indent=2)
            if args.json
            else "\n".join(
                f"{r['ts']}  {r['agent']:<14} {r['event']:<14} {r.get('ticket', '')} {r.get('detail', '')}"
                for r in rows
            )
            or "(chưa có nhật ký)"
        )
    elif action == "watch":
        return _watch(box, _me(args), args.interval, args.once)
    return 0


def _watch(box: Mailbox, agent: str, interval: int, once: bool) -> int:
    """Hỏi hộp thư định kỳ, in thư MỚI. Cho người (một cửa sổ terminal) hoặc agent có thể chạy lệnh nền."""
    seen: set[str] = set()
    while True:
        fresh = [m for m in box.inbox(agent) if m.id not in seen]
        for msg in fresh:
            print(_line(msg), flush=True)
            seen.add(msg.id)
        if once:
            return 0
        time.sleep(max(interval, 15))


def add_parser(sub: argparse._SubParsersAction) -> None:
    mail = sub.add_parser("mail", help="AGENT-LOG: hộp thư + nhật ký dùng chung cho người và agent (docs/AGENT-LOG.md)")
    actions = mail.add_subparsers(dest="mail_action", required=True)

    def with_me(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument("--as", dest="as_agent", help="định danh của bạn (mặc định $AGENTCTL_AGENT)")
        return parser

    reg = with_me(actions.add_parser("register", help="đăng ký thẻ agent"))
    reg.add_argument("--tool", required=True, choices=TOOLS)
    reg.add_argument("--role", required=True, help="vai trò người mà agent làm thay, vd. R3")
    reg.add_argument("--model")
    reg.add_argument("--note")

    send = with_me(actions.add_parser("send", help="gửi thư"))
    send.add_argument("--to", nargs="+", required=True, help="định danh agent, role:Rn, human, all")
    send.add_argument("--thread", required=True, help="mã ticket hoặc chủ đề, vd. API-02")
    send.add_argument("--kind", required=True, choices=KINDS)
    send.add_argument("--subject", required=True)
    send.add_argument("--body")
    send.add_argument("--body-file", help="đường dẫn tệp, hoặc `-` để đọc stdin")
    send.add_argument("--state", choices=STATES)
    send.add_argument("--reply-to")
    send.add_argument("--ack", action="store_true", help="người nhận phải xác nhận")
    send.add_argument("--priority", default="normal", choices=PRIORITIES)
    send.add_argument("--ref", nargs="*", default=[], help="commit, file, ticket liên quan")

    inbox = with_me(actions.add_parser("inbox", help="thư gửi tới bạn chưa xác nhận"))
    inbox.add_argument("--json", action="store_true")
    read = actions.add_parser("read", help="đọc một thư")
    read.add_argument("id")
    read.add_argument("--json", action="store_true")
    ack = with_me(actions.add_parser("ack", help="xác nhận đã xử lý một thư"))
    ack.add_argument("id")
    ack.add_argument("--note")
    thread = actions.add_parser("thread", help="mọi thư của một thread")
    thread.add_argument("thread")
    thread.add_argument("--json", action="store_true")
    state = actions.add_parser("state", help="trạng thái hiện tại của một yêu cầu")
    state.add_argument("id")
    log = with_me(actions.add_parser("log", help="ghi một sự kiện vào nhật ký hoạt động"))
    log.add_argument("--event", required=True, help="vd. session_start, test_run, commit, blocked, session_end")
    log.add_argument("--ticket")
    log.add_argument("--detail")
    events = actions.add_parser("events", help="đọc nhật ký hoạt động")
    events.add_argument("--agent")
    events.add_argument("--json", action="store_true")
    watch = with_me(actions.add_parser("watch", help="theo dõi thư mới (hỏi định kỳ)"))
    watch.add_argument("--interval", type=int, default=60, help="giây giữa hai lần hỏi (tối thiểu 15)")
    watch.add_argument("--once", action="store_true")
