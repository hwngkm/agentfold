"""Bản công khai không còn dấu vết dự án nguồn của các bài học hay thông tin cá nhân.

Vì sao: template được rút ra từ một dự án thật, và người dùng template không cần (và không nên thấy) tên dự án đó, miền nghiệp vụ
riêng của nó, đường dẫn máy cá nhân hay email. Bài học vẫn giữ, nhưng ở dạng trung tính ("đã gặp thật") — nêu cơ chế gây lỗi và
cách phòng, bỏ tên, ngày và con số truy ra nguồn.

Khoá gì: mọi tệp được git theo dõi KHÔNG chứa mẫu cấm bên dưới. Các mẫu được ghép từ mảnh để chính tệp này không tự khớp.
Sửa khi đỏ: viết lại câu đó theo hướng trung tính; ĐỪNG thêm tệp vào danh sách miễn.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SELF = "tests/tools/test_clean_public_tree.py"

FORBIDDEN = {
    "tên dự án nguồn": re.compile("V" + "Nutri" + "Care", re.IGNORECASE),
    "mã dự án nguồn": re.compile(r"\bV" + "M" + r"EC[-_ ]?\w*", re.IGNORECASE),
    "tên tổ chức nguồn": re.compile("Vin" + "mec", re.IGNORECASE),
    "miền nghiệp vụ nguồn": re.compile(
        "đái tháo|dinh dưỡng lâm sàng|thực đơn của bệnh nhân|Food" + "Matcher", re.IGNORECASE
    ),
    "đường dẫn máy cá nhân": re.compile(r"[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9_.-]+|/home/[a-z0-9_-]+/\.claude"),
    "email cá nhân": re.compile(r"[\w.+-]+@(gmail|outlook|hotmail|yahoo|icloud)\.[a-z]{2,}", re.IGNORECASE),
    "tên người": re.compile("Kim" + " Mạnh|hung" + "km"),
}


def _tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8")
    return [name for name in out.split("\0") if name and name != SELF]


def test_khong_tep_nao_con_dau_vet_du_an_nguon_hay_thong_tin_ca_nhan() -> None:
    files = _tracked_files()
    assert files, "không đọc được tệp nào — lưới rỗng nghĩa"
    hits: list[str] = []
    for name in files:
        path = ROOT / name
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # tệp nhị phân (ảnh, font)
        for label, pattern in FORBIDDEN.items():
            match = pattern.search(text)
            if match:
                hits.append(f"{name}: {label} ({match.group(0)!r})")
    assert hits == [], "còn dấu vết dự án nguồn / thông tin cá nhân:\n  " + "\n  ".join(hits[:20])
