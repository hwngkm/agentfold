"""Agent MẪU "LLM chọn — code tính": mô hình chọn mặt hàng + số lượng, lõi tất định tính tiền.

Schema trả về của mô hình (`LLMSelection`) CỐ Ý không có trường tiền/đơn giá/tổng. Kể cả khi
prompt injection thành công tuyệt đối, kẻ tấn công chỉ đổi được *chọn gì*, không đổi được *bao
nhiêu tiền* — và `compute_quote` từ chối mọi mã không có trong danh mục.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field

from src.domain.catalog.pricing import MAX_QUANTITY, CatalogItem, Quote, Selection, compute_quote
from src.llm.gateway import LLMGateway
from src.llm.safety import assert_no_egress, fence, scan_for_injection


class ItemChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1, max_length=64)
    quantity: int = Field(gt=0, le=MAX_QUANTITY)


class LLMSelection(BaseModel):
    """Thứ DUY NHẤT mô hình được sinh ra. `extra="forbid"`: trường lạ (vd. `total`) làm lời gọi hỏng."""

    model_config = ConfigDict(extra="forbid")

    items: list[ItemChoice] = Field(max_length=50)


def build_prompt(request_text: str, catalog: Mapping[str, CatalogItem]) -> str:
    choices = "\n".join(f"- {item.item_id}: {item.name} ({item.unit})" for item in catalog.values())
    return (
        "Chọn mặt hàng và số lượng phù hợp yêu cầu. Chỉ dùng mã trong danh mục. "
        "Không tính tiền — hệ thống tự tính.\n"
        f"Danh mục:\n{choices}\n"
        f"{fence('yêu cầu', request_text)}"
    )


def draft_quote(request_text: str, catalog: Mapping[str, CatalogItem], gateway: LLMGateway) -> Quote:
    scan_for_injection(request_text, source="quote_request")
    prompt = build_prompt(request_text, catalog)
    assert_no_egress(prompt)
    selection = gateway.select(prompt, LLMSelection)
    return compute_quote([Selection(choice.item_id, choice.quantity) for choice in selection.items], catalog)
