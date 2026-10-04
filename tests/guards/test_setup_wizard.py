"""Giao diện tạo dự án cho người không chuyên: an toàn, không lệch nguồn, không làm gì ngoài script có sẵn.

Vì sao: người dùng non-tech sẽ tin giao diện tuyệt đối. Nếu danh mục trong giao diện lệch sổ pack (pack đã xoá vẫn
hiện), lựa chọn của họ hỏng ở bước cuối; nếu giao diện tải script từ mạng hay hỏi khoá, nó thành đường lộ dữ liệu;
nếu bước "làm thật" chạy trên cây git bẩn, họ không còn cách xem lại/hoàn tác thay đổi.

Khoá gì: (1) danh mục nhúng trong wizard == sinh từ nguồn, nhãn loại dự án phủ đúng `project_types`; (2) wizard không
tải tài nguyên ngoài, không gọi mạng, không có ô mật khẩu/khoá; (3) tệp cấu hình sai bị từ chối với thông điệp rõ,
tổ hợp đội không đủ người bị chặn; (4) kế hoạch chỉ gồm script có sẵn; làm thật từ chối cây git bẩn và dừng ở bước lỗi.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

import pytest

from scripts import packs as packs_mod
from scripts import setup_project as sp

ROOT = Path(__file__).resolve().parents[2]
WIZARD = (ROOT / "wizard" / "index.html").read_text(encoding="utf-8")
GOOD = {
    "version": 1,
    "name": "Trợ lý kho thuốc",
    "slug": "tro-ly-kho-thuoc",
    "project_type": "ai-product",
    "team_size": "standard",
    "complexity": "strict",
    "packs": ["testing", "ai-llm", "testing"],
    "agent_tools": ["codex"],
}


def test_danh_muc_trong_wizard_khop_nguon() -> None:
    assert sp.wizard_with_catalog(WIZARD) == WIZARD, "chạy `python scripts/setup_project.py --write-wizard`"
    registry_types = set(packs_mod.load_registry()["project_types"])
    assert set(sp.PROJECT_TYPE_LABELS) == registry_types, (
        "mỗi loại dự án trong sổ cần nhãn ngôn ngữ thường và ngược lại"
    )


def test_wizard_khong_tai_tai_nguyen_ngoai_va_khong_hoi_bi_mat() -> None:
    assert not re.search(r"<(script|link|img|iframe)[^>]+(src|href)=[\"']https?:", WIZARD, re.I), "không tải gì từ mạng"
    assert not re.search(r"\bfetch\(|XMLHttpRequest|WebSocket|navigator\.sendBeacon", WIZARD), "không gọi mạng"
    inputs = re.findall(r"<input\b[^>]*>", WIZARD, re.I)
    assert inputs, "không đọc được ô nhập nào — lưới đang không kiểm gì"
    secret_like = [
        i for i in inputs if re.search(r"type=[\"']password|(id|name)=[\"'][^\"']*(key|token|secret|pass)", i, re.I)
    ]
    assert secret_like == [], f"không hỏi mật khẩu hay khoá: {secret_like}"


def test_tep_hop_le_duoc_chuan_hoa() -> None:
    setup = sp.validate(dict(GOOD))
    assert setup["packs"] == ["ai-llm", "testing"], "bỏ trùng, sắp xếp"


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"slug": "Tro Ly"}, "`slug`"),
        ({"project_type": "lạ"}, "`project_type`"),
        ({"team_size": "small", "complexity": "strict"}, "không đủ người duyệt"),
        ({"packs": ["khong-co"]}, "chưa sẵn sàng"),
        ({"agent_tools": ["skynet"]}, "`agent_tools`"),
        ({"version": 2}, "`version`"),
    ],
)
def test_tep_sai_bi_tu_choi_ro_rang(change: dict, fragment: str) -> None:
    with pytest.raises(sp.SetupError, match=fragment):
        sp.validate({**GOOD, **change})


def test_ke_hoach_chi_goi_script_co_san() -> None:
    steps = sp.plan(sp.validate(dict(GOOD)))
    scripts = {argv[0] for _label, argv in steps}
    assert scripts <= {"scripts/bootstrap.py", "scripts/generate_team_docs.py", "scripts/packs.py"}
    assert ["scripts/packs.py", "--install", "ai-llm"] in [argv for _l, argv in steps]


def test_lam_that_dung_o_buoc_loi_va_tu_choi_cay_ban(monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[Sequence[str]] = []

    def runner(argv: Sequence[str]) -> int:
        ran.append(argv)
        return 1 if argv[0] == "scripts/generate_team_docs.py" else 0

    setup = sp.validate(dict(GOOD))
    assert sp.apply(setup, runner=runner, require_clean=False) == 1
    assert [a[0] for a in ran] == ["scripts/bootstrap.py", "scripts/generate_team_docs.py"], "dừng ngay ở bước lỗi"

    monkeypatch.setattr(sp, "_git_clean", lambda: False)
    ran.clear()
    assert sp.apply(setup, runner=runner) == 1
    assert ran == [], "cây git bẩn thì không chạy bước nào"
