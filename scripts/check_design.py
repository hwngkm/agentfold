"""Bộ kiểm DESIGN.md — token thiết kế máy đọc + lý do — và bộ sinh DESIGN.md khởi đầu.

    python scripts/check_design.py DESIGN.md        # in JSON {findings, summary}; thoát 1 nếu có lỗi
    python scripts/check_design.py --init --name "Kho thuốc" --primary "#0F766E" --background "#FFFFFF" --text "#0F172A" --out DESIGN.md

Bám đặc tả google-labs-code/design.md (README, đối chiếu ngày 2026-10-04, định dạng `alpha`): front matter YAML (`colors`, `typography`,
`rounded`, `spacing`, `components`) + các mục `##` theo thứ tự cố định. Chỉ dùng thư viện chuẩn + PyYAML (đã là phụ thuộc của repo);
KHÔNG gọi `npx @google/design.md` để không thêm phụ thuộc Node hay mạng. Chỉ đo tương phản với màu hex (`#RGB`, `#RRGGBB`); màu kiểu khác
(`oklch()`, tên màu) được báo "không đo được" chứ không đoán.

Luật (lấy từ bảng lint của đặc tả):
  error    tham chiếu `{colors.x}` không trỏ tới token nào · cặp chữ/nền của component dưới WCAG AA 4.5:1 · trùng tiêu đề mục · front matter hỏng
  warning  thiếu màu `primary` · có màu mà không có typography · mục sai thứ tự · khoá cấp cao giống lỗi chính tả của khoá chuẩn · màu không đo được
Đặc tả xếp `contrast-ratio` là warning; ở đây là error vì tiêu chí nghiệm thu của template đòi bộ kiểm đỏ khi cặp chữ/nền không đạt AA.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC_CHECKED = "2026-10-04"
SPEC_VERSION = "alpha"
AA_NORMAL = 4.5

#: Thứ tự mục bắt buộc của đặc tả; mục có thể vắng, nhưng mục có mặt phải đúng thứ tự.
SECTIONS = (
    "Overview",
    "Colors",
    "Typography",
    "Layout",
    "Elevation & Depth",
    "Shapes",
    "Components",
    "Do's and Don'ts",
)
ALIASES = {"Brand & Style": "Overview", "Layout & Spacing": "Layout", "Elevation": "Elevation & Depth"}
TOP_KEYS = ("version", "name", "description", "omitted", "colors", "typography", "rounded", "spacing", "components")

_HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_REF = re.compile(r"^\{([^{}]+)\}$")
_HEADING = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
Finding = dict[str, str]


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        raise ValueError("thiếu front matter YAML (tệp phải bắt đầu bằng `---`)")
    end = normalized.find("\n---", 4)
    if end == -1:
        raise ValueError("front matter không có dòng `---` đóng")
    try:
        data = yaml.safe_load(normalized[4:end])
    except yaml.YAMLError as exc:
        raise ValueError(f"front matter không phải YAML hợp lệ: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("front matter phải là một mapping")
    return data, normalized[end + 4 :].lstrip("\n")


def _rgb(color: str) -> tuple[float, float, float] | None:
    if not isinstance(color, str) or not _HEX.match(color.strip()):
        return None
    digits = color.strip().lstrip("#")
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return tuple(int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _luminance(rgb: tuple[float, float, float]) -> float:
    def channel(value: float) -> float:
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(foreground: str, background: str) -> float | None:
    """Tỷ lệ tương phản WCAG 2.x giữa hai màu hex; `None` nếu một trong hai không phải hex (không đoán)."""
    fg, bg = _rgb(foreground), _rgb(background)
    if fg is None or bg is None:
        return None
    lighter, darker = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _lookup(data: dict[str, Any], path: str) -> Any:
    node: Any = data
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _resolve(data: dict[str, Any], value: Any, depth: int = 0) -> Any:
    match = _REF.match(value) if isinstance(value, str) else None
    if match is None or depth > 8:
        return value
    return _resolve(data, _lookup(data, match.group(1)), depth + 1)


def _walk(node: Any, path: str = "") -> Iterator[tuple[str, str]]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _walk(value, f"{path}.{key}" if path else str(key))
    elif isinstance(node, str):
        yield path, node


def _finding(severity: str, path: str, message: str) -> Finding:
    return {"severity": severity, "path": path, "message": message}


def lint(text: str) -> list[Finding]:
    try:
        data, body = split_front_matter(text)
    except ValueError as exc:
        return [_finding("error", "front-matter", str(exc))]
    findings: list[Finding] = []

    for key in data:
        if key not in TOP_KEYS:
            close = difflib.get_close_matches(str(key), TOP_KEYS, n=1, cutoff=0.75)
            if close:
                findings.append(_finding("warning", str(key), f"khoá `{key}` giống lỗi chính tả của `{close[0]}`"))

    for path, value in _walk(data):
        match = _REF.match(value)
        if match and _lookup(data, match.group(1)) is None:
            findings.append(_finding("error", path, f"tham chiếu `{value}` không trỏ tới token nào"))

    colors = data.get("colors") if isinstance(data.get("colors"), dict) else {}
    if colors and "primary" not in colors:
        findings.append(_finding("warning", "colors", "có màu nhưng thiếu `primary` — agent sẽ tự sinh một màu"))
    if colors and not data.get("typography"):
        findings.append(
            _finding("warning", "typography", "có màu nhưng không có token typography — agent dùng phông mặc định")
        )

    raw_components = data.get("components")
    components: dict[str, Any] = raw_components if isinstance(raw_components, dict) else {}
    for name, props in components.items():
        if not isinstance(props, dict) or "backgroundColor" not in props or "textColor" not in props:
            continue
        where = f"components.{name}"
        fg, bg = _resolve(data, props["textColor"]), _resolve(data, props["backgroundColor"])
        ratio = contrast_ratio(str(fg), str(bg))
        if ratio is None:
            if fg is not None and bg is not None:  # token gãy đã được báo là error ở trên
                findings.append(
                    _finding("warning", where, f"màu chữ ({fg}) hoặc nền ({bg}) không đo được (chỉ đo màu hex)")
                )
        elif ratio < AA_NORMAL:
            findings.append(
                _finding(
                    "error", where, f"chữ {fg} trên nền {bg} có tương phản {ratio:.2f}:1, dưới WCAG AA {AA_NORMAL}:1"
                )
            )

    headings = [ALIASES.get(h, h) for h in _HEADING.findall(body)]
    seen: set[str] = set()
    for heading in headings:
        if heading in seen:
            findings.append(
                _finding("error", f"## {heading}", f"tiêu đề mục `{heading}` bị trùng — đặc tả từ chối tệp")
            )
        seen.add(heading)
    known = [SECTIONS.index(h) for h in headings if h in SECTIONS]
    if known != sorted(known):
        findings.append(
            _finding("warning", "sections", f"các mục chuẩn sai thứ tự; thứ tự đúng: {', '.join(SECTIONS)}")
        )
    return findings


def _on_color(color: str) -> str:
    """Chữ trắng hoặc đen, cái nào tương phản hơn với `color` — luôn ≥ 4.58:1 với mọi màu nền."""
    white = contrast_ratio("#FFFFFF", color) or 0.0
    black = contrast_ratio("#000000", color) or 0.0
    return "#FFFFFF" if white >= black else "#000000"


def _norm(color: str, label: str) -> str:
    if _rgb(color) is None:
        raise ValueError(f"màu {label} `{color}` phải là mã hex (#RGB hoặc #RRGGBB)")
    digits = color.strip().lstrip("#")
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return f"#{digits.upper()}"


def starter(*, name: str, primary: str, background: str, text: str) -> str:
    """DESIGN.md khởi đầu từ ba lựa chọn của người dùng; luôn qua `lint` không lỗi, nếu không thì ném ValueError."""
    clean = (name or "").strip()
    if not clean:
        raise ValueError("thiếu tên dự án (tên không được để trống)")
    primary, background, text = _norm(primary, "chính"), _norm(background, "nền"), _norm(text, "chữ")
    ratio = contrast_ratio(text, background) or 0.0
    if ratio < AA_NORMAL:
        raise ValueError(
            f"chữ {text} trên nền {background} chỉ đạt {ratio:.2f}:1, dưới WCAG AA {AA_NORMAL}:1 — chọn màu chữ đậm hơn"
        )
    on_primary = _on_color(primary)
    title = json.dumps(clean, ensure_ascii=False)
    document = f"""---
version: {SPEC_VERSION}
name: {title}
colors:
  primary: "{primary}"
  on-primary: "{on_primary}"
  background: "{background}"
  on-background: "{text}"
typography:
  body-md:
    fontFamily: system-ui
    fontSize: 1rem
    lineHeight: 1.5
  h1:
    fontFamily: system-ui
    fontSize: 2rem
    fontWeight: 700
rounded:
  sm: 4px
  md: 8px
spacing:
  sm: 8px
  md: 16px
  lg: 24px
components:
  page:
    backgroundColor: "{{colors.background}}"
    textColor: "{{colors.on-background}}"
    typography: "{{typography.body-md}}"
  button-primary:
    backgroundColor: "{{colors.primary}}"
    textColor: "{{colors.on-primary}}"
    rounded: "{{rounded.sm}}"
    padding: 12px
---

## Overview

Bản sắc giao diện khởi đầu của **{clean}**, sinh từ ba lựa chọn: màu chính, màu nền, màu chữ. Sửa tệp này khi thương hiệu đổi;
mọi thay đổi màu đi qua `python scripts/check_design.py DESIGN.md` để giữ chữ đọc được (WCAG AA 4.5:1).

## Colors

- **Primary ({primary}):** màu hành động chính (nút, liên kết). Chữ trên nó dùng `on-primary` ({on_primary}).
- **Background ({background}) / On-background ({text}):** nền trang và chữ thường, tương phản {ratio:.2f}:1.

## Typography

Phông hệ thống (`system-ui`) để không tải gì từ ngoài. Thân bài 1rem, tiêu đề lớn 2rem đậm.

## Layout

Khoảng cách theo thang 8/16/24px; chỉ dùng các bậc này, không giá trị tuỳ ý.

## Components

- `button-primary`: nền `primary`, chữ `on-primary`, bo góc nhỏ.
- `page`: nền và chữ thường của trang.

## Do's and Don'ts

- Dùng token trong tệp này, không viết thẳng mã màu vào component.
- Màu trạng thái luôn đi kèm chữ hoặc biểu tượng, không chỉ bằng màu.
"""
    problems = [f for f in lint(document) if f["severity"] == "error"]
    if problems:
        raise ValueError("bản khởi đầu không qua bộ kiểm: " + "; ".join(f["message"] for f in problems))
    return document


def _report(findings: list[Finding]) -> dict[str, Any]:
    return {
        "findings": findings,
        "summary": {
            "errors": sum(f["severity"] == "error" for f in findings),
            "warnings": sum(f["severity"] == "warning" for f in findings),
        },
    }


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", nargs="?", default="DESIGN.md", help="tệp DESIGN.md cần kiểm (mặc định DESIGN.md)")
    parser.add_argument("--init", action="store_true", help="sinh DESIGN.md khởi đầu thay vì kiểm")
    parser.add_argument("--name")
    parser.add_argument("--primary")
    parser.add_argument("--background")
    parser.add_argument("--text")
    parser.add_argument("--out", default="DESIGN.md", help="nơi ghi khi --init (mặc định DESIGN.md)")
    args = parser.parse_args(argv)

    if args.init:
        try:
            document = starter(
                name=args.name or "", primary=args.primary or "", background=args.background or "", text=args.text or ""
            )
        except ValueError as exc:
            print(f"🔴 {exc}", file=sys.stderr)
            return 1
        Path(args.out).write_text(document, encoding="utf-8", newline="\n")
        print(f"✅ Đã sinh {args.out}")
        return 0

    try:
        text = Path(args.file).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"🔴 không đọc được {args.file}: {exc}", file=sys.stderr)
        return 1
    report = _report(lint(text))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["summary"]["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
