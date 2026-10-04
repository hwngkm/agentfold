# Preset team-size / complexity

Hai trục độc lập, chọn khi khởi tạo dự án (hoặc đổi sau bằng `python scripts/generate_team_docs.py`):

- **team-size** — bao nhiêu người thật đứng sau các vai trò: `solo` (1) · `small` (2) · `standard` (4,
  mặc định) · `large` (6+, tách vận hành và thêm vai trò bảo mật).
- **complexity** — mức nghi thức: `lite` (POC, ADR chỉ cho quyết định khó đảo ngược) · `standard` (mặc
  định) · `strict` (rủi ro cao — thêm lớp bảo mật đồng duyệt, khuyến nghị 2 người duyệt).

Hai trục **không phụ thuộc nhau**: một POC dữ liệu nhạy cảm là `solo` + `strict`; một đội 4 người demo
nội bộ là `standard` + `lite`.

**Team-size không đổi cơ chế `tools/agentctl`.** Claim, worktree, kiểm phạm vi vẫn chạy y hệt dù 1 hay
20 người — chúng ngăn CHÍNH BẠN (qua nhiều phiên agent song song) giẫm chân nhau, không chỉ ngăn đồng
đội. Team-size/complexity chỉ đổi: bảng vai trò (`docs/GOVERNANCE.md`), `.github/CODEOWNERS`, chủ vùng
bảo vệ (`coordination/policy.yaml`), và mức nghi thức duyệt/ADR.

Đổi lựa chọn:

```bash
python scripts/generate_team_docs.py --team-size small --complexity strict --apply
```

`docs/design/team-profile.yaml` là nguồn sự thật đang áp dụng; `GOVERNANCE.md`/`CODEOWNERS`/phần
`owners:` trong `policy.yaml` là **sinh ra** từ nó — lưới canh đỏ nếu ai sửa profile mà quên sinh lại,
hoặc sửa tay ba file kia mà không qua script (giống cách `contracts/openapi.json` được canh).
