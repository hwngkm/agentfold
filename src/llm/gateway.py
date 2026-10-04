"""Giao diện gọi LLM bằng structured output — mô hình chỉ được trả đúng schema được đưa.

Adapter thật cho từng nhà cung cấp đặt cạnh file này (`src/llm/<nhà-cung-cấp>.py`), import SDK
bên trong hàm khởi tạo, và PHẢI gọi `assert_no_egress(prompt)` trước khi gửi.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from typing import Protocol, TypeVar

from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMGateway(Protocol):
    def select(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        """Trả một đối tượng đúng `schema`, hoặc ném lỗi — không bao giờ trả văn bản tự do."""
        ...


class LLMUnavailableError(RuntimeError):
    """Không có câu trả lời hợp lệ trong số lần thử cho phép."""


class ScriptedGateway:
    """Nhà cung cấp `offline`: trả lần lượt các câu trả lời định sẵn, không gọi mạng.

    Mỗi câu trả lời vẫn được kiểm lại qua `schema.model_validate` — đúng như với mô hình thật, để
    test không vô tình dựa vào một đối tượng mà mô hình thật không thể trả.
    """

    def __init__(self, responses: Iterable[BaseModel | dict[str, object]]) -> None:
        self._responses = deque(responses)
        self.prompts: list[str] = []

    def select(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        self.prompts.append(prompt)
        if not self._responses:
            raise LLMUnavailableError("ScriptedGateway đã hết câu trả lời định sẵn")
        response = self._responses.popleft()
        payload = response.model_dump() if isinstance(response, BaseModel) else response
        return schema.model_validate(payload)
