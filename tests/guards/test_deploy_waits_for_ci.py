"""Deploy chỉ đi SAU CI — và mọi giả định mà cổng ấy dựa vào vẫn còn đúng.

Vì sao: đã có dự án đưa lên production một commit có test cổng duyệt ĐỎ — nền tảng deploy mặc định
deploy mọi commit. Cổng `autoDeployTrigger: checksPass` chỉ an toàn khi: (1) trường còn trong render.yaml;
(2) không job nào bị bỏ qua trên lần đẩy vào `main` (`skipped` tính là QUA); (3) không job nào `needs` job khác
(check của job con chưa tồn tại lúc nền tảng đánh giá); (4) không bước nào biến đỏ thành xanh; (5) tên job khớp
cấu hình Vercel Deployment Checks.
Sửa khi đỏ: sửa workflow cho đúng — không nới lưới. Đổi tên job thì đổi `DEPLOY_GATE_JOBS` CÙNG LÚC với dashboard.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEPLOY_GATE_JOBS = {"guards", "test", "migration-postgres", "docker-build", "web"}
DRAFT_GATE = "github.event_name!='pull_request'||github.event.pull_request.draft==false"
STATUS_CONDITIONS = {"", "failure()", "always()", "success()", "cancelled()", "!cancelled()"}


def _ci() -> dict:
    return yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))


def test_render_chi_deploy_khi_ci_qua() -> None:
    services = yaml.safe_load((ROOT / "render.yaml").read_text(encoding="utf-8"))["services"]
    assert services, "render.yaml không có dịch vụ nào — lưới rỗng nghĩa"
    for service in services:
        assert service.get("autoDeployTrigger") == "checksPass", f"`{service.get('name')}` deploy không chờ CI"
        assert "autoDeploy" not in service, "trường cũ `autoDeploy` làm người đọc hiểu nhầm trường nào có hiệu lực"


def test_khong_job_nao_bo_qua_duoc_lan_day_vao_main() -> None:
    jobs = _ci()["jobs"]
    wrong = {name: job.get("if") for name, job in jobs.items() if str(job.get("if", "")).replace(" ", "") != DRAFT_GATE}
    assert not wrong, f"job có điều kiện khác cổng PR nháp (bị bỏ qua = QUA với Render): {wrong}"
    push = _ci().get(True, _ci().get("on", {})).get("push", {})
    assert "main" in push.get("branches", []), "CI phải chạy trên lần đẩy vào main"


def test_khong_job_nao_needs_job_khac() -> None:
    needs = {name: job["needs"] for name, job in _ci()["jobs"].items() if job.get("needs")}
    assert not needs, f"`needs` trì hoãn việc TẠO check của job con — mở khoảng deploy trước khi test tồn tại: {needs}"


def test_khong_buoc_nao_bien_do_thanh_xanh() -> None:
    for name, job in _ci()["jobs"].items():
        assert "continue-on-error" not in job, f"job `{name}` có continue-on-error"
        for step in job.get("steps", []):
            label = step.get("name") or step.get("uses")
            assert "continue-on-error" not in step, f"bước `{label}` của `{name}` có continue-on-error"
            condition = str(step.get("if", "")).replace(" ", "")
            assert condition in STATUS_CONDITIONS, f"bước `{label}` có `if: {step.get('if')}` theo sự kiện/nhánh"
    playwright = (ROOT / "web/playwright.config.ts").read_text(encoding="utf-8")
    assert "retries: 0," in playwright, (
        "chạy lại tới khi xanh biến lỗi chập chờn thành vô hình — checksPass sẽ deploy nó"
    )


def test_ten_job_khop_cong_deploy_cua_vercel() -> None:
    jobs = _ci()["jobs"]
    named = {name: job["name"] for name, job in jobs.items() if "name" in job}
    assert not named, f"`name:` riêng làm tên check run khác id job — cổng Vercel lệch: {named}"
    assert set(jobs) == DEPLOY_GATE_JOBS, (
        f"tên job đổi: thêm {sorted(set(jobs) - DEPLOY_GATE_JOBS)}, mất {sorted(DEPLOY_GATE_JOBS - set(jobs))}. "
        "Cập nhật Vercel → Deployment Checks CÙNG LÚC, rồi mới sửa DEPLOY_GATE_JOBS."
    )
