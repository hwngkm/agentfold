---
name: iac
description: Quản lý hạ tầng đám mây bằng mã (Terraform) — plan trước apply, state ở backend từ xa có khoá, module và phiên bản provider ghim, mọi thay đổi qua PR, agent chỉ chạy plan còn apply do người duyệt. Dùng khi tạo hoặc đổi tài nguyên đám mây (CSDL, bucket, DNS, máy chủ), khi hạ tầng bị sửa tay lệch khỏi mã, hoặc khi đưa hạ tầng đang click tay vào quản lý bằng mã.
---

# Hạ tầng dạng mã: plan là bằng chứng, apply là quyết định của người

Template mặc định dùng nền tảng quản lý (Render, Vercel) — cấu hình của chúng đã là mã (`render.yaml`,
`web/vercel.json`). Chỉ thêm Terraform khi có tài nguyên ngoài các nền tảng đó; ghi lý do thành DEC.

## Bố cục

```
infra/terraform/
  versions.tf      # required_version + required_providers ghim phiên bản
  backend.tf       # state từ xa có khoá — KHÔNG để terraform.tfstate trong repo
  main.tf          # tài nguyên / gọi module
  variables.tf     # đầu vào có mô tả + kiểu; bí mật đánh dấu sensitive = true
  outputs.tf
  envs/{staging,prod}.tfvars   # không chứa bí mật
```

`.gitignore` phải loại `*.tfstate*`, `.terraform/`, `*.tfvars` chứa bí mật. State chứa giá trị nhạy cảm dạng thô.

## Thủ tục một thay đổi

1. Sửa mã trong nhánh của ticket.
2. `terraform fmt -check && terraform validate`.
3. `terraform plan -var-file=envs/staging.tfvars -out=plan.bin` → dán **tóm tắt plan** (thêm/đổi/huỷ bao nhiêu
   tài nguyên, tài nguyên nào bị HUỶ) vào PR.
4. Người duyệt đọc plan. Có `destroy` hoặc `replace` tài nguyên chứa dữ liệu (CSDL, bucket) → dừng, hỏi.
5. **Apply do người chạy** (hoặc job CI cần duyệt thủ công) — agent không chạy `terraform apply` (R60, hành động HIGH).
6. Staging trước, prod sau, cùng mã khác biến.

## Lệch khỏi mã (drift)

`terraform plan` trên `main` mà ra thay đổi = ai đó đã sửa tay. Không "apply cho khớp" mù quáng — tìm ai sửa và
vì sao; giữ thay đổi thì đưa vào mã, bỏ thì apply để khôi phục, ghi DEC.

## Công cụ đi kèm pack

- CLI `terraform` (pack `infra` kiểm có trên PATH).
- MCP `terraform` (`hashicorp/terraform-mcp-server`, chạy trong container cục bộ) để tra provider/module bản hiện
  hành thay vì đoán cú pháp từ trí nhớ. `TFE_TOKEN` chỉ cần khi dùng HCP Terraform.
- Không có MCP: `terraform providers schema -json` và tài liệu provider trên registry.terraform.io (đúng phiên
  bản ghim trong `versions.tf`).
