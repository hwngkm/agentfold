"""Import giữa các lớp của `src/` chỉ đi theo chiều khai trong `contracts/boundaries.yaml`.

Vì sao: "LLM không được tính số" chỉ là lời hứa nếu không có gì ngăn một dòng `import openai` xuất
hiện trong lõi tất định. Đã có dự án liệt kê TAY danh sách file cấm import LLM và chỉ phủ
một nửa số file của tầng nghiệp vụ — file mới không được canh. Lưới này suy lớp từ đường dẫn, nên mọi file
thêm sau tự động bị ràng buộc.

Khoá gì: KẾT QUẢ (không module nào import sai chiều), đọc bằng AST — docstring nhắc tên thư viện
không làm lưới báo động giả.
Sửa khi đỏ: chuyển logic về đúng lớp, hoặc (nếu thật sự đổi kiến trúc) viết ADR rồi sửa hợp đồng.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
CONTRACT = yaml.safe_load((ROOT / "contracts" / "boundaries.yaml").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Import:
    module: str
    line: int


def module_name(path: Path) -> str:
    parts = list(path.relative_to(ROOT).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def imports_of(source: str, module: str, *, is_package: bool) -> list[Import]:
    """Mọi module được import, kể cả import tương đối đã quy về tên tuyệt đối."""
    found: list[Import] = []
    package = module if is_package else module.rpartition(".")[0]
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found += [Import(alias.name, node.lineno) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package.split(".")
                base = base[: len(base) - (node.level - 1)]
                target = ".".join([*base, node.module] if node.module else base)
            else:
                target = node.module or ""
            found.append(Import(target, node.lineno))
    return found


def layer_of(module: str) -> str | None:
    if module == "src":
        return "root"  # chỉ `src/__init__.py`: gói gốc không được import gì
    best: tuple[int, str] | None = None
    for layer, spec in CONTRACT["layers"].items():
        for package in spec["packages"]:
            if (module == package or module.startswith(package + ".")) and (best is None or len(package) > best[0]):
                best = (len(package), layer)
    return best[1] if best else None


def _matches(name: str, prefixes: list[str]) -> bool:
    return any(name == prefix or name.startswith(prefix + ".") for prefix in prefixes)


def violations(source: str, module: str, *, is_package: bool = False) -> list[str]:
    layer = layer_of(module)
    if layer is None:
        return [f"{module}: không thuộc lớp nào trong contracts/boundaries.yaml"]
    allowed = {layer, *CONTRACT["layers"].get(layer, {}).get("may_import", [])}
    forbidden = CONTRACT["third_party"]["forbidden"].get(layer, [])
    sdk_ok = layer in CONTRACT["third_party"]["llm_sdks_allowed_in"]
    problems: list[str] = []
    for item in imports_of(source, module, is_package=is_package):
        where = f"{module}:{item.line} import `{item.module}`"
        if item.module == "src" or item.module.startswith("src."):
            target = layer_of(item.module)
            if target is not None and target not in allowed:
                problems.append(f"{where} — lớp `{layer}` không được import lớp `{target}`")
        elif _matches(item.module, forbidden):
            problems.append(f"{where} — lớp `{layer}` cấm thư viện này")
        elif not sdk_ok and _matches(item.module, CONTRACT["third_party"]["llm_sdks"]):
            problems.append(f"{where} — SDK LLM chỉ được dùng trong {CONTRACT['third_party']['llm_sdks_allowed_in']}")
    return problems


SOURCE_FILES = sorted(SRC.rglob("*.py"))


def test_co_file_de_quet() -> None:
    """Lưới cho chính lưới: glob rỗng thì mọi test bên dưới xanh vô nghĩa."""
    assert len(SOURCE_FILES) >= 15, f"chỉ thấy {len(SOURCE_FILES)} file trong src/"


@pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_moi_module_ton_trong_ranh_gioi_lop(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    assert violations(source, module_name(path), is_package=path.name == "__init__.py") == []


@pytest.mark.parametrize(
    ("source", "module", "fragment"),
    [
        ("import openai\n", "src.domain.catalog.pricing", "cấm thư viện"),
        ("from sqlalchemy import select\n", "src.domain.catalog.pricing", "cấm thư viện"),
        ("from src.llm.gateway import LLMGateway\n", "src.api.routes.x", "không được import lớp `llm`"),
        ("from ..llm import gateway\n", "src.domain.catalog", "không được import lớp `llm`"),
        ("import anthropic\n", "src.agents.quote_agent", "SDK LLM chỉ được dùng"),
        ("import os\n", "src.newpkg.x", "không thuộc lớp nào"),
    ],
)
def test_bo_do_bat_duoc_vi_pham_that(source: str, module: str, fragment: str) -> None:
    """Chứng minh bộ dò đỏ được — kể cả import tương đối và gói chưa khai báo."""
    assert any(fragment in problem for problem in violations(source, module, is_package=False))


def test_docstring_nhac_ten_thu_vien_khong_bi_bao_dong_gia() -> None:
    source = '"""Không bao giờ import openai ở đây."""\nfrom decimal import Decimal\n'
    assert violations(source, "src.domain.catalog.pricing") == []
