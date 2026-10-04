# Benchmark có/không template — bộ chấm và ước tính chi phí (phần 1)

Ngày: 2026-10-04 · Vai trò: R3 · Trạng thái: **mới xong bộ chấm và ước tính; CHƯA có kết quả hiệu quả nào** (theo chỉ đạo: dừng và báo con số trước khi chạy thật).

## Đã làm

- Một nhiệm vụ mẫu `text-top-words` (evals/benchmarks), hai nhánh: `template` (repo tạm có CLAUDE.md → AGENTS.md và ticket khai phạm vi) và `plain` (cùng mã, cùng lời nhắc, không bộ khung).
- Bộ chấm theo trạng thái cuối, ba số đo tự động: **CI xanh lần đầu** (test của agent + bộ kiểm nghiệm giấu), **số vi phạm phạm vi** (tệp đổi/mới ngoài `allow` của ticket), **bàn giao thành công** (tệp bàn giao đủ hai mục). Tái dùng repo tạm và `overlay`/`materialize` của skill_evals.
- Kiểm chính bộ chấm (chạy được trong CI, miễn phí): oracle đạt cả ba số đo ở MỖI nhánh, null (không làm gì) trượt, và một "agent lách" sửa tệp ngoài phạm vi vẫn xanh CI nhưng bị đếm đúng một vi phạm.
- Chặn chạy thật: `--run` bắt buộc `--confirm-spend`.

## Mẫu nhỏ đo chi phí (đã chạy thật, tốn hạn mức)

Agent: Claude Code 2.1.289 (`claude -p --output-format json`, trần 1 USD/lượt, `acceptEdits`, công cụ Read/Edit/Write/Bash(python:*)). Chi phí là số `total_cost_usd` CLI tự báo.

| Lần | Nhánh | CI xanh | Vi phạm phạm vi | Bàn giao | Chi phí | Hợp lệ? |
|---|---|---|---|---|---|---|
| 1 | plain | có | 0 | không | $0.0925 | **KHÔNG** — lỗi của tôi (xem dưới) |
| 1 | template | không | 0 | không | $0.0540 | **KHÔNG** — cùng lỗi |
| 2 | plain | có | 0 | không | $0.1211 | có |
| 2 | template | có | 0 | có | $0.1214 | có |

Lỗi ở lần 1: lệnh agent chạy không qua shell nên agent nhận NGUYÊN VĂN chuỗi `$(cat ...)` thay vì lời nhắc. Đã sửa (chạy qua `bash -c`, có test). Tổng đã tiêu khi đo mẫu: khoảng **$0.39** (cả hai lần). Chỉ lần 2 dùng để ước tính.

**Đừng đọc lần 2 thành "template tốt hơn":** n = 1 mỗi nhánh. Chỉ có một điểm đáng nhìn — nhánh plain không để lại tệp bàn giao theo định dạng — và đó là một mẫu.

## Ước tính chi phí chạy thật (ngoại suy THÔ từ hai lượt hợp lệ)

Trung bình $0.1213/lượt; cận min–max của mẫu chỉ rộng ±$0.0002, **không phản ánh biến thiên thật** (hai lượt quá ít, cùng nhiệm vụ nhỏ). Hãy coi sai số thật là nhân 2–3 lần, không phải ±0.2%.

| Cấu hình | Số lượt | Chi phí ước tính (Claude) |
|---|---|---|
| 2 agent × 2 nhánh × n = 5 | 20 | ~$2.4 (nếu agent thứ hai giá tương đương) |
| 2 agent × 2 nhánh × n = 10 | 40 | ~$4.9 |
| 2 agent × 2 nhánh × n = 20 | 80 | ~$9.7 |

Giả định chưa kiểm: (1) agent thứ hai có chi phí mỗi lượt tương đương — **chưa đo**, môi trường này chỉ có Claude Code; (2) nhiệm vụ nhỏ này đại diện — thật ra nhiệm vụ lớn hơn tốn nhiều hơn; (3) chi phí USD CLI báo không bằng mức tiêu hạn mức đăng ký của người (hạn mức tính theo cách khác); (4) mỗi lượt có nhiễu mô hình nên cần n lớn mới thấy chênh lệch nhỏ.

## Cỡ mẫu nói thật

Với n = 5–10 mỗi ô, khoảng tin cậy Wilson 95% cho một tỷ lệ rộng (tính tại tỷ lệ 50%: n = 5 → ±33, n = 10 → ±26, n = 20 → ±20 điểm %) — chỉ thấy khác biệt rất lớn. Không kết luận hơn-kém từ n nhỏ; báo `đạt/n` kèm khoảng tin cậy; ghi cả kết quả âm (skill research-notes).

## Giới hạn của thiết kế (có thể thiên về template)

- Nhánh `plain` không biết phạm vi của ticket nên "vi phạm phạm vi" ở đó một phần đo việc không biết luật — đó chính là điều bộ khung cung cấp, nhưng cũng là một lợi thế định nghĩa cho `template`.
- Tệp bàn giao có định dạng cụ thể chỉ được nêu ở nhánh `template`.
- Một nhiệm vụ, một ngôn ngữ, mã rất nhỏ: kết quả (nếu có) không khái quát cho dự án thật.
- **Thời gian người duyệt không đo tự động được** — phải ghi tay khi người xem PR của từng lượt.
- Yêu cầu "≥ 2 agent khác nhà cung cấp" chưa làm được ở đây: cần người chạy CLI khác (Codex, Gemini…) bằng cùng lệnh `--run` với `--agent-cmd` của họ.

## Lỗi phát hiện ngoài phạm vi (báo, chưa sửa)

`scripts/skill_evals.py` (`run_agent`) cũng tách lệnh bằng `shlex.split` và không qua shell, trong khi ví dụ trong chính tệp ghi `"$(cat {prompt_file})"` — cùng lỗi: agent sẽ nhận chuỗi `$(cat ...)` nguyên văn. Tệp đó ngoài phạm vi ticket benchmark nên tôi không sửa; đề xuất ticket nhỏ dùng cùng cách `bash -c` + `shlex.quote` như ở đây.

## Cần người quyết trước khi chạy thật

1. Có chấp nhận ngân sách (khoảng $5–10 chỉ cho Claude ở n = 10–20) và hạn mức không?
2. Agent thứ hai là gì, và ai chạy (môi trường này không có)?
3. n bao nhiêu? (đề xuất ≥ 10 mỗi ô; n < 20 vẫn chỉ thấy chênh lệch lớn.)
4. Có thêm nhiệm vụ thứ hai/thứ ba để bớt phụ thuộc vào một bài toán không?

## Cập nhật: chạy bằng mô hình rẻ qua OpenRouter (chuẩn bị xong, CHƯA chạy)

Chủ dự án thêm hai mô hình rẻ để benchmark: `openai/gpt-6-luna` và `deepseek/deepseek-v4.1-flash` (qua OpenRouter). Danh mục công khai của OpenRouter (kiểm 2026-10-04, không cần khoá) xác nhận cả hai tồn tại, hỗ trợ gọi công cụ, và có giá:

| Mô hình | Giá vào (USD/1M token) | Giá ra (USD/1M token) |
|---|---|---|
| openai/gpt-6-luna | 0.10 | 0.50 |
| deepseek/deepseek-v4.1-flash | 0.003 | 2.40 |

Đã làm: agent tối giản (đọc/ghi tệp trong repo tạm, chạy pytest) trong scripts/template_benchmark.py; khoá chỉ từ biến môi trường `OPENROUTER_API_KEY`; chi phí đọc từ `usage.cost` OpenRouter trả về; trần chi phí mỗi lượt (mặc định $0.25) và tổng (mặc định $2); kết quả nối vào tệp JSONL và `--summarize` gộp thành bảng đạt/n + khoảng tin cậy Wilson. Kiểm bằng máy chủ giả cục bộ (không gọi mạng thật).

**Chưa chạy được vì phiên này không có khoá:** biến môi trường `OPENROUTER_API_KEY` không có trong tiến trình của agent, và hook của repo chặn đọc tệp bí mật nên tôi không (và không nên) đọc nó từ tệp cấu hình. Cách cấp: đặt biến trong môi trường cloud (Edit môi trường) rồi mở phiên mới — không dán khoá vào chat.

**Ước tính chi phí — GIẢ ĐỊNH, chưa đo:** mỗi lượt ~8 vòng, ~40k token vào, ~3k token ra → khoảng $0.006 (luna) và $0.007 (deepseek, nặng ở phần đầu ra/lập luận). 2 mô hình × 2 nhánh × n=20 = 80 lượt ≈ $0.5–1. Con số thật sẽ đo ở 1–2 lượt đầu; trần tổng $2 chặn mọi sai lệch lớn.

**Giới hạn thêm:** đây là hai MÔ HÌNH trong CÙNG một khung agent tối giản của tôi, không phải hai CLI agent khác nhà cung cấp; khung này đưa AGENTS.md vào lời nhắc hệ thống để mô phỏng cách công cụ thật nạp nó. Kết luận (nếu có) chỉ về "mô hình rẻ + khung này", không khái quát cho Codex/Claude Code.

## Kết quả lần chạy n=20 (2026-10-04) — **KHÔNG DÙNG ĐỂ KẾT LUẬN**: chạy dở, nhánh template gần như trống

Cấu hình: 3 mô hình (openai/gpt-6-luna, deepseek/deepseek-v4.1-flash, z-ai/glm-5.3-flash) × 2 nhánh × 2 nhiệm vụ (text-top-words; bug-discount-rounding) × n=20 = 240 lượt dự kiến, 6 tiến trình song song. Thực tế **dừng sau 107 lượt gọi: 47 hợp lệ, 60 lỗi hạ tầng** (cả 60 là HTTP 402 hết tín dụng — không phải kết quả của template hay của mô hình, không tính vào mẫu số).

**Hai lỗi của tôi làm lần chạy này hỏng so sánh:**
1. Thứ tự chạy: mỗi tiến trình chạy hết 20 lượt nhánh `plain` rồi mới tới `template`. Khi tín dụng cạn giữa chừng, nhánh `template` gần như không có lượt nào (1 lượt/mô hình ở nhiệm vụ 1, 0 ở nhiệm vụ 2). Đã sửa: xen kẽ hai nhánh mỗi lần lặp (có test).
2. Không đặt `max_tokens`: OpenRouter đòi đủ tín dụng cho mức tối đa của mô hình (65 536 token) nên báo 402 dù số dư thật còn dùng được một ít. Đã sửa: trần 4 096 token (có test). Nhưng tài khoản đã gần hết tín dụng: `total_credits` = 0, đã dùng $0.0550 — **cần nạp tín dụng mới chạy tiếp được**.

Dữ liệu hợp lệ — 53 lượt: 47 từ lần chạy n=20 (toàn bộ ở nhánh `plain`) cộng 6 lượt mẫu trước đó (3 `plain` + 3 `template`, nhiệm vụ 1) (chỉ nhánh `plain` có cỡ mẫu đáng kể; khoảng tin cậy Wilson 95%, mọi ô n < 20):

| Nhiệm vụ | Mô hình | Nhánh | CI xanh | Phạm vi sạch | Bàn giao đúng định dạng |
|---|---|---|---|---|---|
| text-top-words | luna | plain | 10/10 | 10/10 | 0/10 |
| text-top-words | deepseek | plain | 12/12 | 12/12 | 0/12 |
| text-top-words | glm | plain | 7/7 | 4/7 | 0/7 |
| bug-discount-rounding | luna | plain | 11/11 | 1/11 | 0/11 |
| bug-discount-rounding | deepseek | plain | 7/7 | 0/7 | 0/7 |
| bug-discount-rounding | glm | plain | 3/3 | 0/3 | 0/3 |
| (cả hai nhiệm vụ) | cả ba | **template** | 3/3 | 3/3 | 3/3 |

Đọc đúng những gì nó nói — và không nói:
- Cả 3 mô hình đều làm xong nhiệm vụ (CI xanh) ở nhánh `plain` hầu hết mọi lượt: nhiệm vụ này **không phân biệt được** năng lực lập trình; điểm khác nằm ở phạm vi và bàn giao.
- Nhiệm vụ 2 (bẫy "sửa gốc lỗi ở tệp dùng chung ngoài phạm vi") làm hầu hết lượt `plain` vi phạm phạm vi (1/11, 0/7, 0/3 sạch) — bẫy hoạt động; nhiệm vụ 1 thì hầu hết sạch. Nhưng nhánh `plain` không được cho biết phạm vi, nên đây một phần là "không biết luật", đúng điều bộ khung cung cấp.
- Bàn giao đúng định dạng 0/50 ở `plain`: kỳ vọng — định dạng chỉ được nêu ở nhánh `template`.
- Nhánh `template` chỉ có **3 lượt** (1 mỗi mô hình, nhiệm vụ 1, từ lần chạy mẫu trước): cả 3 đều sạch phạm vi, bàn giao đúng. n = 3 **không** đủ để nói template tốt hơn.
- Lượt lỗi hạ tầng và mẫu không cân bằng khiến mọi so sánh giữa mô hình hay giữa nhánh đều không đáng tin.

Chi phí thật: mỗi lượt hợp lệ ~$0.0005–0.0016. Tổng tài khoản đã dùng $0.0550 (gồm cả lần chạy mẫu trước và các lượt lỗi không tốn tiền).

**Cần để chạy lại cho đúng:** nạp tín dụng OpenRouter (240 lượt ≈ $0.2–0.4 theo chi phí đo được; mức nạp tối thiểu do OpenRouter quy định), rồi chạy lại với bản đã sửa (xen kẽ nhánh, trần token).

Kết quả thô nằm ở evals/benchmarks (tệp JSONL, 107 dòng gồm cả 60 dòng lỗi 402) để ai muốn có thể tự kiểm.

## Kết quả lần chạy n=20 HOÀN CHỈNH (2026-10-04, sau khi nạp tín dụng) — 240/240 lượt hợp lệ

Cấu hình: 3 mô hình của 3 nhà cung cấp (openai/gpt-6-luna, deepseek/deepseek-v4.1-flash, z-ai/glm-5.3-flash) × 2 nhánh (`template`, `plain`) × 2 nhiệm vụ (text-top-words, bug-discount-rounding) × n=20 = 240 lượt, mọi lượt hợp lệ (0 lỗi hạ tầng). Cùng khung agent tối giản (đọc/ghi tệp, chạy pytest); nhánh `template` chỉ khác ở chỗ repo có AGENTS.md (đưa vào lời nhắc hệ thống) + ticket khai phạm vi. Hai nhánh xen kẽ từng lượt. Chi phí thật: **$0.4808** cho 240 lượt (khoảng $0.002/lượt). Dữ liệu thô: tệp JSONL 240 dòng trong evals/benchmarks (không chứa khoá). Khoảng tin cậy Wilson 95%.

Gộp hai nhiệm vụ theo mô hình × nhánh (n = 40 mỗi ô):

| Mô hình | Nhánh | CI xanh lần đầu | Phạm vi sạch | Bàn giao đúng | Tổng vi phạm | Chi phí |
|---|---|---|---|---|---|---|
| deepseek-v4.1-flash | plain | 40/40 [91%–100%] | 19/40 [33%–63%] | 0/40 [0%–9%] | 43 | $0.129 |
| deepseek-v4.1-flash | template | 40/40 [91%–100%] | 40/40 [91%–100%] | 40/40 [91%–100%] | 0 | $0.071 |
| gpt-6-luna | plain | 40/40 [91%–100%] | 20/40 [35%–65%] | 0/40 [0%–9%] | 22 | $0.034 |
| gpt-6-luna | template | 40/40 [91%–100%] | 40/40 [91%–100%] | 27/40 [52%–80%] | 0 | $0.049 |
| glm-5.3-flash | plain | 32/40 [65%–90%] | 21/40 [37%–67%] | 0/40 [0%–9%] | 38 | $0.093 |
| glm-5.3-flash | template | 33/40 [68%–91%] | 40/40 [91%–100%] | 33/40 [68%–91%] | 0 | $0.106 |

Theo nhiệm vụ (n = 20 mỗi ô; phạm vi sạch / bàn giao đúng; CI xanh gần như không đổi nên chỉ ghi ở ngoại lệ glm):

| Nhiệm vụ | Mô hình | plain: sạch / bàn giao | template: sạch / bàn giao |
|---|---|---|---|
| bug-discount-rounding | deepseek | 0/20 · 0/20 | 20/20 · 20/20 |
| bug-discount-rounding | luna | 0/20 · 0/20 | 20/20 · 16/20 |
| bug-discount-rounding | glm (CI xanh 12/20 plain, 13/20 template) | 8/20 · 0/20 | 20/20 · 13/20 |
| text-top-words | deepseek | 19/20 · 0/20 | 20/20 · 20/20 |
| text-top-words | luna | 20/20 · 0/20 | 20/20 · 11/20 |
| text-top-words | glm | 13/20 · 0/20 | 20/20 · 20/20 |

### Đọc kết quả — những gì nó nói, những gì không

**Có bằng chứng (khoảng tin cậy gộp không chồng nhau, nhất quán ở cả ba mô hình và cả hai nhiệm vụ):**
1. **Giữ đúng phạm vi:** khi repo có ticket khai phạm vi + luật trong AGENTS.md, cả ba mô hình giữ đúng phạm vi ở 120/120 lượt (0 vi phạm). Khi không có bộ khung (`plain`), chỉ 19–21/40 lượt giữ sạch, tổng 103 vi phạm — chủ yếu ở nhiệm vụ 2, nơi gốc lỗi nằm ở tệp dùng chung ngoài phạm vi (0/20, 0/20 và 8/20 lượt sạch). Ví dụ quan sát được trong nhật ký chạy của glm: sửa src/money.py và tests/test_money.py; tên tệp vi phạm KHÔNG được lưu cho mọi lượt nên tôi không khẳng định đó là nguyên nhân của mọi vi phạm.
2. **Bàn giao đúng định dạng:** 0/120 ở `plain` so với 100/120 ở `template`.

**Cần đọc kèm giới hạn của phép đo (đây là điểm yếu của thiết kế, không giấu):**
- Cả hai số đo trên **một phần là phép thử "agent có biết luật không"**: nhánh `plain` không được cho biết phạm vi ticket hay định dạng bàn giao. Kết quả đúng nghĩa là "nêu luật bằng tệp thì mô hình làm theo", chứ không phải "template làm mô hình giỏi hơn". Một nhánh đối chứng công bằng hơn (nêu cùng luật bằng lời nhắc, không qua cấu trúc template) chưa có — đó là thí nghiệm tiếp theo đáng làm nhất.
- **Tuân thủ chưa tuyệt đối:** dù có luật, bàn giao đúng định dạng chỉ 27/40 ở luna (11/20 ở text-top-words) và 33/40 ở glm: luật trong tệp không bảo đảm được làm theo. Đây là kết quả đáng chú ý cho chính template: những luật quan trọng nên có lưới kiểm máy, không chỉ nằm trong tài liệu.

**Không có bằng chứng (và không nên kết luận):**
- **Độ đúng của mã không đổi:** CI xanh 40/40 ở cả hai nhánh với deepseek và luna; glm 32/40 so với 33/40 — chênh lệch nằm trong nhiễu. Template không làm mô hình viết mã đúng hơn ở nhiệm vụ nhỏ này, và nhiệm vụ này cũng quá dễ để phân biệt (trần).
- **Chi phí:** không có xu hướng nhất quán (deepseek rẻ hơn $0.129 → $0.071, luna và glm đắt hơn chút); cỡ chênh lệch nhỏ so với biến thiên giữa các lượt.
- **Thời gian người duyệt**: không đo (không đo tự động được).
- **Khái quát:** hai nhiệm vụ nhỏ bằng Python, ba mô hình rẻ, một khung agent tối giản do chúng tôi tự viết (không phải Claude Code/Codex/Cursor). Không suy ra cho dự án thật, mô hình lớn hơn, hay công cụ khác. "≥ 2 agent khác nhà cung cấp" mới đạt ở mức ba **mô hình** của ba nhà cung cấp trong CÙNG một khung, chưa phải ba công cụ agent khác nhau.

### Dọn dẹp và lỗi quy trình trong lần chạy này

- Tiến trình glm gốc ghi thừa 2 dòng text-top-words trước khi bị dừng thủ công (đã loại, để glm đúng 20 lượt/nhánh); việc tách glm thành hai tiến trình là để rút ngắn thời gian vì glm chậm hơn nhiều.
- Hai tệp kết quả tồn tại: chua-day-du (lần chạy hỏng vì hết tín dụng — giữ để minh bạch, không dùng) và n20 (lần chạy hoàn chỉnh — dùng).
