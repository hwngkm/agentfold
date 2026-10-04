"""Sinh sơ đồ + bảng Mermaid từ nguồn sự thật máy đọc được — không chép tay thứ suy ra được.

Vì sao có file này: `docs/design/ARCHITECTURE.md` §3 từng CHÉP TAY bảng lớp/ranh giới từ
`contracts/boundaries.yaml`. Hai bản chép tay không có gì buộc chúng khớp nhau — thêm một lớp vào hợp
đồng mà quên sửa bảng thì tài liệu nói sai về chính hệ thống, và không ai biết. Ở đây bảng và sơ đồ đều
SINH RA từ hợp đồng; `scripts/generate_diagrams.py --check` đỏ ngay khi chúng lệch.

Sơ đồ nào KHÔNG sinh ở đây, và vì sao: bối cảnh hệ thống (§2) và luồng găng (§4) mã hoá QUYẾT ĐỊNH
PHẠM VI của con người — không suy được từ code. Lưới canh chỉ kiểm chúng CÓ MẶT, không kiểm đúng; nói
thẳng giới hạn đó thay vì giả vờ kiểm được.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from tools.agentctl.errors import AgentctlError
from tools.agentctl.policy import Policy

BOUNDARIES_PATH = "contracts/boundaries.yaml"

#: Vùng sinh tự động trong tài liệu. Nội dung giữa hai mốc bị GHI ĐÈ mỗi lần sinh.
REGION_OPEN = "<!-- GENERATED:{name} — sinh bởi scripts/generate_diagrams.py, không sửa tay -->"
REGION_CLOSE = "<!-- /GENERATED:{name} -->"

#: Vùng người vẽ. Lưới canh chỉ kiểm CÓ khối sơ đồ bên trong, không kiểm nội dung đúng.
HAND_OPEN = "<!-- HAND-DRAWN:{name} — người vẽ; sơ đồ này mã hoá quyết định, không suy ra được -->"
HAND_CLOSE = "<!-- /HAND-DRAWN:{name} -->"


class DiagramError(AgentctlError):
    """Nguồn sự thật thiếu hoặc sai cấu trúc, hoặc tài liệu thiếu vùng sinh."""


def load_boundaries(root: Path) -> dict[str, Any]:
    path = root / BOUNDARIES_PATH
    if not path.is_file():
        raise DiagramError(f"không thấy {BOUNDARIES_PATH}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise DiagramError(f"{BOUNDARIES_PATH} không phải YAML hợp lệ: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("layers"), dict):
        raise DiagramError(f"{BOUNDARIES_PATH} phải có mapping `layers`")
    return data


def _layers(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    layers: dict[str, dict[str, Any]] = {}
    for name, body in data["layers"].items():
        if not isinstance(body, dict):
            raise DiagramError(f"layers.{name} phải là mapping")
        layers[str(name)] = body
    return layers


def _mermaid_id(raw: str) -> str:
    """Mermaid không nhận mọi ký tự trong id nút — đưa về chữ/số/gạch dưới."""
    return re.sub(r"[^0-9A-Za-z_]", "_", raw)


def render_layers_table(data: dict[str, Any]) -> str:
    """Bảng lớp ↔ gói ↔ được import ↔ trách nhiệm — mọi cột đều suy từ hợp đồng, kể cả cột mô tả.

    Cột "Trách nhiệm" lấy từ `layers.<tên>.description` chứ không viết tay trong tài liệu: một cột viết
    tay cạnh ba cột sinh ra là chỗ duy nhất còn rời được khỏi hợp đồng.
    """
    layers = _layers(data)
    lines = ["| Lớp | Gói | Được import | Trách nhiệm |", "|---|---|---|---|"]
    for name, body in layers.items():
        packages = ", ".join(f"`{p}`" for p in body.get("packages", [])) or "—"
        allowed = body.get("may_import") or []
        # Một lớp được import TẤT CẢ lớp khác thì ghi "mọi lớp" cho người đọc, thay vì liệt kê dài.
        if allowed and set(allowed) == set(layers) - {name}:
            imports = "mọi lớp"
        else:
            imports = ", ".join(f"`{layer}`" for layer in allowed) or "— (không import lớp nào)"
        description = str(body.get("description") or "—")
        lines.append(f"| `{name}` | {packages} | {imports} | {description} |")
    return "\n".join(lines)


def render_layers_mermaid(data: dict[str, Any]) -> str:
    """Sơ đồ chiều import cho phép. Mũi tên A → B nghĩa là A ĐƯỢC PHÉP import B, không phải luồng dữ liệu."""
    layers = _layers(data)
    forbidden = (data.get("third_party") or {}).get("forbidden") or {}
    sdk_allowed = set((data.get("third_party") or {}).get("llm_sdks_allowed_in") or [])

    lines = ["```mermaid", "flowchart LR"]
    lines.append("    classDef pure fill:#e8f5e9,stroke:#2e7d32,color:#1b3d22;")
    lines.append("    classDef gateway fill:#e3f2fd,stroke:#1565c0,color:#10304f;")
    for name, body in layers.items():
        nid = _mermaid_id(name)
        packages = " · ".join(body.get("packages", [])) or "—"
        lines.append(f'    {nid}["{name}<br/>{packages}"]')
    for name, body in layers.items():
        for target in body.get("may_import") or []:
            lines.append(f"    {_mermaid_id(name)} --> {_mermaid_id(str(target))}")
    pure = [n for n, b in layers.items() if not (b.get("may_import") or []) and n in forbidden]
    for name in pure:
        lines.append(f"    class {_mermaid_id(name)} pure;")
    for name in sorted(sdk_allowed & set(layers)):
        lines.append(f"    class {_mermaid_id(name)} gateway;")
    lines.append("```")

    legend = []
    if pure:
        names = ", ".join(f"`{n}`" for n in pure)
        legend.append(f"Nền xanh lá ({names}): lõi tất định — không import lớp nào, và cấm cả SDK mạng/ORM/LLM.")
    if sdk_allowed:
        names = ", ".join(f"`{n}`" for n in sorted(sdk_allowed))
        legend.append(f"Nền xanh dương ({names}): cửa ngõ DUY NHẤT được import SDK nhà cung cấp LLM.")
    legend.append("Mũi tên `A → B` = A **được phép** import B. Chiều nào không có mũi tên là chiều bị lưới canh chặn.")
    return "\n".join(lines) + "\n\n" + "\n".join(legend)


def render_zones_mermaid(policy: Policy) -> str:
    """Sơ đồ ai sở hữu vùng nào + làn độc quyền, suy từ `coordination/policy.yaml`.

    Chủ vùng trong policy.yaml lại được sinh từ `docs/design/team-profile.yaml` — nên đổi team-size thì
    chạy `generate_team_docs.py` TRƯỚC, rồi mới sinh lại sơ đồ này.
    """
    lines = ["```mermaid", "flowchart LR"]
    lines.append("    classDef owner fill:#fff3e0,stroke:#b8862c,color:#4a3607;")
    lines.append("    classDef lane fill:#fdecea,stroke:#c1553a,color:#5b2416;")

    owners: list[str] = []
    for zone in policy.protected:
        for owner in zone.owners:
            if owner not in owners:
                owners.append(owner)
    for owner in owners:
        lines.append(f'    {_mermaid_id(owner)}(["{owner}"])')
    for zone in policy.protected:
        nid = "Z_" + _mermaid_id(zone.id)
        extra = "<br/>(thêm được)" if zone.allow_additions else ""
        paths = " · ".join(zone.paths[:3]) + ("…" if len(zone.paths) > 3 else "")
        lines.append(f'    {nid}["{zone.id}{extra}<br/>{paths}"]')
        for owner in zone.owners:
            lines.append(f"    {_mermaid_id(owner)} -- sở hữu --> {nid}")
    for lane in policy.exclusive:
        nid = "L_" + _mermaid_id(lane.id)
        paths = " · ".join(lane.paths[:3]) + ("…" if len(lane.paths) > 3 else "")
        lines.append(f'    {nid}{{{{"làn: {lane.id}<br/>{paths}"}}}}')
        lines.append(f"    class {nid} lane;")
    for owner in owners:
        lines.append(f"    class {_mermaid_id(owner)} owner;")
    lines.append("```")

    legend = [
        "Vùng bảo vệ: sửa được khi (a) PR có nhãn duyệt, (b) ticket đã duyệt khai id vùng trong "
        "`scope.protected`, hoặc (c) vùng cho `allow_additions` và thay đổi là THÊM file mới.",
        "Làn độc quyền (viền đỏ): **một ticket giữ tại một thời điểm** — không gắn chủ, gắn thứ tự.",
    ]
    return "\n".join(lines) + "\n\n" + "\n".join(legend)


def region_body(text: str, name: str) -> str | None:
    """Nội dung hiện có giữa hai mốc `GENERATED:<name>`; None nếu tài liệu chưa có vùng đó."""
    open_marker = REGION_OPEN.format(name=name)
    close_marker = REGION_CLOSE.format(name=name)
    start = text.find(open_marker)
    end = text.find(close_marker)
    if start == -1 or end == -1 or end < start:
        return None
    return text[start + len(open_marker) : end]


def replace_region(text: str, name: str, body: str) -> str:
    """Ghi đè nội dung giữa hai mốc. Thiếu mốc là lỗi cấu hình tài liệu, không im lặng thêm vào cuối file."""
    open_marker = REGION_OPEN.format(name=name)
    close_marker = REGION_CLOSE.format(name=name)
    start = text.find(open_marker)
    end = text.find(close_marker)
    if start == -1 or end == -1 or end < start:
        raise DiagramError(f"tài liệu thiếu vùng `GENERATED:{name}` — thêm cặp mốc:\n  {open_marker}\n  {close_marker}")
    return text[: start + len(open_marker)] + "\n" + body.strip("\n") + "\n" + text[end:]


def has_hand_drawn(text: str, name: str) -> bool:
    """Vùng người vẽ có tồn tại VÀ có ít nhất một khối sơ đồ (``` hoặc mermaid) bên trong."""
    open_marker = HAND_OPEN.format(name=name)
    close_marker = HAND_CLOSE.format(name=name)
    start = text.find(open_marker)
    end = text.find(close_marker)
    if start == -1 or end == -1 or end < start:
        return False
    return "```" in text[start + len(open_marker) : end]
