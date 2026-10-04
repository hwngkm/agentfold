# Pack kỹ năng

Skill **lõi** (`registry.yaml` mục `core:`) luôn cài — đó là cách template này vận hành. Phần còn lại
chia thành pack, bật theo loại dự án.

```bash
python scripts/packs.py --list              # pack nào có, đang bật cái nào, gợi ý theo loại dự án
python scripts/packs.py --install backend   # bật
python scripts/packs.py --remove backend    # tắt
python scripts/packs.py --check             # CI chạy lệnh này
```

## Vì sao chia pack thay vì cài hết

Mô tả của **mọi** skill được nạp vào ngữ cảnh ở **mọi** phiên của **mọi** agent. Một template 25 skill
bắt dự án CRUD trả giá ngữ cảnh vĩnh viễn cho kỹ năng finetune nó không bao giờ dùng. Chia pack giữ đúng
tinh thần opt-in của template: thứ gì không dùng thì không phải mang.

## Trạng thái pack

| Trạng thái | Nghĩa là |
|---|---|
| `ready` | Có nội dung trong `packs/<tên>/skills/`, cài được |
| `planned` | Đã chốt phạm vi và tên skill, **chưa có nội dung**. `--install` từ chối và nói rõ |

Từ 03/10/2026 mọi pack trong sổ đều `ready`. Nguyên tắc vẫn giữ: **chỉ bật pack dự án thật dùng**, và nội
dung pack phải được kiểm lại bằng dự án thật — pack nào chưa từng được một dự án dùng thì coi là bản nháp viết từ
kinh nghiệm thực tế, sửa ngay khi gặp chỗ sai. Lưới `tests/guards/test_pack_sources.py` kiểm khuôn của
mọi pack `ready` kể cả khi chưa ai bật.

`ai-llm` được viết trước vì template được rút ra từ một ứng dụng LLM thật. Số liệu về token,
cache, giá trong `token-economics` lấy từ tài liệu API chính thức kèm ngày kiểm — không lấy từ trí nhớ.

## Viết nội dung cho một pack đang `planned`

1. Tạo `packs/<pack>/skills/<tên-skill>/SKILL.md` cho **từng** skill mà `registry.yaml` khai — tên thư
   mục phải khớp `name` trong sổ đăng ký.
2. Frontmatter bắt buộc:
   ```markdown
   ---
   name: <trùng tên thư mục>
   description: <làm gì, và DÙNG KHI NÀO — câu "dùng khi" là thứ quyết định agent có gọi đúng lúc không>
   ---
   ```
3. Nội dung là **thủ tục**, không phải bài giảng: các bước chạy được, lệnh thật, bẫy cụ thể đã gặp. Nếu
   một đoạn không đổi được hành vi của người đọc thì bỏ.
4. Đổi `status: planned` → `ready` trong `registry.yaml`.
5. `python scripts/packs.py --install <pack>` rồi `python -m pytest tests/guards/test_packs.py -q`.

## Thêm một pack mới

Thêm mục vào `registry.yaml` với `label`, `status`, `suits` (loại dự án phù hợp) và danh sách `skills`
kèm `summary` một dòng. Cập nhật `project_types:` nếu pack nên được gợi ý cho một loại dự án.

`registry.yaml` và `docs/design/project-profile.yaml` đều nằm trong vùng bảo vệ `design`: bật thêm một
pack là đổi cách cả đội làm việc, cần người duyệt.

## Công cụ đi kèm pack (`integrations:`)

Skill là thủ tục; nhiều thủ tục cần công cụ thật mới làm được — pack kiểm thử cần trình duyệt điều khiển được,
pack hạ tầng cần Terraform. Mỗi pack khai công cụ của nó trong `registry.yaml`, ba loại:

| Loại | `--install` làm gì | Vì sao không tự cài hết |
|---|---|---|
| `mcp` | GHI server vào `.mcp.json`; `--remove` gỡ (server người dùng tự thêm giữ nguyên) | — đã tự động, có lưới canh đồng bộ |
| `claude-plugin` | in lệnh `/plugin install name@marketplace` | plugin cài theo máy/người dùng, không theo repo |
| `cli` | kiểm có trên PATH chưa, in cách cài | cài phần mềm hệ thống là việc của người |

Bắt buộc: mỗi mục có `why` (làm gì, gửi dữ liệu gì ra ngoài nếu là dịch vụ từ xa); MCP chỉ dùng `${TEN_BIEN}`,
không khoá thô; hai pack khai cùng một server thì cấu hình phải giống hệt. Chỉ khai công cụ đã kiểm được cấu
hình từ nguồn chính thức (marketplace `anthropics/claude-plugins-official`, tài liệu nhà cung cấp) — không chép
từ blog. Lưới canh: `tests/guards/test_pack_integrations.py`.

Giới hạn nói thật: `.mcp.json` là cấu hình Claude Code. Codex (`~/.codex/config.toml`) và Gemini CLI
(`mcpServers` trong `.gemini/settings.json`) có chỗ khai MCP riêng — `--list` in đủ thông tin để thêm tay;
tự đồng bộ sang các công cụ đó chưa làm.

## Skill vs rule vs subagent

Ba thứ này hay bị lẫn:

| | Là gì | Ở đâu |
|---|---|---|
| **Rule** | Ràng buộc **không được vi phạm**. Luôn áp dụng, CI/lưới canh chặn | `docs/rules/` |
| **Subagent** | Một **vai trò** có góc nhìn và ngữ cảnh riêng (critic, architect) | `.claude/agents/`, `coordination/roles/` |
| **Skill** | Một **thủ tục** nhiều bước, chỉ cần khi đang làm đúng việc đó | `.claude/skills/` |

Nên "NLP" không phải skill (đó là một lĩnh vực). "Đo truy hồi của pipeline RAG trước khi chỉnh prompt"
mới là skill.
