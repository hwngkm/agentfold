"""`docs/GOVERNANCE.md`, `.github/CODEOWNERS`, và `owners:` trong `policy.yaml` phải khớp
`docs/design/team-profile.yaml` — cùng mẫu với `test_openapi_contract.py`.

Vì sao: nếu ba file đó có thể trôi khỏi profile, "ai chịu trách nhiệm vùng nào" trở thành ba nguồn sự
thật không đồng bộ — đúng lớp lỗi mà `AGENTS.md` một-nguồn-luật (INV-003) đã chặn cho luật, áp lại đây
cho vai trò. Sửa khi đỏ: `python scripts/generate_team_docs.py`, đọc diff, commit cùng lúc.
"""

from __future__ import annotations

from itertools import product
from pathlib import Path

import pytest

from tools.agentctl.policy import POLICY_PATH
from tools.agentctl.team_profile import (
    COMPLEXITIES,
    TEAM_SIZES,
    TeamProfileError,
    build_profile,
    load_team_profile,
    patch_policy_owners,
    render_codeowners,
    render_governance,
)

ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE = ROOT / "docs" / "GOVERNANCE.md"
CODEOWNERS = ROOT / ".github" / "CODEOWNERS"
POLICY_FILE = ROOT / POLICY_PATH
#: Tổ hợp không đủ người để complexity đó yêu cầu (docs/design/presets/README.md) — cố ý không dựng được.
INCOMPATIBLE = {("small", "strict")}


def test_ba_file_khop_team_profile_dang_ap_dung() -> None:
    profile = load_team_profile(ROOT)
    assert GOVERNANCE.read_text(encoding="utf-8") == render_governance(profile), (
        "docs/GOVERNANCE.md lệch team-profile.yaml — chạy `python scripts/generate_team_docs.py`"
    )
    assert CODEOWNERS.read_text(encoding="utf-8") == render_codeowners(profile), (
        ".github/CODEOWNERS lệch team-profile.yaml — chạy `python scripts/generate_team_docs.py`"
    )
    policy_text = POLICY_FILE.read_text(encoding="utf-8")
    assert policy_text == patch_policy_owners(policy_text, profile), (
        f"{POLICY_PATH}: `owners:` lệch team-profile.yaml — chạy `python scripts/generate_team_docs.py`"
    )


@pytest.mark.parametrize(("team_size", "complexity"), sorted(set(product(TEAM_SIZES, COMPLEXITIES)) - INCOMPATIBLE))
def test_moi_to_hop_tuong_thich_dung_duoc(team_size: str, complexity: str) -> None:
    profile = build_profile(team_size, complexity)
    handles = [role.handle for role in profile.roles]
    assert len(handles) == len(set(handles)), f"{team_size}+{complexity}: hai vai trò trùng handle CODEOWNERS {handles}"
    # Không được rỗng và phải dựng được cả hai file mà không lỗi.
    assert render_governance(profile) and render_codeowners(profile)


@pytest.mark.parametrize(("team_size", "complexity"), sorted(INCOMPATIBLE))
def test_to_hop_khong_du_nguoi_bi_tu_choi_ro_rang(team_size: str, complexity: str) -> None:
    with pytest.raises(TeamProfileError, match="không đủ người"):
        build_profile(team_size, complexity)


def _codeowners_patterns(text: str) -> list[str]:
    lines = [line for line in text.splitlines() if line and not line.startswith("#")]
    return [line.split()[0] for line in lines if line.split()[0] != "*"]


def test_pattern_cu_the_luon_dung_sau_pattern_rong_chua_no() -> None:
    """Bất biến NGỮ NGHĨA thật, không phải cách cài đặt: GitHub lấy pattern KHỚP CUỐI trong file — nên với
    mọi cặp (rộng, cụ thể) mà pattern rộng là tiền tố chuỗi của pattern cụ thể (vd. `/web/` và
    `/web/AGENTS.md`), pattern cụ thể phải đứng SAU — nếu không, pattern rộng (đứng sau) sẽ đè lên nó.

    Dựng lại từ `render_codeowners(profile)` — không đọc file tĩnh trên đĩa — để đột biến trong
    `team_profile.py` thật sự bị bài test này bắt, không chỉ bắt được lỗi ai đó sửa tay file đã sinh.

    Cố ý không khoá "sắp theo độ dài": một đột biến đổi khoá sắp sang bảng chữ cái
    (`entries.sort(key=lambda e: e[0])`) KHÔNG vi phạm bất biến này — so sánh chuỗi kiểu Python đã tự đặt
    một tiền tố trước phần mở rộng của nó. Bài học giữ lại: khoá đúng thứ quan sát được (ai thắng ai),
    không khoá chiến lược cài đặt cụ thể tình cờ đang dùng.
    """
    patterns = _codeowners_patterns(render_codeowners(load_team_profile(ROOT)))
    assert len(patterns) > 10, "đọc được quá ít pattern — lưới đang không kiểm gì"
    vi_pham = [
        f"`{specific}` (chỉ số {j}) đứng TRƯỚC `{general}` (chỉ số {i}) dù cụ thể hơn — "
        f"GitHub lấy pattern khớp CUỐI nên `{general}` sẽ đè lên `{specific}`"
        for i, general in enumerate(patterns)
        for j, specific in enumerate(patterns)
        if j < i and general != specific and specific.startswith(general)
    ]
    assert not vi_pham, "\n".join(vi_pham)


def test_web_agents_md_thang_web() -> None:
    """Ca cụ thể đã gây lỗi thật lúc thiết kế: `/web/AGENTS.md` phải đứng SAU `/web/` để thắng."""
    lines = CODEOWNERS.read_text(encoding="utf-8").splitlines()
    generic = next(i for i, line in enumerate(lines) if line.startswith("/web/ ") or line.startswith("/web/\t"))
    specific = next(i for i, line in enumerate(lines) if line.startswith("/web/AGENTS.md"))
    assert specific > generic


def test_patch_policy_owners_thuc_su_doi_gia_tri() -> None:
    """Test riêng cho hàm patch, không qua so sánh với file đã đồng bộ sẵn.

    `test_ba_file_khop_team_profile_dang_ap_dung` không bắt được một `patch_policy_owners` bị biến thành
    no-op: vì file đang SẴN khớp profile, "không đổi gì" tình cờ vẫn khớp. Test này cần một profile mà
    OPS chắc chắn KHÁC OPS hiện tại — để buộc hàm phải thực sự thay giá trị, không phải tình cờ giữ nguyên.

    🔒 KHÔNG hardcode một preset cụ thể (từng là `small`/`lite`): dự án đổi team-size đang áp dụng (đúng
    thứ tính năng này CHO PHÉP làm) khiến "profile khác" hardcoded trùng luôn profile hiện tại, và tiền đề
    `!=` tự vỡ — lỗi thật, bắt được khi thử đổi sống team-size trong một bản pilot (16/09/2026). Hai ứng
    viên `standard` (OPS=R3) và `solo` (OPS=R1) có OPS khác NHAU, nên ít nhất một trong hai luôn khác
    profile đang áp dụng, bất kể profile đó là preset nào.
    """
    current = load_team_profile(ROOT)
    other = next(
        p
        for p in (build_profile("standard", "standard"), build_profile("solo", "lite"))
        if p.owner("OPS") != current.owner("OPS")
    )
    policy_text = POLICY_FILE.read_text(encoding="utf-8")
    patched = patch_policy_owners(policy_text, other)
    assert patched != policy_text
    assert f"owners: [{other.owner('OPS')}]  # OWNER:OPS" in patched


def test_bo_do_bat_duoc_ba_file_troi_khoi_profile() -> None:
    profile = load_team_profile(ROOT)
    tampered = render_governance(profile).replace("R1", "R9", 1)
    assert tampered != GOVERNANCE.read_text(encoding="utf-8")
