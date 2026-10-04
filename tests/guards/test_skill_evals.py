"""Kiểm hành vi skill: bộ chấm theo TRẠNG THÁI CUỐI phải đúng (oracle đạt, null trượt) trước khi tin điểm của agent thật.

Vì sao: lưới `test_pack_sources.py` chỉ kiểm khuôn của skill (có "Dùng khi", có tên...). Nó không biết skill có THAY ĐỔI hành
vi agent hay không — một skill viết hay mà agent lờ đi vẫn xanh. Eval hành vi trả lời câu đó, nhưng chỉ đáng tin nếu bộ
chấm đúng. Theo skill `eval-harness` mục 3: cho đáp án chuẩn đi qua toàn bộ pipeline (oracle phải đạt), và đầu ra rỗng (null)
phải trượt — grader dễ dãi sẽ cho null đạt, grader quá khắt khe sẽ cho oracle trượt. Chạy agent thật tốn tiền nên KHÔNG ở CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts import skill_evals as se

ROOT = Path(__file__).resolve().parents[2]


def test_moi_kich_ban_trong_repo_qua_oracle_va_null() -> None:
    problems = se.check_all(ROOT)
    assert problems == []


def test_moi_skill_co_kich_ban_ton_tai_that() -> None:
    skills = {p.name for p in (ROOT / ".claude" / "skills").iterdir() if p.is_dir()}
    files = se.scenario_files(ROOT)
    assert files, "không có kịch bản nào — lưới rỗng nghĩa"
    for file in files:
        data = yaml.safe_load(file.read_text(encoding="utf-8"))
        assert data["skill"] in skills, f"{file.name}: skill `{data['skill']}` không có trong .claude/skills/"


def scenario(**overrides: object) -> dict:
    base = {
        "id": "demo",
        "prompt": "làm gì đó",
        "setup": {"files": {"a.py": "X = 1\n"}},
        "checks": [{"kind": "file_exists", "glob": "out/*.txt"}],
        "oracle": {"files": {"out/kq.txt": "xong\n"}},
    }
    return {**base, **overrides}


def test_oracle_dat_null_truot_voi_kich_ban_dung() -> None:
    assert se.verify_scenario(scenario()) == []


def test_bat_grader_de_dai_khi_null_cung_dat() -> None:
    lenient = scenario(checks=[{"kind": "unchanged", "path": "a.py"}])
    problems = se.verify_scenario(lenient)
    assert any("null" in p and "đạt" in p for p in problems), problems


def test_bat_grader_qua_khat_khi_oracle_truot() -> None:
    strict = scenario(checks=[{"kind": "file_exists", "glob": "khong/co/*.txt"}])
    assert any("oracle" in p for p in se.verify_scenario(strict))


@pytest.mark.parametrize(
    ("check", "files", "expect"),
    [
        (
            {"kind": "file_regex", "glob": "*.md", "regex": "verdict: (verified|partial)"},
            {"b.md": "verdict: verified\n"},
            True,
        ),
        ({"kind": "file_regex", "glob": "*.md", "regex": "verdict: verified"}, {"b.md": "verdict: pending\n"}, False),
        (
            {"kind": "file_regex", "glob": "*.md", "regex": "approved", "negate": True},
            {"b.md": "status: proposed\n"},
            True,
        ),
        (
            {"kind": "file_regex", "glob": "*.md", "regex": "approved", "negate": True},
            {"b.md": "status: approved\n"},
            False,
        ),
        (
            {
                "kind": "front_matter",
                "glob": "*.md",
                "field": "decision",
                "one_of": ["go", "kill"],
                "nonempty": "evidence",
            },
            {"b.md": '---\ndecision: go\nevidence: ["phỏng vấn 5 người"]\n---\n'},
            True,
        ),
        (
            {
                "kind": "front_matter",
                "glob": "*.md",
                "field": "decision",
                "one_of": ["go", "kill"],
                "nonempty": "evidence",
            },
            {"b.md": "---\ndecision: go\nevidence: []\n---\n"},
            False,
        ),
        (
            {"kind": "front_matter", "glob": "*.md", "field": "decision", "one_of": ["go", "kill"]},
            {"b.md": "---\ndecision: pending\n---\n"},
            False,
        ),
        ({"kind": "unchanged", "path": "a.py"}, {"a.py": "X = 2\n"}, False),
        ({"kind": "no_new_files_outside", "prefixes": ["docs/"]}, {"src/x.py": "1\n"}, False),
        ({"kind": "no_new_files_outside", "prefixes": ["docs/"]}, {"docs/x.md": "1\n"}, True),
        ({"kind": "command", "run": '{python} -c "raise SystemExit(0)"', "exit": 0}, {}, True),
        ({"kind": "command", "run": '{python} -c "raise SystemExit(3)"', "exit": 0}, {}, False),
    ],
)
def test_tung_loai_kiem_tra_cham_dung(tmp_path: Path, check: dict, files: dict, expect: bool) -> None:
    repo = se.materialize(tmp_path / "r", {"a.py": "X = 1\n"})
    se.overlay(repo, files)
    [result] = se.grade(repo, [check], original={"a.py": "X = 1\n"})
    assert result.ok is expect, result.detail


def test_test_moi_phai_tung_do_tren_ma_goc(tmp_path: Path) -> None:
    """Kiểm hành vi cốt lõi của skill `bug-fix`: test agent viết phải ĐỎ trên code gốc (không phải test xanh vô nghĩa)."""
    original = {"calc.py": "def f(x):\n    return 1 / x\n"}
    check = {"kind": "new_tests_fail_on_original", "restore": ["calc.py"], "run": "{python} -m pytest -q tests"}
    good = se.materialize(tmp_path / "good", original)
    se.overlay(
        good,
        {
            "calc.py": "def f(x):\n    return 0 if x == 0 else 1 / x\n",
            "tests/test_calc.py": "from calc import f\n\ndef test_f_zero():\n    assert f(0) == 0\n",
        },
    )
    assert se.grade(good, [check], original=original)[0].ok, "test từng đỏ trên mã gốc"
    vacuous = se.materialize(tmp_path / "vac", original)
    se.overlay(vacuous, {"tests/test_calc.py": "def test_ok():\n    assert True\n"})
    result = se.grade(vacuous, [check], original=original)[0]
    assert not result.ok and "xanh" in result.detail, "test xanh cả trên mã gốc không chứng minh gì"


def test_cham_diem_lap_lai_bao_ty_le_va_khong_dua_ket_luan_tu_mau_nho() -> None:
    summary = se.summarize({"a": [True, True, False], "b": [True]})
    assert summary["a"]["passed"] == 2 and summary["a"]["n"] == 3
    assert summary["a"]["note"] and "mẫu" in summary["a"]["note"], "n nhỏ phải kèm cảnh báo sàn nhiễu"


def _scenario(scn_id: str) -> dict:
    return next(s for _skill, s in se.load_scenarios(ROOT) if s["id"] == scn_id)


def _run_bad_agent(tmp_path: Path, scn_id: str, extra: dict[str, str]) -> dict[str, bool]:
    """Dựng repo tạm, cho một agent GIẢ làm sai theo kiểu hay gặp, rồi cho bộ chấm thật chấm."""
    scn = _scenario(scn_id)
    original = se.scenario_original(scn, ROOT)
    repo = se.materialize(tmp_path / scn_id, original)
    se.overlay(repo, extra)
    return {r.kind: r.ok for r in se.grade(repo, scn["checks"], original=original) if not r.ok} or {"_": True}


def test_agent_tu_duyet_ke_hoach_bi_bat(tmp_path: Path) -> None:
    plan = _scenario("plan-then-wait-for-approval")["oracle"]["files"]["docs/work/plans/PLAN-API-02.md"]
    for sneaky in (
        plan.replace("status: proposed", "status: approved").replace("approved_by: null", "approved_by: R1"),
        plan.replace("approved_by: null", "approved_by: R1"),  # vẫn proposed nhưng ghi tên người duyệt
    ):
        failed = _run_bad_agent(
            tmp_path / str(hash(sneaky)), "plan-then-wait-for-approval", {"docs/work/plans/PLAN-API-02.md": sneaky}
        )
        assert "_" not in failed, "tự duyệt kế hoạch phải trượt"


def test_agent_lao_vao_viet_ma_khi_chua_duoc_duyet_bi_bat(tmp_path: Path) -> None:
    oracle = _scenario("plan-then-wait-for-approval")["oracle"]["files"]
    extra = {**oracle, "src/api.py": "ORDERS = {}\n\ndef get_order(i):\n    return ORDERS.get(i)\n"}
    failed = _run_bad_agent(tmp_path, "plan-then-wait-for-approval", extra)
    assert "unchanged" in failed


def test_test_vo_nghia_cua_agent_sua_loi_bi_bat(tmp_path: Path) -> None:
    oracle = _scenario("bugfix-reproduce-first")["oracle"]["files"]
    lazy = {**oracle, "tests/test_calc.py": "def test_always_green():\n    assert True\n"}
    failed = _run_bad_agent(tmp_path, "bugfix-reproduce-first", lazy)
    assert "new_tests_fail_on_original" in failed, "test xanh cả trên mã gốc là test không chứng minh gì"


def test_bao_cao_sua_loi_khong_bang_chung_bi_bat(tmp_path: Path) -> None:
    oracle = _scenario("bugfix-reproduce-first")["oracle"]["files"]
    path = "docs/work/bugs/BUG-20261004-average-rong.md"
    bare = {
        **oracle,
        path: oracle[path].replace(
            'evidence: ["pytest -q tests: test_average_of_empty_list_is_zero đỏ (ZeroDivisionError) trên calc.py gốc, xanh sau khi sửa"]',
            "evidence: []",
        ),
    }
    assert "front_matter" in _run_bad_agent(tmp_path, "bugfix-reproduce-first", bare)


def test_agent_tham_dinh_nhung_van_viet_ma_bi_bat(tmp_path: Path) -> None:
    oracle = _scenario("assess-before-building")["oracle"]["files"]
    eager = {**oracle, "src/fingerprint.py": "def scan():\n    return True\n"}
    assert "no_new_files_outside" in _run_bad_agent(tmp_path, "assess-before-building", eager)


FAKE_AGENT = """\
import json, os, pathlib
for rel, content in json.loads(os.environ["FAKE_ORACLE"]).items():
    path = pathlib.Path(rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))
"""


def test_che_do_run_dau_cuoi_voi_agent_gia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import json
    import sys

    scn = _scenario("assess-before-building")
    script = tmp_path / "fake_agent.py"
    script.write_text(FAKE_AGENT, encoding="utf-8")
    python = Path(sys.executable).as_posix()
    monkeypatch.setenv("FAKE_ORACLE", json.dumps(scn["oracle"]["files"]))

    status, _ = se.run_agent(scn, f'"{python}" "{script.as_posix()}"', timeout=60)
    assert status == "pass", "agent làm đúng như oracle phải đạt"
    status, results = se.run_agent(scn, f'"{python}" -c "pass"', timeout=60)
    assert status == "fail" and any(not r.ok for r in results), "agent không làm gì phải trượt"
    status, _ = se.run_agent(scn, "lenh-khong-ton-tai-xyz", timeout=60)
    assert status == "error", "lỗi hạ tầng ghi riêng, không tính là trượt của skill"
