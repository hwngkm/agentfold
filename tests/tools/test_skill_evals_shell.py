"""Lệnh agent của `skill_evals --run` phải chạy qua shell để `$(cat {prompt_file})` được bung ra.

Lỗi gốc (thấy khi làm benchmark có/không template): `run_agent` tách lệnh bằng `shlex.split` và chạy không qua shell, nên agent nhận NGUYÊN VĂN chuỗi
`$(cat ...)` thay vì lời nhắc — ví dụ ghi trong docstring và evals/README.md không bao giờ chạy đúng.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts import skill_evals as se

PROMPT = 'Hãy tạo tệp out.txt chứa lời nhắc này.\nDòng hai có "dấu ngoặc" và $đô-la.'


def _scenario() -> dict:
    return {
        "id": "shell-demo",
        "prompt": PROMPT,
        "setup": {"files": {"README.md": "x\n"}},
        "checks": [{"kind": "file_exists", "glob": "out.txt"}],
        "oracle": {"files": {"out.txt": "x"}},
    }


def _run(agent_cmd: str) -> tuple[str, list]:
    return se.run_agent(_scenario(), agent_cmd, timeout=30)


def test_lenh_agent_bung_cat_prompt_file_thanh_noi_dung_that(tmp_path: Path) -> None:
    prompt = tmp_path / "thu muc co dau cach" / "prompt.txt"
    prompt.parent.mkdir()
    prompt.write_text(PROMPT, encoding="utf-8")
    argv = se.build_argv('printf %s "$(cat {prompt_file})" > got.txt', prompt)
    subprocess.run(argv, cwd=tmp_path, check=True)
    assert (tmp_path / "got.txt").read_text(encoding="utf-8") == PROMPT


def test_run_agent_chay_lenh_qua_shell_va_cham_ket_qua() -> None:
    status, results = _run('printf %s "$(cat {prompt_file})" > out.txt')
    assert status == "pass", [r.detail for r in results]


def test_run_agent_van_chay_duoc_lenh_khong_dung_shell_dac_biet() -> None:
    status, results = _run("cp {prompt_file} out.txt")
    assert status == "pass", [r.detail for r in results]


def test_lenh_khong_tao_ra_ket_qua_van_bi_cham_truot() -> None:
    status, _ = _run("true")
    assert status == "fail"
