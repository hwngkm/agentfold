"""Lệnh `python -m tools.agentctl mail ...` — giao diện dòng lệnh của AGENT-LOG (docs/AGENT-LOG.md).

Định danh của phiên: `--as <id>` hoặc biến `AGENTCTL_AGENT`. Mọi lệnh in dạng người đọc; thêm `--json` cho máy đọc.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from pathlib import Path

from tools.agentctl.clock import iso, now
from tools.agentctl.errors import AgentctlError
from tools.agentctl.mail import (
    KINDS,
    PRIORITIES,
    STATES,
    TERMINAL_STATES,
    TOOLS,
    AgentCard,
    Mailbox,
    Message,
    new_message,
)
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
    elif action == "assign":
        _assign(repo, box, args)
    elif action == "reply":
        _reply(box, args)
    elif action == "pending":
        _pending(box, args.to)
    return 0


def _assign(repo: Path, box: Mailbox, args: argparse.Namespace) -> None:
    """Giao một ticket ĐÃ DUYỆT cho một agent trong đội: thư `request` tự đủ bối cảnh, cần xác nhận."""
    from tools.agentctl.lifecycle import load_context
    from tools.agentctl.team import assignment_body, load_team
    from tools.agentctl.tickets import load_ticket, ticket_path

    sender = _me(args)
    policy, base_ref = load_context(repo, fetch=True)
    ticket = load_ticket(repo, policy, args.ticket, base_ref)
    if ticket is None:
        raise AgentctlError(f"ticket `{args.ticket}` không có trên `{base_ref}` — chỉ giao việc đã được người duyệt")
    if ticket.state != "ready":
        raise AgentctlError(
            f"`{ticket.id}` đang `{ticket.state}` trên `{base_ref}` — chỉ giao ticket `ready`; đặt `ready` là việc của người"
        )
    team = load_team(repo, base_ref)
    role = args.role or ticket.owner_role
    if team is not None:
        member = team.member(args.to)
        role = args.role or member.on_behalf_of
        if sender != "human" and team.member(sender).rank != "coordinator":
            raise AgentctlError(
                f"`{sender}` không phải điều phối viên (`{team.coordinator.id}`) — nhờ việc thì dùng `mail send --kind request`"
            )
    path = ticket_path(policy, ticket.id)
    msg = new_message(
        sender=sender,
        to=[args.to],
        thread=ticket.id,
        kind="request",
        subject=f"Giao {ticket.id}: {ticket.title}",
        body=".",
        moment=now(),
        ack_required=True,
        priority=args.priority,
        refs=[path],
    )
    body = assignment_body(
        team,
        ticket,
        ticket_file=path,
        sender=sender,
        recipient=args.to,
        msg_id=msg.id,
        role=role,
        note=args.note or "",
    )
    box.send(replace(msg, body=body))
    print(f"✅ Đã giao {ticket.id} cho `{args.to}`: {msg.id} [{box.mode}]")
    if team is not None and team.members[args.to].wake:
        print(f"   Đánh thức: {team.members[args.to].wake}")


def _reply(box: Mailbox, args: argparse.Namespace) -> None:
    """Trả lời đúng người gửi, đúng thread; cập nhật trạng thái yêu cầu; kết thúc thì tự xác nhận thư gốc."""
    me = _me(args)
    original = box.get(args.id)
    updates = [m for m in box.messages() if m.in_reply_to == original.id]
    moment = now()
    if updates and updates[-1].created >= iso(moment):
        # Hai cập nhật cùng một giây thì thứ tự không xác định — trạng thái phải theo đúng thứ tự gửi.
        moment = datetime.fromisoformat(updates[-1].created.replace("Z", "+00:00")) + timedelta(seconds=1)
    msg = new_message(
        sender=me,
        to=[original.sender],
        thread=original.thread,
        kind="status" if args.state else "answer",
        subject=args.subject or (f"{original.thread}: {args.state}" if args.state else f"Re: {original.subject}"),
        body=_body(args),
        moment=moment,
        state=args.state,
        in_reply_to=original.id,
        ack_required=args.ack,
        refs=args.ref,
    )
    box.send(msg)
    print(f"✅ Đã trả lời {original.id} → `{original.sender}`" + (f" [{args.state}]" if args.state else ""))
    if args.state in TERMINAL_STATES or (not args.state and original.kind != "request"):
        box.ack(original.id, me, note=f"trả lời bằng {msg.id}", moment=moment)


def _pending(box: Mailbox, recipient: str | None) -> None:
    """Yêu cầu chưa kết thúc — ai đang chờ ai. Cho điều phối viên và người, ở mọi công cụ."""
    rows = []
    for msg in box.messages():
        if msg.kind != "request" or (recipient and recipient not in msg.to):
            continue
        state = box.request_state(msg.id)
        if state not in TERMINAL_STATES:
            rows.append(
                f"{msg.created}  {msg.id}  {msg.sender} → {', '.join(msg.to)}  [{state}] ({msg.thread})\n    {msg.subject}"
            )
    print("\n".join(rows) if rows else "✅ Không có yêu cầu nào đang chờ.")


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
    assign = with_me(actions.add_parser("assign", help="điều phối viên giao một ticket `ready` cho agent trong đội"))
    assign.add_argument("ticket")
    assign.add_argument("--to", required=True, help="định danh agent nhận việc (coordination/team.yaml)")
    assign.add_argument("--role", help="vai trò người mà agent làm thay (mặc định theo sổ đội)")
    assign.add_argument("--note", help="ghi chú thêm của người giao")
    assign.add_argument("--priority", default="normal", choices=PRIORITIES)
    reply = with_me(actions.add_parser("reply", help="trả lời một thư: đúng người gửi, đúng thread"))
    reply.add_argument("id")
    reply.add_argument("--state", choices=STATES, help="cập nhật trạng thái yêu cầu (working, completed, …)")
    reply.add_argument("--subject")
    reply.add_argument("--body")
    reply.add_argument("--body-file", help="đường dẫn tệp, hoặc `-` để đọc stdin")
    reply.add_argument("--ack", action="store_true", help="người nhận phải xác nhận")
    reply.add_argument("--ref", nargs="*", default=[], help="commit, file liên quan")
    pending = actions.add_parser("pending", help="yêu cầu chưa kết thúc: ai đang chờ ai")
    pending.add_argument("--to", help="chỉ yêu cầu gửi tới agent này")
    watch = with_me(actions.add_parser("watch", help="theo dõi thư mới (hỏi định kỳ)"))
    watch.add_argument("--interval", type=int, default=60, help="giây giữa hai lần hỏi (tối thiểu 15)")
    watch.add_argument("--once", action="store_true")
