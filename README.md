# Agentfold

**Mẫu dự án để con người giữ quyền quyết thiết kế, còn nhiều AI agent — của nhiều nhà cung cấp khác nhau — cùng làm một repo
mà không giẫm chân nhau và không lệch khỏi thiết kế.**

Stack mẫu: FastAPI · SQLAlchemy + Alembic · PostgreSQL · Next.js · Docker · GitHub Actions · Render + Vercel.
Miền nghiệp vụ không cứng trong khung: thay phần mẫu bằng sản phẩm của bạn, giữ nguyên lớp điều phối.

## Dành cho ai

- **Người làm sản phẩm cùng AI agent** (Claude Code, Codex, Gemini CLI, Cursor, Copilot, Antigravity…) và muốn nhiều agent làm song song
  mà vẫn kiểm soát được phạm vi, chất lượng và chi phí.
- **Nhóm nhỏ hoặc một người** cần quy trình rõ — kế hoạch duyệt trước, kiểm bằng máy, bàn giao giữa các phiên — mà không dựng thêm dịch vụ nào.
- **Người không rành kỹ thuật** muốn tạo một dự án theo mục đích bằng một trang trả lời câu hỏi (xem "Bắt đầu").

## Vấn đề template giải quyết

Khi nhiều agent chung một repo, những sự cố sau lặp lại. Mỗi dòng có cơ chế chặn bằng máy, không bằng lời dặn:

| Sự cố thường gặp | Template chặn bằng |
|---|---|
| Mỗi công cụ AI đọc một file luật khác; luật chép nhiều bản rồi trôi | `AGENTS.md` là nguồn luật duy nhất, adapter chỉ trỏ về — có lưới canh |
| File nhật ký/ticket dùng chung bị mọi nhánh cùng sửa | mỗi mục công việc một file (`docs/work/`), tên theo ngày + slug |
| Nhiều nhánh cùng thêm migration, sinh nhiều head Alembic | làn độc quyền `db-migrations` + claim nguyên tử + lưới một-head |
| Hai phiên agent cùng một cây làm việc, một bên xoá việc của bên kia | mỗi claim một worktree riêng |
| Agent sửa ngoài phạm vi hoặc tự nới phạm vi | kiểm phạm vi ở hook → pre-commit → CI (công cụ CI chạy từ commit gốc) |
| CI đỏ nhiều lần vì kiểm cục bộ khác CI | `scripts/ci_local.py` phản chiếu CI — có lưới canh |
| Commit có test an toàn đỏ vẫn lên production | Render `checksPass` + CI không `needs` + lưới canh cấu trúc CI |
| Thiếu biến môi trường → production chạy với khoá công khai, im lặng | cổng cấu hình production đổ ngay lúc khởi động |
| Agent báo "xong" khi chưa kiểm trên đúng cây làm việc | cổng bằng chứng: không dừng phiên khi `ci_local` chưa đạt trên cây hiện tại |

Lý do thiết kế và các phương án đã loại: `docs/design/adr/0001-multi-agent-control-plane.md`.

## Bắt đầu

**Không rành kỹ thuật?** Mở `wizard/index.html` bằng nhấp đúp (không cần mạng, không cài gì). Trả lời 6 câu hỏi bằng ngôn ngữ thường —
dự án để làm gì, mấy người, có dữ liệu nhạy cảm không, dùng trợ lý AI nào — rồi tải tệp `project-setup.json` và chạy đúng hai lệnh trang đó đưa:

```bash
python scripts/setup_project.py project-setup.json            # xem trước kế hoạch — chưa đổi gì
python scripts/setup_project.py project-setup.json --apply    # làm thật (cần cây git sạch; hoàn tác: git checkout -- . && git clean -fd)
```

Trang không gửi dữ liệu đi đâu và không hỏi mật khẩu hay khoá. Người kỹ thuật làm tay từng bước:

```bash
# 1. Lấy template — trên GitHub bấm "Use this template", rồi:
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
python scripts/bootstrap.py --name "Tên Dự Án" --slug ten-du-an          # chạy thử
python scripts/bootstrap.py --name "Tên Dự Án" --slug ten-du-an --apply  # ghi thật + in việc người phải làm

# 2. Chọn hình dạng đội: bao nhiêu người thật, mức nghi thức (bỏ qua = standard/standard)
python scripts/generate_team_docs.py --team-size solo --complexity lite

# 3. Môi trường + git hooks dùng chung
make setup                     # hoặc: pip install -r requirements-dev.txt && git config core.hooksPath scripts/githooks
cp .env.example .env

# 4. Chạy
alembic upgrade head
make run                       # API http://127.0.0.1:8000/docs
(cd web && npm ci && npm run dev)   # Web http://localhost:3000

# 5. Xác nhận mọi thứ xanh như CI
python scripts/ci_local.py
```

Toàn bộ bằng Docker: `docker compose up --build`. Chạy trên môi trường cloud của agent: `scripts/cloud_setup.sh`.

**Việc đầu tiên sau khi tạo dự án:** đặt tài khoản GitHub thật của người duyệt trong `docs/design/team-profile.yaml` (trường `github_handles`)
rồi chạy `python scripts/generate_team_docs.py` để sinh lại `.github/CODEOWNERS`.

## Hai trục điều chỉnh

| Trục | Không đổi khi bạn chỉnh | Đổi khi bạn chỉnh |
|---|---|---|
| **Miền dự án** — thay `src/domain/catalog/` bằng nghiệp vụ thật, viết bất biến thật vào `docs/design/invariants.yaml`, xoá `EXM-01.md` | năm lớp điều phối (xem dưới), ranh giới lớp (`contracts/boundaries.yaml`), CI/deploy | `docs/design/PRD.md`, `src/domain/`, `docs/rules/10-domain-safety.md`, bất biến miền |
| **Team-size × complexity** | claim, worktree, kiểm phạm vi (chạy y hệt dù 1 hay 20 người) | số vai trò, ai sở hữu vùng nào (`docs/GOVERNANCE.md`, `.github/CODEOWNERS`, chủ vùng trong `coordination/policy.yaml`), số người duyệt, mức bắt buộc ADR |

Bốn team-size (`solo` 1 người · `small` 2 · `standard` 4, mặc định · `large` 6+ có vai trò bảo mật riêng) × ba complexity
(`lite` POC · `standard` mặc định · `strict` dữ liệu nhạy cảm, thêm đồng duyệt bảo mật). Hai trục độc lập nhau; chi tiết: `docs/design/presets/README.md`.
`docs/GOVERNANCE.md` và `.github/CODEOWNERS` được **sinh ra** từ `docs/design/team-profile.yaml`, có lưới canh giữ đồng bộ.

## Kiến trúc: năm lớp của mặt phẳng điều phối

```
1. LUẬT          AGENTS.md ◄── CLAUDE.md · GEMINI.md · .github/copilot-instructions.md · .cursor · .aider
2. THIẾT KẾ      docs/design/ (PRD, ARCHITECTURE, ADR, invariants.yaml) · contracts/ (ranh giới lớp, OpenAPI)
3. KẾ HOẠCH      docs/work/tickets/<ID>.md — phạm vi đã duyệt, trên main
4. ĐIỀU PHỐI     tools/agentctl: claim nguyên tử (nhánh agent-claims) · worktree riêng · kiểm phạm vi
5. CƯỠNG CHẾ     hook ghi file ─► pre-commit ─► CI scope-guard + 5 job ─► branch protection ─► deploy chờ CI
```

Nguyên tắc xuyên suốt: **ràng buộc nằm ở chỗ mọi agent bắt buộc đi qua (git, CI), không nằm ở lời dặn.**

## Một vòng làm việc với nhiều agent

```bash
# Người lập kế hoạch (người hoặc agent planner) đề xuất ticket; người duyệt đổi state: ready qua PR.
python -m tools.agentctl new ticket --id API-02 --title "Thêm endpoint X" --role R1

# Mỗi agent (bất kỳ nhà cung cấp nào), thay mặt một vai trò:
python -m tools.agentctl prime                     # bối cảnh đầu phiên: việc đang mở, bàn giao, môi trường
python -m tools.agentctl board                     # ai đang làm gì, ticket nào ready
python -m tools.agentctl start API-02 --role R3    # từ chối nếu phạm vi chồng người khác
cd .worktrees/API-02
# ... test trước, code, make check-fast, commit "feat(api): ... (API-02)"
python scripts/ci_local.py && python -m tools.agentctl check-scope
python -m tools.agentctl pr-body --ticket API-02   # tiêu đề + nội dung PR; mở PR bằng gh, GitHub MCP hoặc dán vào web
python -m tools.agentctl release API-02            # sau khi merge
```

- **Xem bảng việc không cần dòng lệnh:** `python scripts/render_board.py` ghi `board/index.html` — một tệp HTML tự chứa, đọc được ở màn hình hẹp
  và chế độ tối, chỉ đọc; mọi thay đổi vẫn qua PR/ticket.
- **Người và agent nhắn nhau không cần chép tay:** hộp thư AGENT-LOG nằm trên nhánh git riêng, chỉ cần `git` (`docs/AGENT-LOG.md`).
- **Đội agent có phân cấp:** `coordination/team.yaml` ghi một điều phối viên, sở trường từng agent, tuyến việc và việc chỉ
  người làm; điều phối viên giao bằng `mail assign`, agent báo bằng `mail reply`, ai cũng xem `mail pending`.
- **Bàn giao giữa các phiên:** `python -m tools.agentctl new handoff` điền sẵn từ git; phiên sau đọc rồi làm tiếp.
- **Prompt khởi động có sẵn** cho phiên cloud, hàng đợi nhiều ticket và phiên local: `docs/PROMPTS.md`.

Vai trò agent trung lập nhà cung cấp nằm ở `coordination/roles/`, mỗi vai trò có adapter Claude Code trong `.claude/agents/`:

| Vai trò | Việc | Ghi/sửa? |
|---|---|---|
| `coordinator` | giao ticket `ready` theo tuyến, theo dõi việc chờ, review và merge sau CI xanh | merge sau CI xanh |
| `planner` | đề xuất ticket có phạm vi hẹp | thêm ticket đề xuất |
| `architect` | cân nhắc phương án cho một câu hỏi thiết kế, soạn ADR `Proposed` | ADR đề xuất |
| `system-designer` | dựng sơ đồ + bảng cấu trúc (ERD, máy trạng thái, ma trận quyền, DFD…) cho một giai đoạn | đề xuất qua PR |
| `implementer` | làm ticket trong phạm vi đã duyệt | có, trong scope |
| `ui-designer` | thiết kế UI/UX, prototype chạy được, đủ trạng thái tải/rỗng/lỗi | có, trong scope |
| `reviewer` | đọc một PR như người chịu trách nhiệm | không |
| `critic` | kiểm thứ ĐÃ làm: tự báo cáo, con số không nguồn, lưới chưa từng đỏ | không |
| `red-team` | tấn công thứ SẮP làm: kịch bản thất bại, pre-mortem, giả định ẩn | không |
| `supervisor` | kiểm cả khoảng lịch sử của agent mình không điều khiển | không |
| `release-engineer` | CI đỏ, đổi CI, chuẩn bị deploy/quay lui, kiểm sau deploy | chuẩn bị lệnh; người bấm deploy |
| `researcher` | tìm và tổng hợp bằng chứng: repo, mô hình/bộ dữ liệu Hugging Face, bài báo, thị trường | không (chỉ ghi chú nghiên cứu) |

## Pack kỹ năng và công cụ đi kèm — bật theo loại dự án

Skill lõi (ADR, sơ đồ, lưới canh, ticket, nhiều agent) luôn có. Phần còn lại là **pack**, bật khi dự án cần — mô tả mọi skill đã bật đều tốn
ngữ cảnh ở mọi phiên của mọi agent. Mỗi pack kèm công cụ thật: MCP server được ghi/gỡ tự động trong `.mcp.json`; plugin Claude Code và CLI được in lệnh cài.

| Pack | Dùng cho | Công cụ đi kèm |
|---|---|---|
| `product-design` | sơ đồ cần cho từng giai đoạn, ERD + từ điển dữ liệu, bảng thiết kế (quyền, trạng thái, truy vết), bản mẫu Figma | plugin `figma`, `design`, `product-management` |
| `backend` | hợp đồng API, migration, quan sát được | plugin `pyright-lsp`, MCP `context7` |
| `frontend` | component đủ trạng thái, hệ thống thiết kế (`DESIGN.md` + kiểm tương phản), bản mẫu UX | plugin `frontend-design`, `typescript-lsp`, MCP `playwright` |
| `data` | nạp dữ liệu có nguồn, chất lượng dữ liệu, hiệu năng SQL | CLI `psql` |
| `testing` | chiến lược test, TDD, E2E trình duyệt, test chập chờn | MCP `playwright`, plugin `pr-review-toolkit` |
| `ai-llm` | prompt có cấu trúc, RAG, eval, token, độ trễ | MCP `context7` |
| `ai-product` | kiến trúc agent, thiết kế công cụ, MCP server, người duyệt, phát hành AI | plugin `agent-sdk-dev`, `mcp-server-dev`, MCP `context7` |
| `research` | tổng quan tài liệu, tìm bài báo, chấm repo GitHub, chọn mô hình/bộ dữ liệu Hugging Face, ghi chú nghiên cứu | `python -m scripts.research` (không cần MCP), CLI `gh`, `hf` |
| `market` | nghiên cứu thị trường, phân tích đối thủ | plugin `product-management` |
| `ml-dl` | theo dõi thí nghiệm, huấn luyện/đánh giá, fine-tune, benchmark | CLI `hf` |
| `ops` | CI, cổng deploy, nơi deploy (Render/Vercel/VPS/HF Spaces), sự cố, chi phí | CLI `gh`, MCP `github`, plugin `code-review`, `security-guidance`, `vercel-plugin` |
| `infra` | image container, Docker Compose, Terraform, bí mật theo môi trường, cách ly container (tuỳ chọn) | CLI `docker`, `terraform`, `container-use`, MCP `terraform` |
| `review-audit` | audit dự án định kỳ, audit bảo mật (STRIDE, rủi ro LLM/agent), tranh luận phản biện | plugin `claude-security`, `engineering`, CLI `pip-audit` |

```bash
python scripts/packs.py --set-type ai-product   # ghi loại dự án, in pack gợi ý (không tự bật)
python scripts/packs.py --list                  # mọi pack, skill và công cụ đi kèm
python scripts/packs.py --install testing       # chép skill + ghi MCP vào .mcp.json + in lệnh cài plugin/CLI
```

Chi tiết và cách viết thêm pack: `packs/README.md`. Nội dung pack viết từ kinh nghiệm thực tế — dự án đầu tiên bật một pack nên kiểm lại pack đó bằng việc thật.

## Cài từng skill mà không fork template

Chỉ cần skill, không cần cả cơ chế điều phối? Hai đường:

```bash
# mọi agent hỗ trợ `skills` (Codex, Cursor, Gemini CLI, Copilot…): liệt kê 59 skill (7 lõi + 52 pack), rồi chọn
npx skills add hwngkm/agentfold --list --full-depth
npx skills add hwngkm/agentfold --full-depth --skill adr

# Claude Code: marketplace plugin — `core` là bộ lõi, mỗi pack là một plugin (tên trùng tên pack)
/plugin marketplace add hwngkm/agentfold
/plugin install core@agentfold
```

`--full-depth` cần vì skill của pack nằm ở `packs/<pack>/skills/`, không ở chỗ công cụ tự tìm. Manifest marketplace được SINH từ `packs/registry.yaml`
bằng `python scripts/packs.py --sync-marketplace`; lưới canh `tests/tools/test_publish.py` đỏ khi nó lệch sổ.

## Công cụ AI nào đọc gì

| Công cụ | Luật | Kỹ năng | Chặn ghi sai phạm vi ngay lúc ghi |
|---|---|---|---|
| Codex CLI | `AGENTS.md` | tự nạp `.agents/skills/` | có (`.codex/hooks.json`) |
| Claude Code | `CLAUDE.md` → `@AGENTS.md` | tự nạp `.claude/skills/` + plugin/MCP | có (`.claude/settings.json`) |
| Gemini CLI | `.gemini/settings.json` → `AGENTS.md` | tự nạp `.agents/skills/` | có (`BeforeTool`) |
| GitHub Copilot, Cursor, Antigravity, OpenCode | `AGENTS.md` (+ adapter) | tự nạp `.agents/skills/` | không — bị chặn ở pre-commit và CI |
| Aider, Windsurf, Zed, Jules… | `AGENTS.md` (+ adapter) | `SKILLS.md` → mở SKILL.md | không — bị chặn ở pre-commit và CI |

**Không công cụ nào bị bỏ lại vì thiếu MCP/plugin:** mỗi plugin/MCP khai trong `packs/registry.yaml` bắt buộc có `fallback` (cách làm bằng CLI/HTTP/skill khác),
`SKILLS.md` in sẵn cột "Không có thì", và hộp thư AGENT-LOG chỉ cần git. Lưới canh: `tests/guards/test_tool_agnostic.py`.

## Bản đồ thư mục

| Đường dẫn | Là gì | Ai sở hữu |
|---|---|---|
| `AGENTS.md` | luật cho mọi agent | người (vùng bảo vệ) |
| `docs/design/` | PRD, kiến trúc, ADR, bất biến, `team-profile.yaml` + preset | người (vùng bảo vệ) |
| `docs/rules/` | luật theo lĩnh vực (00 cốt lõi → 80 lưới canh) | người (vùng bảo vệ) |
| `docs/work/` | ticket, nhật ký, quyết định, câu hỏi, bàn giao, sự cố — mỗi mục một file | ticket: người duyệt; còn lại: ai cũng thêm |
| `docs/PROMPTS.md`, `docs/DEPLOY.md` | prompt khởi động cho agent; hướng dẫn deploy và các bẫy đã gặp | theo `docs/GOVERNANCE.md` |
| `coordination/` | chính sách điều phối, vai trò agent | người (vùng bảo vệ) |
| `contracts/` | ranh giới lớp, bản chụp OpenAPI | thiết kế / làn độc quyền |
| `tools/agentctl/` | công cụ điều phối (claim, phạm vi, bảng việc, hộp thư, bàn giao) | người (vùng bảo vệ) |
| `src/` | backend: core · domain (tất định) · db · llm · agents · api | theo `docs/GOVERNANCE.md` |
| `tests/guards/` | lưới canh — thiết kế dạng chạy được | thêm được; sửa cần duyệt |
| `tests/tools/`, `tests/unit/` | test công cụ điều phối, test ứng dụng | theo module |
| `web/` | frontend Next.js | theo `docs/GOVERNANCE.md` |
| `packs/`, `evals/` | pack kỹ năng; kịch bản kiểm hành vi skill và benchmark | theo module |
| `scripts/` | CI cục bộ, hook, khởi tạo, kiểm migration, công cụ nghiên cứu | theo `docs/GOVERNANCE.md` |

## Giới hạn — nói thật

- **Không phải ranh giới bảo mật trước một agent CỐ Ý phá:** agent có token đủ quyền vẫn gắn được nhãn duyệt. Chốt thật là branch protection + CODEOWNERS
  + agent dùng tài khoản không có quyền duyệt (`docs/GOVERNANCE.md` §2).
- **Branch protection có điều kiện tiên quyết:** repo **private** trên gói GitHub **Free** không bật được branch protection lẫn rulesets (API trả
  `403 Upgrade to GitHub Pro or make this repository public`). Khi đó GitHub không chặn gì cả; lớp còn lại chỉ là hook ghi file (không thấy lệnh shell),
  git hook cục bộ (bỏ được) và CI. Chọn một: nâng gói · chuyển repo public · hoặc coi CI xanh là điều kiện merge bắt buộc bằng kỷ luật.
- **CI đỏ vì thanh toán trông giống hệt CI đỏ vì mã** — cả hai đều hiện dấu ✗. Job đỏ trong 2–3 giây và danh sách bước rỗng thì đọc annotation trước
  khi đọc code ("recent account payments have failed or your spending limit needs to be increased" nghĩa là hạ tầng). Runner tự host (biến repo `CI_RUNNER`, xem `docs/DEPLOY.md`) không tốn phút GitHub.
- **Claim cần kết nối tới git remote.** Mất mạng thì chỉ `status` và `board --offline` dùng được.
- **Kiểm chồng phạm vi cố ý bảo thủ:** đôi khi từ chối oan hai mẫu thật ra rời nhau — giải bằng scope hẹp hơn.
- **Vùng bảo vệ giữ claim độc quyền:** ticket cùng khai một vùng bảo vệ chỉ chạy lần lượt, không song song.
- **Mới đo trên một nhà cung cấp:** thử nghiệm có/không template (`evals/benchmarks/`) chạy với ba mô hình rẻ qua OpenRouter; chưa nói gì về Claude Code hay Codex.
- **Miền mẫu** (`src/domain/catalog`, `src/agents/quote_agent.py`) chỉ để minh hoạ hình mẫu; thay bằng miền thật.
- **Chưa kiểm trên mọi môi trường:** `container-use` (cần Docker) chưa chạy thật; hook chặn ghi chỉ có cho Claude Code, Codex và Gemini CLI.

## Kiểm chứng template này

```bash
python -m pytest -q          # unit + lưới canh + công cụ điều phối (claim chạy trên git thật)
python scripts/ci_local.py   # đủ bước như CI
```

## Giấy phép

[MIT](LICENSE). Dự án tạo từ template này tự chọn giấy phép của mình.
