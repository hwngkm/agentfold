---
name: design-system
description: Dựng và giữ hệ thống thiết kế bằng token ba tầng (primitive → semantic → component) trong CSS custom properties, chế độ sáng/tối, cấm giá trị màu/cỡ viết thẳng trong component, và kiểm tương phản. Dùng khi bắt đầu giao diện cho dự án mới, khi màu/khoảng cách bị lặp tràn lan và lệch nhau, khi thêm chế độ tối hoặc đổi thương hiệu, hoặc khi review CSS mới.
---

# Hệ thống thiết kế: đổi thương hiệu là sửa một tầng, không sửa trăm component

Template dùng CSS thuần (`web/src/app/globals.css`), không framework CSS. Token là CSS custom properties.

## Nguồn token: `DESIGN.md`

`DESIGN.md` ở gốc repo là NGUỒN token cho agent: YAML front matter (màu, chữ, bo góc, khoảng cách, component) + lý do bằng Markdown,
theo định dạng google-labs-code/design.md (đối chiếu 2026-10-04, `alpha`). Đọc nó trước khi viết giao diện; muốn đổi màu/chữ thì sửa
nó rồi suy ra CSS bên dưới, không sửa CSS trước.

```bash
python scripts/check_design.py DESIGN.md   # JSON; thoát 1 nếu tham chiếu {colors.x} gãy hoặc cặp chữ/nền dưới WCAG AA 4.5:1
python scripts/check_design.py --init --name "Tên dự án" --primary "#0F766E" --background "#FFFFFF" --text "#0F172A"
```

Wizard của template cũng sinh `DESIGN.md` khởi đầu từ ba màu người dùng chọn. Bộ kiểm chỉ đo màu hex; màu `oklch()` được báo "không
đo được" — đo bằng DevTools rồi ghi cặp đã đo. CI chạy bộ kiểm này.

## Ba tầng token

```css
:root {
  /* 1. Primitive — giá trị thô, KHÔNG dùng trực tiếp trong component */
  --blue-600: #1d4ed8;  --gray-50: #f9fafb;  --gray-900: #111827;
  --space-1: 0.25rem;   --space-4: 1rem;     --radius-2: 0.5rem;

  /* 2. Semantic — ý nghĩa; component chỉ dùng tầng này trở lên */
  --color-bg: var(--gray-50);
  --color-text: var(--gray-900);
  --color-action: var(--blue-600);
  --color-danger: #b91c1c;
  --gap-stack: var(--space-4);
}
@media (prefers-color-scheme: dark) {
  :root { --color-bg: var(--gray-900); --color-text: var(--gray-50); }
}
/* 3. Component — chỉ khi một component cần biến thể riêng */
.button { --button-bg: var(--color-action); background: var(--button-bg); }
```

Chế độ tối/đổi thương hiệu = đổi tầng semantic; component không đổi.

## Luật

- Component **không** chứa giá trị màu hex, `px` khoảng cách tuỳ ý hay font tuỳ ý — chỉ `var(--...)`.
- Thêm token semantic mới khi có **ý nghĩa** mới (vd. `--color-estimate` cho nhãn "ước tính"), không khi chỉ thiếu
  một sắc độ.
- Màu trạng thái luôn đi kèm chữ/biểu tượng (R30.5).

## Kiểm

- Tương phản chữ/nền ≥ 4.5:1 (chữ thường), ≥ 3:1 (chữ lớn, viền điều khiển) ở cả sáng và tối — đo bằng công cụ
  kiểm tương phản của trình duyệt (DevTools), ghi cặp đã đo.
- Tìm giá trị viết thẳng còn sót: `grep -rnE "#[0-9a-fA-F]{3,6}\b" web/src --include=*.tsx --include=*.css`
  (ngoài khối primitive).
- Có thể thêm một lưới canh làm việc này tự động khi hệ thống thiết kế đã ổn định (skill `guard-net`).

## Công cụ đi kèm

Plugin `frontend-design` (pack này gợi ý) hữu ích cho phương án bố cục/thẩm mỹ; mọi phương án vẫn phải đi qua
token ở trên và luật trong `web/AGENTS.md`.
Không có plugin: làm theo các tầng token ở trên là đủ — plugin chỉ gợi ý phương án thẩm mỹ.
