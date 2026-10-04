# GOVERNANCE — Ai quyết gì, và AI agent đứng ở đâu

> Vùng bảo vệ `rules`. File này SINH RA từ `docs/design/team-profile.yaml` bằng
> `python scripts/generate_team_docs.py` — sửa profile rồi sinh lại, đừng sửa tay bảng vai trò dưới đây.
> Điền tên người thật vào cột "Người" rồi commit (PR có người duyệt) — sinh lại không xoá tên đã điền.

## 1. Vai trò con người

Preset team-size `solo` (1 vai trò).

| Mã | Vai trò | Người | Sở hữu | Dự phòng |
|---|---|---|---|---|
| **R1** | Người duy nhất — kiến trúc, miền, backend, frontend, vận hành | `…` | `docs/design/`, `docs/rules/`, `coordination/`, `tests/guards/`, `src/agents/`, `src/llm/`; `src/domain/`, dữ liệu nghiệp vụ và nguồn, bộ đánh giá, bất biến miền; `src/api/`, `src/db/`, `alembic/`; CI, deploy, Docker, bí mật; `web/`, trải nghiệm người dùng; tài liệu phát hành (README, video, pitch deck) | — |

> Không có người thứ hai duyệt PR — bù bằng agent `reviewer` (đổi sang NHÀ CUNG CẤP KHÁC agent đã viết code) đọc diff trước khi tự duyệt: hai mô hình khác nhau ít chia sẻ cùng điểm mù. CI xanh và `check-scope` vẫn bắt buộc, vì mục đích của chúng là ngăn CHÍNH BẠN — qua nhiều phiên agent song song — giẫm chân nhau, không chỉ ngăn người khác.

## 2. AI agent trong mô hình trách nhiệm

- **Mỗi phiên agent làm thay đúng một vai trò** (`--role Rn` khi claim). Người giữ vai trò đó chịu trách
  nhiệm cho mọi thứ agent merge — như với commit của chính họ.
- **Agent không có quyền quyết định** ở các hạng mục trong bảng §3. Agent đề xuất (ticket `proposed`,
  ADR `Proposed`, câu hỏi); người quyết.
- **Agent của nhà cung cấp nào cũng theo cùng luật** (`AGENTS.md`). Không có agent "tin cậy hơn" theo thương hiệu.
- **Ghi nhận tác giả:** commit, PR, nhật ký ghi vai trò con người (`R2`). Dự án muốn ghi thêm công cụ/mô
  hình AI để thống kê thì quyết ở đây, bằng một dòng: *Ghi công cụ AI: không*.
- **Tài khoản của agent:** khuyến nghị agent dùng token/tài khoản **không** có quyền duyệt PR hay gắn nhãn
  `human-approved`. Nếu agent dùng tài khoản của người, cổng duyệt chỉ còn là kỷ luật quy trình — ghi rõ.

## 3. Quyền quyết định

| Hạng mục | Quyết (A) | Hỏi ý kiến (C) | Agent được |
|---|---|---|---|
| Kiến trúc, ranh giới lớp, ADR | R1 | — | soạn ADR `Proposed` |
| Bất biến sản phẩm (`invariants.yaml`) | R1 | cả đội | đề xuất qua câu hỏi |
| Ngưỡng, hệ số, nguồn số liệu nghiệp vụ | R1 | — | **không** — chỉ trích nguồn có sẵn |
| Ticket `ready`, phạm vi ticket | R1 | chủ module | soạn ticket `proposed` |
| Schema CSDL, migration | R1 | — | viết migration trong ticket có làn `db-migrations` |
| Hợp đồng API | R1 | — | đổi trong ticket có làn `api-contract` |
| CI, deploy, bí mật | R1 | — | đề xuất; không đổi cổng an toàn |
| Merge vào `main` | chủ module, sau CI xanh | — | được, sau khi CI xanh VÀ đã tự đọc diff — không có người thứ hai (profile `solo`) |
| Nhãn `human-approved` | chủ vùng bảo vệ | — | **không bao giờ** |

Không ô nào có hai người **A**. Hạng mục hỏng thì hỏi người **A**.

## 4. Quyết định kiến trúc (ADR)

ADR bắt buộc khi: thêm/thay framework, CSDL, nhà cung cấp mô hình, dịch vụ cloud · đổi ranh giới giữa mô
hình ngôn ngữ và lõi tất định · đổi schema/API ảnh hưởng từ hai module · đổi luồng duyệt, phân quyền, kiểm
toán · thêm chi phí vận hành định kỳ · chấp nhận một rủi ro an toàn/bảo mật chưa xử lý.

1. Người đề xuất (người hoặc agent `architect`) tạo `docs/design/adr/NNNN-slug.md` từ `0000-template.md`, `Status: Proposed`.
2. R1 kiểm ít nhất hai phương án có bằng chứng; mời người hỏi ý kiến theo §3.
3. R1 chuyển `Accepted`/`Rejected`/`Deferred` trong PR có người duyệt.
4. ADR không sửa để che lịch sử — quyết định mới thay quyết định cũ bằng ADR mới ghi `Supersedes`.

## 5. Thang đánh giá kiến trúc (trước mỗi mốc phát hành)

Mỗi tiêu chí 0–5; điểm = `điểm/5 × trọng số`. Thiếu bằng chứng (test/log/báo cáo) thì tối đa 2/5.

| Tiêu chí | Trọng số | Bằng chứng tối thiểu |
|---|---:|---|
| An toàn miền & fail-closed | 25% | lưới canh bất biến xanh và từng được chứng minh đỏ |
| Tính đúng & truy vết nguồn | 15% | test tính toán; mọi con số truy được về nguồn |
| Bảo mật & riêng tư | 15% | test phân quyền/IDOR; không bí mật trong repo; egress guard |
| Độ tin cậy & khôi phục | 10% | health/ready; timeout/retry có trần; đường khôi phục migration |
| Khả năng kiểm thử | 10% | unit/integration/e2e; kiểm cục bộ = CI |
| Bảo trì & đơn giản | 10% | ranh giới lớp giữ được; phụ thuộc có lý do |
| Quan sát & kiểm toán | 5% | audit log cho hành động MEDIUM/HIGH; trace id |
| Hiệu năng & chi phí | 5% | p95; số lời gọi mô hình/request |
| Triển khai | 3% | Docker tái lập; deploy chờ CI; rollback |
| Vận hành giao diện/API | 2% | trạng thái tải/rỗng/lỗi; hợp đồng API cập nhật |

**Qua** ≥ 80 · **Qua có điều kiện** 75–79 (có người chịu rủi ro và hạn) · **Không qua** < 75.
Không qua ngay nếu: an toàn miền, tính đúng hoặc bảo mật dưới 3/5; có đường vòng qua cổng duyệt; có
con số không nguồn tới người dùng; migration production không có đường khôi phục.

## 6. Nhịp

| Khi | Việc | Ai |
|---|---|---|
| Đầu mỗi chu kỳ | lập kế hoạch: ticket `ready`, chia nhóm song song/tuần tự | R1 + cả đội |
| Hằng ngày | `python -m tools.agentctl board`; dọn claim quá hạn; trả lời câu hỏi mở | R1 |
| Mỗi PR | review theo `coordination/roles/reviewer.md`; nhãn duyệt nếu chạm vùng bảo vệ | chủ module |
| Cuối chu kỳ | thang đánh giá §5; sự cố → lưới canh mới | R1 |
