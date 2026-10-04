"""`scripts/check_design.py`: bộ kiểm DESIGN.md (token máy đọc + lý do) và bộ sinh DESIGN.md khởi đầu.

Bám đặc tả google-labs-code/design.md (README, đọc 2026-10-04, định dạng `alpha`): front matter YAML + các mục `##` theo thứ tự cố định.
Bộ kiểm chỉ dùng thư viện chuẩn + PyYAML (đã là phụ thuộc), không gọi `npx @google/design.md`.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
import yaml

from scripts import check_design as cd
from scripts import setup_project as sp
from scripts.ci_local import CI_COMMANDS

ROOT = Path(__file__).resolve().parents[2]
GOOD = textwrap.dedent(
    """\
    ---
    name: Mẫu
    colors:
      primary: "#1A1C1E"
      on-primary: "#FFFFFF"
      neutral: "#F7F5F2"
    typography:
      body-md:
        fontFamily: Public Sans
        fontSize: 1rem
    rounded:
      sm: 4px
    spacing:
      md: 16px
    components:
      button-primary:
        backgroundColor: "{colors.primary}"
        textColor: "{colors.on-primary}"
        rounded: "{rounded.sm}"
    ---

    ## Overview

    Lý do.

    ## Colors

    Bảng màu.

    ## Typography

    Chữ.
    """
)


def _lint(text: str) -> list[dict[str, str]]:
    return cd.lint(text)


def _where(findings: list[dict[str, str]], severity: str) -> list[dict[str, str]]:
    return [f for f in findings if f["severity"] == severity]


def _with(text: str, old: str, new: str) -> str:
    assert old in text
    return text.replace(old, new, 1)


# --- tương phản WCAG -------------------------------------------------------------------------------------------------


def test_ty_le_tuong_phan_theo_cong_thuc_wcag() -> None:
    assert cd.contrast_ratio("#000000", "#FFFFFF") == pytest.approx(21.0, abs=0.01)
    assert cd.contrast_ratio("#fff", "#ffffff") == pytest.approx(1.0)
    assert cd.contrast_ratio("#777777", "#FFFFFF") == pytest.approx(4.48, abs=0.02)  # nổi tiếng: ngay dưới ngưỡng AA
    assert cd.contrast_ratio("#767676", "#FFFFFF") >= 4.5


def test_mau_khong_phai_hex_thi_khong_do_duoc_khong_doan() -> None:
    assert cd.contrast_ratio("oklch(62% 0.18 250)", "#FFFFFF") is None
    assert cd.contrast_ratio("red", "#FFFFFF") is None


# --- luật kiểm --------------------------------------------------------------------------------------------------------


def test_design_md_hop_le_khong_co_loi() -> None:
    assert _where(_lint(GOOD), "error") == []


def test_tham_chieu_token_gay_la_loi() -> None:
    findings = _lint(_with(GOOD, "{colors.on-primary}", "{colors.khong-co}"))
    errors = _where(findings, "error")
    assert any("khong-co" in f["message"] and f["path"].startswith("components.button-primary") for f in errors)


def test_cap_chu_nen_duoi_aa_la_loi() -> None:
    low = _with(GOOD, '"#FFFFFF"', '"#777777"')  # chữ #777 trên nền #1A1C1E ~ 3.9:1
    errors = _where(_lint(low), "error")
    assert any("4.5" in f["message"] and "button-primary" in f["path"] for f in errors)


def test_cap_chu_nen_dat_aa_thi_qua() -> None:
    assert _where(_lint(GOOD), "error") == []


def test_mau_khong_do_duoc_la_canh_bao_khong_do() -> None:
    text = _with(GOOD, '"#FFFFFF"', '"oklch(98% 0.01 90)"')
    findings = _lint(text)
    assert _where(findings, "error") == []
    assert any("không đo được" in f["message"] for f in _where(findings, "warning"))


def test_thieu_primary_va_typography_la_canh_bao() -> None:
    text = _with(GOOD, '  primary: "#1A1C1E"\n', "").replace("{colors.primary}", "{colors.neutral}")
    warnings = [f["message"] for f in _where(_lint(text), "warning")]
    assert any("primary" in m for m in warnings)
    no_type = textwrap.dedent(
        """\
        ---
        name: X
        colors:
          primary: "#000000"
        ---
        ## Overview
        x
        """
    )
    assert any("typography" in f["message"] for f in _where(_lint(no_type), "warning"))


def test_muc_sai_thu_tu_la_canh_bao_va_trung_muc_la_loi() -> None:
    swapped = _with(_with(GOOD, "## Colors", "## TMP"), "## Overview", "## Colors").replace("## TMP", "## Overview")
    assert any("thứ tự" in f["message"] for f in _where(_lint(swapped), "warning"))
    duplicate = GOOD + "\n## Colors\n\nLại một mục.\n"
    assert any("trùng" in f["message"] for f in _where(_lint(duplicate), "error"))


def test_khoa_go_sai_chinh_ta_la_canh_bao() -> None:
    findings = _lint(_with(GOOD, "\ncolors:", "\ncolours:"))
    assert any("colours" in f["message"] and f["severity"] == "warning" for f in findings)


def test_khong_co_front_matter_la_loi() -> None:
    assert _where(_lint("## Overview\n\nchỉ có chữ\n"), "error")


def test_front_matter_yaml_hong_la_loi() -> None:
    assert _where(_lint("---\ncolors: [chưa đóng\n---\n## Overview\n"), "error")


# --- bộ sinh DESIGN.md khởi đầu ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("primary", ["#1D4ED8", "#767676", "#808080", "#FFEB3B", "#000000", "#FFFFFF"])
def test_ban_khoi_dau_luon_qua_bo_kiem_ke_ca_mau_chinh_kho(primary: str) -> None:
    text = cd.starter(name="Dự án thử", primary=primary, background="#FFFFFF", text="#111827")
    assert _where(_lint(text), "error") == [], primary
    data, _body = cd.split_front_matter(text)
    on_primary = data["colors"]["on-primary"]
    assert cd.contrast_ratio(on_primary, primary) >= 4.5


def test_ban_khoi_dau_tu_choi_nen_chu_khong_doc_duoc() -> None:
    with pytest.raises(ValueError, match="4.5"):
        cd.starter(name="Xấu", primary="#1D4ED8", background="#FFFFFF", text="#EEEEEE")
    with pytest.raises(ValueError, match="hex"):
        cd.starter(name="Xấu", primary="xanh", background="#FFFFFF", text="#111111")


def test_ban_khoi_dau_khong_co_ten_la_loi_ro_rang() -> None:
    with pytest.raises(ValueError, match="tên"):
        cd.starter(name="  ", primary="#1D4ED8", background="#FFFFFF", text="#111827")


# --- dòng lệnh --------------------------------------------------------------------------------------------------------


def test_main_in_json_va_ma_thoat_theo_loi(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    good = tmp_path / "DESIGN.md"
    good.write_text(GOOD, encoding="utf-8")
    assert cd.main([str(good)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["summary"]["errors"] == 0

    bad = tmp_path / "BAD.md"
    bad.write_text(_with(GOOD, "{colors.on-primary}", "{colors.khong-co}"), encoding="utf-8")
    assert cd.main([str(bad)]) == 1
    assert json.loads(capsys.readouterr().out)["summary"]["errors"] >= 1
    assert cd.main([str(tmp_path / "khong-co.md")]) == 1


def test_init_ghi_tep_hop_le(tmp_path: Path) -> None:
    out = tmp_path / "DESIGN.md"
    argv = ["--init", "--name", "Kho thuốc", "--primary", "#0F766E", "--background", "#FFFFFF", "--text", "#0F172A"]
    assert cd.main([*argv, "--out", str(out)]) == 0
    assert _where(_lint(out.read_text(encoding="utf-8")), "error") == []
    assert cd.main([*argv[:5], "--background", "#FFFFFF", "--text", "#FAFAFA", "--out", str(out)]) == 1


# --- DESIGN.md thật của repo, skill, wizard, CI ------------------------------------------------------------------------


def test_design_md_cua_repo_qua_bo_kiem_va_ghi_ngay_kiem_dac_ta() -> None:
    text = (ROOT / "DESIGN.md").read_text(encoding="utf-8")
    assert _where(_lint(text), "error") == []
    data, _ = cd.split_front_matter(text)
    assert data["version"] == "alpha"
    assert "2026-10-04" in text, "ghi ngày đã đối chiếu đặc tả google-labs-code/design.md"


def test_skill_design_system_tro_design_md_lam_nguon_token() -> None:
    skill = (ROOT / "packs/frontend/skills/design-system/SKILL.md").read_text(encoding="utf-8")
    assert "DESIGN.md" in skill and "check_design.py" in skill


def test_ci_chay_bo_kiem_va_ci_local_phan_chieu() -> None:
    command = "python scripts/check_design.py DESIGN.md"
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    runs = [str(step.get("run", "")) for job in workflow["jobs"].values() for step in job.get("steps", [])]
    assert any(command in run for run in runs), "ci.yml phải chạy bộ kiểm DESIGN.md"
    assert command in CI_COMMANDS.values(), "scripts/ci_local.py phải phản chiếu lệnh CI"


def test_wizard_co_o_chon_mau_va_gui_muc_design() -> None:
    html = (ROOT / "wizard" / "index.html").read_text(encoding="utf-8")
    assert html.count('type="color"') >= 3
    assert "design" in html


# --- wizard sinh DESIGN.md khởi đầu qua setup_project -----------------------------------------------------------------

BASE = {
    "version": 1,
    "name": "Trợ lý kho thuốc",
    "slug": "tro-ly-kho-thuoc",
    "project_type": "ai-product",
    "team_size": "standard",
    "complexity": "standard",
    "packs": ["ai-llm"],
    "agent_tools": ["claude-code"],
}
DESIGN = {"primary": "#0F766E", "background": "#FFFFFF", "text": "#0F172A"}


def test_ke_hoach_khong_co_buoc_design_khi_nguoi_dung_khong_dien() -> None:
    scripts = {argv[0] for _label, argv in sp.plan(sp.validate(dict(BASE)))}
    assert "scripts/check_design.py" not in scripts


def test_ke_hoach_co_buoc_sinh_design_md_khi_co_muc_design() -> None:
    steps = sp.plan(sp.validate({**BASE, "design": DESIGN}))
    argvs = [argv for _label, argv in steps if argv[0] == "scripts/check_design.py"]
    assert len(argvs) == 1
    assert argvs[0][:2] == ["scripts/check_design.py", "--init"]
    assert "#0F766E" in argvs[0] and "DESIGN.md" in argvs[0]


@pytest.mark.parametrize(
    ("design", "fragment"),
    [
        ({**DESIGN, "primary": "xanh"}, "`design`"),
        ({**DESIGN, "text": "#EEEEEE"}, "4.5"),
        ({"primary": "#0F766E"}, "`design`"),
        ("không phải đối tượng", "`design`"),
    ],
)
def test_muc_design_sai_bi_tu_choi_ro_rang(design: object, fragment: str) -> None:
    with pytest.raises(sp.SetupError, match=fragment):
        sp.validate({**BASE, "design": design})
