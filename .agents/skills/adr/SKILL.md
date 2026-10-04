---
name: adr
description: Viết Architecture Decision Record trong docs/design/adr/ khi một quyết định đụng kiến trúc, ranh giới, bất biến hay phụ thuộc. Dùng khi sắp sửa contracts/boundaries.yaml hoặc invariants.yaml, khi thêm/bỏ dependency hay đổi nhà cung cấp LLM, khi nới một ràng buộc an toàn, hoặc khi hai phương án đã tranh luận quá 15 phút mà chưa ngã ngũ.
---

# ADR: ghi lại quyết định, không ghi lại kết quả

ADR trả lời câu **"vì sao lại thế này?"** cho người đọc code sáu tháng sau — kể cả khi người đó là chính
bạn hoặc một agent khác không có ngữ cảnh phiên này.

## Khi nào BẮT BUỘC có ADR

- Sửa `contracts/boundaries.yaml` (thêm lớp, đổi chiều import, đổi danh sách SDK bị cấm)
- Thêm/sửa/xoá bất biến trong `docs/design/invariants.yaml`
- Thêm dependency mới, hoặc đổi nhà cung cấp LLM/CSDL/hạ tầng
- Nới bất kỳ ràng buộc an toàn nào (kể cả "chỉ nới một chút, chỉ cho trường hợp này")
- Đổi cấu trúc CI/deploy gate

Mức nghi thức ADR theo `complexity` trong `docs/design/team-profile.yaml` (`lite` nhẹ hơn `strict`) —
xem `docs/design/presets/README.md`.

## Khi nào KHÔNG cần

Sửa bug, đổi cài đặt trong một lớp mà không đụng ranh giới, thêm test, đổi câu chữ. Nếu phải hỏi "có cần
ADR không" cho một thay đổi nhỏ, thường là không — nhưng nếu thay đổi **khó đảo ngược**, viết.

## Thủ tục

1. `cp docs/design/adr/0000-template.md docs/design/adr/<số>-<slug-ngắn>.md` — số kế tiếp, 4 chữ số.
2. Điền header: `Status` (Proposed khi mở PR, Accepted khi merge), `Date`, `Owner`, `Reviewers`,
   `Supersedes` nếu thay ADR cũ.
3. **Bối cảnh** — viết bằng *số đo và sự kiện*, không bằng ý kiến. ADR-0001 làm mẫu: nó dẫn số commit
   thật trên file điểm nóng, không nói "file này hay xung đột".
4. **Phương án đã cân nhắc** — ít nhất hai, kèm lý do loại. Một ADR chỉ có một phương án là bản thông báo,
   không phải quyết định.
5. **Quyết định** — một đoạn, ở thể chủ động.
6. **Hệ quả** — cả mặt được và mặt mất. Mục "mất gì" trống là dấu hiệu chưa nghĩ đủ.
7. Nếu quyết định sinh ra một lời hứa cần giữ mãi ⇒ thêm bất biến vào `invariants.yaml` và làm lưới canh
   (skill `guard-net`). **ADR nói nên làm gì; lưới canh mới buộc làm.**
8. Cập nhật `docs/design/ARCHITECTURE.md` trong **cùng PR** nếu kiến trúc đổi (`docs/rules/00-core.md`
   R00.4: luồng mới mà không có trong ARCHITECTURE là tính năng ẩn).

## Đổi ý sau này

Không sửa ADR cũ để nó "đúng lại". Viết ADR mới, đặt `Supersedes: ADR-00xx`, và sửa ADR cũ đúng một dòng
`Status: Superseded by ADR-00yy`. Lịch sử quyết định sai cũng là thông tin — nó cho biết đường nào đã thử.

## Bẫy hay gặp

- **Viết ADR sau khi code xong để hợp thức hoá.** Lúc đó nó không còn là quyết định, chỉ là mô tả. Viết
  trước, kể cả bản nháp ba dòng.
- **Bối cảnh toàn tính từ** ("phức tạp", "khó bảo trì") thay vì số đo. Đo trước: `git log --format=%H -- <file> | wc -l`
  cho biết điểm nóng thật, trả lời được nhiều hơn một câu cảm nhận.
- **Không ghi mặt mất.** Mọi quyết định kiến trúc đều đánh đổi; ADR giấu đánh đổi sẽ bị người sau lật lại
  mà không biết vì sao lần trước chọn vậy.
