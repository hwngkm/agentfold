"""Cửa ngõ duy nhất tới mô hình ngôn ngữ. SDK của nhà cung cấp chỉ được import trong gói này.

Đổi nhà cung cấp (OpenAI ↔ Anthropic ↔ Gemini ↔ model cục bộ) chỉ chạm gói này; phần còn lại của hệ
thống thấy một giao diện `LLMGateway`. Import SDK trễ (trong hàm/adapter), để khởi động ứng dụng
không kéo theo thư viện nặng chỉ để trả `/health`.
"""
