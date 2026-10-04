"""Giao diện dòng lệnh của agentctl. Mỗi lệnh in kết quả cho người/agent đọc và trả mã thoát.

Mã thoát: 0 = ổn · 1 = vi phạm/từ chối · 2 = sai cú pháp lệnh · 3 = môi trường thiếu công cụ.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import socket
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from tools.agentctl import mail_cli
from tools.agentctl.board import render_board
from tools.agentctl.claims import Claim, ClaimRegistry
from tools.agentctl.clock import now
from tools.agentctl.commitmsg import check_commit_message
from tools.agentctl.entries import KINDS, create_entry, create_plan, create_ticket
from tools.agentctl.errors import AgentctlError
from tools.agentctl.gitutil import current_branch, diff_changes, project_root, resolve, show_file, staged_changes
from tools.agentctl.handoff import collect_facts
from tools.agentctl.lifecycle import (
    ClaimRequest,
    claim_ticket,
    create_worktree,
    load_context,
    reap_expired,
    release_claim,
    renew_claim,
)
from tools.agentctl.policy import POLICY_PATH, load_policy
from tools.agentctl.prbody import render_pr
from tools.agentctl.prime import fix_environment, render_prime
from tools.agentctl.scope import claim_findings, evaluate, plan_approval_findings, render, ticket_for_branch
from tools.agentctl.spec import archive_delta, repo_problems
from tools.agentctl.tickets import TICKET_ID, load_ticket, ticket_id_from_branch
from tools.agentctl.workcheck import validate_work_items

Handler = Callable[[Path, argparse.Namespace], int]


def _session(explicit: str | None) -> str:
    return explicit or os.environ.get("AGENTCTL_SESSION", "").strip() or socket.gethostname()


def _ticket_arg(repo: Path, explicit: str | None) -> str:
    ticket_id = explicit or ticket_id_from_branch(current_branch(repo))
    if not ticket_id or not TICKET_ID.match(ticket_id):
        raise AgentctlError("không xác định được mã ticket — truyền mã, hoặc chạy trong worktree `feature/<ID>-...`")
    return ticket_id


def _claim_request(repo: Path, args: argparse.Namespace, *, use_current_branch: bool) -> ClaimRequest:
    branch = args.branch
    if branch is None and use_current_branch and ticket_id_from_branch(current_branch(repo)) == args.ticket:
        branch = current_branch(repo)
    return ClaimRequest(
        ticket_id=args.ticket,
        role=args.role,
        session=_session(args.session),
        branch=branch,
        hours=args.hours,
        allow_unmerged_deps=args.allow_unmerged_deps,
    )


def _cmd_start(repo: Path, args: argparse.Namespace) -> int:
    claim, notes = claim_ticket(repo, _claim_request(repo, args, use_current_branch=False), now())
    _policy, base_ref = load_context(repo, fetch=False)
    path, created = create_worktree(repo, claim, base_ref)
    for note in notes:
        print(f"ℹ️  {note}")
    print(f"✅ Đã claim `{claim.ticket}` cho {claim.on_behalf_of} tới {claim.lease_until}")
    print(f"   Worktree {'mới' if created else 'có sẵn'}: {path}  (nhánh `{claim.branch}`)")
    print("   Tiếp theo: cd vào worktree · đọc ticket + design_refs · viết test trước · `make check-fast`")
    return 0


def _cmd_claim(repo: Path, args: argparse.Namespace) -> int:
    claim, notes = claim_ticket(repo, _claim_request(repo, args, use_current_branch=True), now())
    for note in notes:
        print(f"ℹ️  {note}")
    print(f"✅ Đã claim `{claim.ticket}` · nhánh `{claim.branch}` · hạn {claim.lease_until}")
    return 0


def _cmd_renew(repo: Path, args: argparse.Namespace) -> int:
    claim = renew_claim(repo, _ticket_arg(repo, args.ticket), current_branch(repo), args.hours, now())
    print(f"✅ Gia hạn `{claim.ticket}` tới {claim.lease_until}")
    return 0


def _cmd_release(repo: Path, args: argparse.Namespace) -> int:
    if args.override and not args.reason:
        raise AgentctlError("`--override` bắt buộc kèm `--reason` — lý do được ghi vào lịch sử sổ claim")
    claim = release_claim(
        repo, _ticket_arg(repo, args.ticket), current_branch(repo), args.reason if args.override else None
    )
    print(f"✅ Đã release `{claim.ticket}` (từng giữ bởi {claim.on_behalf_of})")
    return 0


def _cmd_reap(repo: Path, _args: argparse.Namespace) -> int:
    reaped = reap_expired(repo, now())
    print("✅ Không có claim hết hạn." if not reaped else "✅ Đã dọn: " + ", ".join(c.ticket for c in reaped))
    return 0


def _cmd_status(repo: Path, args: argparse.Namespace) -> int:
    policy, _base = load_context(repo, fetch=not args.offline)
    registry = ClaimRegistry(repo, policy)
    claims = registry.read(registry.local_tip() if args.offline else registry.fetch())
    moment = now()
    if not claims:
        print("Sổ claim trống.")
    for claim in sorted(claims.values(), key=lambda c: c.ticket):
        state = "HẾT HẠN" if claim.expired(moment) else "còn hạn"
        print(f"{claim.ticket:<10} {state:<8} {claim.on_behalf_of:<4} {claim.lease_until}  {claim.branch}")
    return 0


def _labels(raw: str | None) -> set[str]:
    if not raw:
        return set()
    text = raw.strip()
    if text.startswith("["):
        try:
            return {str(item) for item in json.loads(text)}
        except json.JSONDecodeError as exc:
            raise AgentctlError(f"`--labels` không phải JSON hợp lệ: {exc}") from exc
    return {item.strip() for item in text.split(",") if item.strip()}


def _cmd_check_scope(repo: Path, args: argparse.Namespace) -> int:
    local = args.staged
    local_policy = load_policy(repo, None) if (repo / POLICY_PATH).is_file() else None
    base = args.base or (local_policy.base_ref if local_policy else "origin/main")
    if resolve(repo, base) is None:
        if local:
            print(f"⚠️  không thấy `{base}` — bỏ qua kiểm phạm vi cục bộ (CI vẫn kiểm).", file=sys.stderr)
            return 0
        raise AgentctlError(f"không thấy base `{base}`")
    policy = load_policy(repo, base)
    branch = args.branch or current_branch(repo)
    registry = ClaimRegistry(repo, policy)
    # Cục bộ (pre-commit) không đụng mạng: chỉ đọc sổ đã kéo về lần `start`/`renew` gần nhất.
    offline = args.offline or local
    claims_cache: list[dict[str, Claim]] = []

    def ledger() -> dict[str, Claim]:
        if not claims_cache:
            try:
                claims_cache.append(registry.read(registry.local_tip() if offline else registry.fetch()))
            except AgentctlError:
                claims_cache.append({})  # không đọc được sổ → không gắn ticket, không nới phạm vi
        return claims_cache[0]

    ticket_id = args.ticket or ticket_id_from_branch(branch) or ticket_for_branch(branch, ledger(), now())
    ticket = load_ticket(repo, policy, ticket_id, base) if ticket_id else None
    changes = staged_changes(repo) if local else diff_changes(repo, base, args.head)
    verdict = evaluate(
        changes,
        policy=policy,
        ticket_id=ticket_id,
        ticket=ticket,
        approved=policy.human_approval_label in _labels(args.labels),
    )
    if args.require_claim and ticket_id and not verdict.errors:
        claim_errors, claim_warnings = claim_findings(ledger(), ticket_id, branch, now())
        verdict = dataclasses.replace(
            verdict, errors=verdict.errors + tuple(claim_errors), warnings=verdict.warnings + tuple(claim_warnings)
        )
    if not local and policy.human_approval_label not in _labels(args.labels):
        extra = plan_approval_findings(
            changes,
            lambda path: show_file(repo, args.head, path),
            lambda path: show_file(repo, base, path),
        )
        verdict = dataclasses.replace(verdict, approvals_needed=verdict.approvals_needed + tuple(extra))
    print(render(verdict, label=policy.human_approval_label, local=local))
    if verdict.errors or (verdict.approvals_needed and not local):
        return 1
    return 0


def _cmd_check_work(repo: Path, _args: argparse.Namespace) -> int:
    problems = validate_work_items(repo, load_policy(repo, None))
    if problems:
        print(f"🔴 {len(problems)} mục công việc sai cấu trúc:")
        print("\n".join(f"  - {problem}" for problem in problems))
        return 1
    print("✅ Ticket, câu hỏi, quyết định, sự cố, nhật ký đều đúng cấu trúc.")
    return 0


def _cmd_check_commit_msg(repo: Path, args: argparse.Namespace) -> int:
    message = Path(args.file).read_text(encoding="utf-8", errors="replace")
    problems = check_commit_message(message, ticket_id_from_branch(args.branch or current_branch(repo)))
    if problems:
        print("🔴 Thông điệp commit chưa đạt:\n" + "\n".join(f"  - {p}" for p in problems), file=sys.stderr)
        return 1
    return 0


def _cmd_new(repo: Path, args: argparse.Namespace) -> int:
    if args.kind == "ticket":
        if not args.id or not TICKET_ID.match(args.id):
            raise AgentctlError("`new ticket` cần `--id` dạng `ABC-01`")
        path = create_ticket(
            repo, load_policy(repo, None).tickets_dir, ticket_id=args.id, title=args.title, role=args.role
        )
    elif args.kind == "plan":
        if not args.id or not TICKET_ID.match(args.id):
            raise AgentctlError("`new plan` cần `--id` là mã ticket, dạng `ABC-01`")
        path = create_plan(repo, ticket_id=args.id, title=args.title, role=args.role)
    else:
        path = create_entry(
            repo,
            args.kind,
            title=args.title,
            role=args.role,
            moment=now(),
            blocking=args.blocking,
            answer_by=args.answer_by,
            facts=collect_facts(repo) if args.kind == "handoff" else None,
        )
    print(f"✅ Đã tạo {path.relative_to(repo).as_posix()}")
    return 0


def _cmd_pr_body(repo: Path, args: argparse.Namespace) -> int:
    part = "title" if args.title_only else "body" if args.body_only else "both"
    sys.stdout.write(render_pr(repo, _ticket_arg(repo, args.ticket), part=part))
    return 0


def _cmd_prime(repo: Path, args: argparse.Namespace) -> int:
    agent = (args.as_agent or os.environ.get("AGENTCTL_AGENT", "")).strip() or None
    fixed = fix_environment(repo) if args.fix_env else 0
    print(render_prime(repo, agent=agent, fetch=not args.offline, moment=now()))
    return fixed


def _cmd_spec(repo: Path, args: argparse.Namespace) -> int:
    if args.spec_action == "check":
        problems = repo_problems(repo)
        if problems:
            print(f"🔴 {len(problems)} vấn đề trong đặc tả:")
            print("\n".join(f"  - {p}" for p in problems))
            return 1
        print("✅ Mọi đặc tả và delta chờ gộp đều hợp lệ (SHALL, kịch bản WHEN/THEN, test có thật).")
        return 0
    result = archive_delta(repo, args.delta, today=now().strftime("%Y-%m-%d"))
    print(f"✅ Đã gộp vào {result.spec_path.relative_to(repo).as_posix()} ({result.requirements_after} yêu cầu)")
    print(f"   Delta lưu tại {result.archived_path.relative_to(repo).as_posix()}")
    return 0


def _cmd_board(repo: Path, args: argparse.Namespace) -> int:
    print(render_board(repo, fetch=not args.offline, moment=now()))
    return 0


def _add_claim_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("ticket", help="mã ticket, vd. API-03")
    parser.add_argument("--role", required=True, help="vai trò con người mà agent làm thay, vd. R3")
    parser.add_argument("--session", help="nhãn phiên (mặc định: $AGENTCTL_SESSION hoặc tên máy)")
    parser.add_argument("--branch", help="tên nhánh (mặc định: feature/<ID>-<slug-tiêu-đề>)")
    parser.add_argument("--hours", type=int, help="độ dài lease (mặc định theo policy)")
    parser.add_argument(
        "--allow-unmerged-deps", action="store_true", help="bỏ chặn phụ thuộc chưa merge (cần xác nhận)"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m tools.agentctl", description=__doc__)
    parser.add_argument("--repo", type=Path, help="đường dẫn trong repo cần thao tác (mặc định: thư mục hiện tại)")
    sub = parser.add_subparsers(dest="command", required=True)

    _add_claim_arguments(sub.add_parser("start", help="claim ticket + tạo worktree/nhánh riêng"))
    _add_claim_arguments(sub.add_parser("claim", help="chỉ claim (đã có nhánh)"))
    renew = sub.add_parser("renew", help="gia hạn lease của claim đang giữ")
    renew.add_argument("ticket", nargs="?")
    renew.add_argument("--hours", type=int)
    release = sub.add_parser("release", help="nhả claim sau khi merge hoặc bỏ việc")
    release.add_argument("ticket", nargs="?")
    release.add_argument("--override", action="store_true", help="người điều phối dọn claim của nhánh khác")
    release.add_argument("--reason")
    sub.add_parser("reap", help="dọn mọi claim đã hết hạn")
    status = sub.add_parser("status", help="liệt kê claim")
    status.add_argument("--offline", action="store_true")

    scope = sub.add_parser("check-scope", help="so thay đổi với phạm vi ticket đã duyệt")
    scope.add_argument("--base", help="ref gốc để đọc policy/ticket (mặc định origin/main)")
    scope.add_argument("--head", default="HEAD")
    scope.add_argument("--staged", action="store_true", help="kiểm file đã `git add` (pre-commit)")
    scope.add_argument("--branch", help="tên nhánh nguồn (CI truyền vào)")
    scope.add_argument("--ticket")
    scope.add_argument("--labels", help="nhãn PR: JSON array hoặc chuỗi phân tách bằng dấu phẩy")
    scope.add_argument("--require-claim", action="store_true")
    scope.add_argument("--offline", action="store_true", help="không kéo sổ claim, dùng bản cục bộ")

    sub.add_parser("check-work", help="kiểm cấu trúc ticket/câu hỏi/quyết định/sự cố/nhật ký")
    commit = sub.add_parser("check-commit-msg", help="kiểm thông điệp commit (hook commit-msg)")
    commit.add_argument("file")
    commit.add_argument("--branch")

    new = sub.add_parser("new", help="tạo mục công việc mới thành file riêng")
    new.add_argument("kind", choices=[*KINDS, "ticket", "plan"])
    new.add_argument("--title", required=True)
    new.add_argument("--role", required=True)
    new.add_argument("--id", help="mã ticket (cho `new ticket` và `new plan`)")
    new.add_argument("--blocking", nargs="*", default=[], help="mã ticket bị câu hỏi chặn")
    new.add_argument("--answer-by", default="R1")

    mail_cli.add_parser(sub)
    spec = sub.add_parser("spec", help="đặc tả sống: kiểm yêu cầu/kịch bản/test, gộp delta của một ticket")
    spec_actions = spec.add_subparsers(dest="spec_action", required=True)
    spec_actions.add_parser("check", help="kiểm mọi đặc tả và delta chờ gộp")
    archive = spec_actions.add_parser("archive", help="gộp delta vào đặc tả chung rồi chuyển delta vào archive")
    archive.add_argument("delta", help="tên delta không đuôi, vd. ABC-01-handoff")
    pr_body = sub.add_parser(
        "pr-body",
        help="in tiêu đề + nội dung PR từ ticket và git (không cần gh, MCP hay mạng); dán vào công cụ tạo PR bất kỳ",
    )
    pr_body.add_argument("--ticket", help="mã ticket (mặc định lấy từ tên nhánh)")
    pr_part = pr_body.add_mutually_exclusive_group()
    pr_part.add_argument("--title-only", action="store_true", help="chỉ in tiêu đề")
    pr_part.add_argument("--body-only", action="store_true", help="chỉ in nội dung")
    prime = sub.add_parser("prime", help="bối cảnh đầu phiên trong một lệnh: luật, việc, thư, bàn giao, skill")
    prime.add_argument("--as", dest="as_agent", help="định danh để đọc hộp thư (mặc định $AGENTCTL_AGENT)")
    prime.add_argument("--offline", action="store_true", help="không gọi mạng, dùng bản đã kéo về")
    prime.add_argument(
        "--fix-env",
        action="store_true",
        help="chạy `bash scripts/cloud_setup.sh` để dựng môi trường (chỉ khi người cho phép; mặc định chỉ cảnh báo)",
    )

    board = sub.add_parser("board", help="bảng công việc suy ra từ ticket + claim + lịch sử")
    board.add_argument("--offline", action="store_true")
    return parser


HANDLERS: dict[str, Handler] = {
    "start": _cmd_start,
    "claim": _cmd_claim,
    "renew": _cmd_renew,
    "release": _cmd_release,
    "reap": _cmd_reap,
    "status": _cmd_status,
    "check-scope": _cmd_check_scope,
    "check-work": _cmd_check_work,
    "check-commit-msg": _cmd_check_commit_msg,
    "new": _cmd_new,
    "board": _cmd_board,
    "mail": mail_cli.handle,
    "pr-body": _cmd_pr_body,
    "prime": _cmd_prime,
    "spec": _cmd_spec,
}


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        repo = project_root(args.repo or Path.cwd())
        return HANDLERS[args.command](repo, args)
    except AgentctlError as exc:
        print(f"🔴 {exc}", file=sys.stderr)
        return exc.exit_code
