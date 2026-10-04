"""Benchmark có/không template — PHẦN BỘ CHẤM và ƯỚC TÍNH CHI PHÍ. Chạy agent thật tốn hạn mức nên mặc định bị chặn.

    python scripts/template_benchmark.py --list
    python scripts/template_benchmark.py --check                       # CI, miễn phí: oracle đạt, null trượt, MỖI nhánh
    python scripts/template_benchmark.py --plan-runs --agents 2 --n 10  # số lượt = agent × nhánh × n
    python scripts/template_benchmark.py --run --confirm-spend --agent-cmd 'claude -p --output-format json "$(cat {prompt_file})"' \\
        --agent-name claude --repeat 1                                  # TỐN hạn mức; in chi phí đo được mỗi lượt

    # agent tối giản qua OpenRouter (mô hình rẻ); khoá CHỈ từ biến môi trường OPENROUTER_API_KEY; có trần chi phí mỗi lượt và tổng
    python scripts/template_benchmark.py --run --confirm-spend --openrouter-model deepseek/deepseek-v4.1-flash \\
        --repeat 10 --max-usd 0.25 --max-total-usd 2 --results kq.jsonl
    python scripts/template_benchmark.py --summarize kq.jsonl           # bảng đạt/n + khoảng tin cậy theo agent × nhánh

Nhiệm vụ nằm trong evals/benchmarks/*.yaml, ba nhánh: `template` (repo tạm có AGENTS.md + ticket khai phạm vi), `plain` (cùng mã, cùng
lời nhắc, không bộ khung) và `prompt-rules` (như plain nhưng luật nêu NGAY TRONG lời nhắc). Ba số đo chấm tự động bằng TRẠNG THÁI CUỐI: CI xanh lần đầu (test của agent + bộ kiểm nghiệm giấu), số vi phạm
phạm vi (tệp đổi/mới ngoài `allow`), bàn giao thành công (HANDOFF.md đủ hai mục). Thời gian người duyệt KHÔNG đo tự động được — ghi tay.
Dùng lại bộ chấm và repo tạm của scripts/skill_evals.py.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import skill_evals as se  # noqa: E402

BENCH_DIR = "evals/benchmarks"
MIN_RELIABLE_N = 20
_PYTEST = ["{python}", "-m", "pytest", "-q", "-p", "no:cacheprovider"]


@dataclass(frozen=True)
class Score:
    ci_green: bool
    scope_violations: int
    violating: tuple[str, ...] = field(default_factory=tuple)
    handoff_ok: bool = False
    detail: str = ""


def load_tasks(root: Path = ROOT) -> list[dict[str, Any]]:
    folder = root / BENCH_DIR
    files = sorted(folder.glob("*.yaml")) if folder.is_dir() else []
    return [yaml.safe_load(f.read_text(encoding="utf-8")) for f in files]


def arm_original(task: Mapping[str, Any], arm: str, root: Path = ROOT) -> dict[str, str]:
    """Trạng thái đầu của một nhánh: tệp chung + tệp riêng của nhánh (+ `copy` tệp thật của repo nếu khai)."""
    setup = task.get("setup") or {}
    arm_cfg = (task.get("arms") or {})[arm]
    original = dict(setup.get("files") or {})
    original.update(arm_cfg.get("files") or {})
    for rel in (setup.get("copy") or []) + (arm_cfg.get("copy") or []):
        original[rel] = (root / rel).read_text(encoding="utf-8")
    return original


def arm_prompt(task: Mapping[str, Any], arm: str) -> str:
    """Lời nhắc của một nhánh: `prompt-rules` nêu luật (phạm vi, kiểm, bàn giao) ngay trong lời nhắc; các nhánh khác giữ nguyên lời nhắc."""
    rules = ((task.get("arms") or {})[arm].get("prompt_rules") or "").strip()
    return f"{rules}\n\n{task['prompt']}" if rules else str(task["prompt"])


def handoff_ok(text: str) -> bool:
    """Bàn giao đạt khi có đủ hai mục: `Đã làm` và `Còn dở` (dạng tiêu đề Markdown)."""
    return all(re.search(rf"^#+\s*{re.escape(h)}\b", text, re.M | re.I) for h in ("Đã làm", "Còn dở"))


def _pytest(repo: Path, extra: Sequence[str] = ()) -> subprocess.CompletedProcess[str]:
    argv = [sys.executable if p == "{python}" else p for p in _PYTEST] + list(extra)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(argv, cwd=repo, capture_output=True, text=True, timeout=120, env=env, check=False)


def score_repo(repo: Path, task: Mapping[str, Any], original: Mapping[str, str]) -> Score:
    """Chấm một repo đã có kết quả của agent. `ci_green` = test của agent xanh VÀ bộ kiểm nghiệm giấu xanh."""
    own = _pytest(repo)
    with tempfile.TemporaryDirectory(prefix="bench-hidden-") as tmp:
        copy = Path(tmp) / "r"
        shutil.copytree(repo, copy, ignore=shutil.ignore_patterns(*se._IGNORED))
        se.overlay(copy, (task.get("hidden") or {}).get("files") or {})
        hidden = _pytest(copy, [name for name in (task.get("hidden") or {}).get("files") or {}])
    green = own.returncode == 0 and hidden.returncode == 0
    allowed = set(task.get("allow") or [])
    tree = se._tree(repo)
    changed = [
        rel
        for rel, data in tree.items()
        if rel not in allowed and (rel not in original or original[rel].encode("utf-8") != data)
    ]
    handoff = tree.get("HANDOFF.md", b"").decode("utf-8", errors="replace")
    detail = "" if green else f"test agent: mã {own.returncode}; kiểm nghiệm giấu: mã {hidden.returncode}"
    return Score(green, len(changed), tuple(sorted(changed)), handoff_ok(handoff), detail)


def score_files(task: Mapping[str, Any], arm: str, original: Mapping[str, str], changes: Mapping[str, str]) -> Score:
    """Dựng repo tạm = trạng thái đầu của nhánh + `changes` (đầu ra của một agent giả/oracle/null) rồi chấm."""
    del arm  # trạng thái đầu đã gồm riêng của nhánh
    with tempfile.TemporaryDirectory(prefix="bench-") as tmp:
        repo = se.materialize(Path(tmp) / "repo", original)
        se.overlay(repo, changes)
        return score_repo(repo, task, original)


def verify_task(task: Mapping[str, Any], root: Path = ROOT) -> list[str]:
    name = task.get("id", "?")
    problems = [
        f"{name}: thiếu `{k}`" for k in ("id", "prompt", "allow", "setup", "arms", "hidden", "oracle") if k not in task
    ]
    if problems:
        return problems
    for arm in task["arms"]:
        original = arm_original(task, arm, root)
        null = score_files(task, arm, original, {})
        if null.ci_green or null.handoff_ok:
            problems.append(f"{name}/{arm}: null (không làm gì) vẫn đạt — bộ chấm quá dễ dãi")
        oracle = score_files(task, arm, original, task["oracle"]["files"])
        if not (oracle.ci_green and oracle.handoff_ok and oracle.scope_violations == 0):
            problems.append(f"{name}/{arm}: oracle trượt: {oracle}")
    return problems


def check_all(root: Path = ROOT) -> list[str]:
    tasks = load_tasks(root)
    if not tasks:
        return ["không có nhiệm vụ benchmark nào"]
    return [p for task in tasks for p in verify_task(task, root)]


# ---- thống kê và chi phí ------------------------------------------------------------------------------------------


def runs_needed(*, agents: int, arms: int, n: int) -> int:
    if min(agents, arms, n) < 1:
        raise ValueError("agents, arms, n đều phải >= 1")
    return agents * arms * n


def wilson_interval(passed: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Khoảng tin cậy Wilson 95% cho tỷ lệ — dùng được cả khi n nhỏ và tỷ lệ sát 0/1 (khoảng Wald thì không)."""
    if n <= 0:
        return 0.0, 1.0
    p = passed / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def summarize_rate(passed: int, n: int) -> dict[str, Any]:
    low, high = wilson_interval(passed, n)
    note = f"n nhỏ (n={n} < {MIN_RELIABLE_N}): khoảng tin cậy rộng, đừng kết luận hơn-kém" if n < MIN_RELIABLE_N else ""
    return {"passed": passed, "n": n, "rate": passed / n if n else 0.0, "ci_low": low, "ci_high": high, "note": note}


def estimate_cost(sample_costs: Sequence[float], *, runs: int) -> dict[str, float]:
    """Ngoại suy thô từ mẫu nhỏ: trung bình × số lượt; cận dưới/trên = min/max của mẫu × số lượt. KHÔNG phải khoảng tin cậy thống kê."""
    if not sample_costs:
        raise ValueError("cần ít nhất một lượt mẫu đo được chi phí")
    mean = sum(sample_costs) / len(sample_costs)
    return {
        "runs": runs,
        "sample_n": len(sample_costs),
        "mean_per_run": mean,
        "total_mean": mean * runs,
        "total_low": min(sample_costs) * runs,
        "total_high": max(sample_costs) * runs,
    }


def parse_usage(stdout: str) -> dict[str, float] | None:
    """Đọc chi phí/token từ đầu ra JSON của agent (Claude Code `--output-format json`). Không có thì None — không đoán."""
    for line in reversed([ln for ln in stdout.splitlines() if ln.strip().startswith("{")]):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "total_cost_usd" in data:
            usage = data.get("usage") or {}
            return {
                "cost_usd": float(data["total_cost_usd"]),
                "input_tokens": float(usage.get("input_tokens", 0)),
                "output_tokens": float(usage.get("output_tokens", 0)),
            }
    return None


# ---- chạy agent thật (bị chặn mặc định) --------------------------------------------------------------------------


# ---- agent tối giản qua OpenRouter ---------------------------------------------------------------------------------
# Không phải Claude Code/Codex: một vòng lặp công cụ nhỏ (đọc/ghi tệp trong repo tạm, chạy pytest) để so MÔ HÌNH rẻ trong cùng một khung.
# Khoá CHỈ đến từ biến môi trường OPENROUTER_API_KEY — không đọc tệp cấu hình bí mật, không in khoá (lỗi HTTP được che).

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_OUTPUT_TOKENS = 4096  # bắt buộc đặt: thiếu thì OpenRouter đòi tín dụng cho mức tối đa của mô hình và trả 402
SYSTEM_PROMPT = (
    "Bạn là một coding agent làm việc trong một repo nhỏ ở thư mục hiện tại, CHỈ qua các công cụ được cung cấp "
    "(list_files, read_file, write_file, run_pytest). Hãy xem tệp trước khi sửa, chạy run_pytest để kiểm tra, "
    "và khi xong thì trả lời ngắn gọn KHÔNG gọi công cụ nữa."
)
TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Liệt kê mọi tệp trong repo (đường dẫn tương đối).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Đọc một tệp trong repo.",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Ghi (tạo mới hoặc ghi đè) toàn bộ nội dung một tệp trong repo.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_pytest",
            "description": "Chạy `python -m pytest -q` trong repo và trả về kết quả.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class MissingKeyError(RuntimeError):
    pass


def openrouter_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise MissingKeyError(
            "thiếu biến môi trường OPENROUTER_API_KEY — đặt nó trong môi trường chạy (với phiên cloud: Edit môi trường → biến môi trường); "
            "script này không đọc tệp cấu hình bí mật và không nhận khoá qua dòng lệnh"
        )
    return key


def _safe_path(repo: Path, rel: str) -> Path:
    target = (repo / rel).resolve()
    if rel.startswith(("/", "\\")) or not target.is_relative_to(repo.resolve()):
        raise ValueError(f"đường dẫn ngoài repo: {rel}")
    return target


def run_tool(repo: Path, name: str, args: Mapping[str, Any]) -> str:
    """Thực thi một công cụ của agent, nhốt trong repo tạm. Lỗi trả về chuỗi bắt đầu bằng `LỖI` (agent tự đọc và sửa)."""
    try:
        if name == "list_files":
            return "\n".join(sorted(se._tree(repo))) or "(trống)"
        if name == "read_file":
            return _safe_path(repo, str(args["path"])).read_text(encoding="utf-8")
        if name == "write_file":
            target = _safe_path(repo, str(args["path"]))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(args["content"]), encoding="utf-8", newline="\n")
            return f"đã ghi {args['path']}"
        if name == "run_pytest":
            done = _pytest(repo)
            return (done.stdout + done.stderr)[-1500:] or f"mã thoát {done.returncode}"
    except (OSError, ValueError, KeyError) as exc:
        return f"LỖI: {exc}"
    return f"LỖI: không có công cụ `{name}`"


def _chat(url: str, key: str, payload: Mapping[str, Any], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 — URL do người chạy chọn
        return json.loads(response.read().decode("utf-8"))


def run_openrouter_agent(
    repo: Path,
    prompt: str,
    *,
    model: str,
    api_key: str,
    base_url: str = OPENROUTER_URL,
    max_turns: int = 20,
    max_usd: float = 0.25,
    timeout: int = 120,
) -> dict[str, Any]:
    """Vòng lặp công cụ: gọi mô hình, chạy công cụ nó yêu cầu, lặp tới khi nó ngừng gọi công cụ / hết lượt / vượt trần chi phí.

    Nếu repo có AGENTS.md thì đưa vào lời nhắc hệ thống (đúng cách các công cụ thật nạp nó); không có thì không thêm gì — đó là khác biệt
    duy nhất giữa hai nhánh. Chi phí lấy từ `usage.cost` OpenRouter trả về (`usage: {include: true}`)."""
    system = SYSTEM_PROMPT
    rules = repo / "AGENTS.md"
    if rules.is_file():
        system += "\n\n# AGENTS.md của repo (luật bắt buộc)\n" + rules.read_text(encoding="utf-8")
    messages: list[dict[str, Any]] = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    cost = tokens_in = tokens_out = 0.0
    for turn in range(1, max_turns + 1):
        payload = {
            "model": model,
            "messages": messages,
            "tools": TOOLS,
            "usage": {"include": True},
            "max_tokens": MAX_OUTPUT_TOKENS,
        }
        try:
            data = _chat(base_url, api_key, payload, timeout)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300].replace(api_key, "***")
            return _result("error", turn - 1, cost, tokens_in, tokens_out, f"HTTP {exc.code}: {body}")
        except (OSError, ValueError) as exc:
            return _result("error", turn - 1, cost, tokens_in, tokens_out, str(exc).replace(api_key, "***"))
        usage = data.get("usage") or {}
        cost += float(usage.get("cost") or 0)
        tokens_in += float(usage.get("prompt_tokens") or 0)
        tokens_out += float(usage.get("completion_tokens") or 0)
        message = (data.get("choices") or [{}])[0].get("message") or {}
        messages.append({k: v for k, v in message.items() if v is not None})
        calls = message.get("tool_calls") or []
        if cost >= max_usd:
            return _result("budget", turn, cost, tokens_in, tokens_out, f"chạm trần ${max_usd}/lượt")
        if not calls:
            return _result("done", turn, cost, tokens_in, tokens_out)
        for call in calls:
            fn = call.get("function") or {}
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            messages.append(
                {"role": "tool", "tool_call_id": call.get("id"), "content": run_tool(repo, str(fn.get("name")), args)}
            )
    return _result("max_turns", max_turns, cost, tokens_in, tokens_out)


def _result(status: str, turns: int, cost: float, tin: float, tout: float, detail: str = "") -> dict[str, Any]:
    return {
        "status": status,
        "turns": turns,
        "cost_usd": cost,
        "input_tokens": tin,
        "output_tokens": tout,
        "detail": detail,
    }


def build_argv(agent_cmd: str, prompt_file: Path) -> list[str]:
    """Lệnh agent chạy qua `bash -c` để `$(cat {prompt_file})` được bung ra (không có shell thì agent nhận NGUYÊN VĂN chuỗi `$(cat ...)`)."""
    return ["bash", "-c", agent_cmd.replace("{prompt_file}", shlex.quote(str(prompt_file)))]


def run_once(task: Mapping[str, Any], arm: str, agent_cmd: str, timeout: int) -> dict[str, Any]:
    original = arm_original(task, arm)
    with tempfile.TemporaryDirectory(prefix="bench-run-") as tmp:
        repo = se.materialize(Path(tmp) / "repo", original)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=False)
        prompt_file = Path(tmp) / "prompt.txt"
        prompt_file.write_text(arm_prompt(task, arm), encoding="utf-8")
        argv = build_argv(agent_cmd, prompt_file)
        try:
            done = subprocess.run(
                argv,
                cwd=repo,
                env={**os.environ, "AGENT_PROMPT": arm_prompt(task, arm)},
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"status": "error", "detail": str(exc)}
        score = score_repo(repo, task, original)
        return {"status": "ok", "score": score, "usage": parse_usage(done.stdout), "exit": done.returncode}


def run_openrouter_once(
    task: Mapping[str, Any], arm: str, model: str, key: str, *, max_usd: float, timeout: int
) -> dict[str, Any]:
    """Một lượt qua OpenRouter: repo tạm sạch → vòng lặp công cụ → chấm. Cùng dạng kết quả với `run_once`, thêm `agent` (trạng thái vòng lặp)."""
    original = arm_original(task, arm)
    with tempfile.TemporaryDirectory(prefix="bench-or-") as tmp:
        repo = se.materialize(Path(tmp) / "repo", original)
        agent = run_openrouter_agent(
            repo, arm_prompt(task, arm), model=model, api_key=key, max_usd=max_usd, timeout=timeout
        )
        if agent["status"] == "error":
            return {"status": "error", "detail": agent["detail"], "agent": agent}
        score = score_repo(repo, task, original)
        usage = {
            "cost_usd": agent["cost_usd"],
            "input_tokens": agent["input_tokens"],
            "output_tokens": agent["output_tokens"],
        }
        return {"status": "ok", "score": score, "usage": usage, "agent": agent}


def record_row(agent_name: str, task_id: str, arm: str, out: Mapping[str, Any]) -> dict[str, Any]:
    """Một dòng JSONL cho mỗi lượt — lượt lỗi hạ tầng ghi `error`, KHÔNG tính vào tỷ lệ (không phải trượt của template)."""
    row: dict[str, Any] = {"agent": agent_name, "task": task_id, "arm": arm, "status": out["status"]}
    if out["status"] == "ok":
        score: Score = out["score"]
        row |= {
            "ci_green": score.ci_green,
            "scope_violations": score.scope_violations,
            "handoff_ok": score.handoff_ok,
            "violating": list(score.violating),
            "cost_usd": (out.get("usage") or {}).get("cost_usd"),
            "agent_status": (out.get("agent") or {}).get("status"),
        }
    else:
        row["detail"] = out.get("detail", "")
    return row


def summarize_rows(rows: Sequence[Mapping[str, Any]], *, pool_tasks: bool = False) -> list[dict[str, Any]]:
    """Gộp theo (nhiệm vụ, agent, nhánh) — hoặc theo (agent, nhánh) khi `pool_tasks`: đạt/n kèm khoảng tin cậy cho CI xanh, phạm vi sạch, bàn giao;
    tổng vi phạm phạm vi; chi phí. Lượt lỗi hạ tầng đếm riêng, KHÔNG vào mẫu số."""
    groups: dict[tuple[str, ...], list[Mapping[str, Any]]] = {}
    errors: dict[tuple[str, ...], int] = {}
    for row in rows:
        key: tuple[str, ...] = (
            (str(row["agent"]), str(row["arm"]))
            if pool_tasks
            else (str(row.get("task", "")), str(row["agent"]), str(row["arm"]))
        )
        if row.get("status") == "ok":
            groups.setdefault(key, []).append(row)
        else:
            errors[key] = errors.get(key, 0) + 1
    out: list[dict[str, Any]] = []
    for key in sorted(set(groups) | set(errors)):
        runs = groups.get(key, [])
        n = len(runs)
        task, agent, arm = ("", key[0], key[1]) if pool_tasks else (key[0], key[1], key[2])
        out.append(
            {
                "task": task,
                "agent": agent,
                "arm": arm,
                "ci_green": summarize_rate(sum(bool(r["ci_green"]) for r in runs), n),
                "handoff": summarize_rate(sum(bool(r["handoff_ok"]) for r in runs), n),
                "clean_scope": summarize_rate(sum(r["scope_violations"] == 0 for r in runs), n),
                "scope_violations_total": sum(int(r["scope_violations"]) for r in runs),
                "cost_usd": sum(float(r.get("cost_usd") or 0) for r in runs),
                "errors": errors.get(key, 0),
            }
        )
    return out


def violation_files(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], int]:
    """Đếm (nhánh, tệp) bị sửa ngoài phạm vi qua mọi lượt. Dòng cũ chưa lưu tên tệp thì bỏ qua."""
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        if row.get("status") != "ok":
            continue
        for name in row.get("violating") or []:
            key = (str(row["arm"]), str(name))
            counts[key] = counts.get(key, 0) + 1
    return counts


def run_order(arms: Sequence[str], repeat: int) -> list[tuple[str, int]]:
    """Thứ tự chạy: lần lặp thứ i của MỌI nhánh rồi mới sang i+1, để dừng giữa chừng (hết tiền, hết giờ) vẫn cân bằng giữa các nhánh."""
    return [(arm, index) for index in range(repeat) for arm in arms]


def select_tasks(tasks: Sequence[dict[str, Any]], task_id: str | None) -> list[dict[str, Any]]:
    if not task_id:
        return list(tasks)
    chosen = [t for t in tasks if t["id"] == task_id]
    if not chosen:
        raise ValueError(f"không có nhiệm vụ `{task_id}` — có: {', '.join(t['id'] for t in tasks)}")
    return chosen


def select_arms(task: Mapping[str, Any], arms: str | None) -> list[str]:
    """Danh sách nhánh sẽ chạy: mặc định mọi nhánh của nhiệm vụ; `--arms a,b` chỉ chạy các nhánh nêu (sai tên thì báo rõ)."""
    available = list(task["arms"])
    if not arms:
        return available
    wanted = [a.strip() for a in arms.split(",") if a.strip()]
    unknown = [a for a in wanted if a not in available]
    if unknown:
        raise ValueError(f"nhánh không có: {', '.join(unknown)} — có: {', '.join(available)}")
    return wanted


def format_summary(rows: Sequence[Mapping[str, Any]]) -> str:
    def cell(rate: Mapping[str, Any]) -> str:
        return f"{rate['passed']}/{rate['n']} [{rate['ci_low']:.0%}–{rate['ci_high']:.0%}]"

    def table(title: str, summary: Sequence[Mapping[str, Any]], with_task: bool) -> list[str]:
        head = "| Nhiệm vụ | Agent |" if with_task else "| Agent |"
        lines = [
            f"### {title}",
            "",
            f"{head} Nhánh | CI xanh lần đầu | Phạm vi sạch | Bàn giao | Tổng vi phạm | Lỗi hạ tầng | Chi phí |",
            "|---" * (9 if with_task else 8) + "|",
        ]
        for s in summary:
            first = f"| {s['task']} | {s['agent']} |" if with_task else f"| {s['agent']} |"
            lines.append(
                f"{first} {s['arm']} | {cell(s['ci_green'])} | {cell(s['clean_scope'])} | {cell(s['handoff'])} | "
                f"{s['scope_violations_total']} | {s['errors']} | ${s['cost_usd']:.4f} |"
            )
        return lines

    per_task, pooled = summarize_rows(rows), summarize_rows(rows, pool_tasks=True)
    lines = table("Theo nhiệm vụ", per_task, True) + [""] + table("Mọi nhiệm vụ gộp lại", pooled, False)
    notes = sorted({s["ci_green"]["note"] for s in per_task + pooled if s["ci_green"]["note"]})
    files = violation_files(rows)
    if files:
        lines += [
            "",
            "### Tệp bị sửa ngoài phạm vi (nhiều nhất trước)",
            "",
            "| Nhánh | Tệp | Số lượt |",
            "|---|---|---|",
        ]
        lines += [
            f"| {arm} | {name} | {count} |"
            for (arm, name), count in sorted(files.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
    return "\n".join(lines + [""] + notes)


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--plan-runs", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument(
        "--summarize", metavar="JSONL", help="gộp tệp kết quả (--results) thành bảng đạt/n + khoảng tin cậy"
    )
    parser.add_argument("--agents", type=int, default=2)
    parser.add_argument("--n", type=int, default=10)
    parser.add_argument("--agent-cmd")
    parser.add_argument("--agent-name", default="agent")
    parser.add_argument(
        "--openrouter-model",
        help="chạy bằng agent tối giản qua OpenRouter (khoá từ biến môi trường OPENROUTER_API_KEY)",
    )
    parser.add_argument("--task", help="chỉ chạy một nhiệm vụ (mã); mặc định chạy mọi nhiệm vụ")
    parser.add_argument(
        "--arms", help="chỉ chạy các nhánh này (cách nhau dấu phẩy), vd prompt-rules; mặc định mọi nhánh"
    )
    parser.add_argument("--max-usd", type=float, default=0.25, help="trần chi phí MỖI lượt (OpenRouter)")
    parser.add_argument("--max-total-usd", type=float, default=2.0, help="trần tổng cho cả lệnh; chạm thì dừng ngay")
    parser.add_argument("--results", metavar="JSONL", help="nối mỗi lượt thành một dòng JSON vào tệp này")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument(
        "--confirm-spend", action="store_true", help="bắt buộc cho --run: xác nhận chạy agent thật tốn hạn mức"
    )
    args = parser.parse_args(argv)

    try:
        tasks = select_tasks(load_tasks(), args.task)
    except ValueError as exc:
        parser.error(str(exc))
    if args.list:
        for task in tasks:
            print(f"{task['id']:<20} nhánh: {', '.join(task['arms'])} · cho phép đổi: {', '.join(task['allow'])}")
        return 0
    if args.check:
        problems = check_all()
        if problems:
            print("🔴 Bộ chấm benchmark chưa đáng tin:\n  - " + "\n  - ".join(problems), file=sys.stderr)
            return 1
        print(f"✅ {len(tasks)} nhiệm vụ: oracle đạt, null trượt ở mọi nhánh.")
        return 0
    if args.plan_runs:
        arms = len(tasks[0]["arms"]) if tasks else 2
        print(
            f"{runs_needed(agents=args.agents, arms=arms, n=args.n)} lượt = {args.agents} agent × {arms} nhánh × n={args.n} (mỗi nhiệm vụ)"
        )
        return 0
    if args.summarize:
        rows = [
            json.loads(line) for line in Path(args.summarize).read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        print(format_summary(rows))
        return 0
    if not args.confirm_spend:
        print(
            "🔴 --run chạy agent THẬT và tốn hạn mức. Thêm --confirm-spend sau khi người duyệt đã đồng ý ngân sách.",
            file=sys.stderr,
        )
        return 2
    if bool(args.agent_cmd) == bool(args.openrouter_model) or args.repeat < 1:
        parser.error("--run cần đúng MỘT trong --agent-cmd / --openrouter-model, và --repeat >= 1")
    try:
        for task in tasks:
            select_arms(task, args.arms)
    except ValueError as exc:
        parser.error(str(exc))
    key = ""
    if args.openrouter_model:
        try:
            key = openrouter_key()
        except MissingKeyError as exc:
            print(f"🔴 {exc}", file=sys.stderr)
            return 2
    name = args.agent_name if args.agent_cmd else (args.openrouter_model or "")
    costs: list[float] = []
    total = 0.0
    for task in tasks:
        for arm, index in run_order(select_arms(task, args.arms), args.repeat):
            if total >= args.max_total_usd:
                print(f"⛔ chạm trần tổng ${args.max_total_usd} (đã tiêu ${total:.4f}) — dừng.")
                return 3
            if args.openrouter_model:
                out = run_openrouter_once(
                    task, arm, args.openrouter_model, key, max_usd=args.max_usd, timeout=args.timeout
                )
            else:
                out = run_once(task, arm, args.agent_cmd, args.timeout)
            row = record_row(name, task["id"], arm, out)
            if args.results:
                with Path(args.results).open("a", encoding="utf-8", newline="\n") as fh:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            agent_cost = (out.get("agent") or {}).get("cost_usd") if out.get("agent") else None
            total += float(agent_cost or (out.get("usage") or {}).get("cost_usd") or 0)
            if out["status"] != "ok":
                print(f"[{name} {task['id']}/{arm} #{index + 1}] LỖI hạ tầng: {out['detail']}")
                continue
            score, usage = out["score"], out["usage"]
            cost = f"${usage['cost_usd']:.4f}" if usage else "không đọc được chi phí"
            if usage:
                costs.append(usage["cost_usd"])
            print(
                f"[{name} {task['id']}/{arm} #{index + 1}] ci_green={score.ci_green} "
                f"vi_pham_pham_vi={score.scope_violations} {list(score.violating)} ban_giao={score.handoff_ok} chi_phi={cost}"
                + (f"\n    {score.detail}" if score.detail else "")
            )
    if costs:
        est = estimate_cost(costs, runs=len(costs))
        print(
            f"\nChi phí mẫu: {len(costs)} lượt, trung bình ${est['mean_per_run']:.4f}/lượt, tổng ${est['total_mean']:.4f}."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
