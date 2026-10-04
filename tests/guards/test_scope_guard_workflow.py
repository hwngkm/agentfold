"""Workflow scope-guard kiểm PR bằng công cụ của commit GỐC, không bằng công cụ trong chính PR.

Vì sao: nếu bộ kiểm phạm vi chạy từ nhánh PR, một agent chỉ cần sửa `tools/agentctl/scope.py` để luôn trả
"không vi phạm" trong cùng PR đó. Bên bị kiểm không được cầm bộ kiểm.
Khoá gì: công cụ chạy từ worktree tại base sha; không `pull_request_target` (token ghi cho mã từ PR); quyền tối
thiểu; chạy lại khi gắn/gỡ nhãn duyệt; đòi claim và truyền nhãn PR.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _workflow() -> dict:
    return yaml.safe_load((ROOT / ".github/workflows/scope-guard.yml").read_text(encoding="utf-8"))


def _triggers(workflow: dict) -> dict:
    # PyYAML (YAML 1.1) đọc khoá `on` thành True.
    return workflow.get(True) or workflow.get("on") or {}


def test_scope_guard_chay_cong_cu_tu_commit_goc() -> None:
    steps = _workflow()["jobs"]["scope-guard"]["steps"]
    runs = [str(step.get("run", "")) for step in steps]
    assert any("git worktree add" in run and "BASE_SHA" in run and "RUNNER_TEMP" in run for run in runs), (
        "không thấy bước dựng worktree tại commit gốc"
    )
    checker = next(step for step in steps if "check-scope" in str(step.get("run", "")))
    assert "runner.temp" in str(checker.get("working-directory", "")), "bộ kiểm phải chạy trong worktree commit gốc"
    command = str(checker["run"])
    for flag in ("--repo", "--base", "--head", "--branch", "--labels", "--require-claim"):
        assert flag in command, f"lệnh check-scope thiếu {flag}"
    checkout = next(step for step in steps if str(step.get("uses", "")).startswith("actions/checkout"))
    assert checkout.get("with", {}).get("fetch-depth") == 0, "diff ba chấm cần lịch sử đầy đủ"


def test_scope_guard_an_toan_va_chay_lai_khi_doi_nhan() -> None:
    workflow = _workflow()
    triggers = _triggers(workflow)
    assert "pull_request_target" not in triggers, "pull_request_target cấp token ghi cho mã từ PR"
    types = set(triggers["pull_request"]["types"])
    assert {"opened", "synchronize", "reopened", "labeled", "unlabeled"} <= types
    assert workflow["permissions"] == {"contents": "read"}, "scope-guard chỉ cần đọc"
