"""AGENT-LOG v1 — hộp thư và nhật ký dùng chung cho người và AI agent của MỌI nhà cung cấp. Đặc tả: docs/AGENT-LOG.md.

Vì sao không phải MCP server hay dịch vụ ngoài
----------------------------------------------
Agent dùng trong một dự án rất khác nhau (Claude Code, Codex, Copilot, Cursor, Antigravity, Gemini CLI…); không phải
công cụ nào cũng nói được MCP, nhưng công cụ nào cũng chạy được `git`. Hộp thư nằm trên một nhánh git mồ côi
(`agent-mail`), ghi bằng cùng cơ chế nguyên tử với sổ claim (`claims.py`): commit trên index tạm + `git push` không
fast-forward bị từ chối ⇒ đọc lại, ghi lại. Không có remote (máy cá nhân, agent không có quyền push) thì ghi vào nhánh
cục bộ bằng `update-ref` có so sánh giá trị cũ — các worktree trên cùng máy vẫn thấy nhau.

Mượn ý từ: mcp_agent_mail (thư Markdown + front matter lưu trong git, thread, `ack_required`) và A2A (trạng thái
yêu cầu `submitted → working → input-required → completed/failed/canceled/rejected`, thẻ agent).

Mọi thứ chỉ THÊM file mới (thư, xác nhận) hoặc nối vào file của chính agent (nhật ký) — hai agent không bao giờ sửa
cùng một file, nên không có xung đột nội dung, chỉ có tranh ghi ref, và CAS lo phần đó.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import secrets
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from tools.agentctl.clock import iso
from tools.agentctl.errors import AgentctlError
from tools.agentctl.gitutil import GitError, git, identity_env, list_files, resolve, run_git

KINDS = ("request", "inform", "question", "answer", "handoff", "review", "status")
STATES = ("submitted", "working", "input-required", "completed", "failed", "canceled", "rejected")
TERMINAL_STATES = ("completed", "failed", "canceled", "rejected")
PRIORITIES = ("low", "normal", "high")
TOOLS = (
    "claude-code",
    "codex",
    "copilot",
    "cursor",
    "antigravity",
    "gemini-cli",
    "aider",
    "windsurf",
    "human",
    "other",
)
AGENT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
_RECIPIENT = re.compile(r"^(all|human|role:R\d+|[a-z0-9][a-z0-9-]{0,39})$")
_MAX_ATTEMPTS = 6
_ZERO = "0" * 40


@dataclass(frozen=True)
class AgentCard:
    """Thẻ agent (ý từ A2A AgentCard): ai, công cụ gì, thay mặt vai trò người nào, làm được gì."""

    id: str
    tool: str
    on_behalf_of: str
    registered_at: str
    model: str = ""
    capabilities: tuple[str, ...] = ("shell", "git")
    note: str = ""

    def to_yaml(self) -> str:
        data = {**asdict(self), "capabilities": list(self.capabilities)}
        return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


@dataclass(frozen=True)
class Message:
    id: str
    thread: str
    sender: str
    to: tuple[str, ...]
    kind: str
    subject: str
    body: str
    created: str
    state: str | None = None
    in_reply_to: str | None = None
    ack_required: bool = False
    priority: str = "normal"
    refs: tuple[str, ...] = field(default_factory=tuple)

    @property
    def path(self) -> str:
        return f"messages/{self.created[:4]}/{self.created[5:7]}/{self.id}.md"

    def render(self) -> str:
        meta = {
            "id": self.id,
            "thread": self.thread,
            "from": self.sender,
            "to": list(self.to),
            "kind": self.kind,
            "state": self.state,
            "in_reply_to": self.in_reply_to,
            "ack_required": self.ack_required,
            "priority": self.priority,
            "refs": list(self.refs),
            "created": self.created,
            "subject": self.subject,
        }
        return "---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + "---\n" + self.body


def _fail(problem: str) -> None:
    raise AgentctlError(f"thư không hợp lệ: {problem}")


def new_message(
    *,
    sender: str,
    to: Sequence[str],
    thread: str,
    kind: str,
    subject: str,
    body: str,
    moment: datetime,
    state: str | None = None,
    in_reply_to: str | None = None,
    ack_required: bool = False,
    priority: str = "normal",
    refs: Sequence[str] = (),
) -> Message:
    """Dựng và KIỂM một thư. Mã thư theo thời điểm + người gửi + số ngẫu nhiên: hai agent không bao giờ tranh mã."""
    if sender != "human" and not AGENT_ID.match(sender):
        _fail(f"định danh người gửi `{sender}` phải dạng chữ-thường-gạch-nối (vd. codex-1), hoặc `human`")
    if not to:
        _fail("cần ít nhất một người nhận (định danh agent, `role:Rn`, `human` hoặc `all`)")
    bad = [r for r in to if not _RECIPIENT.match(r)]
    if bad:
        _fail(f"người nhận không hợp lệ: {bad}")
    if kind not in KINDS:
        _fail(f"`kind` phải thuộc {KINDS}")
    if kind == "request" and state is None:
        state = "submitted"
    if state is not None and state not in STATES:
        _fail(f"`state` phải thuộc {STATES}")
    if kind == "status" and (state is None or not in_reply_to):
        _fail("thư `status` cần `state` và `in_reply_to` (mã yêu cầu đang cập nhật)")
    if priority not in PRIORITIES:
        _fail(f"`priority` phải thuộc {PRIORITIES}")
    if not thread.strip() or not subject.strip():
        _fail("cần `thread` và `subject` không rỗng")
    created = iso(moment)
    stamp = created.replace("-", "").replace(":", "")
    msg_id = f"M-{stamp}-{sender}-{secrets.token_hex(2)}"
    return Message(
        id=msg_id,
        thread=thread.strip(),
        sender=sender,
        to=tuple(to),
        kind=kind,
        subject=subject.strip(),
        body=body if body.endswith("\n") else body + "\n",
        created=created,
        state=state,
        in_reply_to=in_reply_to,
        ack_required=ack_required,
        priority=priority,
        refs=tuple(refs),
    )


def parse_message(text: str, *, source: str) -> Message:
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise AgentctlError(f"{source}: thiếu front matter `---`")
    head, body = text[4:].split("\n---\n", 1)
    try:
        meta = yaml.safe_load(head)
        return Message(
            id=str(meta["id"]),
            thread=str(meta["thread"]),
            sender=str(meta["from"]),
            to=tuple(str(r) for r in meta["to"]),
            kind=str(meta["kind"]),
            subject=str(meta["subject"]),
            body=body,
            created=str(meta["created"]),
            state=meta.get("state"),
            in_reply_to=meta.get("in_reply_to"),
            ack_required=bool(meta.get("ack_required", False)),
            priority=str(meta.get("priority", "normal")),
            refs=tuple(str(r) for r in meta.get("refs") or ()),
        )
    except (yaml.YAMLError, KeyError, TypeError) as exc:
        raise AgentctlError(f"{source}: thư hỏng: {exc}") from exc


class Mailbox:
    """Đọc/ghi hộp thư trên nhánh mồ côi. `mode` = `remote` (có remote) hoặc `local` (chỉ nhánh cục bộ)."""

    def __init__(self, repo: Path, *, remote: str, branch: str, offline: bool = False) -> None:
        self.repo = repo
        self.remote = remote
        self.branch = branch
        self.offline = offline  # chỉ đọc bản đã kéo về — cho hook đầu phiên, không được treo khi mất mạng
        has_remote = run_git(repo, ["remote", "get-url", remote]).returncode == 0
        self.mode = "remote" if has_remote else "local"
        self.ref = f"refs/remotes/{remote}/{branch}" if has_remote else f"refs/heads/{branch}"

    # ---- tầng lưu trữ -------------------------------------------------------------------------------
    def fetch(self) -> str | None:
        if self.mode == "local" or self.offline:
            return resolve(self.repo, self.ref)
        result = run_git(self.repo, ["fetch", "--no-tags", self.remote, f"+refs/heads/{self.branch}:{self.ref}"])
        if result.returncode != 0:
            if "couldn't find remote ref" in result.stderr.lower():
                return None
            raise GitError(f"không kéo được hộp thư `{self.branch}`: {result.stderr.strip()}")
        return resolve(self.repo, self.ref)

    def _commit(self, parent: str | None, changes: Mapping[str, str], message: str) -> str:
        handle, index_file = tempfile.mkstemp(prefix="agentctl-mail-index-")
        os.close(handle)
        os.unlink(index_file)
        env = {"GIT_INDEX_FILE": index_file, **identity_env(self.repo)}
        try:
            git(self.repo, "read-tree", *([parent] if parent else ["--empty"]), env=env)
            for path, content in sorted(changes.items()):
                blob = git(self.repo, "hash-object", "-w", "--stdin", input_text=content).strip()
                git(self.repo, "update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=env)
            tree = git(self.repo, "write-tree", env=env).strip()
            return git(
                self.repo, "commit-tree", tree, *(["-p", parent] if parent else []), "-m", message, env=env
            ).strip()
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(index_file)

    def _publish(self, commit: str, parent: str | None) -> bool:
        if self.mode == "local":
            return run_git(self.repo, ["update-ref", self.ref, commit, parent or _ZERO]).returncode == 0
        result = run_git(self.repo, ["push", "--quiet", self.remote, f"{commit}:refs/heads/{self.branch}"])
        if result.returncode == 0:
            git(self.repo, "update-ref", self.ref, commit)
            return True
        if any(word in result.stderr for word in ("rejected", "fetch first", "non-fast-forward")):
            return False
        raise GitError(f"không đẩy được hộp thư: {result.stderr.strip()}")

    def write(self, build: Callable[[str | None], Mapping[str, str]], message: str) -> None:
        """Đọc đầu nhánh → dựng thay đổi TRÊN đầu nhánh đó → ghi; bị từ chối vì ghi đồng thời thì làm lại từ đầu."""
        for _attempt in range(_MAX_ATTEMPTS):
            tip = self.fetch()
            changes = build(tip)
            if self._publish(self._commit(tip, changes, message), tip):
                return
        raise AgentctlError(f"không ghi được hộp thư sau {_MAX_ATTEMPTS} lần — đang bị ghi liên tục, thử lại sau")

    def _read(self, tip: str | None, path: str) -> str | None:
        if tip is None:
            return None
        result = run_git(self.repo, ["show", f"{tip}:{path}"])
        return result.stdout if result.returncode == 0 else None

    def _files(self, tip: str | None, prefix: str) -> list[str]:
        return list_files(self.repo, tip, prefix, full_tree=True) if tip else []

    # ---- thẻ agent ----------------------------------------------------------------------------------
    def register(self, card: AgentCard) -> None:
        if not AGENT_ID.match(card.id):
            raise AgentctlError(f"định danh agent `{card.id}` phải dạng chữ-thường-gạch-nối, ≤ 40 ký tự")
        if card.tool not in TOOLS:
            raise AgentctlError(f"`tool` phải thuộc {TOOLS}")
        self.write(lambda _tip: {f"agents/{card.id}.yaml": card.to_yaml()}, f"agent: đăng ký {card.id}")

    def cards(self, tip: str | None = None) -> dict[str, dict[str, Any]]:
        tip = tip if tip is not None else self.fetch()
        found: dict[str, dict[str, Any]] = {}
        for path in self._files(tip, "agents/"):
            data = yaml.safe_load(self._read(tip, path) or "") or {}
            if isinstance(data, dict) and data.get("id"):
                found[str(data["id"])] = data
        return found

    # ---- thư ----------------------------------------------------------------------------------------
    def send(self, msg: Message) -> Message:
        self.write(lambda _tip: {msg.path: msg.render()}, f"mail: {msg.sender} → {', '.join(msg.to)} [{msg.thread}]")
        return msg

    def messages(self, tip: str | None = None) -> list[Message]:
        tip = tip if tip is not None else self.fetch()
        found = [
            parse_message(self._read(tip, path) or "", source=path)
            for path in self._files(tip, "messages/")
            if path.endswith(".md")
        ]
        return sorted(found, key=lambda m: (m.created, m.id))

    def acks(self, msg_id: str, tip: str | None = None) -> set[str]:
        tip = tip if tip is not None else self.fetch()
        return {Path(p).stem for p in self._files(tip, f"acks/{msg_id}/")}

    def inbox(self, agent: str) -> list[Message]:
        """Thư gửi tới `agent` (trực tiếp, theo vai trò, `all`, hoặc `human` khi agent là người) mà agent chưa xác nhận."""
        tip = self.fetch()
        role = str(self.cards(tip).get(agent, {}).get("on_behalf_of", ""))
        targets = {agent, "all"} | ({f"role:{role}"} if role else set())
        mine = [m for m in self.messages(tip) if m.sender != agent and targets & set(m.to)]
        acked = {Path(p).parts[1] for p in self._files(tip, "acks/") if Path(p).stem == agent}
        return [m for m in mine if m.id not in acked]

    def ack(self, msg_id: str, agent: str, *, note: str = "", moment: datetime) -> None:
        payload = yaml.safe_dump({"by": agent, "at": iso(moment), "note": note}, allow_unicode=True, sort_keys=False)
        self.write(lambda _tip: {f"acks/{msg_id}/{agent}.yaml": payload}, f"ack: {agent} {msg_id}")

    def thread(self, thread_id: str) -> list[Message]:
        return [m for m in self.messages() if m.thread == thread_id]

    def get(self, msg_id: str) -> Message:
        for msg in self.messages():
            if msg.id == msg_id:
                return msg
        raise AgentctlError(f"không có thư `{msg_id}`")

    def request_state(self, msg_id: str) -> str:
        """Trạng thái của một yêu cầu = `state` của thư trả lời MỚI NHẤT có `in_reply_to` trỏ tới nó (A2A task state)."""
        all_msgs = self.messages()
        request = next((m for m in all_msgs if m.id == msg_id), None)
        if request is None:
            raise AgentctlError(f"không có thư `{msg_id}`")
        updates = [m for m in all_msgs if m.in_reply_to == msg_id and m.state]
        return updates[-1].state if updates else (request.state or "submitted")  # type: ignore[return-value]

    # ---- nhật ký hoạt động --------------------------------------------------------------------------
    def log_event(self, agent: str, event: str, *, moment: datetime, **fields: str) -> None:
        if not AGENT_ID.match(agent) and agent != "human":
            raise AgentctlError(f"định danh agent `{agent}` không hợp lệ")
        stamp = iso(moment)
        path = f"log/{stamp[:4]}/{stamp[5:7]}/{stamp[8:10]}/{agent}.jsonl"
        line = json.dumps({"ts": stamp, "agent": agent, "event": event, **fields}, ensure_ascii=False) + "\n"
        self.write(lambda tip: {path: (self._read(tip, path) or "") + line}, f"log: {agent} {event}")

    def events(self, *, agent: str | None = None) -> list[dict[str, Any]]:
        tip = self.fetch()
        rows: list[dict[str, Any]] = []
        for path in self._files(tip, "log/"):
            if agent and Path(path).stem != agent:
                continue
            rows += [json.loads(line) for line in (self._read(tip, path) or "").splitlines() if line.strip()]
        return sorted(rows, key=lambda r: (r.get("ts", ""), r.get("agent", "")))
