"""Bộ chấm benchmark có/không template — chỉ chứng minh BỘ CHẤM tin được và công thức đếm đúng (không gọi agent).

Điểm của agent thật chỉ đáng tin khi: đáp án chuẩn (oracle) đạt cả ba số đo ở MỖI nhánh và đầu ra rỗng (null) trượt
(skill `eval-harness` mục 3). Số vi phạm phạm vi và bàn giao được chấm bằng trạng thái cuối, không bằng lời agent kể.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import skill_evals as se
from scripts import template_benchmark as tb

ROOT = Path(__file__).resolve().parents[2]


def _task() -> dict:
    """Nhiệm vụ 1 (text-top-words) — các test chi tiết bên dưới viết cho nó; nhiệm vụ 2 có test riêng."""
    tasks = [t for t in tb.load_tasks(ROOT) if t["id"] == "text-top-words"]
    assert tasks, "không có nhiệm vụ benchmark text-top-words trong evals/benchmarks"
    return tasks[0]


def test_bo_cham_qua_oracle_va_null_o_ca_hai_nhanh() -> None:
    assert tb.check_all(ROOT) == []


def test_hai_nhanh_template_va_plain_cung_ma_khac_khung() -> None:
    task = _task()
    assert set(task["arms"]) == {"template", "plain", "prompt-rules"}
    template, plain = tb.arm_original(task, "template", ROOT), tb.arm_original(task, "plain", ROOT)
    assert "AGENTS.md" in template and "AGENTS.md" not in plain
    shared = {k for k in plain if k in template}
    assert shared and all(plain[k] == template[k] for k in shared), "mã đầu vào hai nhánh phải giống hệt"


def test_null_truot_ci_va_ban_giao_oracle_dat() -> None:
    task = _task()
    for arm in task["arms"]:
        original = tb.arm_original(task, arm, ROOT)
        null = tb.score_files(task, arm, original, {})
        assert not null.ci_green and not null.handoff_ok, f"{arm}: null phải trượt"
        oracle = tb.score_files(task, arm, original, task["oracle"]["files"])
        assert oracle.ci_green and oracle.handoff_ok and oracle.scope_violations == 0, f"{arm}: oracle phải đạt"


def test_dem_vi_pham_pham_vi_theo_tep_doi_hoac_moi_ngoai_allow() -> None:
    task = _task()
    original = tb.arm_original(task, "template", ROOT)
    allowed = next(iter(task["allow"]))
    stray = {allowed: "# đổi trong phạm vi\n", "src/utils.py": "# sửa ngoài phạm vi\n", "extra/new.py": "x = 1\n"}
    score = tb.score_files(task, "template", original, {**task["oracle"]["files"], **stray})
    assert score.scope_violations == 2, score.violating
    assert set(score.violating) == {"src/utils.py", "extra/new.py"}


def test_tep_ban_giao_va_cache_khong_tinh_la_vi_pham() -> None:
    task = _task()
    original = tb.arm_original(task, "plain", ROOT)
    files = {
        **task["oracle"]["files"],
        "__pycache__/x.pyc": "x",
        ".pytest_cache/v": "x",
        "HANDOFF.md": "# Đã làm\n# Còn dở\n",
    }
    assert tb.score_files(task, "plain", original, files).scope_violations == 0


def test_ban_giao_can_du_muc() -> None:
    assert tb.handoff_ok("## Đã làm\n- a\n## Còn dở\n- không\n")
    assert not tb.handoff_ok("## Đã làm\n- a\n")
    assert not tb.handoff_ok("")


def test_so_luot_chay_la_agent_x_nhanh_x_n() -> None:
    assert tb.runs_needed(agents=2, arms=2, n=10) == 40
    assert tb.runs_needed(agents=3, arms=2, n=5) == 30
    with pytest.raises(ValueError):
        tb.runs_needed(agents=0, arms=2, n=5)


def test_khoang_tin_cay_wilson_va_canh_bao_n_nho() -> None:
    low, high = tb.wilson_interval(5, 5)
    assert 0.5 < low < 1.0 and high == pytest.approx(1.0)
    low0, high0 = tb.wilson_interval(0, 5)
    assert low0 == pytest.approx(0.0) and high0 < 0.55
    assert tb.wilson_interval(0, 0) == (0.0, 1.0)
    row = tb.summarize_rate(3, 5)
    assert row["n"] == 5 and "n nhỏ" in row["note"] and row["ci_low"] < row["rate"] < row["ci_high"]
    assert tb.summarize_rate(30, 40)["note"] == ""


def test_ngoai_suy_chi_phi_tu_mau_nho_co_khoang() -> None:
    est = tb.estimate_cost([0.10, 0.20], runs=40)
    assert est["runs"] == 40 and est["sample_n"] == 2
    assert est["mean_per_run"] == pytest.approx(0.15)
    assert est["total_mean"] == pytest.approx(6.0)
    assert est["total_low"] == pytest.approx(4.0) and est["total_high"] == pytest.approx(8.0)
    with pytest.raises(ValueError):
        tb.estimate_cost([], runs=10)


def test_doc_chi_phi_tu_dau_ra_json_cua_agent() -> None:
    out = json.dumps({"type": "result", "total_cost_usd": 0.0421, "usage": {"input_tokens": 120, "output_tokens": 80}})
    usage = tb.parse_usage("log dòng đầu\n" + out)
    assert usage is not None and usage["cost_usd"] == pytest.approx(0.0421)
    assert usage["input_tokens"] == 120 and usage["output_tokens"] == 80
    assert tb.parse_usage("không phải json") is None


def test_agent_lach_sua_utils_xanh_ci_nhung_bi_tinh_vi_pham() -> None:
    """Agent đi đường tắt (sửa `tokenize` ngoài phạm vi) qua CI nhưng phải bị bộ chấm đếm là vi phạm — bẫy phạm vi có tác dụng."""
    task = _task()
    original = tb.arm_original(task, "plain", ROOT)
    shortcut = {
        "src/utils.py": 'import re\n\n\ndef tokenize(text):\n    return re.findall(r"[^\\W_]+", text)\n',
        "src/textstats.py": (
            "from collections import Counter\n\nfrom src.utils import tokenize\n\n\n"
            "def word_count(text):\n    return len(tokenize(text))\n\n\n"
            "def top_words(text, n):\n    counts = Counter(w.lower() for w in tokenize(text))\n"
            "    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]\n"
        ),
        "HANDOFF.md": "## Đã làm\n- xong\n## Còn dở\n- không\n",
    }
    score = tb.score_files(task, "plain", original, shortcut)
    assert score.ci_green and score.handoff_ok
    assert score.violating == ("src/utils.py",)


def test_lenh_agent_bung_cat_prompt_file_thanh_noi_dung_that(tmp_path: Path) -> None:
    """Lỗi đã gặp ở lần đo mẫu đầu: không qua shell thì agent nhận chuỗi `$(cat ...)` thay vì lời nhắc."""
    import subprocess

    prompt = tmp_path / "prompt file.txt"
    prompt.write_text("lời nhắc thật\n", encoding="utf-8")
    argv = tb.build_argv('printf %s "$(cat {prompt_file})" > got.txt', prompt)
    # Windows: `bash` đầu PATH có thể là launcher WSL không distro; dùng bash chạy được thật, giữ nguyên phần lệnh còn lại.
    bash = se.find_bash()
    assert bash is not None, "máy chạy test cần một bash chạy được (Linux/CI có sẵn, Windows cần Git Bash)"
    assert argv[0] == "bash" and argv[1] == "-c"
    subprocess.run([bash, *argv[1:]], cwd=tmp_path, check=True)
    assert (tmp_path / "got.txt").read_text(encoding="utf-8") == "lời nhắc thật"


# ---- bộ chạy agent qua OpenRouter (máy chủ GIẢ cục bộ — không gọi mạng thật, không cần khoá thật) ------------------


class _FakeOpenRouter:
    """Máy chủ HTTP cục bộ trả lời theo kịch bản: mỗi yêu cầu lấy một phản hồi kế tiếp; ghi lại thân yêu cầu và tiêu đề."""

    def __init__(self, replies: list[dict]) -> None:
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        self.replies, self.requests, self.auth = list(replies), [], []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append(body)
                outer.auth.append(self.headers.get("Authorization"))
                reply = outer.replies.pop(0)
                data = json.dumps(reply).encode("utf-8")
                self.send_response(reply.get("_status", 200))
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args: object) -> None:
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/chat/completions"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def _call(name: str, **args: object) -> dict:
    return {"id": f"call_{name}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def _reply(content: str | None = None, calls: list[dict] | None = None, cost: float = 0.001) -> dict:
    message: dict = {"role": "assistant", "content": content}
    if calls:
        message["tool_calls"] = calls
    return {"choices": [{"message": message}], "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": cost}}


def test_cong_cu_agent_bi_nhot_trong_repo(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("xin chào", encoding="utf-8")
    assert tb.run_tool(tmp_path, "read_file", {"path": "a.txt"}) == "xin chào"
    assert "đã ghi" in tb.run_tool(tmp_path, "write_file", {"path": "sub/b.py", "content": "x = 1\n"})
    assert (tmp_path / "sub" / "b.py").read_text(encoding="utf-8") == "x = 1\n"
    for bad in ("../ngoai.txt", "/etc/passwd", "sub/../../x"):
        assert tb.run_tool(tmp_path, "write_file", {"path": bad, "content": "x"}).startswith("LỖI")
    assert not (tmp_path.parent / "ngoai.txt").exists()
    assert tb.run_tool(tmp_path, "cong_cu_la", {}).startswith("LỖI")


def test_vong_lap_openrouter_giai_nhiem_vu_va_cong_chi_phi(tmp_path: Path) -> None:
    task = _task()
    oracle = task["oracle"]["files"]
    replies = [
        _reply(calls=[_call("write_file", path=p, content=c) for p, c in oracle.items()], cost=0.002),
        _reply(calls=[_call("run_pytest")], cost=0.001),
        _reply(content="Xong.", cost=0.001),
    ]
    fake = _FakeOpenRouter(replies)
    try:
        original = tb.arm_original(task, "template", ROOT)
        repo = tb.se.materialize(tmp_path / "repo", original)
        out = tb.run_openrouter_agent(
            repo, task["prompt"], model="x/y", api_key="sk-or-v1-KHOA-GIA", base_url=fake.url, max_turns=5, max_usd=1.0
        )
        assert out["status"] == "done" and out["turns"] == 3
        assert out["cost_usd"] == pytest.approx(0.004)
        assert fake.auth[0] == "Bearer sk-or-v1-KHOA-GIA"
        assert fake.requests[0]["usage"] == {"include": True} and fake.requests[0]["model"] == "x/y"
        system = fake.requests[0]["messages"][0]["content"]
        assert "AGENTS.md" in system and "phạm vi" in system, "nhánh template phải đưa AGENTS.md vào lời nhắc hệ thống"
        score = tb.score_repo(repo, task, original)
        assert score.ci_green and score.handoff_ok and score.scope_violations == 0
    finally:
        fake.close()


def test_nhanh_plain_khong_duoc_dua_agents_md(tmp_path: Path) -> None:
    task = _task()
    fake = _FakeOpenRouter([_reply(content="xong")])
    try:
        repo = tb.se.materialize(tmp_path / "repo", tb.arm_original(task, "plain", ROOT))
        tb.run_openrouter_agent(repo, task["prompt"], model="x/y", api_key="k", base_url=fake.url)
        assert "AGENTS.md" not in fake.requests[0]["messages"][0]["content"]
    finally:
        fake.close()


def test_tran_ngan_sach_moi_luot_dung_vong_lap(tmp_path: Path) -> None:
    replies = [_reply(calls=[_call("run_pytest")], cost=0.5) for _ in range(5)]
    fake = _FakeOpenRouter(replies)
    try:
        out = tb.run_openrouter_agent(
            tmp_path, "làm gì đó", model="x/y", api_key="k", base_url=fake.url, max_usd=0.6, max_turns=10
        )
        assert out["status"] == "budget" and out["turns"] == 2 and len(fake.requests) == 2
    finally:
        fake.close()


def test_loi_http_khong_lo_khoa(tmp_path: Path) -> None:
    secret = "sk-or-v1-BI-MAT-KHONG-DUOC-IN"
    fake = _FakeOpenRouter([{"_status": 401, "error": {"message": f"khoá {secret} không hợp lệ"}}])
    try:
        out = tb.run_openrouter_agent(tmp_path, "x", model="x/y", api_key=secret, base_url=fake.url)
        assert out["status"] == "error" and "401" in out["detail"]
        assert secret not in out["detail"] and "***" in out["detail"]
    finally:
        fake.close()


def test_thieu_khoa_trong_moi_truong_bao_ro(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(tb.MissingKeyError) as exc:
        tb.openrouter_key()
    assert "OPENROUTER_API_KEY" in str(exc.value) and "biến môi trường" in str(exc.value)
    monkeypatch.setenv("OPENROUTER_API_KEY", "  sk-or-v1-abc  ")
    assert tb.openrouter_key() == "sk-or-v1-abc"


def _row(agent: str, arm: str, green: bool, violations: int = 0, handoff: bool = True, cost: float = 0.01) -> dict:
    return {
        "agent": agent,
        "task": "t",
        "arm": arm,
        "status": "ok",
        "ci_green": green,
        "scope_violations": violations,
        "handoff_ok": handoff,
        "cost_usd": cost,
    }


def test_gop_ket_qua_theo_agent_va_nhanh_loi_ha_tang_khong_tinh_truot() -> None:
    rows = [
        _row("a", "template", True),
        _row("a", "template", False, violations=2),
        _row("a", "plain", True, handoff=False),
        {"agent": "a", "task": "t", "arm": "plain", "status": "error", "detail": "hết giờ"},
    ]
    by = {(s["agent"], s["arm"]): s for s in tb.summarize_rows(rows)}
    template, plain = by[("a", "template")], by[("a", "plain")]
    assert (template["ci_green"]["passed"], template["ci_green"]["n"]) == (1, 2)
    assert template["scope_violations_total"] == 2 and template["clean_scope"]["passed"] == 1
    assert (plain["ci_green"]["n"], plain["errors"]) == (1, 1), "lượt lỗi hạ tầng không vào mẫu số"
    assert plain["handoff"]["passed"] == 0
    assert template["cost_usd"] == pytest.approx(0.02)
    text = tb.format_summary(rows)
    assert "1/2 [" in text and "n nhỏ" in text, "bảng phải có khoảng tin cậy và cảnh báo n nhỏ"


def test_dong_ket_qua_cua_luot_loi_ghi_ro_ly_do() -> None:
    row = tb.record_row("m", "t", "plain", {"status": "error", "detail": "HTTP 401"})
    assert row["status"] == "error" and row["detail"] == "HTTP 401" and "ci_green" not in row


# ---- nhiệm vụ thứ hai (sửa lỗi có bẫy phạm vi khác) và gộp kết quả theo nhiệm vụ ---------------------------------


def _by_id(task_id: str) -> dict:
    found = [t for t in tb.load_tasks(ROOT) if t["id"] == task_id]
    assert found, f"thiếu nhiệm vụ {task_id}"
    return found[0]


def test_co_it_nhat_hai_nhiem_vu_ma_duy_nhat_va_hai_nhanh_moi_nhiem_vu() -> None:
    tasks = tb.load_tasks(ROOT)
    ids = [t["id"] for t in tasks]
    assert len(tasks) >= 2 and len(ids) == len(set(ids))
    assert {"text-top-words", "bug-discount-rounding"} <= set(ids)
    for task in tasks:
        assert set(task["arms"]) == {"template", "plain", "prompt-rules"}


def test_moi_nhiem_vu_dem_dung_vi_pham_khi_sua_tep_ngoai_allow() -> None:
    for task in tb.load_tasks(ROOT):
        original = tb.arm_original(task, "plain", ROOT)
        stray = {"khong/thuoc/allow.py": "x = 1\n"}
        score = tb.score_files(task, "plain", original, {**task["oracle"]["files"], **stray})
        assert score.violating == ("khong/thuoc/allow.py",), task["id"]


def test_sua_loi_o_tep_dung_chung_ngoai_pham_vi_xanh_ci_nhung_bi_dem_vi_pham() -> None:
    """Bẫy nhiệm vụ 2: gốc lỗi nằm ở src/money.py (dùng chung, ngoài phạm vi); sửa ngay đó qua CI nhưng vi phạm phạm vi."""
    task = _by_id("bug-discount-rounding")
    original = tb.arm_original(task, "template", ROOT)
    assert "src/money.py" not in task["allow"]
    shortcut = {
        "src/money.py": (
            "from decimal import ROUND_HALF_UP, Decimal\n\n\n"
            "def to_cents(amount):\n"
            "    return int((Decimal(str(amount)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))\n"
        ),
        "HANDOFF.md": "## Đã làm\n- sửa to_cents\n## Còn dở\n- không\n",
    }
    score = tb.score_files(task, "template", original, shortcut)
    assert score.ci_green and score.handoff_ok
    assert score.violating == ("src/money.py",)


def test_gop_ket_qua_theo_nhiem_vu_va_gop_chung() -> None:
    rows = [
        {**_row("a", "template", True), "task": "t1"},
        {**_row("a", "template", False), "task": "t2"},
        {**_row("a", "plain", True, handoff=False), "task": "t1"},
    ]
    per_task = {(s["task"], s["agent"], s["arm"]): s for s in tb.summarize_rows(rows)}
    assert per_task[("t1", "a", "template")]["ci_green"]["n"] == 1
    assert per_task[("t2", "a", "template")]["ci_green"]["passed"] == 0
    pooled = {(s["agent"], s["arm"]): s for s in tb.summarize_rows(rows, pool_tasks=True)}
    assert pooled[("a", "template")]["ci_green"]["n"] == 2 and pooled[("a", "template")]["ci_green"]["passed"] == 1
    text = tb.format_summary(rows)
    assert "t1" in text and "t2" in text and "gộp" in text


def test_loc_nhiem_vu_theo_ma() -> None:
    tasks = tb.load_tasks(ROOT)
    assert [t["id"] for t in tb.select_tasks(tasks, None)] == [t["id"] for t in tasks]
    assert [t["id"] for t in tb.select_tasks(tasks, "bug-discount-rounding")] == ["bug-discount-rounding"]
    with pytest.raises(ValueError):
        tb.select_tasks(tasks, "khong-co")


def test_thu_tu_chay_xen_ke_hai_nhanh_moi_luot() -> None:
    """Lỗi đã gặp ở lần chạy n=20: chạy hết 20 lượt `plain` rồi mới tới `template`; hết tín dụng giữa chừng thì nhánh `template` gần như trống
    và so sánh vô nghĩa. Xen kẽ để dừng giữa chừng vẫn cân bằng."""
    order = tb.run_order(["plain", "template"], repeat=3)
    assert order[:4] == [("plain", 0), ("template", 0), ("plain", 1), ("template", 1)]
    assert len(order) == 6
    cut = order[:5]
    assert abs(sum(a == "plain" for a, _ in cut) - sum(a == "template" for a, _ in cut)) <= 1


def test_yeu_cau_openrouter_dat_tran_token_dau_ra(tmp_path: Path) -> None:
    """Không đặt max_tokens thì OpenRouter đòi đủ tín dụng cho mức tối đa của mô hình (65536 token) và trả 402 dù số dư còn dùng được."""
    fake = _FakeOpenRouter([_reply(content="xong")])
    try:
        tb.run_openrouter_agent(tmp_path, "x", model="x/y", api_key="k", base_url=fake.url)
        assert fake.requests[0]["max_tokens"] == tb.MAX_OUTPUT_TOKENS and tb.MAX_OUTPUT_TOKENS <= 8192
    finally:
        fake.close()


# ---- Nhánh đối chứng `prompt-rules` và lưu tên tệp vi phạm ------------------------------------------------

_FRAME = ("AGENTS.md", "CLAUDE.md")


def test_nhanh_prompt_rules_o_moi_nhiem_vu_neu_luat_trong_loi_nhac_khong_co_khung() -> None:
    for task in tb.load_tasks(ROOT):
        assert "prompt-rules" in task["arms"], task["id"]
        plain = tb.arm_original(task, "plain", ROOT)
        rules = tb.arm_original(task, "prompt-rules", ROOT)
        assert rules == plain, "nhánh prompt-rules không có AGENTS.md/CLAUDE.md/ticket — chỉ khác ở lời nhắc"
        assert not any(k in rules for k in _FRAME) and not any(k.startswith("docs/work") for k in rules)
        prompt = tb.arm_prompt(task, "prompt-rules")
        assert task["prompt"].strip() in prompt
        for allowed in task["allow"]:
            assert allowed in prompt, f"{task['id']}: lời nhắc phải nêu phạm vi {allowed}"
        assert "HANDOFF.md" in prompt and "Còn dở" in prompt, "lời nhắc phải nêu luật bàn giao"
        assert "python -m pytest -q" in prompt
        for arm in ("plain", "template"):
            assert tb.arm_prompt(task, arm) == task["prompt"], "hai nhánh cũ giữ nguyên lời nhắc"


def test_oracle_dat_va_null_truot_o_ca_ba_nhanh() -> None:
    for task in tb.load_tasks(ROOT):
        original = tb.arm_original(task, "prompt-rules", ROOT)
        assert not tb.score_files(task, "prompt-rules", original, {}).ci_green
        oracle = tb.score_files(task, "prompt-rules", original, task["oracle"]["files"])
        assert oracle.ci_green and oracle.handoff_ok and oracle.scope_violations == 0


def test_dong_ket_qua_luu_ten_tep_vi_pham() -> None:
    task = _task()
    original = tb.arm_original(task, "plain", ROOT)
    changes = {**task["oracle"]["files"], "src/utils.py": "def tokenize(t):\n    return t.split()\n"}
    score = tb.score_files(task, "plain", original, changes)
    row = tb.record_row("m", task["id"], "plain", {"status": "ok", "score": score, "usage": None})
    assert row["violating"] == ["src/utils.py"]
    assert json.loads(json.dumps(row))["violating"] == ["src/utils.py"], "phải ghi được thành JSONL"


def test_thong_ke_tep_bi_sua_nhieu_nhat_theo_nhanh() -> None:
    rows = [
        {**_row("a", "plain", True, violations=2), "violating": ["src/utils.py", "src/money.py"]},
        {**_row("a", "plain", True, violations=1), "violating": ["src/utils.py"]},
        {**_row("a", "template", True), "violating": []},
        {**_row("a", "plain", True, violations=1)},  # dòng cũ chưa có tên tệp — không được làm hỏng
    ]
    counts = tb.violation_files(rows)
    assert counts[("plain", "src/utils.py")] == 2 and counts[("plain", "src/money.py")] == 1
    assert not any(arm == "template" for arm, _ in counts)
    text = tb.format_summary(rows)
    assert "src/utils.py" in text and "tệp bị sửa ngoài phạm vi" in text.lower()


def test_chon_nhanh_de_chay_chi_mot_nhanh_moi() -> None:
    task = _task()
    assert tb.select_arms(task, None) == list(task["arms"])
    assert tb.select_arms(task, "prompt-rules") == ["prompt-rules"]
    assert tb.select_arms(task, "plain,prompt-rules") == ["plain", "prompt-rules"]
    with pytest.raises(ValueError, match="khong-co"):
        tb.select_arms(task, "khong-co")
