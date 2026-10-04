# evals/ — kiểm hành vi của chính template

Lưới canh trong `tests/guards/` kiểm **luật máy kiểm được**. Skill thì khác: một skill viết hay mà agent lờ đi vẫn qua mọi
lưới khuôn. `evals/skills/*.yaml` đo điều còn lại — **agent có làm đúng như skill dặn không** — bằng trạng thái cuối của một
repo tạm, không bằng lời agent kể. Ý tưởng chấm theo trạng thái cuối và kiểm chính bộ chấm: skill `eval-harness` (pack `ai-llm`)
và `obra/superpowers` (kiểm skill bằng kịch bản ép buộc).

## Hai chế độ

```bash
python scripts/skill_evals.py --check      # CI, miễn phí: bộ chấm đúng? oracle đạt, null trượt, mã kịch bản duy nhất
python scripts/skill_evals.py --list
python scripts/skill_evals.py --run --agent-cmd 'codex exec "$(cat {prompt_file})"' --repeat 5 --skill bug-fix   # TỐN TIỀN, chạy tay
```

`--check` chứng minh **bộ chấm** tin được: đáp án chuẩn (`oracle`) phải đạt mọi kiểm tra, đầu ra rỗng (null — agent không làm
gì) phải trượt ít nhất một. Grader dễ dãi cho null đạt; grader quá khắt cho oracle trượt; cả hai làm điểm vô nghĩa. Lưới
`tests/guards/test_skill_evals.py` còn thử các agent GIẢ làm sai kiểu hay gặp (tự duyệt kế hoạch, viết test xanh vô nghĩa,
lao vào viết mã khi chỉ được thẩm định) và đòi bộ chấm bắt được.

`--run` dựng repo tạm sạch cho MỖI lượt (kèm SKILL.md hiện hành của repo này), chạy lệnh agent trong đó, rồi chấm. `{prompt_file}`
là tệp lời nhắc nằm ngoài repo tạm (đường dẫn đã được quote). Lệnh agent chạy qua `bash -c`, nên `$(cat {prompt_file})` được bung ra thành nội dung lời nhắc (cần `bash`; Windows dùng Git Bash/WSL). Lượt agent lỗi/hết giờ ghi là `error`, **không** tính là trượt của skill.

## Khuôn một kịch bản

```yaml
skill: bug-fix            # phải là skill có thật trong .claude/skills/
version: 1                # đổi bộ chấm thì tăng — điểm trước/sau khi đổi không so được
scenarios:
  - id: bugfix-reproduce-first
    prompt: |             # đưa nguyên văn cho agent
    setup:
      copy: [".claude/skills/bug-fix/SKILL.md"]   # tệp THẬT của repo này đưa vào repo tạm
      files: {calc.py: "..."}                      # trạng thái đầu
    checks: [...]         # chấm trạng thái cuối
    oracle: {files: {...}}   # đáp án chuẩn dùng để kiểm bộ chấm
```

| Loại `kind` | Đạt khi |
|---|---|
| `file_exists` (`glob`) | có tệp khớp |
| `file_regex` (`glob`, `regex`, `negate`) | có tệp khớp regex (hoặc, với `negate`, KHÔNG tệp nào khớp) |
| `front_matter` (`glob`, `field`, `one_of`, `nonempty`) | front matter có `field` thuộc tập, và danh sách `nonempty` không rỗng |
| `unchanged` (`path`) | tệp giữ nguyên từng byte |
| `no_new_files_outside` (`prefixes`) | mọi tệp mới đều nằm dưới một tiền tố cho phép |
| `command` (`run`, `exit`) | lệnh trong repo tạm thoát đúng mã (`{python}` = Python đang chạy) |
| `new_tests_fail_on_original` (`restore`, `run`) | test của agent **ĐỎ** khi khôi phục các tệp mã về bản gốc — test xanh cả trên mã gốc không chứng minh gì |

## Đọc kết quả cho đúng

- Mỗi lượt là MỘT mẫu từ mô hình có nhiễu: 3–5 lượt chỉ thấy chênh lệch rất lớn (sàn nhiễu ~±45 điểm % ở n = 5). Báo `đạt/n`,
  không báo phần trăm tròn; đừng so hai lần chạy nhỏ để kết luận "skill mới tốt hơn".
- Đạt kịch bản **không** chứng minh skill có ích trong mọi tình huống — chỉ rằng với tình huống này agent đã làm theo.
- Muốn thấy skill có THAY ĐỔI hành vi: chạy cùng kịch bản với và không có SKILL.md trong `setup.copy`, so hai tỷ lệ.
- Lệnh agent chạy với quyền của chính CLI đó; repo tạm cô lập tệp nhưng không cô lập mạng/máy. Chỉ chạy công cụ bạn tin.
