"""Lỗi của agentctl — thông điệp viết cho người và agent đọc, không phải stack trace."""

from __future__ import annotations


class AgentctlError(Exception):
    """Việc bị từ chối hoặc dữ liệu sai. CLI in thông điệp và thoát với `exit_code`."""

    exit_code = 1


class AgentctlEnvironmentError(AgentctlError):
    """Môi trường thiếu công cụ (git, PyYAML...).

    Tách mã thoát riêng (3) để hook cục bộ phân biệt được "môi trường hỏng" với "vi phạm phạm vi":
    hook chỉ cảnh báo ở ca đầu (CI vẫn chặn), nhưng chặn ở ca sau.
    """

    exit_code = 3
