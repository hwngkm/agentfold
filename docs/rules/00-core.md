# RULE 00 — Cốt lõi

> Áp dụng cho mọi người, mọi agent, mọi file. Rule tầng dưới mâu thuẫn file này thì file này thắng.

## R00.1 — Thứ tự ưu tiên khi phải đánh đổi

```
An toàn người dùng > Tính đúng của dữ liệu > Thiết kế đã chốt > Tính năng > Tốc độ > Vẻ đẹp code
```

Phân vân thì chọn phương án an toàn hơn và ghi lý do (`python -m tools.agentctl new decision ...`).

## R00.2 — Fail closed

Nghi ngờ thì chặn. Không có "cảnh báo nhưng vẫn cho qua" với: vi phạm bất biến, dữ liệu không nguồn tới
người dùng, hành động rủi ro cao chưa duyệt, cấu hình production thiếu.

## R00.3 — Truy vết được

Mọi thứ tới tay người dùng trả lời được: *con số này ở đâu ra* (`source`, `source_ref`) · *vì sao hệ thống
chọn thế* (quy tắc/giải thích) · *ai chịu trách nhiệm* (người duyệt + `audit_log`).

## R00.4 — Không tính năng ẩn

Không code path nào chạy mà không có trong `docs/design/ARCHITECTURE.md`. Thêm luồng ⇒ cập nhật tài liệu
trong cùng PR. Đổi API ⇒ `contracts/openapi.json` đổi trong cùng PR.

## R00.5 — Nói thật về giới hạn

Trong giao diện, README, báo cáo: mô tả đúng những gì hệ thống làm được. Không "chính xác tuyệt đối", không
"thay thế chuyên gia". Báo cáo công việc: không báo "xong" khi còn dở, không báo "đã kiểm" khi chưa chạy.

## R00.6 — Quyết định để lại vết

Quyết định kỹ thuật đáng kể: một file DEC (*bối cảnh → phương án → quyết định → hệ quả*). Đổi thiết kế đã
chốt: ADR. Không sửa lịch sử — ghi sai thì thêm mục đính chính.

## R00.7 — Ranh giới sở hữu

Mỗi vùng có chủ (`docs/GOVERNANCE.md`, `coordination/policy.yaml`, `.github/CODEOWNERS`). Sửa module người
khác thì trong phạm vi ticket đã duyệt, không âm thầm refactor giữa chu kỳ.

## R00.8 — Bằng chứng thắng tự khai

"Xong" = lệnh đã chạy + kết quả. Test mới phải từng đỏ. Một con số đo được thắng mọi suy luận hợp lý —
khi ba dữ kiện khớp thành một câu chuyện mạch lạc, kiểm giả thuyết đối lập rẻ nhất trước khi kết luận.

## R00.9 — Định nghĩa "xong"

Một ticket chỉ xong khi TẤT CẢ đúng:

- [ ] Mọi tiêu chí `acceptance` có bằng chứng (lệnh/test).
- [ ] `python scripts/ci_local.py` xanh; CI xanh.
- [ ] `python -m tools.agentctl check-scope` không vi phạm.
- [ ] Có test cho logic mới, đã thấy đỏ trước.
- [ ] Tài liệu/hợp đồng liên quan cập nhật cùng PR.
- [ ] Được người (hoặc agent reviewer + người merge) review.
- [ ] Có mục nhật ký; claim đã release sau merge.

## R00.10 — Ngôn ngữ

Định danh trong code, tên file, lệnh: **tiếng Anh** (mọi công cụ và agent xử lý ổn định). Văn xuôi — tài
liệu, docstring, comment giải thích lý do, thông điệp cho người dùng Việt: **tiếng Việt có dấu**. Ngoại lệ:
file cấu hình mà công cụ đọc bằng mã hoá hệ thống (vd. `alembic.ini`) chỉ dùng ASCII.

## R00.11 — Comment nói "vì sao", và phải còn đúng

Comment giải thích lý do và sự cố đã gặp — thứ code không tự nói được. Comment kiểu "đang chờ X" phải được
gỡ ngay khi X xong: comment lỗi thời nghe có thẩm quyền hơn một linh cảm, và người đọc (lẫn agent) sẽ tin nó.
