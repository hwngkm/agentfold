"""Phát hiện khoá thô trong cấu hình được commit (`.mcp.json`, khai báo MCP trong `packs/registry.yaml`).

Một nguồn cho cả lưới canh `tests/guards/test_mcp_no_secrets.py` lẫn `scripts/packs.py` — hai bản sao danh sách
tiền tố khoá sẽ trôi khỏi nhau, và bản bị bỏ quên là bản để lọt khoá.
"""

from __future__ import annotations

import re

KEY_PREFIXES = (
    "sk-",
    "sk_",
    "rnd_",
    "ghp_",
    "github_pat_",
    "hf_",
    "sbp_",
    "AIza",
    "xoxb-",
    "eyJ",
    "postgres://",
    "postgresql://",
)
ENV_REFERENCE = re.compile(r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?")
_SECRET_FIELDS = ("authorization", "api_key", "apikey", "token", "secret", "password")


def strings(node: object, path: str = "") -> list[tuple[str, str]]:
    if isinstance(node, dict):
        return [item for key, value in node.items() for item in strings(value, f"{path}.{key}" if path else str(key))]
    if isinstance(node, list):
        return [item for index, value in enumerate(node) for item in strings(value, f"{path}[{index}]")]
    return [(path, node)] if isinstance(node, str) else []


def secret_problems(data: object) -> list[str]:
    found = strings(data)
    problems = [f"{where}: trông như khoá thô" for where, value in found if any(p in value for p in KEY_PREFIXES)]
    problems += [
        f"{where}: header xác thực phải là `${{TEN_BIEN}}`"
        for where, value in found
        if any(word in where.lower() for word in _SECRET_FIELDS) and not ENV_REFERENCE.search(value)
    ]
    return problems
