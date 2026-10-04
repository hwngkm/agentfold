# RULE 20 — Backend, CSDL, lớp LLM

> Owner: **R3** (API/CSDL) + **R1** (lớp agent/LLM).

## A. Python

| Chủ đề | Luật | Cưỡng chế |
|---|---|---|
| Phiên bản | 3.11+ | `pyproject.toml` |
| Kiểu | type hint mọi hàm | `mypy` với `disallow_untyped_defs` |
| Ngoại lệ | cấm `except:` và `except Exception:` trần — bắt đúng loại, log, ném lại nếu không xử lý được | ruff `E722`, `BLE` |
| In ra | cấm `print()` trong `src/` — dùng logger; không log bí mật/dữ liệu định danh | ruff `T20` |
| Định dạng | `ruff format`, bản ruff GHIM chính xác | CI `ruff format --check` |
| Bất biến dữ liệu | ưu tiên `@dataclass(frozen=True)`, trả bản mới thay vì sửa tại chỗ | review |

## B. Tránh điểm nóng xung đột

- **R20.1 — Router tự khám phá.** Thêm endpoint = thêm `src/api/routes/<tài-nguyên>.py` có biến `router`.
  Không sửa `src/api/routes/__init__.py`.
- **R20.2 — Model tự khám phá.** Thêm bảng = thêm `src/db/models/<miền>.py`. Không sửa `src/db/models/__init__.py`.
- **R20.3 — Settings theo miền.** Mỗi miền một lớp `BaseSettings` với `env_prefix` riêng trong gói của nó
  (mẫu: `src/llm/settings.py`). Không dồn trường vào `src/core/settings.py`. Không `os.getenv()` rải rác.
- **R20.4 — Một tập giá trị, một nơi định nghĩa.** Tập hằng dùng ở nhiều chỗ (Literal của schema + set kiểm dữ
  liệu) phải suy ra từ một định nghĩa (`typing.get_args`), không chép hai lần. Từng có trường hợp sửa một nơi,
  quên nơi kia: script kiểm hẹp vẫn xanh, toàn hệ thống vỡ.

## C. FastAPI

- **R20.5** — Route `async def` khi không chặn; I/O đồng bộ (driver CSDL đồng bộ) dùng `def` để FastAPI đưa vào threadpool.
- **R20.6** — Pydantic ở mọi ranh giới vào/ra. Không trả model ORM thẳng ra ngoài.
- **R20.7** — Phân quyền hai lần: vai trò ở route (`require_role`), chủ sở hữu ở truy vấn. Không có quyền với
  bản ghi của người khác → **404**, không 403 (không lộ bản ghi tồn tại).
- **R20.8** — Lỗi thống nhất `{code, detail, retryable}`; không trả stack trace hay thông điệp driver ra client.

## D. CSDL và migration

- **R20.9 — Alembic là nguồn sự thật duy nhất của schema.** Đổi model ⇒ migration trong cùng PR, ticket khai làn
  `db-migrations`. Autogenerate xong phải ĐỌC LẠI: nó sinh DROP+ADD khi đổi tên cột (mất dữ liệu).
- **R20.10 — Đồ thị đúng một head.** Hai head ⇒ `alembic merge`. **Không bao giờ `alembic stamp`** để chữa: stamp
  ghi đè phiên bản mà không chạy DDL, tức nói dối về schema thật.
- **R20.11 — Tương thích SQLite cho dev/test:** thay đổi cột dùng `op.batch_alter_table`. Nhưng xanh trên SQLite
  không đủ — CI chạy migration trên PostgreSQL thật (`scripts/check_migration_matches_models.py`).
- **R20.12 — CSDL máy dev không phải production.** Test trỏ `DATABASE_URL` vào cổng chết (`tests/conftest.py`).
  Script ghi dữ liệu: mặc định chạy thử, in rõ host đích, chỉ ghi khi có `--apply`, sao lưu trước thao tác hàng loạt.
- **R20.13 — Hành động MEDIUM/HIGH ghi `audit_log`.**

## E. Lớp LLM và agent sản phẩm

- **R20.14 — SDK nhà cung cấp chỉ trong `src/llm/`,** import trễ trong adapter (khởi động không kéo thư viện nặng).
- **R20.15 — Structured output bắt buộc,** schema `extra="forbid"`, chỉ trường cần chọn — không trường con số nghiệp vụ.
- **R20.16 — Mọi lời gọi có timeout; mọi vòng lặp gọi mô hình có trần** (`max_attempts`). Hết lượt ⇒ lỗi rõ ràng, không treo.
- **R20.17 — Prompt không chứa ngưỡng nghiệp vụ hardcode;** prompt nằm trong code/tệp có version, không dán rải rác.
- **R20.18 — Dữ liệu ngoài vào prompt qua `sanitize_untrusted` + `fence`; văn bản ra ngoài qua `assert_no_egress`**
  (`docs/rules/60-agent-security.md`).
- **R20.19 — Node/hàm khai rõ có gọi LLM hay không** (docstring đầu module: `LLM: có/không`). Hàm tính toán không gọi LLM.

## F. Kiểm thử

- **R20.20** — Logic mới có test ca hợp lệ + ca biên/ca hỏng; thấy đỏ trước khi viết code.
- **R20.21** — Test tấn công đường đi thật của dữ liệu và kèm bộ "không báo động giả" — cảnh báo giả làm người
  dùng mất niềm tin nhanh hơn thiếu cảnh báo.
- **R20.22** — Test lệ thuộc thời gian cố định múi giờ; CI chạy UTC (`scripts/ci_local.py` ép `TZ=UTC`).
