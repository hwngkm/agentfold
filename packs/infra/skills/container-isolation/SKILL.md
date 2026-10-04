---
name: container-isolation
description: Cách ly TUỲ CHỌN mỗi agent bằng container (dagger/container-use) — mỗi agent một container và một nhánh git, xem lại lịch sử lệnh thật. Dùng khi agent phải chạy lệnh không tin cậy (cài phụ thuộc lạ, chạy mã tải về, script người khác viết), khi cần cách ly mạng hoặc tiến trình giữa các agent chạy song song, hoặc khi người muốn xem chính xác agent đã chạy lệnh gì. Worktree đã đủ cho phần còn lại.
---

# Cách ly bằng container: tuỳ chọn, không bắt buộc

Worktree (`python -m tools.agentctl start <ID>`) cách ly **tệp**: mỗi ticket một nhánh, một thư mục. Nó **không** cách ly
tiến trình hay mạng — lệnh agent chạy vẫn là lệnh của máy bạn, thấy cùng mạng, cùng biến môi trường, cùng `$HOME`.
Container-use bù đúng chỗ đó: mỗi agent một container + một nhánh git, người xem lại được lịch sử lệnh.

## Khi nào đáng dùng

- Agent chạy lệnh **không tin cậy**: cài phụ thuộc chưa kiểm, chạy mã tải về, script do bên thứ ba viết.
- Nhiều agent chạy **song song** và cần tách tiến trình/cổng mạng (hai agent cùng mở một cổng, cùng ghi một cơ sở dữ liệu thử).
- Người muốn **xem lại** chính xác agent đã chạy lệnh gì, không chỉ diff cuối.

## Khi nào worktree là đủ (đa số trường hợp)

- Sửa mã, chạy `make check-fast`, test nội bộ của repo — lệnh đã nằm trong `Makefile`/`ci_local.py`.
- Một agent một lúc, không chạy mã lạ.
- Máy không có Docker, hoặc người không muốn thêm công cụ — **không dùng container cũng không sai luật nào**.

## Cách bật

1. Người cài `container-use` (cần Docker và Git; xem README dagger/container-use — `brew install dagger/tap/container-use`
   hoặc script `install.sh` của repo). Cài phần mềm hệ thống là việc của người, `packs.py` chỉ kiểm có trên PATH.
2. `python scripts/packs.py --install infra` ghi MCP `container-use` (`container-use stdio`) vào `.mcp.json` và đồng bộ
   skill sang `.agents/skills`. Tắt: `--remove infra` gỡ cả hai. Pack `infra` cũng mang Terraform/Docker — chưa cần thì đừng bật.
3. Agent có MCP thì chạy lệnh qua container. README nói người xem được lịch sử lệnh và log của từng agent, và có thể
   `git checkout <nhánh>` của agent để xem việc đã làm; tên lệnh xem lịch sử cụ thể xem trong tài liệu bản bạn cài (README không nêu).

## Giới hạn nói thật

- Container-use KHÔNG thay luật của repo: claim, phạm vi ticket, hook và `human-approved` vẫn áp dụng. Nhánh git do nó tạo
  phải về nhánh ticket qua PR như mọi thay đổi.
- Không cách ly bí mật nếu bạn truyền biến môi trường vào container: đừng đưa khoá thật cho agent chạy mã không tin cậy.
- Agent không có MCP (Codex, Copilot, Cursor…) không dùng được cách này: fallback là worktree, lệnh rủi ro do người chạy.

## Công cụ đi kèm pack

- CLI `container-use` (pack `infra` kiểm có trên PATH) và MCP `container-use` (chạy cục bộ).
- Không có MCP: worktree hiện có (fallback ghi trong `packs/registry.yaml`).
