"""Đặc tả sống: yêu cầu `SHALL` + kịch bản `WHEN/THEN` + test chứng minh; thay đổi đi qua delta rồi gộp vào đặc tả chung.

Vì sao: ticket có tiêu chí nghiệm thu nhưng sau khi merge, tiêu chí biến mất cùng ticket — hệ thống "đã hứa gì" nằm rải
rác trong lịch sử. Đặc tả tích luỹ giữ lời hứa hiện hành ở MỘT nơi, mỗi thay đổi ghi rõ thêm/sửa/bỏ yêu cầu nào, và mỗi
yêu cầu trỏ tới test chứng minh nó (hoặc nói thẳng là chưa có). Ý tưởng mượn từ Fission-AI/OpenSpec (delta ADDED/MODIFIED/REMOVED).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.agentctl.errors import AgentctlError
from tools.agentctl.spec import (
    Delta,
    apply_delta,
    archive_delta,
    parse_delta,
    parse_spec,
    render_spec,
    spec_problems,
)

SPEC = """# Spec: handoff

### Requirement: Bàn giao điền sẵn từ git
Hệ thống SHALL điền nhánh, commit cuối và tệp chưa commit vào mục bàn giao.

#### Scenario: Agent hết hạn mức giữa chừng
- **WHEN** agent chạy `new handoff`
- **THEN** mục bàn giao chứa nhánh và danh sách tệp chưa commit
- **Test:** tests/fake/test_demo.py::test_dien_san

### Requirement: Bàn giao hỏng bị bắt
Bộ kiểm cấu trúc SHALL từ chối bàn giao có `status` ngoài tập cho phép.

#### Scenario: Status lạ
- **WHEN** một mục có `status: pending`
- **THEN** `check-work` báo lỗi
- **Test:** planned:META-99
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "tests" / "fake").mkdir(parents=True)
    (tmp_path / "tests" / "fake" / "test_demo.py").write_text("def test_dien_san():\n    pass\n", encoding="utf-8")
    return tmp_path


def test_doc_roi_ghi_lai_giong_het() -> None:
    spec = parse_spec("handoff", SPEC)
    assert [r.name for r in spec.requirements] == ["Bàn giao điền sẵn từ git", "Bàn giao hỏng bị bắt"]
    assert spec.requirements[0].scenarios[0].tests == ("tests/fake/test_demo.py::test_dien_san",)
    assert render_spec(spec) == SPEC


def test_spec_hop_le_khong_co_van_de(repo: Path) -> None:
    assert spec_problems(parse_spec("handoff", SPEC), repo) == []


@pytest.mark.parametrize(
    ("old", "new", "fragment"),
    [
        ("SHALL điền", "nên điền", "SHALL"),
        ("- **THEN** `check-work` báo lỗi\n", "", "THEN"),
        ("- **WHEN** agent chạy `new handoff`\n", "", "WHEN"),
        ("tests/fake/test_demo.py::test_dien_san", "tests/fake/khong_co.py::test_x", "không tồn tại"),
        ("tests/fake/test_demo.py::test_dien_san", "tests/fake/test_demo.py::test_khac", "không có hàm"),
        ("- **Test:** planned:META-99", "", "Test"),
    ],
)
def test_bo_kiem_bat_dac_ta_hong(repo: Path, old: str, new: str, fragment: str) -> None:
    assert old in SPEC
    problems = spec_problems(parse_spec("handoff", SPEC.replace(old, new)), repo)
    assert any(fragment in p for p in problems), problems


def test_yeu_cau_khong_kich_ban_va_trung_ten_bi_bat(repo: Path) -> None:
    text = "### Requirement: A\nHệ thống SHALL làm A.\n\n### Requirement: A\nHệ thống SHALL làm A lần hai.\n"
    problems = spec_problems(parse_spec("x", text), repo)
    assert any("kịch bản" in p for p in problems) and any("trùng tên" in p for p in problems)


DELTA = """## ADDED Requirements

### Requirement: Bàn giao hiện trên bảng
Bảng việc SHALL liệt kê bàn giao còn mở ở nhánh chưa merge.

#### Scenario: Nhánh feature
- **WHEN** bàn giao `open` nằm trên nhánh chưa merge
- **THEN** `board` hiện nó kèm tên nhánh
- **Test:** planned:META-02

## MODIFIED Requirements

### Requirement: Bàn giao điền sẵn từ git
Hệ thống SHALL điền nhánh, commit cuối, tệp chưa commit và commit chưa đẩy vào mục bàn giao.

#### Scenario: Agent hết hạn mức giữa chừng
- **WHEN** agent chạy `new handoff`
- **THEN** mục bàn giao chứa nhánh, danh sách tệp chưa commit và số commit chưa đẩy
- **Test:** tests/fake/test_demo.py::test_dien_san

## REMOVED Requirements

### Requirement: Bàn giao hỏng bị bắt
"""


def test_gop_delta_them_sua_bo() -> None:
    delta = parse_delta("META-02-handoff", DELTA)
    assert isinstance(delta, Delta) and delta.capability == "handoff" and delta.ticket == "META-02"
    merged = apply_delta(parse_spec("handoff", SPEC), delta)
    assert [r.name for r in merged.requirements] == ["Bàn giao điền sẵn từ git", "Bàn giao hiện trên bảng"]
    assert "commit chưa đẩy" in merged.requirements[0].text
    assert "commit chưa đẩy" not in SPEC, "bản gốc không bị sửa tại chỗ"


@pytest.mark.parametrize(
    ("section_swap", "fragment"),
    [
        (
            (
                "## ADDED Requirements\n\n### Requirement: Bàn giao hiện trên bảng",
                "## ADDED Requirements\n\n### Requirement: Bàn giao điền sẵn từ git",
            ),
            "đã tồn tại",
        ),
        (
            (
                "### Requirement: Bàn giao điền sẵn từ git\nHệ thống SHALL điền nhánh, commit cuối, tệp",
                "### Requirement: Không có đâu\nHệ thống SHALL điền nhánh, commit cuối, tệp",
            ),
            "không tồn tại",
        ),
        (
            (
                "## REMOVED Requirements\n\n### Requirement: Bàn giao hỏng bị bắt",
                "## REMOVED Requirements\n\n### Requirement: Ma",
            ),
            "không tồn tại",
        ),
    ],
)
def test_delta_sai_bi_tu_choi(section_swap: tuple[str, str], fragment: str) -> None:
    old, new = section_swap
    assert old in DELTA
    with pytest.raises(AgentctlError, match=fragment):
        apply_delta(parse_spec("handoff", SPEC), parse_delta("META-02-handoff", DELTA.replace(old, new)))


def test_archive_ghi_dac_ta_chung_va_chuyen_delta(repo: Path) -> None:
    specs = repo / "docs" / "design" / "specs"
    (specs / "changes").mkdir(parents=True)
    (specs / "handoff.md").write_text(SPEC, encoding="utf-8")
    (specs / "changes" / "META-02-handoff.md").write_text(DELTA, encoding="utf-8")

    result = archive_delta(repo, "META-02-handoff", today="2026-10-04")
    assert result.requirements_after == 2
    assert not (specs / "changes" / "META-02-handoff.md").exists()
    assert (specs / "changes" / "archive" / "2026-10-04-META-02-handoff.md").exists()
    assert "Bàn giao hiện trên bảng" in (specs / "handoff.md").read_text(encoding="utf-8")
    with pytest.raises(AgentctlError, match="không thấy delta"):
        archive_delta(repo, "META-02-handoff", today="2026-10-04")


def test_archive_tao_dac_ta_moi_va_tu_choi_neu_ket_qua_hong(repo: Path) -> None:
    specs = repo / "docs" / "design" / "specs"
    (specs / "changes").mkdir(parents=True)
    added = DELTA.split("## MODIFIED")[0]
    (specs / "changes" / "META-03-moi.md").write_text(added, encoding="utf-8")
    archive_delta(repo, "META-03-moi", today="2026-10-04")
    assert (specs / "moi.md").is_file()

    bad = added.replace("SHALL liệt kê", "nên liệt kê")
    (specs / "changes" / "META-04-hong.md").write_text(bad, encoding="utf-8")
    with pytest.raises(AgentctlError, match="SHALL"):
        archive_delta(repo, "META-04-hong", today="2026-10-04")
    assert (specs / "changes" / "META-04-hong.md").exists(), "lỗi thì không đụng tệp nào"
    assert not (specs / "hong.md").exists()
