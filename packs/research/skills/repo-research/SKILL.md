---
name: repo-research
description: Tìm và đánh giá repo mã nguồn mở trên GitHub (hoặc GitLab) trước khi dùng, fork, chép ý tưởng hay thêm làm phụ thuộc — tìm có hệ thống, rồi chấm theo tiêu chí kiểm được (còn bảo trì, giấy phép, mức dùng thật, chất lượng, bảo mật, rủi ro một người duy trì), đọc mã thật chứ không chỉ README. Dùng khi cần thư viện/khung/công cụ cho một việc, khi tham khảo kiến trúc của dự án khác, khi định thêm phụ thuộc mới, hoặc khi so sánh nhiều lựa chọn mã nguồn mở.
---

# Nghiên cứu repo: số sao là tín hiệu yếu, mã và lịch sử là bằng chứng

Tìm cái có sẵn TRƯỚC khi viết mới; nhưng thêm
phụ thuộc là làn độc quyền `python-deps`/`web-deps` và là quyết định có ghi lại (DEC).

## 1. Tìm

```bash
python -m scripts.research github "agent coordination git" --limit 10          # không cần MCP, không cần gh
gh search repos "agent coordination" --sort stars --limit 10 --json fullName,stargazersCount,pushedAt,license
gh search code "sanitize_untrusted language:python" --limit 20                 # tìm cách người khác làm một việc cụ thể
python -m scripts.research pypi <tên-gói>    # / npm <tên-gói> — phiên bản mới nhất, giấy phép, Python hỗ trợ
```

Tìm bằng vài cách diễn đạt (tiếng Anh, tên khái niệm, tên đối thủ). Ghi lại truy vấn đã dùng.

## 2. Chấm (bảng, mỗi ô có bằng chứng)

| Tiêu chí | Kiểm bằng | Cờ đỏ |
|---|---|---|
| Còn bảo trì | commit/phát hành gần nhất: `gh api repos/<o>/<r>/commits?per_page=5`, `gh release list -R <o>/<r>` | archived; không commit > 12 tháng mà issue vẫn mở |
| Giấy phép | `gh api repos/<o>/<r>/license --jq .license.spdx_id`; đọc file LICENSE | không có giấy phép = KHÔNG được dùng; AGPL/GPL với sản phẩm đóng → hỏi người |
| Mức dùng thật | lượt tải PyPI/npm, "Used by", số người đóng góp | sao cao mà tải thấp (trend nhất thời) |
| Rủi ro một người | `gh api repos/<o>/<r>/contributors --jq '.[].contributions'` | > 90% commit từ một người, không người thay |
| Chất lượng | có test + CI xanh; đọc 2–3 file lõi | không test; README hứa nhiều hơn mã làm |
| Bảo mật | advisory (`gh api repos/<o>/<r>/security-advisories`), `pip-audit`/`npm audit` sau khi thử cài | lỗ hổng chưa vá; cài kéo theo script chạy khi cài |
| Hợp với ta | ngôn ngữ, phiên bản runtime, phụ thuộc kéo theo, kích thước | kéo theo framework thứ hai; xung đột phiên bản |

## 3. Đọc mã thật

Clone nông vào thư mục tạm ngoài repo (`git clone --depth 1 <url> /tmp/x`), đọc phần lõi giải quyết đúng việc cần — không
phải README. Thử chạy ví dụ tối thiểu. **Không** chạy script cài đặt của repo lạ trên máy có bí mật thật.

## 4. Quyết định

| Kết luận | Khi |
|---|---|
| Thêm làm phụ thuộc | tiêu chí đều qua; ghi DEC + ticket có làn `python-deps`/`web-deps` |
| Học ý tưởng, tự viết | repo tốt nhưng to/kéo theo nhiều; ghi nguồn ý tưởng trong docstring (như `tools/agentctl/mail.py`) |
| Fork | chỉ khi cần sửa sâu và chấp nhận tự bảo trì — ghi rõ chi phí bảo trì |
| Bỏ | có cờ đỏ không giải quyết được |

Chép mã: tôn trọng giấy phép (giữ thông báo bản quyền khi giấy phép yêu cầu). Kết quả ghi theo skill `research-notes`.

Không có `gh`: `python -m scripts.research github ...` và trang web GitHub cho mọi bước trên.
