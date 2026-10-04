# Lối tắt cho lệnh hay dùng. Không có `make` (Windows)? Mọi lệnh đều chạy trực tiếp được — xem từng target.
PY ?= python

.PHONY: setup run migrate check-fast check test guards ci-local openapi board lint format typecheck

setup:  ## Cài phụ thuộc + bật git hooks dùng chung (một lần mỗi bản clone; worktree dùng chung cấu hình)
	$(PY) -m pip install -r requirements-dev.txt
	git config core.hooksPath scripts/githooks
	-chmod +x scripts/githooks/* scripts/_pyrun.sh

run:  ## Chạy API ở chế độ phát triển
	$(PY) -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000

migrate:  ## Áp migration lên CSDL trong DATABASE_URL (KIỂM LẠI đó không phải production)
	alembic upgrade head

lint:
	$(PY) -m ruff check .

format:
	$(PY) -m ruff format .

typecheck:
	$(PY) -m mypy

guards:  ## Lưới canh + công cụ điều phối
	$(PY) -m pytest tests/guards tests/tools -q

test:  ## Toàn bộ test Python
	$(PY) -m pytest -q

check-fast:  ## Trước MỖI commit: các bước tĩnh + lưới canh, không build frontend
	$(PY) scripts/ci_local.py --fast

check:  ## Trước khi mở/cập nhật PR: đủ bước như CI
	$(PY) scripts/ci_local.py

ci-local: check

openapi:  ## Ghi lại bản chụp hợp đồng API sau khi đổi API có chủ đích
	$(PY) scripts/export_openapi.py

board:  ## Bảng công việc suy ra từ ticket + claim + lịch sử main
	$(PY) -m tools.agentctl board
