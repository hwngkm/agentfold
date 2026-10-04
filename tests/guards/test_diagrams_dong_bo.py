"""Sơ đồ/bảng trong `docs/design/ARCHITECTURE.md` phải khớp nguồn sự thật — cùng mẫu với
`test_team_profile.py` và `test_openapi_contract.py`.

Vì sao: §3 từng CHÉP TAY bảng lớp/ranh giới từ `contracts/boundaries.yaml`. Hai bản chép tay không có
gì buộc chúng khớp — thêm một lớp vào hợp đồng mà quên sửa bảng thì tài liệu nói sai về chính hệ thống,
im lặng, và người đọc tin bảng chứ không đi đọc YAML. Cùng lớp lỗi mà `test_openapi_contract.py` chặn
cho hợp đồng API, áp lại đây cho kiến trúc.

Khoá gì: (1) mọi vùng `GENERATED:` trong tài liệu bằng đúng thứ bộ sinh tạo ra từ nguồn hiện tại;
(2) mọi lớp khai trong hợp đồng đều xuất hiện trong bảng và sơ đồ; (3) hai sơ đồ NGƯỜI VẼ (§2 bối cảnh,
§4 luồng găng) còn nguyên — chúng mã hoá quyết định phạm vi, mất đi là mất thiết kế, không phải mất
trang trí; (4) bộ sinh thật sự đọc nguồn, không trả về văn bản hằng.

Sửa khi đỏ: `python scripts/generate_diagrams.py`, đọc diff, commit cùng PR. ĐỪNG sửa tay trong vùng
`GENERATED:` — lần sinh sau sẽ ghi đè, và CI lại đỏ. Muốn đổi nội dung bảng thì sửa
`contracts/boundaries.yaml` (kể cả `description`) hoặc `coordination/policy.yaml`.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from tools.agentctl.policy import load_policy
from tools.diagrams import (
    DiagramError,
    has_hand_drawn,
    load_boundaries,
    region_body,
    render_layers_mermaid,
    render_layers_table,
    render_zones_mermaid,
    replace_region,
)

ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURE = ROOT / "docs" / "design" / "ARCHITECTURE.md"

#: Sơ đồ người vẽ bắt buộc có mặt. Lưới chỉ kiểm CÓ, không kiểm ĐÚNG — nói thẳng giới hạn thay vì
#: giả vờ kiểm được một quyết định thiết kế bằng test.
HAND_DRAWN_BAT_BUOC = ["context", "flow"]


@pytest.fixture(scope="module")
def text() -> str:
    return ARCHITECTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def boundaries() -> dict:
    return load_boundaries(ROOT)


def test_vung_sinh_ra_khop_nguon_su_that(text: str, boundaries: dict) -> None:
    layers_body = render_layers_table(boundaries) + "\n\n" + render_layers_mermaid(boundaries)
    expected = replace_region(text, "layers", layers_body)
    expected = replace_region(expected, "ownership", render_zones_mermaid(load_policy(ROOT, None)))
    assert text == expected, (
        "ARCHITECTURE.md lệch boundaries.yaml/policy.yaml — chạy `python scripts/generate_diagrams.py`"
    )


def test_moi_lop_trong_hop_dong_deu_co_trong_tai_lieu(text: str, boundaries: dict) -> None:
    """Bất biến KẾT QUẢ: thêm lớp vào hợp đồng mà tài liệu không nhắc tới lớp đó là tài liệu nói thiếu.

    Không khoá cách trình bày (bảng hay sơ đồ, thứ tự, nhãn) — chỉ khoá "lớp nào có trong hợp đồng thì
    phải thấy được trong tài liệu", nên refactor cách vẽ không làm lưới đỏ oan (R80.3).
    """
    body = region_body(text, "layers")
    assert body is not None, "thiếu vùng GENERATED:layers trong ARCHITECTURE.md"
    thieu = [name for name in boundaries["layers"] if name not in body]
    assert not thieu, f"lớp khai trong hợp đồng nhưng không xuất hiện trong tài liệu: {thieu}"


def test_so_do_nguoi_ve_con_nguyen(text: str) -> None:
    thieu = [name for name in HAND_DRAWN_BAT_BUOC if not has_hand_drawn(text, name)]
    assert not thieu, (
        f"thiếu sơ đồ người vẽ (hoặc vùng còn mốc nhưng rỗng): {thieu}. "
        "Hai sơ đồ này mã hoá quyết định phạm vi — bộ sinh KHÔNG dựng lại được cho bạn."
    )


def test_bo_sinh_doc_nguon_that_khong_tra_van_ban_hang(boundaries: dict) -> None:
    """Chứng minh lưới ở trên không xanh một cách vô nghĩa.

    Một bộ sinh trả về văn bản hằng vẫn làm `test_vung_sinh_ra_khop_nguon_su_that` xanh vĩnh viễn. Đổi
    nguồn trong bộ nhớ rồi đòi đầu ra phải đổi theo — đây là phiên bản test của thói quen "phải thấy
    đỏ trước khi tin" (R80.4).
    """
    goc = render_layers_table(boundaries)
    doi = copy.deepcopy(boundaries)
    doi["layers"]["domain"]["description"] = "MÔ TẢ THỬ KHÔNG BAO GIỜ COMMIT"
    assert render_layers_table(doi) != goc, "bảng không đổi khi hợp đồng đổi — bộ sinh không đọc nguồn"

    them = copy.deepcopy(boundaries)
    them["layers"]["lop_moi_thu"] = {"packages": ["src.lop_moi_thu"], "may_import": [], "description": "thử"}
    assert "lop_moi_thu" in render_layers_mermaid(them), "sơ đồ bỏ qua lớp mới trong hợp đồng"


def test_thieu_moc_thi_bao_loi_chu_khong_am_tham_them_vao_cuoi_file() -> None:
    """Mốc bị xoá nhầm phải thành lỗi ồn ào: im lặng ghi vào cuối file là cách tài liệu mọc hai bản."""
    with pytest.raises(DiagramError, match="thiếu vùng"):
        replace_region("# tài liệu không có mốc nào\n", "layers", "nội dung")
