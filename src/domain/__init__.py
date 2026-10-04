"""Lõi nghiệp vụ TẤT ĐỊNH: mọi con số người dùng thấy được tính ở đây, bằng code, có nguồn.

🔒 Tầng này không import SDK LLM, framework web, ORM hay thư viện mạng — lưới canh
`tests/guards/test_import_boundaries.py` đỏ nếu có. Lý do không phải thẩm mỹ: nếu một con số có
thể đi qua mô hình ngôn ngữ, không test nào chứng minh được nó đúng (nguyên tắc: "LLM chọn,
Python tính").
"""
