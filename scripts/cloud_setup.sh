#!/usr/bin/env bash
# Dựng môi trường cho một phiên chạy trên cloud (hoặc một máy mới). Chạy lại bao nhiêu lần cũng được (idempotent).
#
# Ô "Setup script" của môi trường cloud chỉ cần gọi tệp này (xem docs/work/handoffs/… phần "Cấu hình môi trường cloud"):
#     root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"; bash "$root/scripts/cloud_setup.sh"
#
# Biến điều khiển (đều tuỳ chọn):
#     SETUP_WEB=1             cài thêm phụ thuộc frontend (npm ci trong web/) — chỉ khi việc cần chạm web/
#     CLOUD_SETUP_VERIFY=1    chạy `scripts/ci_local.py --fast` cuối cùng để xác nhận môi trường xanh (~1–2 phút)
#     CLOUD_SETUP_DRY_RUN=1   chỉ IN kế hoạch, không đổi gì
#     CLOUD_SETUP_ROOT=<dir>  thư mục tìm repo (mặc định: gốc git của thư mục hiện tại)
#
# Không dùng sudo, không cài gói hệ thống, không chạy mã tải từ mạng: chỉ `pip install -r requirements-dev.txt`
# (và `npm ci` theo lockfile khi bật SETUP_WEB). Không đọc hay in bí mật.
set -u

dry="${CLOUD_SETUP_DRY_RUN:-0}"
root="${CLOUD_SETUP_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

if [ ! -f "$root/requirements-dev.txt" ] || [ ! -f "$root/scripts/_pyrun.sh" ]; then
  echo "cloud_setup: chưa thấy repo ở '$root' (setup có thể chạy trước khi repo được clone)."
  echo "cloud_setup: không sao — trong phiên, ở thư mục repo chạy:  bash scripts/cloud_setup.sh"
  exit 0
fi
cd "$root" || exit 0

run() {
  echo "+ $*"
  [ "$dry" = "1" ] && return 0
  "$@"
}

py="$(command -v python3 || command -v python || true)"
if [ -z "$py" ]; then
  echo "cloud_setup: không thấy python3/python trên PATH — dừng (cần Python 3.11+)." >&2
  exit 0
fi

echo "cloud_setup: repo $root · python $("$py" --version 2>&1)"
if [ -z "${VIRTUAL_ENV:-}" ] && [ "$dry" != "1" ]; then
  echo "cloud_setup: lưu ý — chưa bật virtualenv nên phụ thuộc được cài vào Python '$py'. Trên cloud thì ổn;"
  echo "cloud_setup: trên máy cá nhân hãy bật venv trước (python -m venv .venv) để không đụng Python hệ thống."
fi

# 1. Phụ thuộc Python (ghim phiên bản trong requirements-dev.txt)
run "$py" -m pip install --quiet --disable-pip-version-check -r requirements-dev.txt \
  || echo "cloud_setup: pip install lỗi — kiểm quyền truy cập mạng tới pypi.org / files.pythonhosted.org của môi trường." >&2

# 2. Hook git dùng chung (commit-msg + pre-commit) — cùng đường dẫn với `make setup`
run git config core.hooksPath scripts/githooks
run chmod +x scripts/githooks/commit-msg scripts/githooks/pre-commit scripts/githooks/pre-push scripts/_pyrun.sh

# 3. Frontend (chỉ khi cần)
if [ "${SETUP_WEB:-0}" = "1" ]; then
  if [ -f web/package-lock.json ]; then
    echo "+ (cd web && npm ci --no-audit --no-fund)"
    [ "$dry" = "1" ] || (cd web && npm ci --no-audit --no-fund) \
      || echo "cloud_setup: npm ci lỗi — kiểm quyền truy cập registry.npmjs.org và phiên bản Node (cần 22)." >&2
  else
    echo "cloud_setup: SETUP_WEB=1 nhưng không có web/package-lock.json — bỏ qua."
  fi
fi

# 4. Xác nhận (tuỳ chọn) — môi trường phải xanh TRƯỚC khi agent sửa gì, để lỗi sau này là lỗi của việc đang làm
if [ "${CLOUD_SETUP_VERIFY:-0}" = "1" ]; then
  run "$py" scripts/ci_local.py --fast || echo "cloud_setup: ci_local --fast đỏ ngay từ đầu — ĐỪNG sửa gì khi chưa hiểu vì sao." >&2
fi

echo "cloud_setup: xong. Việc tiếp theo:  export AGENTCTL_AGENT=<định-danh>  &&  python -m tools.agentctl prime"
exit 0
