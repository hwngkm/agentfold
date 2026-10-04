"""Sổ bất biến (`docs/design/invariants.yaml`) trỏ tới lưới canh THẬT, và không lưới canh nào mồ côi.

Vì sao: một bất biến "được cưỡng chế bởi test X" mà X đã bị đổi tên hay xoá là lời hứa không có gì phía sau —
tệ hơn không có lời hứa, vì người đọc tin là đã có. Chiều ngược lại: lưới canh không bất biến nào nhận thì không
ai biết vì sao nó tồn tại, và sớm muộn bị gỡ trong một lần "dọn dẹp".
Khoá gì: mọi `enforced_by` tồn tại (đọc tên hàm bằng AST); mọi file `tests/guards/test_*.py` được nhận; bảng tóm
tắt trong AGENTS.md không bịa mã bất biến.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = yaml.safe_load((ROOT / "docs/design/invariants.yaml").read_text(encoding="utf-8"))
INVARIANTS: list[dict] = REGISTRY["invariants"]
_ID = re.compile(r"^INV-(?:\d{3}|D\d{2})$")


def _functions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)}


def missing_references(entries: list[str]) -> list[str]:
    missing: list[str] = []
    for entry in entries:
        rel, _, function = entry.partition("::")
        path = ROOT / rel
        if not path.is_file():
            missing.append(f"{entry} (không có file)")
        elif function and function not in _functions(path):
            missing.append(f"{entry} (không có hàm)")
    return missing


def test_so_dang_ky_dung_cau_truc() -> None:
    ids = [item["id"] for item in INVARIANTS]
    assert len(ids) == len(set(ids)), "mã bất biến trùng"
    for item in INVARIANTS:
        assert _ID.match(item["id"]), f"mã `{item['id']}` phải dạng INV-001 hoặc INV-D01"
        assert item["severity"] in {"critical", "high", "medium"}
        assert re.fullmatch(r"R\d+", item["owner"]), f"{item['id']}: chủ phải là vai trò R<n>"
        assert item["statement"].strip() and item["title"].strip()
        assert item["enforcement"] in {"automated", "manual"}
        if item["enforcement"] == "automated":
            assert item.get("enforced_by"), f"{item['id']}: tự động mà không trỏ tới lưới canh nào"


def test_moi_bat_bien_tro_toi_luoi_canh_ton_tai() -> None:
    missing = [ref for item in INVARIANTS for ref in missing_references(item.get("enforced_by", []))]
    assert not missing, f"bất biến trỏ vào khoảng không: {missing}"


def test_moi_file_luoi_canh_duoc_mot_bat_bien_nhan() -> None:
    referenced = {entry.partition("::")[0] for item in INVARIANTS for entry in item.get("enforced_by", [])}
    guards = {path.relative_to(ROOT).as_posix() for path in (ROOT / "tests/guards").glob("test_*.py")}
    assert len(guards) >= 10, "quét được quá ít lưới canh"
    orphans = sorted(guards - referenced)
    assert not orphans, f"lưới canh không bất biến nào nhận (thêm vào invariants.yaml hoặc gỡ có lý do): {orphans}"


def test_tom_tat_trong_agents_md_khong_bia_ma() -> None:
    summary_ids = set(re.findall(r"\bINV-\d{3}\b", (ROOT / "AGENTS.md").read_text(encoding="utf-8")))
    assert summary_ids, "AGENTS.md không còn bảng tóm tắt bất biến"
    assert summary_ids <= {item["id"] for item in INVARIANTS}


def test_bo_do_bat_duoc_tham_chieu_chet() -> None:
    fake = ["tests/guards/test_import_boundaries.py::khong_co_ham_nay", "tests/guards/khong_ton_tai.py"]
    assert len(missing_references(fake)) == 2
