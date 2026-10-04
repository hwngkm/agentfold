---
name: diagram
description: Thêm hoặc cập nhật sơ đồ kiến trúc trong docs/design/ARCHITECTURE.md — biết sơ đồ nào SINH TỰ ĐỘNG từ contracts/boundaries.yaml và coordination/policy.yaml, sơ đồ nào người phải vẽ. Dùng khi thêm lớp/gói mới, đổi ranh giới import, đổi vùng bảo vệ hay chủ vùng, khi CI báo sơ đồ lệch nguồn, hoặc khi cần vẽ luồng/ERD/máy trạng thái mới.
---

# Sơ đồ: sinh cái suy ra được, vẽ tay cái mã hoá quyết định

Nguyên tắc: **thứ gì suy được từ nguồn máy đọc thì không chép tay.** Bản chép tay thứ hai luôn rời bản
thứ nhất, im lặng, và người đọc tin bản chép chứ không đi đọc YAML.

## Bước 0 — sơ đồ bạn cần thuộc loại nào?

| Sơ đồ | Loại | Nguồn / nơi vẽ |
|---|---|---|
| Lớp & ranh giới import (§3) | **sinh** | `contracts/boundaries.yaml` |
| Ai sở hữu vùng nào (§9) | **sinh** | `coordination/policy.yaml` ← `team-profile.yaml` |
| Bối cảnh hệ thống (§2) | **người vẽ** | vùng `HAND-DRAWN:context` |
| Luồng găng (§4) | **người vẽ** | vùng `HAND-DRAWN:flow` |
| ERD, máy trạng thái, triển khai | **người vẽ** | chưa có — thêm khi dự án cần (xem dưới) |

Cần sơ đồ nào ở giai đoạn nào của sản phẩm (khám phá → vận hành), cho ai đọc: skill `diagram-roadmap` (pack
`product-design`). Skill này chỉ lo cơ chế vẽ và giữ đồng bộ.

## Nếu là sơ đồ SINH

Đừng mở tài liệu ra sửa. Sửa **nguồn**, rồi sinh lại:

```bash
# đổi lớp / chiều import / mô tả trách nhiệm:
$EDITOR contracts/boundaries.yaml          # kể cả trường `description` — nó là nguồn của cột Trách nhiệm
# đổi vùng bảo vệ / làn độc quyền:
$EDITOR coordination/policy.yaml
# đổi ai sở hữu (chủ vùng sinh từ team-profile):
python scripts/generate_team_docs.py       # PHẢI chạy trước, nó viết lại `owners:` trong policy.yaml

python scripts/generate_diagrams.py        # rồi mới sinh sơ đồ
python scripts/generate_diagrams.py --check   # đúng lệnh CI chạy
```

⚠️ Sửa tay trong vùng `<!-- GENERATED:... -->` sẽ bị lần sinh sau ghi đè **và** bị CI bắt lệch. Nếu thấy
mình đang muốn sửa tay ở đó, nghĩa là nguồn đang thiếu trường — thêm trường vào nguồn thay vì phá vùng.

Đổi hợp đồng ranh giới là **đổi kiến trúc**: cần ADR (skill `adr`) và người duyệt — `contracts/` và
`docs/design/` đều là vùng bảo vệ.

## Nếu là sơ đồ NGƯỜI VẼ

Viết trong cặp mốc `<!-- HAND-DRAWN:<tên> -->` … `<!-- /HAND-DRAWN:<tên> -->`. Lưới canh
`tests/guards/test_diagrams_dong_bo.py` chỉ kiểm vùng **có mặt và có khối sơ đồ bên trong** — nó
**không** kiểm sơ đồ vẽ đúng. Nói thẳng giới hạn này khi báo cáo, đừng để người khác tưởng CI đã duyệt
nội dung.

Thêm sơ đồ người vẽ mới: thêm cặp mốc vào tài liệu, thêm tên vào `HAND_DRAWN_BAT_BUOC` trong lưới canh,
rồi chứng minh lưới đỏ khi xoá sơ đồ (skill `guard-net` bước 3).

## Chọn dạng sơ đồ

- **Mermaid** cho thứ có cấu trúc (lớp, quyền sở hữu, trạng thái, ERD): GitHub và artifact đều render
  sẵn, không cần toolchain, và diff đọc được.
- **ASCII** cho luồng tuyến tính có chú thích dài (như §2, §4): mermaid làm nhãn dài trở nên khó đọc.
- Một sơ đồ nói **một điều**. Cần nói hai điều thì vẽ hai sơ đồ.
- **Ghi nhãn mũi tên.** Mũi tên không nhãn nghĩa là "có liên quan"; `được phép import`, `sở hữu`,
  `chờ check xanh` mới là thông tin.

## Khi CI đỏ ở bước "Sơ đồ kiến trúc khớp..."

Không phải lỗi hạ tầng. Nghĩa là tài liệu và nguồn đã lệch: chạy `python scripts/generate_diagrams.py`,
**đọc diff** (diff cho biết ai đổi cái gì mà quên sinh lại), rồi commit cùng PR.
