"""Kiểm cấu trúc mọi mục công việc trong cây làm việc: ticket, câu hỏi, quyết định, sự cố, nhật ký.

Chạy trong CI (job `guards`) và trong lưới canh `tests/guards/test_work_items.py`. Một ticket hỏng
cú pháp phát hiện ở đây rẻ hơn nhiều so với phát hiện lúc một agent claim nó.
"""

from __future__ import annotations

from pathlib import Path

from tools.agentctl.entries import (
    ASSESSMENT_DECISIONS,
    ASSESSMENT_NEEDS_EVIDENCE,
    BUG_NEEDS_EVIDENCE,
    BUG_VERDICTS,
    HANDOFF_STATUSES,
    PLAN_STATUSES,
    QUESTION_STATUSES,
    WORK_DIR,
)
from tools.agentctl.errors import AgentctlEnvironmentError
from tools.agentctl.policy import Policy
from tools.agentctl.tickets import TICKET_ID, TicketError, merged_ticket_ids, split_front_matter, validate_tickets_dir


def _concluded(
    rel: str, data: dict, field: str, allowed: tuple[str, ...], needs_evidence: tuple[str, ...]
) -> list[str]:
    """Kết luận thuộc tập đóng; kết luận khẳng định thì phải kèm bằng chứng (R00.8: bằng chứng thắng tự khai)."""
    value = data.get(field)
    if value not in allowed:
        return [f"{rel}: `{field}` phải thuộc {allowed}"]
    evidence = data.get("evidence")
    if value in needs_evidence and not (
        isinstance(evidence, list) and any(isinstance(e, str) and e.strip() for e in evidence)
    ):
        return [
            f"{rel}: `{field}: {value}` cần bằng chứng — điền `evidence` (lệnh đã chạy + kết quả, hoặc nguồn đã mở)"
        ]
    return []


def _plan_problems(rel: str, stem: str, data: dict) -> list[str]:
    problems: list[str] = []
    ticket = data.get("ticket")
    if not (isinstance(ticket, str) and TICKET_ID.match(ticket)) or stem != f"PLAN-{ticket}":
        problems.append(f"{rel}: `ticket` phải là mã ticket và tên tệp phải là `PLAN-<ticket>.md`")
    if data.get("status") not in PLAN_STATUSES:
        problems.append(f"{rel}: `status` phải thuộc {PLAN_STATUSES}")
    if data.get("status") == "approved" and not data.get("approved_by"):
        problems.append(f"{rel}: `status: approved` cần `approved_by` (vai trò người duyệt)")
    return problems


def _front_matter_problems(root: Path, folder: str, *, needs_id: bool) -> list[str]:
    problems: list[str] = []
    directory = root / WORK_DIR / folder
    for file in sorted(directory.rglob("*.md")) if directory.is_dir() else []:
        if file.name == "README.md" or file.name.startswith("_"):
            continue
        rel = file.relative_to(root).as_posix()
        try:
            data, _body = split_front_matter(file.read_text(encoding="utf-8"))
        except TicketError as exc:
            problems.append(f"{rel}: {exc}")
            continue
        if needs_id and data.get("id") != file.stem:
            problems.append(f"{rel}: `id` phải trùng tên file (`{file.stem}`)")
        if folder == "questions":
            if data.get("status") not in QUESTION_STATUSES:
                problems.append(f"{rel}: `status` phải thuộc {QUESTION_STATUSES}")
            blocking = data.get("blocking") or []
            if not isinstance(blocking, list) or not all(isinstance(b, str) and TICKET_ID.match(b) for b in blocking):
                problems.append(f"{rel}: `blocking` phải là danh sách mã ticket")
        if folder == "bugs":
            problems += _concluded(rel, data, "verdict", BUG_VERDICTS, BUG_NEEDS_EVIDENCE)
        if folder == "assessments":
            problems += _concluded(rel, data, "decision", ASSESSMENT_DECISIONS, ASSESSMENT_NEEDS_EVIDENCE)
        if folder == "plans":
            problems += _plan_problems(rel, file.stem, data)
        if folder == "handoffs":
            if data.get("status") not in HANDOFF_STATUSES:
                problems.append(f"{rel}: `status` phải thuộc {HANDOFF_STATUSES}")
            ticket = data.get("ticket")
            if ticket is not None and not (isinstance(ticket, str) and TICKET_ID.match(ticket)):
                problems.append(f"{rel}: `ticket` phải là mã ticket hoặc null")
    return problems


def validate_work_items(root: Path, policy: Policy) -> list[str]:
    # Mã ticket đã merge lấy từ lịch sử nhánh GỐC (không phải HEAD: commit của chính ticket đang làm cũng mang mã).
    # Không có git/remote/ref → tập rỗng → không lọc, kiểm đầy đủ.
    try:
        merged = merged_ticket_ids(root, policy.base_ref)
    except AgentctlEnvironmentError:
        merged = set()
    problems = validate_tickets_dir(root, policy, merged)
    problems += _front_matter_problems(root, "questions", needs_id=True)
    problems += _front_matter_problems(root, "decisions", needs_id=True)
    problems += _front_matter_problems(root, "incidents", needs_id=True)
    problems += _front_matter_problems(root, "handoffs", needs_id=True)
    problems += _front_matter_problems(root, "bugs", needs_id=True)
    problems += _front_matter_problems(root, "assessments", needs_id=True)
    problems += _front_matter_problems(root, "plans", needs_id=True)
    problems += _front_matter_problems(root, "log", needs_id=False)
    return problems
