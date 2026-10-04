---
version: alpha
name: "Agentfold (mẫu)"
colors:
  primary: "#0F766E"
  on-primary: "#FFFFFF"
  background: "#FFFFFF"
  on-background: "#0F172A"
typography:
  body-md:
    fontFamily: system-ui
    fontSize: 1rem
    lineHeight: 1.5
  h1:
    fontFamily: system-ui
    fontSize: 2rem
    fontWeight: 700
rounded:
  sm: 4px
  md: 8px
spacing:
  sm: 8px
  md: 16px
  lg: 24px
components:
  page:
    backgroundColor: "{colors.background}"
    textColor: "{colors.on-background}"
    typography: "{typography.body-md}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.sm}"
    padding: 12px
---

## Overview

Bản sắc giao diện MẪU của template (trung tính, không phải thương hiệu thật). Dự án thật sinh lại tệp này bằng wizard hoặc
`python scripts/check_design.py --init ...`, rồi sửa khi thương hiệu đổi. Đã đối chiếu đặc tả google-labs-code/design.md ngày 2026-10-04
(định dạng `alpha`; nếu đặc tả đổi, rà lại bộ kiểm). Mọi thay đổi màu đi qua `python scripts/check_design.py DESIGN.md`
để giữ chữ đọc được (WCAG AA 4.5:1).

## Colors

- **Primary (#0F766E):** màu hành động chính (nút, liên kết). Chữ trên nó dùng `on-primary` (#FFFFFF).
- **Background (#FFFFFF) / On-background (#0F172A):** nền trang và chữ thường, tương phản 17.85:1.

## Typography

Phông hệ thống (`system-ui`) để không tải gì từ ngoài. Thân bài 1rem, tiêu đề lớn 2rem đậm.

## Layout

Khoảng cách theo thang 8/16/24px; chỉ dùng các bậc này, không giá trị tuỳ ý.

## Components

- `button-primary`: nền `primary`, chữ `on-primary`, bo góc nhỏ.
- `page`: nền và chữ thường của trang.

## Do's and Don'ts

- Dùng token trong tệp này, không viết thẳng mã màu vào component.
- Màu trạng thái luôn đi kèm chữ hoặc biểu tượng, không chỉ bằng màu.
