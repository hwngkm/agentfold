"""Cổng bằng chứng: phiên agent đã đổi tệp thì không được dừng khi chưa có lần kiểm nào ĐẠT trên đúng cây đó.

Vì sao: "xong" mà không chạy gì là lỗi lặp lại nhiều nhất của agent (R00.8 "bằng chứng thắng tự khai"); trước đây chỉ
người duyệt/supervisor bắt được, SAU khi việc đã báo xong. Ý tưởng mượn từ qkal/Canny ("sự thật mới được chặn"): ở đây sự
thật là dấu vân tay của cây làm việc lúc `scripts/ci_local.py` đạt, so với cây lúc agent định dừng.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from tests.tools.helpers import run_git
from tools.agentctl import evidence as ev


@pytest.fixture
def repo(tmp_path: Path, git_isolated: None) -> Path:
    path = tmp_path / "r"
    run_git(tmp_path, "init", "--quiet", "--initial-branch=main", str(path))
    (path / "a.py").write_text("x = 1\n", encoding="utf-8")
    run_git(path, "add", "a.py")
    run_git(path, "commit", "--quiet", "-m", "chore: đầu")
    return path


def test_dau_van_tay_doi_khi_sua_them_tep_hoac_commit(repo: Path) -> None:
    first = ev.fingerprint(repo)
    assert ev.fingerprint(repo) == first, "không đổi gì thì ổn định"
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    edited = ev.fingerprint(repo)
    (repo / "b.py").write_text("y = 1\n", encoding="utf-8")
    added = ev.fingerprint(repo)
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "--quiet", "-m", "feat: x")
    committed = ev.fingerprint(repo)
    assert len({first, edited, added, committed}) == 4


def test_cong_chi_chan_khi_doi_ma_chua_kiem(repo: Path) -> None:
    ev.record_session_start(repo, "s1")
    assert ev.stop_verdict(repo, "s1") is None, "phiên chỉ đọc/trả lời thì dừng tự do"
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    message = ev.stop_verdict(repo, "s1")
    assert message and "ci_local.py" in message
    ev.record_pass(repo, "python scripts/ci_local.py --fast")
    assert ev.stop_verdict(repo, "s1") is None, "đã kiểm đạt trên đúng cây này"
    (repo / "a.py").write_text("x = 3\n", encoding="utf-8")
    assert ev.stop_verdict(repo, "s1"), "sửa tiếp sau lần kiểm thì phải kiểm lại"


def test_khong_ket_vong_lap_va_tat_duoc_bang_cau_hinh(repo: Path) -> None:
    ev.record_session_start(repo, "s2")
    (repo / "a.py").write_text("x = 9\n", encoding="utf-8")
    verdicts = [ev.stop_verdict(repo, "s2") for _ in range(ev.MAX_BLOCKS + 1)]
    assert all(verdicts[: ev.MAX_BLOCKS]) and verdicts[-1] is None, "chặn tối đa MAX_BLOCKS lần rồi nhường người"
    ev.record_session_start(repo, "s3")
    (repo / "a.py").write_text("x = 10\n", encoding="utf-8")
    run_git(repo, "config", "agentctl.evidenceGate", "off")
    assert ev.stop_verdict(repo, "s3") is None


def test_hook_doc_payload_va_thoat_ma_2(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.chdir(repo)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(repo))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"session_id": "s4", "hook_event_name": "SessionStart"})))
    assert ev.hook_main(["start"]) == 0
    (repo / "a.py").write_text("x = 4\n", encoding="utf-8")
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"session_id": "s4", "hook_event_name": "Stop"})))
    assert ev.hook_main(["stop"]) == 2
    assert "ci_local.py" in capsys.readouterr().err
    monkeypatch.setattr("sys.stdin", io.StringIO("không phải json"))
    assert ev.hook_main(["stop"]) == 0, "hook hỏng thì cho qua"
