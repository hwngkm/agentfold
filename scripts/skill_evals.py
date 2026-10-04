"""Kiểm HÀNH VI skill: một agent có làm đúng như skill dặn không — chấm bằng TRẠNG THÁI CUỐI, không bằng lời kể.

    python scripts/skill_evals.py --list                 # kịch bản có sẵn (evals/skills/*.yaml)
    python scripts/skill_evals.py --check                # CI: bộ chấm đúng? (oracle phải đạt, null phải trượt) — KHÔNG gọi agent
    python scripts/skill_evals.py --run --agent-cmd 'codex exec "$(cat {prompt_file})"' --repeat 5 [--skill bug-fix]

Vì sao tách hai chế độ: chạy agent thật tốn tiền và có nhiễu, nên không ở CI. CI chỉ chứng minh BỘ CHẤM tin được (skill
`eval-harness` mục 3): đáp án chuẩn (oracle) đi qua phải đạt, đầu ra rỗng (null) phải trượt. Điểm của agent thật chỉ đáng tin
khi bộ chấm qua bước đó.

`--run`: mỗi lượt dựng một repo tạm sạch từ `setup.files`, chạy lệnh agent trong đó (`{prompt_file}` = tệp lời nhắc ngoài repo;
biến AGENT_PROMPT chứa cùng nội dung), rồi chấm repo. Lệnh agent chạy với quyền của chính CLI đó — repo tạm cô lập tệp
nhưng KHÔNG cô lập mạng hay máy; chỉ chạy lệnh của công cụ bạn tin. Lượt agent lỗi/hết giờ ghi là `error`, không tính trượt.
"""

from __future__ import annotations

import argparse
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
EVALS_DIR = "evals/skills"
COMMAND_TIMEOUT = 120
MIN_RELIABLE_N = 20
_IGNORED = {".git", "__pycache__", ".pytest_cache", ".ruff_cache"}
_FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


@dataclass(frozen=True)
class CheckResult:
    kind: str
    ok: bool
    detail: str = ""


# ---- repo tạm ---------------------------------------------------------------------------------------------------


def overlay(repo: Path, files: Mapping[str, str]) -> None:
    for rel, content in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8"))


def materialize(dest: Path, files: Mapping[str, str]) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    overlay(dest, files)
    return dest


def _tree(repo: Path) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    for path in repo.rglob("*"):
        rel = path.relative_to(repo)
        if path.is_file() and not _IGNORED.intersection(rel.parts):
            found[rel.as_posix()] = path.read_bytes()
    return found


def _split(command: str) -> list[str]:
    return [sys.executable if part == "{python}" else part for part in shlex.split(command)]


def _run(argv: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=COMMAND_TIMEOUT,
        env=env,
        check=False,
    )


def scenario_original(scn: Mapping[str, Any], root: Path = ROOT) -> dict[str, str]:
    """Trạng thái đầu của repo tạm: `setup.files` + các tệp THẬT của repo này liệt kê ở `setup.copy` (vd. SKILL.md đang kiểm).

    Đưa đúng SKILL.md hiện hành vào repo tạm là điểm mấu chốt: sửa skill thì kịch bản đo skill mới, không phải bản cũ.
    """
    setup = scn.get("setup") or {}
    original = dict(setup.get("files") or {})
    for rel in setup.get("copy") or []:
        original[rel] = (root / rel).read_text(encoding="utf-8")
    return original


# ---- bộ chấm theo trạng thái cuối --------------------------------------------------------------------------------


def _matches(repo: Path, pattern: str) -> list[Path]:
    return sorted(p for p in repo.glob(pattern) if p.is_file() and not _IGNORED.intersection(p.relative_to(repo).parts))


def _front_matter(path: Path) -> dict[str, Any]:
    match = _FRONT.match(path.read_text(encoding="utf-8"))
    try:
        data = yaml.safe_load(match.group(1)) if match else None
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _check(repo: Path, check: Mapping[str, Any], original: Mapping[str, str]) -> CheckResult:
    kind = str(check.get("kind"))
    if kind == "file_exists":
        found = _matches(repo, check["glob"])
        return CheckResult(kind, bool(found), "" if found else f"không có tệp khớp `{check['glob']}`")
    if kind == "file_regex":
        hits = [
            p for p in _matches(repo, check["glob"]) if re.search(check["regex"], p.read_text(encoding="utf-8"), re.M)
        ]
        if check.get("negate"):
            return CheckResult(kind, not hits, f"{hits[0].name} khớp điều cấm `{check['regex']}`" if hits else "")
        return CheckResult(kind, bool(hits), "" if hits else f"không tệp `{check['glob']}` nào khớp `{check['regex']}`")
    if kind == "front_matter":
        reasons: list[str] = []
        for path in _matches(repo, check["glob"]):
            data = _front_matter(path)
            if "one_of" in check and data.get(check["field"]) not in check["one_of"]:
                reasons.append(f"{path.name}: `{check['field']}` = {data.get(check['field'])!r}, cần {check['one_of']}")
            elif "nonempty" in check and not [e for e in (data.get(check["nonempty"]) or []) if str(e).strip()]:
                reasons.append(f"{path.name}: `{check['nonempty']}` rỗng")
            else:
                return CheckResult(kind, True)
        return CheckResult(kind, False, "; ".join(reasons) or f"không có tệp khớp `{check['glob']}`")
    if kind == "unchanged":
        same = (repo / check["path"]).is_file() and (repo / check["path"]).read_bytes() == original[
            check["path"]
        ].encode("utf-8")
        return CheckResult(kind, same, "" if same else f"`{check['path']}` đã bị đổi hoặc xoá")
    if kind == "no_new_files_outside":
        stray = [p for p in _tree(repo) if p not in original and not p.startswith(tuple(check["prefixes"]))]
        return CheckResult(kind, not stray, f"tệp mới ngoài {check['prefixes']}: {stray[:3]}" if stray else "")
    if kind == "command":
        result = _run(_split(check["run"]), repo)
        want = int(check.get("exit", 0))
        return CheckResult(
            kind,
            result.returncode == want,
            f"mã thoát {result.returncode} (cần {want}): {result.stdout[-160:]}{result.stderr[-160:]}".strip(),
        )
    if kind == "new_tests_fail_on_original":
        with tempfile.TemporaryDirectory(prefix="skill-eval-orig-") as tmp:
            copy = Path(tmp) / "r"
            shutil.copytree(repo, copy, ignore=shutil.ignore_patterns(*_IGNORED))
            overlay(copy, {rel: original[rel] for rel in check["restore"]})
            result = _run(_split(check["run"]), copy)
        if result.returncode == 5:
            return CheckResult(kind, False, "không thu thập được test nào")
        return CheckResult(
            kind,
            result.returncode != 0,
            "test xanh cả trên mã gốc — không chứng minh được lỗi" if result.returncode == 0 else "",
        )
    return CheckResult(kind, False, f"loại kiểm tra lạ: {kind}")


def grade(repo: Path, checks: Sequence[Mapping[str, Any]], *, original: Mapping[str, str]) -> list[CheckResult]:
    return [_check(repo, check, original) for check in checks]


# ---- kiểm chính bộ chấm ------------------------------------------------------------------------------------------


def verify_scenario(scn: Mapping[str, Any], root: Path = ROOT) -> list[str]:
    name = scn.get("id", "?")
    problems = [f"{name}: thiếu `{key}`" for key in ("id", "prompt", "setup", "checks", "oracle") if key not in scn]
    if problems:
        return problems
    original = scenario_original(scn, root)
    with tempfile.TemporaryDirectory(prefix="skill-eval-") as tmp:
        null_repo = materialize(Path(tmp) / "null", original)
        if all(r.ok for r in grade(null_repo, scn["checks"], original=original)):
            problems.append(f"{name}: null (agent không làm gì) vẫn đạt mọi kiểm tra — bộ chấm quá dễ dãi")
        oracle_repo = materialize(Path(tmp) / "oracle", original)
        overlay(oracle_repo, scn["oracle"]["files"])
        failed = [r for r in grade(oracle_repo, scn["checks"], original=original) if not r.ok]
        problems += [f"{name}: oracle trượt kiểm tra `{r.kind}`: {r.detail}" for r in failed]
    return problems


def scenario_files(root: Path) -> list[Path]:
    folder = root / EVALS_DIR
    return sorted(p for p in folder.glob("*.yaml")) if folder.is_dir() else []


def load_scenarios(root: Path) -> list[tuple[str, dict[str, Any]]]:
    found: list[tuple[str, dict[str, Any]]] = []
    for file in scenario_files(root):
        data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
        found += [(str(data.get("skill")), scn) for scn in data.get("scenarios") or []]
    return found


def check_all(root: Path) -> list[str]:  # noqa: D103
    problems: list[str] = []
    seen: set[str] = set()
    for skill, scn in load_scenarios(root):
        if scn.get("id") in seen:
            problems.append(f"{scn.get('id')}: trùng mã kịch bản")
        seen.add(str(scn.get("id")))
        problems += verify_scenario(scn, root) if skill else [f"{scn.get('id')}: tệp thiếu `skill`"]
    return problems


# ---- chạy agent thật ---------------------------------------------------------------------------------------------


def summarize(results: Mapping[str, Sequence[bool]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for key, outcomes in results.items():
        n, passed = len(outcomes), sum(outcomes)
        note = ""
        if n < MIN_RELIABLE_N:
            note = f"mẫu n={n} nhỏ: sàn nhiễu ~±{round(100 / math.sqrt(max(n, 1)))} điểm % — chỉ thấy khác biệt lớn, đừng so hai lần chạy"
        summary[key] = {"passed": passed, "n": n, "rate": passed / n if n else 0.0, "note": note}
    return summary


GIT_BASH = r"C:\Program Files\Git\bin\bash.exe"


class BashNotFoundError(RuntimeError):
    """Không có `bash` nào chạy được thật trên máy này."""


def _bash_candidates() -> list[str]:
    """Mọi `bash` trên PATH theo thứ tự (không chỉ cái đầu tiên), rồi Git Bash ở chỗ cài mặc định (Windows)."""
    found: list[str] = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        candidate = shutil.which("bash", path=entry) if entry else None
        if candidate and candidate not in found:
            found.append(candidate)
    return [*found, GIT_BASH]


def find_bash() -> str | None:
    """Bash CHẠY ĐƯỢC THẬT (thử `bash -c 'echo ok'`), như tests/guards/test_cloud_setup.py. Trên Windows `bash` đầu PATH thường là launcher WSL
    không có distro (thoát mã 1); khi đó thử `bash` kế tiếp trên PATH rồi Git Bash. Linux/CI: `bash` đầu PATH chạy được nên không đổi gì."""
    for candidate in _bash_candidates():
        try:
            probe = subprocess.run(
                [candidate, "-c", "echo ok"], capture_output=True, text=True, check=False, timeout=15
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == "ok":
            return candidate
    return None


BASH_HELP = (
    "không tìm thấy `bash` chạy được: `bash` đầu PATH có thể là launcher WSL không có distro (Windows). "
    "Cài Git for Windows (Git Bash) hoặc một distro WSL, rồi chạy lại."
)


def build_argv(agent_cmd: str, prompt_file: Path) -> list[str]:
    """Lệnh agent chạy qua `bash -c` để `$(cat {prompt_file})` được bung ra; không qua shell thì agent nhận NGUYÊN VĂN chuỗi `$(cat ...)`.

    Đường dẫn tệp lời nhắc được `shlex.quote` (an toàn với dấu cách). Lệnh agent do NGƯỜI CHẠY cung cấp (đã là lệnh tuỳ ý) nên chạy qua shell
    không mở rộng bề mặt tấn công; lời nhắc của kịch bản KHÔNG bao giờ được nhúng vào chuỗi lệnh — chỉ đi qua tệp và biến AGENT_PROMPT.
    Ném `BashNotFoundError` (nói rõ cách xử lý) nếu máy không có bash chạy được.
    """
    bash = find_bash()
    if bash is None:
        raise BashNotFoundError(BASH_HELP)
    return [bash, "-c", agent_cmd.replace("{prompt_file}", shlex.quote(str(prompt_file)))]


def run_agent(scn: Mapping[str, Any], agent_cmd: str, timeout: int) -> tuple[str, list[CheckResult]]:
    """Một lượt: repo tạm sạch → agent → chấm. Trả (`pass|fail|error`, kết quả từng kiểm tra)."""
    original = scenario_original(scn)
    with tempfile.TemporaryDirectory(prefix="skill-eval-run-") as tmp:
        repo = materialize(Path(tmp) / "repo", original)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=False)
        prompt_file = Path(tmp) / "prompt.txt"
        prompt_file.write_text(scn["prompt"], encoding="utf-8")
        try:
            argv = build_argv(agent_cmd, prompt_file)
        except BashNotFoundError as exc:
            return "error", [CheckResult("agent", False, str(exc))]
        env = {**os.environ, "AGENT_PROMPT": scn["prompt"]}
        try:
            done = subprocess.run(argv, cwd=repo, env=env, capture_output=True, text=True, timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return "error", [CheckResult("agent", False, f"không chạy được/hết giờ: {exc}")]
        if done.returncode != 0 and not _tree(repo).keys() - original.keys():
            return "error", [CheckResult("agent", False, f"agent thoát mã {done.returncode}: {done.stderr[-200:]}")]
        results = grade(repo, scn["checks"], original=original)
    return ("pass" if all(r.ok for r in results) else "fail"), results


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--agent-cmd")
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--skill")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args(argv)

    if args.list:
        for skill, scn in load_scenarios(ROOT):
            print(f"{skill:<18} {scn['id']:<28} {len(scn['checks'])} kiểm tra")
        return 0
    if args.check:
        problems = check_all(ROOT)
        if problems:
            print("🔴 Bộ chấm kịch bản chưa đáng tin:\n  - " + "\n  - ".join(problems), file=sys.stderr)
            return 1
        print(f"✅ {len(load_scenarios(ROOT))} kịch bản: oracle đạt, null trượt.")
        return 0
    if not args.agent_cmd or args.repeat < 1:
        parser.error("--run cần --agent-cmd và --repeat >= 1")
    if find_bash() is None:
        print(f"🔴 {BASH_HELP}", file=sys.stderr)
        return 3
    results: dict[str, list[bool]] = {}
    errors: dict[str, int] = {}
    for skill, scn in load_scenarios(ROOT):
        if args.skill and skill != args.skill:
            continue
        for index in range(args.repeat):
            status, checks = run_agent(scn, args.agent_cmd, args.timeout)
            key = f"{skill}/{scn['id']}"
            if status == "error":
                errors[key] = errors.get(key, 0) + 1
            else:
                results.setdefault(key, []).append(status == "pass")
            print(
                f"  [{key} #{index + 1}] {status}"
                + "".join(f"\n      ✗ {c.kind}: {c.detail}" for c in checks if not c.ok),
                flush=True,
            )
    print("\n| Kịch bản | Đạt | Lỗi hạ tầng | Ghi chú |\n|---|---|---|---|")
    for key, row in summarize(results).items():
        print(f"| {key} | {row['passed']}/{row['n']} | {errors.get(key, 0)} | {row['note']} |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
